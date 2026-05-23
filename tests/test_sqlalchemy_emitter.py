from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any

import pytest

from paramora import Query, QueryContract, query_field
from paramora.emitters.sqlalchemy import (
    SqlAlchemyEmitter,
    SqlAlchemyQuery,
    SqlModelEmitter,
)


@dataclass(frozen=True, slots=True)
class FakeExpression:
    text: str


@dataclass(frozen=True, slots=True)
class FakeColumn:  # noqa: PLW1641
    name: str

    def __eq__(self, other: object) -> Any:
        return FakeExpression(f"{self.name} = {other!r}")

    def __ne__(self, other: object) -> Any:
        return FakeExpression(f"{self.name} != {other!r}")

    def __gt__(self, other: object) -> FakeExpression:
        return FakeExpression(f"{self.name} > {other!r}")

    def __ge__(self, other: object) -> FakeExpression:
        return FakeExpression(f"{self.name} >= {other!r}")

    def __lt__(self, other: object) -> FakeExpression:
        return FakeExpression(f"{self.name} < {other!r}")

    def __le__(self, other: object) -> FakeExpression:
        return FakeExpression(f"{self.name} <= {other!r}")

    def in_(self, values: object) -> FakeExpression:
        return FakeExpression(f"{self.name} IN {values!r}")

    def not_in(self, values: object) -> FakeExpression:
        return FakeExpression(f"{self.name} NOT IN {values!r}")

    def asc(self) -> FakeExpression:
        return FakeExpression(f"{self.name} ASC")

    def desc(self) -> FakeExpression:
        return FakeExpression(f"{self.name} DESC")


@dataclass(frozen=True, slots=True)
class FakeTable:
    c: dict[str, FakeColumn]


@dataclass(frozen=True, slots=True)
class FakeStatement:
    where_clauses: tuple[FakeExpression, ...] = ()
    order_by_clauses: tuple[FakeExpression, ...] = ()
    limit_value: int | None = None
    offset_value: int | None = None

    def where(self, clause: FakeExpression) -> FakeStatement:
        return FakeStatement(
            where_clauses=(*self.where_clauses, clause),
            order_by_clauses=self.order_by_clauses,
            limit_value=self.limit_value,
            offset_value=self.offset_value,
        )

    def order_by(self, *clauses: FakeExpression) -> FakeStatement:
        return FakeStatement(
            where_clauses=self.where_clauses,
            order_by_clauses=(*self.order_by_clauses, *clauses),
            limit_value=self.limit_value,
            offset_value=self.offset_value,
        )

    def limit(self, value: int) -> FakeStatement:
        return FakeStatement(
            where_clauses=self.where_clauses,
            order_by_clauses=self.order_by_clauses,
            limit_value=value,
            offset_value=self.offset_value,
        )

    def offset(self, value: int) -> FakeStatement:
        return FakeStatement(
            where_clauses=self.where_clauses,
            order_by_clauses=self.order_by_clauses,
            limit_value=self.limit_value,
            offset_value=value,
        )


class FakeModel:
    status = FakeColumn("status")
    price = FakeColumn("price")
    created_at = FakeColumn("created_at")


class SqlAlchemyItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "ne", "in", "nin")]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True),
    ]


def fake_table() -> FakeTable:
    return FakeTable(
        c={
            "status": FakeColumn("status"),
            "price": FakeColumn("price"),
            "created_at": FakeColumn("created_at"),
        }
    )


def test_sqlalchemy_emitter_builds_expressions_from_table_columns() -> None:
    # Arrange
    query: Query[SqlAlchemyQuery] = Query(
        SqlAlchemyItemQuery,
        emitter=SqlAlchemyEmitter.from_table(fake_table()),
    )

    # Act
    compiled = query.parse(
        {"status__in": "free,busy", "price__gte": "10", "sort": "-created_at"}
    )

    # Assert
    assert compiled.output.where == (
        FakeExpression("status IN ('free', 'busy')"),
        FakeExpression("price >= 10.0"),
    )
    assert compiled.output.order_by == (FakeExpression("created_at DESC"),)


def test_sqlalchemy_query_applies_clauses_to_statement() -> None:
    # Arrange
    query: Query[SqlAlchemyQuery] = Query(
        SqlAlchemyItemQuery,
        emitter=SqlAlchemyEmitter.from_table(fake_table()),
        default_limit=20,
        max_limit=100,
    )
    output = query.parse(
        {"price__lt": "50", "sort": "created_at", "offset": "5"}
    ).output

    # Act
    statement = output.apply(FakeStatement())

    # Assert
    assert statement == FakeStatement(
        where_clauses=(FakeExpression("price < 50.0"),),
        order_by_clauses=(FakeExpression("created_at ASC"),),
        limit_value=20,
        offset_value=5,
    )


def test_sqlalchemy_emitter_can_resolve_model_attributes() -> None:
    # Arrange
    query: Query[SqlAlchemyQuery] = Query(
        SqlAlchemyItemQuery,
        emitter=SqlAlchemyEmitter.from_model(FakeModel),
    )

    # Act
    output = query.parse({"status__ne": "archived"}).output

    # Assert
    assert output.where == (FakeExpression("status != 'archived'"),)


def test_sqlmodel_emitter_uses_the_same_model_attribute_resolution() -> None:
    # Arrange
    query: Query[SqlAlchemyQuery] = Query(
        SqlAlchemyItemQuery,
        emitter=SqlModelEmitter.from_model(FakeModel),
    )

    # Act
    output = query.parse({"price__lte": "25"}).output

    # Assert
    assert output.where == (FakeExpression("price <= 25.0"),)


def test_sqlalchemy_emitter_can_use_explicit_column_mapping() -> None:
    # Arrange
    query: Query[SqlAlchemyQuery] = Query(
        SqlAlchemyItemQuery,
        emitter=SqlAlchemyEmitter.from_mapping({"price": FakeColumn("items.price")}),
    )

    # Act
    output = query.parse({"price__gt": "10"}).output

    # Assert
    assert output.where == (FakeExpression("items.price > 10.0"),)


def test_sqlalchemy_emitter_rejects_unknown_columns() -> None:
    # Arrange
    query: Query[SqlAlchemyQuery] = Query(
        SqlAlchemyItemQuery,
        emitter=SqlAlchemyEmitter.from_mapping({}),
    )

    # Act / Assert
    with pytest.raises(ValueError, match="Unknown SQLAlchemy column"):
        query.parse({"price__gt": "10"})


@pytest.mark.integration
@pytest.mark.sql
def test_sqlalchemy_emitter_can_compile_real_sqlalchemy_select_if_available() -> None:
    sqlalchemy: Any = pytest.importorskip("sqlalchemy")

    # Arrange
    items = sqlalchemy.Table(
        "items",
        sqlalchemy.MetaData(),
        sqlalchemy.Column("id", sqlalchemy.Integer),
        sqlalchemy.Column("status", sqlalchemy.String),
        sqlalchemy.Column("price", sqlalchemy.Float),
        sqlalchemy.Column("created_at", sqlalchemy.DateTime),
    )
    query: Query[SqlAlchemyQuery] = Query(
        SqlAlchemyItemQuery,
        emitter=SqlAlchemyEmitter.from_table(items),
    )

    # Act
    output = query.parse({"status": "free", "price__gte": "10"}).output
    statement: Any = output.apply(sqlalchemy.select(items))
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))

    # Assert
    assert "WHERE items.status = 'free' AND items.price >= 10.0" in compiled
    assert "LIMIT 50 OFFSET 0" in compiled

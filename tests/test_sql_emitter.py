from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

import pytest

from paramora import Query, QueryContract, SqlEmitter, SqlQuery, query_field

if TYPE_CHECKING:
    from paramora.emitters.sql import SqlParamStyle


class SqlItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "ne", "in", "nin")]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="items.created_at"),
    ]


class UnsafeAliasQuery(QueryContract):
    status: Annotated[str, query_field("eq", alias="items.status; DROP TABLE items")]


def test_sql_emitter_builds_parameterized_where_order_and_pagination() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        SqlItemQuery,
        default_limit=20,
        max_limit=100,
        emitter=SqlEmitter(),
    )
    params = {
        "status__in": "free,busy",
        "price__gte": "10",
        "sort": "-created_at",
        "limit": "5",
        "offset": "2",
    }

    # Act
    compiled = query.parse(params)

    # Assert
    assert compiled.output == SqlQuery(
        where='"status" IN (?, ?) AND "price" >= ?',
        params=("free", "busy", 10.0),
        order_by=('"items"."created_at" DESC',),
        limit=5,
        offset=2,
    )


@pytest.mark.parametrize(
    ("param_style", "expected_where"),
    [
        ("qmark", '"price" <= ?'),
        ("format", '"price" <= %s'),
        ("numeric", '"price" <= :1'),
        ("pyformat", '"price" <= %(p1)s'),
    ],
)
def test_sql_emitter_supports_placeholder_styles(
    param_style: SqlParamStyle,
    expected_where: str,
) -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        SqlItemQuery,
        emitter=SqlEmitter(param_style=param_style),
    )

    # Act
    compiled = query.parse({"price__lte": "20"})

    # Assert
    assert compiled.output.where == expected_where
    assert compiled.output.params == (20.0,)


def test_sql_emitter_numbers_numeric_placeholders_across_list_and_scalar_filters() -> (
    None
):
    # Arrange
    query: Query[SqlQuery] = Query(
        SqlItemQuery,
        emitter=SqlEmitter(param_style="numeric"),
    )

    # Act
    compiled = query.parse({"status__in": "free,busy", "price__gt": "10"})

    # Assert
    assert compiled.output.where == '"status" IN (:1, :2) AND "price" > :3'
    assert compiled.output.params == ("free", "busy", 10.0)


def test_sql_emitter_can_leave_identifiers_unquoted_for_callers_that_need_it() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        SqlItemQuery,
        emitter=SqlEmitter(quote_identifiers=False),
    )

    # Act
    compiled = query.parse({"price__gte": "10", "sort": "created_at"})

    # Assert
    assert compiled.output.where == "price >= ?"
    assert compiled.output.order_by == ("items.created_at ASC",)


def test_sql_emitter_builds_empty_where_clause_when_no_filters_are_provided() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(SqlItemQuery, emitter=SqlEmitter())

    # Act
    compiled = query.parse({})

    # Assert
    assert compiled.output.where == ""
    assert compiled.output.params == ()
    assert compiled.output.order_by == ()


def test_sql_emitter_rejects_unsafe_loose_identifier() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(emitter=SqlEmitter())

    # Act / Assert
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        query.parse({"unsafe-name": "value"})


def test_sql_emitter_rejects_unsafe_contract_alias() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(UnsafeAliasQuery, emitter=SqlEmitter())

    # Act / Assert
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        query.parse({"status": "free"})

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

import pytest

from paramora import (
    PostgresEmitter,
    Query,
    QueryContract,
    SqlEmitter,
    SqliteEmitter,
    SqlQuery,
    SqlStatement,
    query_field,
)

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
        emitter=SqliteEmitter(),
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
        param_style="qmark",
        quote_identifiers=True,
    )


@pytest.mark.parametrize(
    ("param_style", "expected_where", "expected_limit_offset"),
    [
        ("qmark", '"price" <= ?', "LIMIT ? OFFSET ?"),
        ("format", '"price" <= %s', "LIMIT %s OFFSET %s"),
        ("numeric", '"price" <= :1', "LIMIT :2 OFFSET :3"),
        ("dollar", '"price" <= $1', "LIMIT $2 OFFSET $3"),
    ],
)
def test_sql_emitter_supports_positional_placeholder_styles(
    param_style: SqlParamStyle,
    expected_where: str,
    expected_limit_offset: str,
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
    assert compiled.output.limit_offset_clause() == expected_limit_offset


def test_sqlite_emitter_uses_qmark_placeholders_by_default() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(SqlItemQuery, emitter=SqliteEmitter())

    # Act
    compiled = query.parse({"price__gte": "10"})

    # Assert
    assert compiled.output.where == '"price" >= ?'
    assert compiled.output.param_style == "qmark"


def test_postgres_emitter_uses_format_placeholders_by_default() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(SqlItemQuery, emitter=PostgresEmitter())

    # Act
    compiled = query.parse({"price__gte": "10", "sort": "-created_at"})

    # Assert
    assert compiled.output.where == '"price" >= %s'
    assert compiled.output.order_by == ('"items"."created_at" DESC',)
    assert compiled.output.param_style == "format"
    assert compiled.output.limit_offset_clause() == "LIMIT %s OFFSET %s"


def test_postgres_emitter_can_emit_dollar_placeholders() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        SqlItemQuery,
        emitter=PostgresEmitter(param_style="dollar"),
    )

    # Act
    compiled = query.parse({"status__in": "free,busy", "price__gt": "10"})

    # Assert
    assert compiled.output.where == '"status" IN ($1, $2) AND "price" > $3'
    assert compiled.output.params == ("free", "busy", 10.0)
    assert compiled.output.limit_offset_clause() == "LIMIT $4 OFFSET $5"


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
        emitter=SqliteEmitter(quote_identifiers=False),
    )

    # Act
    compiled = query.parse({"price__gte": "10", "sort": "created_at"})

    # Assert
    assert compiled.output.where == "price >= ?"
    assert compiled.output.order_by == ("items.created_at ASC",)


def test_sql_query_builds_safe_select_statement() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        SqlItemQuery,
        emitter=SqliteEmitter(),
        default_limit=20,
        max_limit=100,
    )

    # Act
    sql_query = query.parse({"status": "free", "limit": "2"}).output
    statement = sql_query.select_statement("items", columns=("id", "status"))

    # Assert
    assert statement == SqlStatement(
        sql='SELECT "id", "status" FROM "items" WHERE "status" = ? LIMIT ? OFFSET ?',
        params=("free", 2, 0),
    )


def test_sql_query_builds_postgres_select_statement_with_format_placeholders() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        SqlItemQuery,
        emitter=PostgresEmitter(),
        default_limit=20,
        max_limit=100,
    )

    # Act
    sql_query = query.parse({"status__ne": "archived", "limit": "2"}).output
    statement = sql_query.select_statement("items", columns=("id", "status"))

    # Assert
    assert statement == SqlStatement(
        sql='SELECT "id", "status" FROM "items" WHERE "status" <> %s LIMIT %s OFFSET %s',
        params=("archived", 2, 0),
    )


def test_sql_query_rejects_unsafe_select_table_identifier() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(SqlItemQuery, emitter=SqliteEmitter())
    sql_query = query.parse({"status": "free"}).output

    # Act / Assert
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        sql_query.select_statement("items; DROP TABLE items")


def test_sql_query_rejects_unsafe_select_column_identifier() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(SqlItemQuery, emitter=SqliteEmitter())
    sql_query = query.parse({"status": "free"}).output

    # Act / Assert
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        sql_query.select_statement("items", columns=("id; DROP TABLE items",))


def test_sql_query_allows_star_column_in_select_statement() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(SqlItemQuery, emitter=SqliteEmitter())
    sql_query = query.parse({"status": "free"}).output

    # Act
    statement = sql_query.select_statement("items")

    # Assert
    assert statement.sql == 'SELECT * FROM "items" WHERE "status" = ? LIMIT ? OFFSET ?'


def test_sql_emitter_builds_empty_where_clause_when_no_filters_are_provided() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(SqlItemQuery, emitter=SqliteEmitter())

    # Act
    compiled = query.parse({})

    # Assert
    assert compiled.output.where == ""
    assert compiled.output.where_clause() == ""
    assert compiled.output.params == ()
    assert compiled.output.order_by == ()
    assert compiled.output.order_by_clause() == ""


def test_sql_emitter_rejects_unsafe_loose_identifier() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(emitter=SqliteEmitter())

    # Act / Assert
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        query.parse({"unsafe-name": "value"})


def test_sql_emitter_rejects_unsafe_contract_alias() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(UnsafeAliasQuery, emitter=SqliteEmitter())

    # Act / Assert
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        query.parse({"status": "free"})

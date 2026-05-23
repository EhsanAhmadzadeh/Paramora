from __future__ import annotations

import os
from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Any

import pytest

from paramora import PostgresEmitter, Query, QueryContract, SqlQuery, query_field

if TYPE_CHECKING:
    from collections.abc import Iterator


class PostgresItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "ne", "in", "nin")]
    active: bool
    price: Annotated[float, query_field("eq", "gte", "lte", sortable=True)]
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="items.created_at"),
    ]


def test_postgres_emitter_builds_psycopg_compatible_sql_statement() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        PostgresItemQuery,
        emitter=PostgresEmitter(),
        default_limit=20,
        max_limit=100,
    )
    params = {
        "status__in": "free,busy",
        "price__gte": "10",
        "sort": "-created_at",
        "limit": "5",
        "offset": "2",
    }

    # Act
    sql_query = query.parse(params).output
    statement = sql_query.select_statement("items", columns=("id", "status", "price"))

    # Assert
    assert statement.sql == (
        'SELECT "id", "status", "price" FROM "items" '
        'WHERE "status" IN (%s, %s) AND "price" >= %s '
        'ORDER BY "items"."created_at" DESC LIMIT %s OFFSET %s'
    )
    assert statement.params == ("free", "busy", 10.0, 5, 2)


def test_postgres_emitter_can_build_dollar_placeholder_sql_statement() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        PostgresItemQuery,
        emitter=PostgresEmitter(param_style="dollar"),
        default_limit=20,
        max_limit=100,
    )

    # Act
    sql_query = query.parse({"active": "true", "price__lte": "20"}).output
    statement = sql_query.select_statement("items", columns=("id",))

    # Assert
    assert statement.sql == (
        'SELECT "id" FROM "items" '
        'WHERE "active" = $1 AND "price" <= $2 LIMIT $3 OFFSET $4'
    )
    assert statement.params == (True, 20.0, 20, 0)


def test_postgres_emitter_treats_injection_payload_as_bound_data() -> None:
    # Arrange
    query: Query[SqlQuery] = Query(PostgresItemQuery, emitter=PostgresEmitter())
    payload = "free' OR TRUE --"

    # Act
    sql_query = query.parse({"status": payload}).output
    statement = sql_query.select_statement("items", columns=("id",))

    # Assert
    assert "OR TRUE" not in statement.sql
    assert payload in statement.params


@pytest.fixture
def postgres_connection() -> Iterator[Any]:
    """Yield a psycopg connection when PARAMORA_POSTGRES_DSN is configured."""
    dsn = os.environ.get("PARAMORA_POSTGRES_DSN")
    if not dsn:
        pytest.skip("Set PARAMORA_POSTGRES_DSN to run PostgreSQL integration tests.")

    psycopg = pytest.importorskip("psycopg")
    connection: Any = psycopg.connect(dsn)
    try:
        yield connection
    finally:
        connection.close()


@pytest.mark.integration
@pytest.mark.postgres
def test_postgres_integration_executes_generated_psycopg_sql(
    postgres_connection: Any,
) -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        PostgresItemQuery,
        emitter=PostgresEmitter(),
        default_limit=20,
        max_limit=100,
    )
    with postgres_connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS paramora_items")
        cursor.execute(
            """
            CREATE TEMP TABLE paramora_items (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                active BOOLEAN NOT NULL,
                price DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
            """,
        )
        cursor.executemany(
            """
            INSERT INTO paramora_items (id, status, active, price, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                (1, "free", True, 10.0, "2026-01-01T00:00:00"),
                (2, "busy", True, 12.5, "2026-01-02T00:00:00"),
                (3, "archived", False, 7.5, "2026-01-03T00:00:00"),
            ],
        )

    # Act
    sql_query = query.parse({"status__in": "free,busy", "sort": "price"}).output
    statement = sql_query.select_statement("paramora_items", columns=("id",))
    with postgres_connection.cursor() as cursor:
        cursor.execute(statement.sql, statement.params)
        rows = cursor.fetchall()

    # Assert
    assert [row[0] for row in rows] == [1, 2]

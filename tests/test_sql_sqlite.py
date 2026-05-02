from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Annotated

import pytest

from paramora import Query, QueryContract, SqlEmitter, SqlQuery, query_field

if TYPE_CHECKING:
    from collections.abc import Iterator


class SqliteItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "ne", "in", "nin")]
    active: bool
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte", sortable=True)]
    created_at: Annotated[str, query_field("eq", "gte", "lte", sortable=True)]


@pytest.fixture
def sqlite_connection() -> Iterator[sqlite3.Connection]:
    """Return an in-memory SQLite database seeded with item documents."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            status TEXT NOT NULL,
            active INTEGER NOT NULL,
            price REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
    )
    connection.executemany(
        """
        INSERT INTO items (id, status, active, price, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, "free", 1, 10.0, "2026-01-01T00:00:00"),
            (2, "busy", 1, 12.5, "2026-01-02T00:00:00"),
            (3, "archived", 0, 7.5, "2026-01-03T00:00:00"),
            (4, "free", 0, 25.0, "2026-01-04T00:00:00"),
            (5, "busy", 1, 30.0, "2026-01-05T00:00:00"),
        ],
    )
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def sqlite_query() -> Query[SqlQuery]:
    """Return a SQL-backed Paramora query dependency for SQLite tests."""
    return Query(
        SqliteItemQuery,
        default_limit=20,
        max_limit=100,
        emitter=SqlEmitter(),
    )


def fetch_item_ids(connection: sqlite3.Connection, sql_query: SqlQuery) -> list[int]:
    """Execute emitted SQL fragments against SQLite and return matching item IDs."""
    where_clause = f" WHERE {sql_query.where}" if sql_query.where else ""
    order_clause = (
        f" ORDER BY {', '.join(sql_query.order_by)}" if sql_query.order_by else ""
    )
    statement = f"SELECT id FROM items{where_clause}{order_clause} LIMIT ? OFFSET ?"
    cursor = connection.execute(
        statement,
        (*sql_query.params, sql_query.limit, sql_query.offset),
    )
    return [int(row["id"]) for row in cursor.fetchall()]


def test_sqlite_integration_executes_equality_filter(
    sqlite_connection: sqlite3.Connection,
    sqlite_query: Query[SqlQuery],
) -> None:
    # Arrange
    params = {"status": "free"}

    # Act
    sql_query = sqlite_query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)

    # Assert
    assert ids == [1, 4]


def test_sqlite_integration_executes_in_filter(
    sqlite_connection: sqlite3.Connection,
    sqlite_query: Query[SqlQuery],
) -> None:
    # Arrange
    params = {"status__in": "free,busy", "sort": "price"}

    # Act
    sql_query = sqlite_query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)

    # Assert
    assert ids == [1, 2, 4, 5]


def test_sqlite_integration_executes_nin_filter(
    sqlite_connection: sqlite3.Connection,
    sqlite_query: Query[SqlQuery],
) -> None:
    # Arrange
    params = {"status__nin": "free,busy"}

    # Act
    sql_query = sqlite_query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)

    # Assert
    assert ids == [3]


def test_sqlite_integration_executes_not_equal_filter(
    sqlite_connection: sqlite3.Connection,
    sqlite_query: Query[SqlQuery],
) -> None:
    # Arrange
    params = {"status__ne": "archived", "sort": "price"}

    # Act
    sql_query = sqlite_query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)

    # Assert
    assert ids == [1, 2, 4, 5]


def test_sqlite_integration_executes_numeric_range_filters(
    sqlite_connection: sqlite3.Connection,
    sqlite_query: Query[SqlQuery],
) -> None:
    # Arrange
    params = {"price__gte": "10", "price__lt": "30", "sort": "price"}

    # Act
    sql_query = sqlite_query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)

    # Assert
    assert ids == [1, 2, 4]


def test_sqlite_integration_executes_boolean_filter(
    sqlite_connection: sqlite3.Connection,
    sqlite_query: Query[SqlQuery],
) -> None:
    # Arrange
    params = {"active": "false", "sort": "price"}

    # Act
    sql_query = sqlite_query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)

    # Assert
    assert ids == [3, 4]


def test_sqlite_integration_applies_sort_limit_and_offset(
    sqlite_connection: sqlite3.Connection,
    sqlite_query: Query[SqlQuery],
) -> None:
    # Arrange
    params = {"sort": "-price", "limit": "2", "offset": "1"}

    # Act
    sql_query = sqlite_query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)

    # Assert
    assert ids == [4, 2]


def test_sqlite_integration_handles_combined_filters_sort_and_pagination(
    sqlite_connection: sqlite3.Connection,
    sqlite_query: Query[SqlQuery],
) -> None:
    # Arrange
    params = {
        "status__in": "free,busy",
        "active": "true",
        "price__gte": "10",
        "sort": "-created_at",
        "limit": "2",
    }

    # Act
    sql_query = sqlite_query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)

    # Assert
    assert ids == [5, 2]


def test_sqlite_integration_treats_injection_payload_as_data(
    sqlite_connection: sqlite3.Connection,
    sqlite_query: Query[SqlQuery],
) -> None:
    # Arrange
    params = {"status": "free' OR 1=1 --"}

    # Act
    sql_query = sqlite_query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)
    total_rows = sqlite_connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]

    # Assert
    assert ids == []
    assert total_rows == 5


def test_sqlite_integration_supports_loose_mode_for_safe_identifiers(
    sqlite_connection: sqlite3.Connection,
) -> None:
    # Arrange
    query: Query[SqlQuery] = Query(
        default_limit=20, max_limit=100, emitter=SqlEmitter()
    )
    params = {"status": "busy", "sort": "-price"}

    # Act
    sql_query = query.parse(params).output
    ids = fetch_item_ids(sqlite_connection, sql_query)

    # Assert
    assert ids == [5, 2]

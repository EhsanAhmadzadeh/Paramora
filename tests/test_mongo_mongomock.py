from __future__ import annotations

from datetime import datetime
from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from paramora import Query
    from paramora.emitters.mongo import MongoQuery

mongomock = cast("Any", import_module("mongomock"))


@pytest.fixture
def mongo_items_collection() -> Any:
    # Arrange
    client = mongomock.MongoClient()
    collection = client["paramora_test"]["items"]
    collection.insert_many(
        [
            {
                "_id": 1,
                "status": "free",
                "active": True,
                "created_at": datetime(2026, 1, 1, 9, 0),
                "price": 10.0,
            },
            {
                "_id": 2,
                "status": "busy",
                "active": True,
                "created_at": datetime(2026, 1, 2, 9, 0),
                "price": 20.0,
            },
            {
                "_id": 3,
                "status": "archived",
                "active": False,
                "created_at": datetime(2026, 1, 3, 9, 0),
                "price": 30.0,
            },
            {
                "_id": 4,
                "status": "free",
                "active": False,
                "created_at": datetime(2026, 1, 4, 9, 0),
                "price": 40.0,
            },
        ]
    )
    return collection


def run_mongo_query(collection: Any, mongo: MongoQuery) -> list[dict[str, Any]]:
    cursor = collection.find(mongo.filter)
    if mongo.sort:
        cursor = cursor.sort(mongo.sort)
    cursor = cursor.skip(mongo.offset).limit(mongo.limit)
    return list(cursor)


def test_compiled_equality_filter_returns_matching_documents_from_mongomock(
    make_item_query: Callable[..., Query], mongo_items_collection: Any
) -> None:
    # Arrange
    query = make_item_query()

    # Act
    mongo = query.parse({"status": "free"}).to_mongo()
    docs = run_mongo_query(mongo_items_collection, mongo)

    # Assert
    assert [doc["_id"] for doc in docs] == [1, 4]


def test_compiled_in_filter_returns_matching_documents_from_mongomock(
    make_item_query: Callable[..., Query], mongo_items_collection: Any
) -> None:
    # Arrange
    query = make_item_query()

    # Act
    mongo = query.parse({"status__in": "free,busy"}).to_mongo()
    docs = run_mongo_query(mongo_items_collection, mongo)

    # Assert
    assert [doc["_id"] for doc in docs] == [1, 2, 4]


def test_compiled_nin_filter_excludes_matching_documents_in_mongomock(
    make_item_query: Callable[..., Query], mongo_items_collection: Any
) -> None:
    # Arrange
    query = make_item_query()

    # Act
    mongo = query.parse({"status__nin": "archived"}).to_mongo()
    docs = run_mongo_query(mongo_items_collection, mongo)

    # Assert
    assert [doc["_id"] for doc in docs] == [1, 2, 4]


def test_compiled_boolean_filter_uses_coerced_boolean_in_mongomock(
    make_item_query: Callable[..., Query], mongo_items_collection: Any
) -> None:
    # Arrange
    query = make_item_query()

    # Act
    mongo = query.parse({"active": "false"}).to_mongo()
    docs = run_mongo_query(mongo_items_collection, mongo)

    # Assert
    assert [doc["_id"] for doc in docs] == [3, 4]


def test_compiled_numeric_range_filter_returns_matching_documents_from_mongomock(
    make_item_query: Callable[..., Query], mongo_items_collection: Any
) -> None:
    # Arrange
    query = make_item_query()

    # Act
    mongo = query.parse({"price__gte": "20", "price__lt": "40"}).to_mongo()
    docs = run_mongo_query(mongo_items_collection, mongo)

    # Assert
    assert [doc["_id"] for doc in docs] == [2, 3]


def test_compiled_datetime_range_filter_returns_matching_documents_from_mongomock(
    make_item_query: Callable[..., Query], mongo_items_collection: Any
) -> None:
    # Arrange
    query = make_item_query()
    params = {
        "created_at__gte": "2026-01-02T00:00:00",
        "created_at__lte": "2026-01-03T23:59:59",
    }

    # Act
    mongo = query.parse(params).to_mongo()
    docs = run_mongo_query(mongo_items_collection, mongo)

    # Assert
    assert [doc["_id"] for doc in docs] == [2, 3]


def test_compiled_sort_limit_and_offset_are_applied_by_mongomock(
    make_item_query: Callable[..., Query], mongo_items_collection: Any
) -> None:
    # Arrange
    query = make_item_query()

    # Act
    mongo = query.parse(
        {"sort": "-created_at", "limit": "2", "offset": "1"}
    ).to_mongo()
    docs = run_mongo_query(mongo_items_collection, mongo)

    # Assert
    assert [doc["_id"] for doc in docs] == [3, 2]


def test_compiled_combined_filters_sort_and_pagination_work_together_in_mongomock(
    make_item_query: Callable[..., Query], mongo_items_collection: Any
) -> None:
    # Arrange
    query = make_item_query()
    params = {
        "status__in": "free,busy",
        "active": "true",
        "sort": "-created_at",
        "limit": "1",
    }

    # Act
    mongo = query.parse(params).to_mongo()
    docs = run_mongo_query(mongo_items_collection, mongo)

    # Assert
    assert [doc["_id"] for doc in docs] == [2]

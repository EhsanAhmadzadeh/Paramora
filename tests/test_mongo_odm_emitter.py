from __future__ import annotations

from typing import Annotated

from paramora import MongoOdmEmitter, MongoOdmQuery, Query, QueryContract, query_field


class OdmItemQueryContract(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    created_at: Annotated[str, query_field("eq", sortable=True)]


def test_mongo_odm_emitter_wraps_mongo_query_for_odm_usage() -> None:
    # Arrange
    query: Query[MongoOdmQuery] = Query(
        OdmItemQueryContract,
        emitter=MongoOdmEmitter(),
    )

    # Act
    output = query.parse(
        {"status__in": "free,busy", "sort": "-created_at", "limit": "10"}
    ).output

    # Assert
    assert output.filter == {"status": {"$in": ["free", "busy"]}}
    assert output.sort == [("created_at", -1)]
    assert output.limit == 10
    assert output.offset == 0


def test_mongo_odm_query_exposes_common_sort_helpers() -> None:
    # Arrange
    query = MongoOdmQuery(
        filter={"status": "free"},
        sort=[("created_at", -1), ("status", 1)],
        limit=20,
        offset=5,
    )

    # Act / Assert
    assert query.beanie_sort() == ("-created_at", "status")
    assert query.mongoengine_order_by() == ("-created_at", "status")
    assert query.find_kwargs() == {
        "filter": {"status": "free"},
        "sort": [("created_at", -1), ("status", 1)],
        "limit": 20,
        "skip": 5,
    }

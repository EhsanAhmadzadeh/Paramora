from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Any, TypeVar, overload

import pytest

from paramora import MongoQuery, Query, QueryContract, query_field
from paramora.emitters.mongo import MongoEmitter

if TYPE_CHECKING:
    from paramora.emitters.base import QueryEmitter
    from paramora.query_modes import QueryMode

QueryOutputT = TypeVar("QueryOutputT")


class ItemQueryFactory:
    """Typed factory fixture for item query dependencies."""

    @overload
    def __call__(
        self,
        *,
        mode: QueryMode | None = None,
        emitter: None = None,
    ) -> Query[MongoQuery]: ...

    @overload
    def __call__(
        self,
        *,
        mode: QueryMode | None = None,
        emitter: QueryEmitter[QueryOutputT],
    ) -> Query[QueryOutputT]: ...

    def __call__(
        self,
        *,
        mode: QueryMode | None = None,
        emitter: QueryEmitter[Any] | None = None,
    ) -> Query[Any]:
        selected_emitter: QueryEmitter[Any] = (
            MongoEmitter() if emitter is None else emitter
        )
        return Query(
            ItemQueryContract,
            default_limit=20,
            max_limit=100,
            mode=mode,
            emitter=selected_emitter,
        )


class ItemQueryContract(QueryContract):
    """Canonical item query contract used by tests."""

    status: Annotated[str, query_field("eq", "in", "nin", "ne")]
    active: bool
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True),
    ]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]


@pytest.fixture
def item_contract() -> type[ItemQueryContract]:
    """Return the canonical item query contract used by tests."""
    return ItemQueryContract


@pytest.fixture
def make_item_query() -> ItemQueryFactory:
    """Return a typed factory for the canonical item query dependency."""
    return ItemQueryFactory()

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

import pytest

from paramora import Query, QueryContract, query_field

if TYPE_CHECKING:
    from collections.abc import Callable

    from paramora.query_modes import QueryMode


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
def make_item_query() -> Callable[..., Query]:
    """Return a factory for the canonical item query dependency used by tests."""

    def _make_item_query(*, mode: QueryMode | None = None) -> Query:
        return Query(
            ItemQueryContract,
            default_limit=20,
            max_limit=100,
            mode=mode,
        )

    return _make_item_query

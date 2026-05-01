"""Profile Paramora query parsing with cProfile.

This script is intentionally dependency-light. It gives maintainers a repeatable
starting point for investigating parser and emission bottlenecks before adding
more formal benchmark tooling.
"""

from __future__ import annotations

import cProfile
import pstats
from datetime import datetime  # noqa: TC003
from io import StringIO
from typing import Annotated

from paramora import Query, QueryContract, query_field


class ItemQuery(QueryContract):
    """Representative query contract for parser profiling."""

    status: Annotated[str, query_field("eq", "in", "nin", "ne")]
    active: bool
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]


QUERY = Query(ItemQuery, default_limit=20, max_limit=100)
PARAMS = {
    "status__in": "free,busy",
    "active": "true",
    "created_at__gte": "2026-01-01T00:00:00Z",
    "price__gte": "10",
    "price__lt": "50",
    "sort": "-created_at",
    "limit": "20",
}


def profile_parse(iterations: int = 50_000) -> None:
    """Run parser/emitter profiling for a representative query."""
    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(iterations):
        QUERY.parse(PARAMS).to_mongo()
    profiler.disable()

    output = StringIO()
    stats = pstats.Stats(profiler, stream=output).strip_dirs().sort_stats("cumtime")
    stats.print_stats(30)
    print(output.getvalue())


if __name__ == "__main__":
    profile_parse()

"""Shared benchmark fixtures for Paramora.

The benchmark scripts intentionally use realistic public APIs instead of private
shortcuts. This keeps measurements representative of what application code pays
when using Paramora in FastAPI routes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime  # noqa: TC003
from typing import Annotated, TypeAlias

from paramora import MongoQuery, Query, QueryContract, QueryValidationError, query_field
from paramora.emitters.mongo import MongoEmitter
from paramora.emitters.sql import SqlEmitter, SqlQuery

BenchmarkResult: TypeAlias = object
BenchmarkRunner: TypeAlias = Callable[[], BenchmarkResult]
QueryParams: TypeAlias = Mapping[str, str]


class ItemQuery(QueryContract):
    """Representative contract used by parser and emitter benchmarks."""

    status: Annotated[str, query_field("eq", "in", "nin", "ne")]
    active: bool
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]


STRICT_PARAMS: QueryParams = {
    "status__in": "free,busy",
    "active": "true",
    "created_at__gte": "2026-01-01T00:00:00Z",
    "price__gte": "10",
    "price__lt": "50",
    "sort": "-created_at",
    "limit": "20",
}

LOOSE_PARAMS: QueryParams = {
    "status__in": "free,busy",
    "active": "true",
    "score__gte": "10",
    "sort": "-created_at",
    "limit": "20",
}

INVALID_PARAMS: QueryParams = {
    "price": "not-a-float",
    "sort": "price",
    "limit": "20",
}

STRICT_MONGO_QUERY: Query[MongoQuery] = Query(
    ItemQuery,
    default_limit=20,
    max_limit=100,
    emitter=MongoEmitter(),
)
STRICT_SQL_QUERY: Query[SqlQuery] = Query(
    ItemQuery,
    default_limit=20,
    max_limit=100,
    emitter=SqlEmitter(),
)
LOOSE_MONGO_QUERY: Query[MongoQuery] = Query(
    default_limit=20,
    max_limit=100,
    emitter=MongoEmitter(),
)

STRICT_AST = STRICT_MONGO_QUERY.parse(STRICT_PARAMS).ast
MONGO_EMITTER = MongoEmitter()
SQL_EMITTER = SqlEmitter()


@dataclass(frozen=True, slots=True)
class BenchmarkScenario:
    """Named benchmark scenario.

    Args:
        name: Stable scenario name used by benchmark CLIs.
        description: Human-readable description for reports.
        runner: Zero-argument function that executes one operation.
    """

    name: str
    description: str
    runner: BenchmarkRunner


def run_strict_mongo_parse() -> MongoQuery:
    """Parse strict params and emit Mongo output."""
    return STRICT_MONGO_QUERY.parse(STRICT_PARAMS).output


def run_strict_sql_parse() -> SqlQuery:
    """Parse strict params and emit SQL output."""
    return STRICT_SQL_QUERY.parse(STRICT_PARAMS).output


def run_loose_mongo_parse() -> MongoQuery:
    """Parse loose params and emit Mongo output."""
    return LOOSE_MONGO_QUERY.parse(LOOSE_PARAMS).output


def run_invalid_strict_parse() -> list[dict[str, object]]:
    """Parse invalid strict params and return structured validation errors."""
    try:
        STRICT_MONGO_QUERY.parse(INVALID_PARAMS)
    except QueryValidationError as exc:
        return exc.to_list() # type: ignore
    raise RuntimeError("Invalid benchmark params unexpectedly parsed successfully.")


def run_mongo_emit_only() -> MongoQuery:
    """Emit Mongo output from a prebuilt AST."""
    return MONGO_EMITTER.emit(STRICT_AST, STRICT_MONGO_QUERY.compiled_contract)


def run_sql_emit_only() -> SqlQuery:
    """Emit SQL output from a prebuilt AST."""
    return SQL_EMITTER.emit(STRICT_AST, STRICT_SQL_QUERY.compiled_contract)


SCENARIOS: dict[str, BenchmarkScenario] = {
    "strict-mongo": BenchmarkScenario(
        name="strict-mongo",
        description="Strict contract parse plus Mongo emission.",
        runner=run_strict_mongo_parse,
    ),
    "strict-sql": BenchmarkScenario(
        name="strict-sql",
        description="Strict contract parse plus SQL emission.",
        runner=run_strict_sql_parse,
    ),
    "loose-mongo": BenchmarkScenario(
        name="loose-mongo",
        description="Loose-mode parse plus Mongo emission.",
        runner=run_loose_mongo_parse,
    ),
    "invalid-strict": BenchmarkScenario(
        name="invalid-strict",
        description="Strict-mode invalid query validation path.",
        runner=run_invalid_strict_parse,
    ),
    "emit-mongo": BenchmarkScenario(
        name="emit-mongo",
        description="Mongo emission from a prebuilt AST.",
        runner=run_mongo_emit_only,
    ),
    "emit-sql": BenchmarkScenario(
        name="emit-sql",
        description="SQL emission from a prebuilt AST.",
        runner=run_sql_emit_only,
    ),
}

DEFAULT_SCENARIO = "strict-mongo"

"""Backend-neutral query nodes used by Paramora emitters.

The classes in this module are the stable intermediate representation between
FastAPI query parameters and backend-specific query objects. Query parsing should
produce these nodes first; backend emitters should consume these nodes later.
This keeps Paramora from coupling request syntax directly to MongoDB or another
storage backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

type FilterOperator = Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "nin"]
type SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True, slots=True)
class FilterNode:
    """Represents one backend-neutral filter predicate.

    Args:
        field: Public query field name as declared in the schema.
        op: Normalized operator name.
        value: Coerced Python value for the predicate.
    """

    field: str
    op: FilterOperator
    value: Any


@dataclass(frozen=True, slots=True)
class SortNode:
    """Represents one backend-neutral sort instruction.

    Args:
        field: Public query field name as declared in the schema.
        direction: Sort direction, either ``"asc"`` or ``"desc"``.
    """

    field: str
    direction: SortDirection


@dataclass(frozen=True, slots=True)
class PaginationNode:
    """Represents limit and offset pagination.

    Args:
        limit: Maximum number of records to return.
        offset: Number of records to skip.
    """

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class QueryAst:
    """Backend-neutral query abstract syntax tree.

    Args:
        filters: Filter predicates.
        sort: Sort instructions in request order.
        pagination: Pagination settings.
    """

    filters: tuple[FilterNode, ...]
    sort: tuple[SortNode, ...]
    pagination: PaginationNode

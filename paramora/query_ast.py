"""Backend-neutral query nodes used by Paramora emitters.

The classes in this module form the small intermediate representation between
FastAPI query parameters and backend-specific query objects. Query parsing always
produces these nodes first. Backend emitters then consume the nodes to produce
MongoDB, SQL, or custom query objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

FilterOperator: TypeAlias = Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "nin"]
SortDirection: TypeAlias = Literal["asc", "desc"]


@dataclass(frozen=True, slots=True)
class FilterNode:
    """Represents one backend-neutral filter predicate.

    Args:
        field: Public query field name as declared in the contract.
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
        field: Public query field name as declared in the contract.
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

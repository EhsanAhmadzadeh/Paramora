"""Query contract field metadata for Paramora.

Paramora query contracts use regular Python annotations for value types and
``typing.Annotated`` metadata for Paramora-specific query behavior. This keeps
contracts friendly to static type checkers while still letting Paramora declare
allowed operators, sortability, backend aliases, and required filters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from .query_ast import FilterOperator

FieldType: TypeAlias = type | str

DEFAULT_OPERATORS: frozenset[FilterOperator] = frozenset({"eq"})
KNOWN_OPERATORS: frozenset[FilterOperator] = frozenset(
    {"eq", "ne", "gt", "gte", "lt", "lte", "in", "nin"}
)


@dataclass(frozen=True, slots=True)
class QueryFieldInfo:
    """Metadata attached to a ``QueryContract`` annotation.

    Args:
        operators: Operators allowed for this field. Defaults to equality only.
        sortable: Whether this field can be used by the ``sort`` parameter.
        alias: Backend field path. Defaults to the public field name.
        required: Whether at least one filter for this field must be present.
    """

    operators: frozenset[FilterOperator] = DEFAULT_OPERATORS
    sortable: bool = False
    alias: str | None = None
    required: bool = False


@dataclass(frozen=True, slots=True)
class QueryField:
    """Resolved field declaration used by the parser and emitters.

    Args:
        type_: Python type, enum type, or supported string type name.
        operators: Operators allowed for this field.
        sortable: Whether this field can be used by the ``sort`` parameter.
        alias: Backend field path. Defaults to the public field name.
        required: Whether at least one filter for this field must be present.
    """

    type_: FieldType
    operators: frozenset[FilterOperator] = DEFAULT_OPERATORS
    sortable: bool = False
    alias: str | None = None
    required: bool = False

    def backend_name(self, public_name: str) -> str:
        """Return the backend field name for a public field name."""
        return self.alias or public_name


def query_field(
    *operators: FilterOperator,
    sortable: bool = False,
    alias: str | None = None,
    required: bool = False,
) -> QueryFieldInfo:
    """Declare Paramora metadata for an annotated contract field.

    Passing operators as positional string literals gives editors better
    autocomplete than a nested ``allow=(...)`` sequence.

    Args:
        operators: Allowed query operators. Defaults to ``"eq"`` when omitted.
        sortable: Whether this field may be used in ``sort``.
        alias: Backend field name/path used by emitters.
        required: Whether the request must include this filter.

    Returns:
        Field metadata consumed by ``QueryContract`` inspection.

    Raises:
        ValueError: Raised when an unknown operator is declared.
    """
    allowed_operators = frozenset(operators or DEFAULT_OPERATORS)
    unknown = allowed_operators - KNOWN_OPERATORS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown operator(s): {names}.")
    return QueryFieldInfo(
        operators=allowed_operators,
        sortable=sortable,
        alias=alias,
        required=required,
    )


def resolve_query_field(
    type_: FieldType, info: QueryFieldInfo | None = None
) -> QueryField:
    """Resolve an annotation and optional metadata into a concrete field."""
    metadata = info or QueryFieldInfo()
    return QueryField(
        type_=type_,
        operators=metadata.operators,
        sortable=metadata.sortable,
        alias=metadata.alias,
        required=metadata.required,
    )

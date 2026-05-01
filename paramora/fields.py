"""Query contract field metadata for Paramora.

Paramora query contracts use regular Python annotations for value types and
``typing.Annotated`` metadata for Paramora-specific query behavior. This keeps
contracts friendly to static type checkers while still letting Paramora declare
allowed operators, sortability, backend aliases, and required filters.

Example:
    from typing import Annotated

    class ItemQuery(QueryContract):
        status: Annotated[str, query_field("eq", "in")]
        active: bool
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeIs

from .query_ast import FilterOperator

type FieldType = type | str

DEFAULT_OPERATORS: frozenset[FilterOperator] = frozenset({"eq"})
KNOWN_OPERATORS: frozenset[FilterOperator] = frozenset(
    {"eq", "ne", "gt", "gte", "lt", "lte", "in", "nin"}
)


def is_known_operator(value: str) -> TypeIs[FilterOperator]:
    """Return whether ``value`` is a supported Paramora filter operator.

    The ``TypeIs`` return type lets Pyright and other type checkers narrow a
    raw query-string suffix to ``FilterOperator`` after validation.
    """
    return value in KNOWN_OPERATORS


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
        """Return the backend field name for a public field name.

        Args:
            public_name: Public contract field name.

        Returns:
            The configured backend alias, otherwise ``public_name``.
        """
        return self.alias or public_name


def query_field(
    *operators: FilterOperator,
    sortable: bool = False,
    alias: str | None = None,
    required: bool = False,
) -> QueryFieldInfo:
    """Declare Paramora metadata for an annotated contract field.

    The Python type comes from the annotation, not from this function. Use this
    helper inside ``typing.Annotated`` so type checkers still see the field as
    its real Python type.

    Passing operators as positional string literals gives editors much better
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
    """Resolve an annotation and optional metadata into a concrete field.

    Args:
        type_: Python type, enum type, or supported string type name.
        info: Optional Paramora field metadata.

    Returns:
        A concrete query field declaration.
    """
    metadata = info or QueryFieldInfo()
    return QueryField(
        type_=type_,
        operators=metadata.operators,
        sortable=metadata.sortable,
        alias=metadata.alias,
        required=metadata.required,
    )

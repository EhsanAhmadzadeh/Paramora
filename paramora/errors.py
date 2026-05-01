"""Structured validation errors returned by Paramora.

Paramora exposes stable, JSON-compatible validation errors that intentionally
look familiar to FastAPI and Pydantic users. Error dictionaries are part of the
public API surface: new codes may be added, but existing codes should only change
with a documented compatibility note.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

from .query_ast import FilterOperator

type QueryErrorCode = Literal[
    "query.empty_list",
    "query.invalid_field",
    "query.invalid_operator",
    "query.invalid_sort_field",
    "query.limit_too_large",
    "query.operator_not_allowed",
    "query.raw_operator_not_allowed",
    "query.required",
    "query.sort_not_allowed",
    "query.type_error.bool",
    "query.type_error.datetime",
    "query.type_error.enum",
    "query.type_error.float",
    "query.type_error.int",
    "query.unknown_field",
    "query.unknown_operator",
    "query.unknown_sort_field",
    "query.value_error.non_negative",
]


class QueryErrorDict(TypedDict):
    """JSON-compatible validation error dictionary."""

    loc: list[str]
    msg: str
    type: str
    input: NotRequired[Any]


@dataclass(frozen=True, slots=True)
class QueryErrorDetail:
    """Structured validation error detail.

    Args:
        loc: Location path, usually ``("query", param_name)``.
        msg: Human-readable error message.
        error_type: Stable machine-readable error code.
        input: Original input value when useful.
    """

    loc: tuple[str, ...]
    msg: str
    error_type: QueryErrorCode | str
    input: Any | None = None

    def to_dict(self) -> QueryErrorDict:
        """Convert this error detail to a JSON-compatible dictionary.

        Returns:
            A dictionary shaped similarly to FastAPI/Pydantic validation errors.
        """
        data: QueryErrorDict = {
            "loc": list(self.loc),
            "msg": self.msg,
            "type": self.error_type,
        }
        if self.input is not None:
            data["input"] = self.input
        return data


class QueryValidationError(ValueError):
    """Raised when query parameters cannot be compiled safely.

    Args:
        errors: Structured query validation details.
    """

    def __init__(
        self, errors: list[QueryErrorDetail] | tuple[QueryErrorDetail, ...]
    ) -> None:
        self.errors = tuple(errors)
        super().__init__("Invalid query parameters.")

    def to_list(self) -> list[QueryErrorDict]:
        """Return JSON-compatible validation errors.

        Returns:
            A list of validation error dictionaries.
        """
        return [error.to_dict() for error in self.errors]


def query_error(
    param_name: str,
    msg: str,
    error_type: QueryErrorCode | str,
    input_value: Any | None = None,
) -> QueryErrorDetail:
    """Create a query-parameter-scoped validation error."""
    return QueryErrorDetail(("query", param_name), msg, error_type, input_value)


def type_error(param_name: str, type_name: str, input_value: Any) -> QueryErrorDetail:
    """Create a scalar type coercion error."""
    return query_error(
        param_name,
        f"Expected a {type_name}-compatible value.",
        f"query.type_error.{type_name}",
        input_value,
    )


def enum_type_error(
    param_name: str, allowed_names: list[str], input_value: Any
) -> QueryErrorDetail:
    """Create an enum coercion error."""
    return query_error(
        param_name,
        f"Expected one of: {', '.join(allowed_names)}.",
        "query.type_error.enum",
        input_value,
    )


def unknown_field(param_name: str, input_value: Any) -> QueryErrorDetail:
    """Create an unknown filter field error."""
    return query_error(
        param_name, "Unknown filter field.", "query.unknown_field", input_value
    )


def unknown_operator(
    param_name: str, operator: str, input_value: Any
) -> QueryErrorDetail:
    """Create an unknown filter operator error."""
    return query_error(
        param_name,
        f"Unknown operator '{operator}'.",
        "query.unknown_operator",
        input_value,
    )


def operator_not_allowed(
    param_name: str, field_name: str, operator: FilterOperator, input_value: Any
) -> QueryErrorDetail:
    """Create an operator-not-allowed error."""
    return query_error(
        param_name,
        f"Operator '{operator}' is not allowed for field '{field_name}'.",
        "query.operator_not_allowed",
        input_value,
    )


def empty_list(param_name: str, input_value: Any) -> QueryErrorDetail:
    """Create an empty list filter error."""
    return query_error(
        param_name,
        "Expected at least one comma-separated value.",
        "query.empty_list",
        input_value,
    )


def invalid_filter_field(param_name: str, input_value: Any) -> QueryErrorDetail:
    """Create an invalid filter field name error."""
    return query_error(
        param_name,
        "Filter field name cannot be empty.",
        "query.invalid_field",
        input_value,
    )


def invalid_filter_operator(param_name: str, input_value: Any) -> QueryErrorDetail:
    """Create an invalid filter operator error."""
    return query_error(
        param_name,
        "Filter operator cannot be empty.",
        "query.invalid_operator",
        input_value,
    )


def raw_operator_not_allowed(param_name: str, input_value: Any) -> QueryErrorDetail:
    """Create a raw backend-operator rejection error."""
    return query_error(
        param_name,
        "Raw backend operators are not allowed in query parameters.",
        "query.raw_operator_not_allowed",
        input_value,
    )


def required_field(param_name: str) -> QueryErrorDetail:
    """Create a missing required filter error."""
    return query_error(
        param_name,
        "Required filter field is missing.",
        "query.required",
    )


def unknown_sort_field(field_name: str, input_value: Any) -> QueryErrorDetail:
    """Create an unknown sort field error."""
    return query_error(
        "sort",
        f"Unknown sort field '{field_name}'.",
        "query.unknown_sort_field",
        input_value,
    )


def sort_not_allowed(field_name: str, input_value: Any) -> QueryErrorDetail:
    """Create a non-sortable field error."""
    return query_error(
        "sort",
        f"Field '{field_name}' is not sortable.",
        "query.sort_not_allowed",
        input_value,
    )


def invalid_sort_field(input_value: Any) -> QueryErrorDetail:
    """Create an invalid sort field name error."""
    return query_error(
        "sort",
        "Sort field name cannot be empty.",
        "query.invalid_sort_field",
        input_value,
    )


def non_negative_int_type(param_name: str, input_value: Any) -> QueryErrorDetail:
    """Create a non-negative integer type error."""
    return query_error(
        param_name,
        "Expected a non-negative integer.",
        "query.type_error.int",
        input_value,
    )


def non_negative_int_value(param_name: str, input_value: Any) -> QueryErrorDetail:
    """Create a non-negative integer value error."""
    return query_error(
        param_name,
        "Expected a non-negative integer.",
        "query.value_error.non_negative",
        input_value,
    )


def limit_too_large(max_limit: int, input_value: Any) -> QueryErrorDetail:
    """Create a maximum-limit violation error."""
    return query_error(
        "limit",
        f"Limit must be less than or equal to {max_limit}.",
        "query.limit_too_large",
        input_value,
    )

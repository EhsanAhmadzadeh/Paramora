"""Query-string parser for Paramora contracts.

This module turns normalized HTTP query parameters into the backend-neutral
``QueryAst``. It is intentionally backend-agnostic: no MongoDB operators or
backend query objects should be produced here.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .coercion import coerce_list, coerce_value
from .errors import (
    QueryErrorDetail,
    QueryValidationError,
    empty_list,
    invalid_filter_field,
    invalid_filter_operator,
    invalid_sort_field,
    limit_too_large,
    non_negative_int_type,
    non_negative_int_value,
    operator_not_allowed,
    raw_operator_not_allowed,
    required_field,
    sort_not_allowed,
    unknown_field,
    unknown_operator,
    unknown_sort_field,
)
from .fields import QueryField, is_known_operator
from .query_ast import (
    FilterNode,
    FilterOperator,
    PaginationNode,
    QueryAst,
    SortDirection,
    SortNode,
)

if TYPE_CHECKING:
    from .query_modes import QueryMode

RESERVED_PARAMS = {"sort", "limit", "offset"}
LIST_OPERATORS: frozenset[FilterOperator] = frozenset({"in", "nin"})


@dataclass(frozen=True, slots=True)
class _ParsedFilters:
    """Internal parser result for filter parameters."""

    nodes: list[FilterNode]
    errors: list[QueryErrorDetail]


def normalize_params(
    params: Mapping[str, str | Sequence[str]] | Iterable[tuple[str, str]],
) -> dict[str, str]:
    """Normalize query params to one string value per key.

    Repeated parameters currently use the last value. This is deliberately
    conservative for 0.1; repeated-parameter policy can become explicit in a
    future release.

    Args:
        params: Mapping from query names to strings or string sequences, or an
            iterable of repeated key-value pairs.

    Returns:
        A dictionary using the last value when a parameter is repeated.
    """
    normalized: dict[str, str] = {}
    items_iter = params.items() if isinstance(params, Mapping) else params # type: ignore
    for key, value in items_iter: # type: ignore
        if isinstance(value, str):
            normalized[str(key)] = value
        else:
            values = list(value) # type: ignore
            if values:
                normalized[str(key)] = str(values[-1])
    return normalized


class QueryParser:
    """Parses HTTP query parameters into a backend-neutral AST."""

    def parse(
        self,
        params: Mapping[str, str | Sequence[str]] | Iterable[tuple[str, str]],
        *,
        fields: Mapping[str, QueryField],
        default_limit: int,
        max_limit: int,
        mode: QueryMode,
    ) -> QueryAst:
        """Parse and validate query parameters.

        Args:
            params: Query parameter mapping or repeated key-value pairs.
            fields: Declared contract fields.
            default_limit: Limit used when the request omits ``limit``.
            max_limit: Maximum accepted limit.
            mode: Query validation mode.

        Returns:
            Backend-neutral query AST.

        Raises:
            QueryValidationError: Raised when one or more validation errors occur.
        """
        raw_params = normalize_params(params)
        parsed_filters = _parse_filters(raw_params, fields=fields, mode=mode)
        errors = parsed_filters.errors
        errors.extend(_required_field_errors(fields, parsed_filters.nodes))

        sort = parse_sort(
            raw_params.get("sort"), fields=fields, mode=mode, errors=errors
        )
        pagination = parse_pagination(
            raw_params, default_limit=default_limit, max_limit=max_limit, errors=errors
        )

        if errors:
            raise QueryValidationError(errors)
        return QueryAst(
            filters=tuple(parsed_filters.nodes),
            sort=tuple(sort),
            pagination=pagination,
        )


def split_filter_param(param_name: str) -> tuple[str, str]:
    """Split a Django-style filter parameter into field and operator.

    Args:
        param_name: Raw query parameter name.

    Returns:
        A ``(field, operator)`` pair. Bare fields default to ``eq``.
    """
    if "__" not in param_name:
        return param_name, "eq"
    field_name, op = param_name.rsplit("__", 1)
    return field_name, op


def parse_sort(
    raw_sort: str | None,
    *,
    fields: Mapping[str, QueryField],
    mode: QueryMode,
    errors: list[QueryErrorDetail],
) -> list[SortNode]:
    """Parse the ``sort`` query parameter."""
    if not raw_sort:
        return []

    nodes: list[SortNode] = []
    for token in _split_csv(raw_sort):
        direction: SortDirection = "desc" if token.startswith("-") else "asc"
        field_name = token[1:] if token.startswith("-") else token
        error = _sort_field_error(field_name, raw_sort, fields=fields, mode=mode)
        if error is not None:
            errors.append(error)
            continue
        nodes.append(SortNode(field=field_name, direction=direction))
    return nodes


def parse_pagination(
    raw_params: Mapping[str, str],
    *,
    default_limit: int,
    max_limit: int,
    errors: list[QueryErrorDetail],
) -> PaginationNode:
    """Parse ``limit`` and ``offset`` query parameters."""
    limit = _parse_non_negative_int(
        raw_params.get("limit"), "limit", default_limit, errors
    )
    offset = _parse_non_negative_int(raw_params.get("offset"), "offset", 0, errors)
    if limit > max_limit:
        errors.append(limit_too_large(max_limit, raw_params.get("limit")))
    return PaginationNode(limit=limit, offset=offset)


def _parse_filters(
    raw_params: Mapping[str, str],
    *,
    fields: Mapping[str, QueryField],
    mode: QueryMode,
) -> _ParsedFilters:
    nodes: list[FilterNode] = []
    errors: list[QueryErrorDetail] = []

    for param_name, raw_value in raw_params.items():
        if param_name in RESERVED_PARAMS:
            continue
        node, param_errors = _parse_filter_param(
            param_name, raw_value, fields=fields, mode=mode
        )
        errors.extend(param_errors)
        if node is not None:
            nodes.append(node)

    return _ParsedFilters(nodes=nodes, errors=errors)


def _parse_filter_param(
    param_name: str,
    raw_value: str,
    *,
    fields: Mapping[str, QueryField],
    mode: QueryMode,
) -> tuple[FilterNode | None, list[QueryErrorDetail]]:
    field_name, raw_operator = split_filter_param(param_name)
    shape_error = _filter_shape_error(field_name, raw_operator, param_name, raw_value)
    if shape_error is not None:
        return None, [shape_error]

    declaration = fields.get(field_name)
    declaration_error = _declaration_error(
        declaration, field_name, param_name, raw_value, mode=mode
    )
    if declaration_error is not None:
        return None, [declaration_error]

    operator, operator_error = _resolve_operator(
        raw_operator, declaration, field_name, param_name, raw_value
    )
    if operator_error is not None:
        return None, [operator_error]
    if operator is None:
        return None, []

    return _coerce_filter_node(field_name, operator, raw_value, param_name, declaration)


def _coerce_filter_node(
    field_name: str,
    operator: FilterOperator,
    raw_value: str,
    param_name: str,
    declaration: QueryField | None,
) -> tuple[FilterNode | None, list[QueryErrorDetail]]:
    type_ = declaration.type_ if declaration is not None else None
    if operator in LIST_OPERATORS:
        return _coerce_list_filter(field_name, operator, raw_value, param_name, type_)
    return _coerce_scalar_filter(field_name, operator, raw_value, param_name, type_)


def _coerce_list_filter(
    field_name: str,
    operator: FilterOperator,
    raw_value: str,
    param_name: str,
    type_: type | str | None,
) -> tuple[FilterNode | None, list[QueryErrorDetail]]:
    values, errors = coerce_list(type_, raw_value, param_name=param_name)
    if errors:
        return None, errors
    if not values:
        return None, [empty_list(param_name, raw_value)]
    return FilterNode(field=field_name, op=operator, value=values), []


def _coerce_scalar_filter(
    field_name: str,
    operator: FilterOperator,
    raw_value: str,
    param_name: str,
    type_: type | str | None,
) -> tuple[FilterNode | None, list[QueryErrorDetail]]:
    value, error = coerce_value(type_, raw_value, param_name=param_name)
    if error is not None:
        return None, [error]
    return FilterNode(field=field_name, op=operator, value=value), []


def _required_field_errors(
    fields: Mapping[str, QueryField], filters: list[FilterNode]
) -> list[QueryErrorDetail]:
    present_fields = {node.field for node in filters}
    return [
        required_field(public_name)
        for public_name, declaration in fields.items()
        if declaration.required and public_name not in present_fields
    ]


def _parse_non_negative_int(
    raw: str | None, name: str, default: int, errors: list[QueryErrorDetail]
) -> int:
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        errors.append(non_negative_int_type(name, raw))
        return default
    if value < 0:
        errors.append(non_negative_int_value(name, raw))
        return default
    return value


def _filter_shape_error(
    field_name: str, op: str, param_name: str, raw_value: str
) -> QueryErrorDetail | None:
    if not field_name:
        return invalid_filter_field(param_name, raw_value)
    if not op:
        return invalid_filter_operator(param_name, raw_value)
    if "$" in field_name or "$" in op:
        return raw_operator_not_allowed(param_name, raw_value)
    return None


def _declaration_error(
    declaration: QueryField | None,
    field_name: str,
    param_name: str,
    raw_value: str,
    *,
    mode: QueryMode,
) -> QueryErrorDetail | None:
    if declaration is None and mode == "strict":
        return unknown_field(param_name, raw_value)
    return None


def _resolve_operator(
    operator: str,
    declaration: QueryField | None,
    field_name: str,
    param_name: str,
    raw_value: str,
) -> tuple[FilterOperator | None, QueryErrorDetail | None]:
    if not is_known_operator(operator):
        return None, unknown_operator(param_name, operator, raw_value)
    if declaration is not None and operator not in declaration.operators:
        return None, operator_not_allowed(param_name, field_name, operator, raw_value)
    return operator, None


def _sort_field_error(
    field_name: str,
    raw_sort: str,
    *,
    fields: Mapping[str, QueryField],
    mode: QueryMode,
) -> QueryErrorDetail | None:
    if not field_name:
        return invalid_sort_field(raw_sort)
    if "$" in field_name:
        return raw_operator_not_allowed("sort", raw_sort)

    declaration = fields.get(field_name)
    if mode == "strict" and declaration is None:
        return unknown_sort_field(field_name, raw_sort)
    if declaration is not None and not declaration.sortable:
        return sort_not_allowed(field_name, raw_sort)
    return None


def _split_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]

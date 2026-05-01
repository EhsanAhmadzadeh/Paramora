"""Optimized query-string parser for Paramora contracts.

The parser consumes precompiled contract metadata so request-time parsing avoids
repeated type dispatch and repeated schema introspection.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, TypeIs

from .compiled import (
    STRING_LIST_COERCER,
    STRING_SCALAR_COERCER,
    CompiledContract,
    CompiledField,
)
from .errors import QueryErrorDetail, QueryValidationError
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

type ScalarCoercer = Callable[[str, str], tuple[Any, QueryErrorDetail | None]]
type ListCoercer = Callable[[str, str], tuple[list[Any], list[QueryErrorDetail]]]
type ResolvedCoercers = tuple[ScalarCoercer, ListCoercer]
type CoercerResolution = tuple[ResolvedCoercers | None, QueryErrorDetail | None]
type ParsedFilterResult = tuple[
    FilterNode | None,
    QueryErrorDetail | None,
    list[QueryErrorDetail] | None,
]

RESERVED_PARAMS = frozenset({"sort", "limit", "offset"})
KNOWN_OPERATORS: frozenset[FilterOperator] = frozenset(
    {"eq", "ne", "gt", "gte", "lt", "lte", "in", "nin"}
)
LIST_OPERATORS: frozenset[FilterOperator] = frozenset({"in", "nin"})

STRING_COERCERS: ResolvedCoercers = (
    STRING_SCALAR_COERCER,
    STRING_LIST_COERCER,
)


def normalize_params(
    params: Mapping[str, str | Sequence[str]] | Iterable[tuple[str, str]],
) -> dict[str, str]:
    """Normalize query params to one string value per key.

    Repeated parameters currently use the last value. This is deliberately
    conservative for 0.1; repeated-parameter policy can become explicit in a
    future release.
    """
    if _is_str_dict(params):
        return params

    normalized: dict[str, str] = {}

    if isinstance(params, Mapping):
        for key, value in params.items():
            if type(value) is str:
                normalized[str(key)] = value
            elif value:
                normalized[str(key)] = str(value[-1])
        return normalized

    for key, value in params:
        normalized[str(key)] = value

    return normalized


def _is_str_dict(value: object) -> TypeIs[dict[str, str]]:
    if type(value) is not dict:
        return False

    for key, item in value.items():
        if type(key) is not str or type(item) is not str:
            return False

    return True


class QueryParser:
    """Parses HTTP query parameters into a backend-neutral AST."""

    __slots__ = ("contract", "default_limit", "max_limit", "mode")

    def __init__(
        self,
        *,
        contract: CompiledContract,
        default_limit: int,
        max_limit: int,
        mode: QueryMode,
    ) -> None:
        self.contract = contract
        self.default_limit = default_limit
        self.max_limit = max_limit
        self.mode = mode

    def parse(
        self,
        params: Mapping[str, str | Sequence[str]] | Iterable[tuple[str, str]],
    ) -> QueryAst:
        """Parse and validate query parameters.

        Args:
            params: Query parameter mapping or repeated key-value pairs.

        Returns:
            Backend-neutral query AST.

        Raises:
            QueryValidationError: Raised when one or more validation errors occur.
        """
        raw_params = normalize_params(params)
        errors: list[QueryErrorDetail] = []
        filters: list[FilterNode] = []
        seen_fields: set[str] = set()

        self._parse_filters(raw_params, filters, seen_fields, errors)
        self._add_required_field_errors(seen_fields, errors)

        sort = parse_sort(
            raw_params.get("sort"),
            contract=self.contract,
            mode=self.mode,
            errors=errors,
        )
        pagination = parse_pagination(
            raw_params,
            default_limit=self.default_limit,
            max_limit=self.max_limit,
            errors=errors,
        )

        if errors:
            raise QueryValidationError(errors)

        return QueryAst(
            filters=tuple(filters),
            sort=tuple(sort),
            pagination=pagination,
        )

    def _parse_filters(
        self,
        raw_params: Mapping[str, str],
        filters: list[FilterNode],
        seen_fields: set[str],
        errors: list[QueryErrorDetail],
    ) -> None:
        fields_get = self.contract.fields.get
        strict = self.mode == "strict"

        filters_append = filters.append
        seen_add = seen_fields.add
        errors_append = errors.append
        errors_extend = errors.extend

        for param_name, raw_value in raw_params.items():
            if param_name in RESERVED_PARAMS:
                continue

            node, error, value_errors = _parse_filter_param(
                param_name=param_name,
                raw_value=raw_value,
                fields_get=fields_get,
                strict=strict,
            )

            if error is not None:
                errors_append(error)
                continue

            if value_errors is not None:
                errors_extend(value_errors)
                continue

            if node is not None:
                filters_append(node)
                seen_add(node.field)

    def _add_required_field_errors(
        self,
        seen_fields: set[str],
        errors: list[QueryErrorDetail],
    ) -> None:
        errors_append = errors.append

        for required_name in self.contract.required_fields:
            if required_name not in seen_fields:
                errors_append(_required_field(required_name))


def _parse_filter_param(
    *,
    param_name: str,
    raw_value: str,
    fields_get: Callable[[str], CompiledField | None],
    strict: bool,
) -> ParsedFilterResult:
    field_name, operator = split_filter_param(param_name)

    error = _filter_shape_error(field_name, operator, param_name, raw_value)
    if error is not None:
        return None, error, None

    coercers, error = _resolve_coercers(
        field_name=field_name,
        operator=operator,
        param_name=param_name,
        raw_value=raw_value,
        fields_get=fields_get,
        strict=strict,
    )
    if error is not None:
        return None, error, None

    if coercers is None or not _is_known_operator(operator):
        return None, _unknown_operator(param_name, operator, raw_value), None

    scalar_coercer, list_coercer = coercers

    match operator:
        case "in" | "nin":
            return _parse_list_filter(
                field_name=field_name,
                operator=operator,
                raw_value=raw_value,
                param_name=param_name,
                list_coercer=list_coercer,
            )
        case _:
            return _parse_scalar_filter(
                field_name=field_name,
                operator=operator,
                raw_value=raw_value,
                param_name=param_name,
                scalar_coercer=scalar_coercer,
            )


def _resolve_coercers(
    *,
    field_name: str,
    operator: str,
    param_name: str,
    raw_value: str,
    fields_get: Callable[[str], CompiledField | None],
    strict: bool,
) -> CoercerResolution:
    declaration = fields_get(field_name)

    match declaration:
        case None if strict:
            return None, _unknown_filter_field(param_name, raw_value)
        case None:
            return STRING_COERCERS, None
        case _:
            return _resolve_declared_coercers(
                declaration=declaration,
                field_name=field_name,
                operator=operator,
                param_name=param_name,
                raw_value=raw_value,
            )


def _resolve_declared_coercers(
    *,
    declaration: CompiledField,
    field_name: str,
    operator: str,
    param_name: str,
    raw_value: str,
) -> CoercerResolution:
    if not _is_known_operator(operator):
        return None, _unknown_operator(param_name, operator, raw_value)

    if operator not in declaration.operators:
        return (
            None,
            _operator_not_allowed(
                param_name,
                field_name,
                operator,
                raw_value,
            ),
        )

    return (
        declaration.scalar_coercer,
        declaration.list_coercer,
    ), None


def _parse_list_filter(
    *,
    field_name: str,
    operator: FilterOperator,
    raw_value: str,
    param_name: str,
    list_coercer: ListCoercer,
) -> ParsedFilterResult:
    values, value_errors = list_coercer(raw_value, param_name)

    if value_errors:
        return None, None, value_errors

    if not values:
        return None, _empty_list(param_name, raw_value), None

    return FilterNode(field=field_name, op=operator, value=values), None, None


def _parse_scalar_filter(
    *,
    field_name: str,
    operator: FilterOperator,
    raw_value: str,
    param_name: str,
    scalar_coercer: ScalarCoercer,
) -> ParsedFilterResult:
    value, error = scalar_coercer(raw_value, param_name)

    if error is not None:
        return None, error, None

    return FilterNode(field=field_name, op=operator, value=value), None, None


def split_filter_param(param_name: str) -> tuple[str, str]:
    """Split a Django-style filter parameter into field and operator."""
    field_name, separator, operator = param_name.rpartition("__")

    if not separator:
        return param_name, "eq"

    return field_name, operator


def parse_sort(
    raw_sort: str | None,
    *,
    contract: CompiledContract,
    mode: QueryMode,
    errors: list[QueryErrorDetail],
) -> list[SortNode]:
    """Parse the ``sort`` query parameter."""
    if not raw_sort:
        return []

    fields = contract.fields

    if "," not in raw_sort:
        token = raw_sort.strip()
        if not token:
            return []

        node = _parse_sort_token(token, raw_sort, fields, mode, errors)
        return [] if node is None else [node]

    nodes: list[SortNode] = []
    nodes_append = nodes.append

    for token in _split_csv(raw_sort):
        node = _parse_sort_token(token, raw_sort, fields, mode, errors)
        if node is not None:
            nodes_append(node)

    return nodes


def _parse_sort_token(
    token: str,
    raw_sort: str,
    fields: Mapping[str, CompiledField],
    mode: QueryMode,
    errors: list[QueryErrorDetail],
) -> SortNode | None:
    match token.startswith("-"):
        case True:
            direction: SortDirection = "desc"
            field_name = token[1:]
        case False:
            direction = "asc"
            field_name = token

    error = _sort_field_error(field_name, raw_sort, fields, mode)
    if error is not None:
        errors.append(error)
        return None

    return SortNode(field=field_name, direction=direction)


def parse_pagination(
    raw_params: Mapping[str, str],
    *,
    default_limit: int,
    max_limit: int,
    errors: list[QueryErrorDetail],
) -> PaginationNode:
    """Parse ``limit`` and ``offset`` query parameters."""
    limit = _parse_non_negative_int(
        raw_params.get("limit"),
        "limit",
        default_limit,
        errors,
    )
    offset = _parse_non_negative_int(
        raw_params.get("offset"),
        "offset",
        0,
        errors,
    )

    if limit > max_limit:
        errors.append(_limit_too_large(max_limit, raw_params.get("limit")))

    return PaginationNode(limit=limit, offset=offset)


def _parse_non_negative_int(
    raw: str | None,
    name: str,
    default: int,
    errors: list[QueryErrorDetail],
) -> int:
    match raw:
        case None | "":
            return default
        case _:
            pass

    try:
        value = int(raw)
    except ValueError:
        errors.append(_non_negative_int_error(name, "query.type_error.int", raw))
        return default

    if value < 0:
        errors.append(
            _non_negative_int_error(name, "query.value_error.non_negative", raw)
        )
        return default

    return value


def _filter_shape_error(
    field_name: str,
    operator: str,
    param_name: str,
    raw_value: str,
) -> QueryErrorDetail | None:
    match (bool(field_name), bool(operator), "$" in field_name or "$" in operator):
        case (False, _, _):
            return QueryErrorDetail(
                ("query", param_name),
                "Filter field name cannot be empty.",
                "query.invalid_field",
                raw_value,
            )
        case (_, False, _):
            return QueryErrorDetail(
                ("query", param_name),
                "Filter operator cannot be empty.",
                "query.invalid_operator",
                raw_value,
            )
        case (_, _, True):
            return QueryErrorDetail(
                ("query", param_name),
                "Raw backend operators are not allowed in query parameters.",
                "query.raw_operator_not_allowed",
                raw_value,
            )
        case _:
            return None


def _sort_field_error(
    field_name: str,
    raw_sort: str,
    fields: Mapping[str, CompiledField],
    mode: QueryMode,
) -> QueryErrorDetail | None:
    match (bool(field_name), "$" in field_name):
        case (False, _):
            return QueryErrorDetail(
                ("query", "sort"),
                "Sort field name cannot be empty.",
                "query.invalid_sort_field",
                raw_sort,
            )
        case (_, True):
            return QueryErrorDetail(
                ("query", "sort"),
                "Raw backend operators are not allowed in sort parameters.",
                "query.raw_operator_not_allowed",
                raw_sort,
            )
        case _:
            pass

    declaration = fields.get(field_name)

    match declaration:
        case None if mode == "strict":
            return _unknown_sort_field(field_name, raw_sort)
        case None:
            return None
        case _ if not declaration.sortable:
            return _sort_not_allowed(field_name, raw_sort)
        case _:
            return None


def _is_known_operator(operator: str) -> TypeIs[FilterOperator]:
    return operator in KNOWN_OPERATORS


def _split_csv(raw: str) -> list[str]:
    return [part for part in (item.strip() for item in raw.split(",")) if part]


def _unknown_filter_field(param_name: str, raw_value: str) -> QueryErrorDetail:
    return QueryErrorDetail(
        ("query", param_name),
        "Unknown filter field.",
        "query.unknown_field",
        raw_value,
    )


def _unknown_operator(
    param_name: str,
    operator: str,
    raw_value: str,
) -> QueryErrorDetail:
    return QueryErrorDetail(
        ("query", param_name),
        f"Unknown operator '{operator}'.",
        "query.unknown_operator",
        raw_value,
    )


def _operator_not_allowed(
    param_name: str,
    field_name: str,
    operator: FilterOperator,
    raw_value: str,
) -> QueryErrorDetail:
    return QueryErrorDetail(
        ("query", param_name),
        f"Operator '{operator}' is not allowed for field '{field_name}'.",
        "query.operator_not_allowed",
        raw_value,
    )


def _empty_list(param_name: str, raw_value: str) -> QueryErrorDetail:
    return QueryErrorDetail(
        ("query", param_name),
        "Expected at least one comma-separated value.",
        "query.empty_list",
        raw_value,
    )


def _required_field(required_name: str) -> QueryErrorDetail:
    return QueryErrorDetail(
        ("query", required_name),
        "Required filter field is missing.",
        "query.required",
    )


def _unknown_sort_field(field_name: str, raw_sort: str) -> QueryErrorDetail:
    return QueryErrorDetail(
        ("query", "sort"),
        f"Unknown sort field '{field_name}'.",
        "query.unknown_sort_field",
        raw_sort,
    )


def _sort_not_allowed(field_name: str, raw_sort: str) -> QueryErrorDetail:
    return QueryErrorDetail(
        ("query", "sort"),
        f"Field '{field_name}' is not sortable.",
        "query.sort_not_allowed",
        raw_sort,
    )


def _limit_too_large(max_limit: int, raw: str | None) -> QueryErrorDetail:
    return QueryErrorDetail(
        ("query", "limit"),
        f"Limit must be less than or equal to {max_limit}.",
        "query.limit_too_large",
        raw,
    )


def _non_negative_int_error(
    name: str,
    error_type: str,
    raw: str,
) -> QueryErrorDetail:
    return QueryErrorDetail(
        ("query", name),
        "Expected a non-negative integer.",
        error_type,
        raw,
    )

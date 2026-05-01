"""Compiled query contract metadata for Paramora's hot path."""

# The public contract API is intentionally ergonomic and type-checker friendly.
# This module turns those declarations into a compact runtime representation that
# can be reused for every request handled by a ``Query`` instance.


from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from .errors import QueryErrorDetail

if TYPE_CHECKING:
    from .fields import FieldType, QueryField
    from .query_ast import FilterOperator

TRUE_VALUES = {"true", "1", "yes", "on"}
FALSE_VALUES = {"false", "0", "no", "off"}

type ScalarCoercer = Callable[[str, str], tuple[Any | None, QueryErrorDetail | None]]
type ListCoercer = Callable[[str, str], tuple[list[Any], list[QueryErrorDetail]]]


@dataclass(frozen=True, slots=True)
class CompiledField:
    """Runtime field metadata used by the parser and emitters."""

    public_name: str
    backend_name: str
    type_: FieldType
    operators: frozenset[FilterOperator]
    sortable: bool
    required: bool
    scalar_coercer: ScalarCoercer
    list_coercer: ListCoercer


@dataclass(frozen=True, slots=True)
class CompiledContract:
    """Runtime contract metadata reused by a ``Query`` instance."""

    fields: Mapping[str, CompiledField]
    required_fields: tuple[str, ...]
    sortable_fields: frozenset[str]
    raw_fields: Mapping[str, QueryField]


def compile_contract(fields: Mapping[str, QueryField]) -> CompiledContract:
    """Compile public field declarations into hot-path metadata.

    Args:
        fields: Public query field declarations by public field name.

    Returns:
        Runtime metadata used by the parser and emitters.
    """
    compiled_fields: dict[str, CompiledField] = {}
    required_fields: list[str] = []
    sortable_fields: set[str] = set()

    for public_name, field in fields.items():
        scalar_coercer = make_scalar_coercer(field.type_)
        compiled = CompiledField(
            public_name=public_name,
            backend_name=field.backend_name(public_name),
            type_=field.type_,
            operators=field.operators,
            sortable=field.sortable,
            required=field.required,
            scalar_coercer=scalar_coercer,
            list_coercer=make_list_coercer(scalar_coercer),
        )
        compiled_fields[public_name] = compiled
        if field.required:
            required_fields.append(public_name)
        if field.sortable:
            sortable_fields.add(public_name)

    return CompiledContract(
        fields=compiled_fields,
        required_fields=tuple(required_fields),
        sortable_fields=frozenset(sortable_fields),
        raw_fields=fields,
    )


def make_list_coercer(scalar_coercer: ScalarCoercer) -> ListCoercer:
    """Create a comma-separated list coercer from a scalar coercer."""

    def coerce_list_value(
        raw: str, param_name: str
    ) -> tuple[list[Any], list[QueryErrorDetail]]:
        values: list[Any] = []
        errors: list[QueryErrorDetail] = []
        for part in raw.split(","):
            item = part.strip()
            if not item:
                continue
            value, error = scalar_coercer(item, param_name)
            if error is None:
                values.append(value)
            else:
                errors.append(error)
        return values, errors

    return coerce_list_value


def coerce_str(raw: str, _param_name: str) -> tuple[str, None]:
    """Return a string value unchanged.

    Args:
        raw: Raw query parameter value.
        _param_name: Unused parameter kept to match the scalar coercer protocol.

    Returns:
        The original string and no validation error.
    """
    return raw, None


def coerce_int(raw: str, param_name: str) -> tuple[int | None, QueryErrorDetail | None]:
    """Coerce a string into an integer."""
    try:
        return int(raw), None
    except ValueError:
        return None, _type_error(param_name, "int", raw)


def coerce_float(
    raw: str, param_name: str
) -> tuple[float | None, QueryErrorDetail | None]:
    """Coerce a string into a float."""
    try:
        return float(raw), None
    except ValueError:
        return None, _type_error(param_name, "float", raw)


def coerce_bool(
    raw: str, param_name: str
) -> tuple[bool | None, QueryErrorDetail | None]:
    """Coerce a string into a boolean."""
    lowered = raw.strip().lower()
    if lowered in TRUE_VALUES:
        return True, None
    if lowered in FALSE_VALUES:
        return False, None
    return None, _type_error(param_name, "bool", raw)


def coerce_datetime(
    raw: str, param_name: str
) -> tuple[datetime | None, QueryErrorDetail | None]:
    """Coerce an ISO-8601 string into ``datetime``."""
    try:
        normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        return datetime.fromisoformat(normalized), None
    except ValueError:
        return None, _type_error(param_name, "datetime", raw)


def make_enum_coercer(enum_type: type[Enum]) -> ScalarCoercer:
    """Create an enum coercer with precomputed value/name lookup."""
    lookup = {member.name: member for member in enum_type}
    lookup.update({str(member.value): member for member in enum_type})
    expected = ", ".join(member.name for member in enum_type)

    def coerce_enum(
        raw: str, param_name: str
    ) -> tuple[Enum | None, QueryErrorDetail | None]:
        value = lookup.get(raw)
        if value is not None:
            return value, None
        return None, QueryErrorDetail(
            loc=("query", param_name),
            msg=f"Expected one of: {expected}.",
            error_type="query.type_error.enum",
            input=raw,
        )

    return coerce_enum


def _type_error(param_name: str, type_name: str, raw: str) -> QueryErrorDetail:
    return QueryErrorDetail(
        loc=("query", param_name),
        msg=f"Expected a {type_name}-compatible value.",
        error_type=f"query.type_error.{type_name}",
        input=raw,
    )


STRING_SCALAR_COERCER: ScalarCoercer = coerce_str
STRING_LIST_COERCER: ListCoercer = make_list_coercer(STRING_SCALAR_COERCER)

SCALAR_COERCERS_BY_TYPE: dict[object, ScalarCoercer] = {
    str: coerce_str,
    "str": coerce_str,
    int: coerce_int,
    "int": coerce_int,
    float: coerce_float,
    "float": coerce_float,
    bool: coerce_bool,
    "bool": coerce_bool,
    datetime: coerce_datetime,
    "datetime": coerce_datetime,
}


def make_scalar_coercer(type_: FieldType) -> ScalarCoercer:
    """Create a scalar coercer for a declared field type."""
    coercer = SCALAR_COERCERS_BY_TYPE.get(type_)
    if coercer is not None:
        return coercer

    if isinstance(type_, type) and issubclass(type_, Enum):
        return make_enum_coercer(type_)

    return coerce_str

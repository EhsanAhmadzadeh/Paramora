"""Scalar value coercion for query parameter values.

The coercion layer converts trusted schema-declared fields into Python values.
Unknown fields in loose mode pass ``None`` as the target type and therefore keep
string values, except ``in`` and ``nin`` which split into lists of strings.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from .errors import QueryErrorDetail, enum_type_error, type_error

TRUE_VALUES = {"true", "1", "yes", "on"}
FALSE_VALUES = {"false", "0", "no", "off"}


def coerce_value(
    type_: type | str | None, raw: str, *, param_name: str
) -> tuple[Any | None, QueryErrorDetail | None]:
    """Coerce a raw query string to a Python value."""
    if type_ is None or type_ is str or type_ == "str":
        value: Any = raw
        error = None
    else:
        value, error = _coerce_typed_value(type_, raw, param_name)

    return value, error


def _coerce_typed_value(
    type_: type | str, raw: str, param_name: str
) -> tuple[Any | None, QueryErrorDetail | None]:
    if isinstance(type_, type) and issubclass(type_, Enum):
        return _coerce_enum(type_, raw, param_name)

    try:
        value = _coerce_known_type(type_, raw, param_name)
    except ValueError:
        type_name = _type_name(type_)
        return None, type_error(param_name, type_name, raw)
    return value, None


def _coerce_known_type(type_: type | str, raw: str, param_name: str) -> Any:
    if type_ is int or type_ == "int":
        return int(raw)

    if type_ is float or type_ == "float":
        return float(raw)

    if type_ is bool or type_ == "bool":
        return _coerce_bool(raw, param_name)

    if type_ is datetime or type_ == "datetime":
        normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        return datetime.fromisoformat(normalized)

    return raw


def _coerce_bool(raw: str, param_name: str) -> bool:
    lowered = raw.strip().lower()

    if lowered in TRUE_VALUES:
        return True

    if lowered in FALSE_VALUES:
        return False

    raise ValueError(f"Expected a boolean-compatible value for {param_name}")


def _type_name(type_: type | str) -> str:
    return type_ if isinstance(type_, str) else getattr(type_, "__name__", str(type_))


def coerce_list(
    type_: type | str | None, raw: str, *, param_name: str
) -> tuple[list[Any], list[QueryErrorDetail]]:
    """Coerce a comma-separated query string into a list of values.

    Args:
        type_: Target scalar element type.
        raw: Comma-separated query string.
        param_name: Query parameter name used in validation locations.

    Returns:
        A tuple of ``(values, errors)``.
    """
    values: list[Any] = []
    errors: list[QueryErrorDetail] = []
    for item in [part.strip() for part in raw.split(",") if part.strip() != ""]:
        value, error = coerce_value(type_, item, param_name=param_name)
        if error is not None:
            errors.append(error)
        else:
            values.append(value)
    return values, errors


def _coerce_enum(
    enum_type: type[Enum], raw: str, param_name: str
) -> tuple[Enum | None, QueryErrorDetail | None]:
    for member in enum_type:
        if raw == member.name or raw == str(member.value):
            return member, None
    return None, enum_type_error(
        param_name, [member.name for member in enum_type], raw
    )

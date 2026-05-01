"""Pydantic-like query contract declarations for Paramora.

A ``QueryContract`` class describes the typed query surface for one FastAPI
endpoint or a reusable group of endpoints. Paramora inspects class annotations
and ``typing.Annotated[..., query_field(...)]`` metadata to build resolved
``QueryField`` declarations.

Contract classes are declarative and are not meant to be instantiated by users.
Using ``Annotated`` rather than assigning metadata objects to annotated fields
keeps Pylance, Pyright, and other type checkers happy:

    class ItemQuery(QueryContract):
        created_at: Annotated[datetime, query_field("gte", "lte")]
"""

from __future__ import annotations

from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from .fields import FieldType, QueryField, QueryFieldInfo, resolve_query_field

if TYPE_CHECKING:
    from collections.abc import Mapping


class QueryContract:
    """Base class for typed Paramora query contracts.

    Subclass this class and add annotated fields. Bare annotations default to an
    equality-only filter. Use ``Annotated[T, query_field(...)]`` to add operator,
    sorting, alias, or required-field metadata.
    """

    __paramora_contract__: ClassVar[bool] = True


def contract_fields(contract: type[QueryContract]) -> Mapping[str, QueryField]:
    """Extract resolved field declarations from a contract class.

    Args:
        contract: ``QueryContract`` subclass to inspect.

    Returns:
        A mapping of public query field names to resolved declarations.

    Raises:
        ValueError: Raised when a contract field uses an unsupported default or
            contains more than one ``query_field(...)`` metadata object.
    """
    resolved: dict[str, QueryField] = {}

    for base in reversed(contract.__mro__):
        if base is QueryContract or not issubclass(base, QueryContract):
            continue

        hints = get_type_hints(base, include_extras=True)
        annotations = getattr(base, "__annotations__", {})

        for name in annotations:
            if name.startswith("_"):
                continue

            annotated_type = hints.get(name)
            if annotated_type is None or _is_class_var(annotated_type):
                continue

            if name in base.__dict__:
                msg = (
                    f"Query contract field '{name}' must not assign defaults. "
                    "Use Annotated[T, query_field(...)] metadata instead."
                )
                raise ValueError(msg)

            type_, info = _extract_annotation(annotated_type)
            resolved[name] = resolve_query_field(type_, info)

    return resolved


def _is_class_var(type_: Any) -> bool:
    return get_origin(type_) is ClassVar


def _extract_annotation(type_: Any) -> tuple[FieldType, QueryFieldInfo | None]:
    """Return the scalar field type and Paramora metadata from an annotation."""
    origin = get_origin(type_)
    if origin is Annotated:
        args = get_args(type_)
        base_type = args[0]
        metadata = [item for item in args[1:] if isinstance(item, QueryFieldInfo)]
        if len(metadata) > 1:
            raise ValueError("A contract field can contain only one query_field(...).")
        return _normalize_field_type(base_type), metadata[0] if metadata else None
    return _normalize_field_type(type_), None


def _normalize_field_type(type_: Any) -> FieldType:
    """Normalize supported annotations into Paramora field types."""
    origin = get_origin(type_)
    if origin is None:
        if isinstance(type_, type):
            return type_
        if isinstance(type_, str):
            return type_
        return str

    if origin in {Union, UnionType}:
        args = tuple(arg for arg in get_args(type_) if arg is not NoneType)
        if len(args) == 1:
            return _normalize_field_type(args[0])

    # Query filters are optional at the request level. Container annotations and
    # arbitrary unions are intentionally unsupported in 0.1; operators such as
    # ``in`` and ``nin`` provide list semantics at the query syntax layer.
    msg = f"Unsupported query contract annotation: {type_!r}."
    raise ValueError(msg)

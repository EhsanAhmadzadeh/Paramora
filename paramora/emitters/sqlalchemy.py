"""SQLAlchemy and SQLModel emitter support.

This module intentionally keeps SQLAlchemy as an optional integration. Paramora
builds typed query contracts and an AST without importing SQLAlchemy. The emitter
only relies on the small expression protocol that SQLAlchemy columns already
implement: comparison operators, ``in_()``, ``not_in()``, ``asc()``, and
``desc()``.

The same emitter works for SQLAlchemy Core tables, SQLAlchemy ORM models, and
SQLModel models because SQLModel is built on top of SQLAlchemy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias

from paramora.emitters.base import QueryEmitter

if TYPE_CHECKING:
    from collections.abc import Mapping

    from paramora.compiled import CompiledContract
    from paramora.query_ast import QueryAst

SqlAlchemyClause: TypeAlias = Any
SqlAlchemyStatement: TypeAlias = Any


SqlAlchemyColumn: TypeAlias = Any


@dataclass(frozen=True, slots=True)
class SqlAlchemyQuery:
    """Compiled SQLAlchemy-compatible query fragments.

    Args:
        where: SQLAlchemy boolean expressions for ``WHERE``.
        order_by: SQLAlchemy ordering expressions.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.

    The object does not execute anything and does not own a session. Applications
    apply it to a SQLAlchemy ``Select`` or ORM query object.
    """

    where: tuple[SqlAlchemyClause, ...]
    order_by: tuple[SqlAlchemyClause, ...]
    limit: int
    offset: int

    def apply(self, statement: SqlAlchemyStatement) -> SqlAlchemyStatement:
        """Apply generated filters, sorting, limit, and offset to a statement.

        The method is intentionally duck-typed so it works with SQLAlchemy Core
        ``Select`` objects and SQLModel ``select(...)`` statements.
        """
        for clause in self.where:
            statement = statement.where(clause)
        if self.order_by:
            statement = statement.order_by(*self.order_by)
        return statement.limit(self.limit).offset(self.offset)


class ColumnResolver(Protocol):
    """Resolves Paramora backend field names into column-like objects."""

    def resolve(self, field_name: str) -> SqlAlchemyColumn:
        """Return a column-like object for a backend field name."""
        ...


@dataclass(frozen=True, slots=True)
class MappingColumnResolver:
    """Resolve columns from a mapping by backend field name."""

    columns: Mapping[str, SqlAlchemyColumn]

    def resolve(self, field_name: str) -> SqlAlchemyColumn:
        """Return a column from ``columns`` or raise a clear error."""
        column = self.columns.get(_terminal_name(field_name))
        if column is None:
            msg = f"Unknown SQLAlchemy column for field {field_name!r}."
            raise ValueError(msg)
        return column


@dataclass(frozen=True, slots=True)
class AttributeColumnResolver:
    """Resolve columns from model/table attributes.

    This supports SQLAlchemy ORM models and SQLModel classes where fields are
    exposed as class attributes.
    """

    model: object

    def resolve(self, field_name: str) -> SqlAlchemyColumn:
        """Return a column-like attribute from the model."""
        attr_name = _terminal_name(field_name)
        column = getattr(self.model, attr_name, None)
        if column is None:
            msg = f"Unknown SQLAlchemy model attribute for field {field_name!r}."
            raise ValueError(msg)
        return column


@dataclass(frozen=True, slots=True)
class TableColumnResolver:
    """Resolve columns from a SQLAlchemy Core table-like object."""

    table: object

    def resolve(self, field_name: str) -> SqlAlchemyColumn:
        """Return a table column from ``table.c``."""
        columns = getattr(self.table, "c", None)
        if columns is None:
            msg = "Expected a SQLAlchemy Table-like object with a .c collection."
            raise ValueError(msg)
        attr_name = _terminal_name(field_name)
        try:
            return columns[attr_name]
        except KeyError as exc:
            msg = f"Unknown SQLAlchemy table column for field {field_name!r}."
            raise ValueError(msg) from exc


@dataclass(frozen=True, slots=True)
class SqlAlchemyEmitter(QueryEmitter[SqlAlchemyQuery]):
    """Emit SQLAlchemy/SQLModel-compatible query fragments.

    Args:
        resolver: Column resolver used to map Paramora backend field names to
            SQLAlchemy column objects.
    """

    resolver: ColumnResolver

    @classmethod
    def from_table(cls, table: object) -> SqlAlchemyEmitter:
        """Create an emitter for a SQLAlchemy Core ``Table`` object."""
        return cls(TableColumnResolver(table))

    @classmethod
    def from_model(cls, model: object) -> SqlAlchemyEmitter:
        """Create an emitter for a SQLAlchemy ORM or SQLModel model class."""
        return cls(AttributeColumnResolver(model))

    @classmethod
    def from_mapping(cls, columns: Mapping[str, SqlAlchemyColumn]) -> SqlAlchemyEmitter:
        """Create an emitter from an explicit field-to-column mapping."""
        return cls(MappingColumnResolver(columns))

    def emit(self, ast: QueryAst, contract: CompiledContract) -> SqlAlchemyQuery:
        """Emit SQLAlchemy-compatible expressions from an AST."""
        fields_get = contract.fields.get
        where: list[SqlAlchemyClause] = []
        order_by: list[SqlAlchemyClause] = []

        for node in ast.filters:
            field = fields_get(node.field)
            backend_name = field.backend_name if field is not None else node.field
            column = self.resolver.resolve(backend_name)
            where.append(_filter_expression(column, node.op, node.value))

        for node in ast.sort:
            field = fields_get(node.field)
            backend_name = field.backend_name if field is not None else node.field
            column = self.resolver.resolve(backend_name)
            order_by.append(column.asc() if node.direction == "asc" else column.desc())

        return SqlAlchemyQuery(
            where=tuple(where),
            order_by=tuple(order_by),
            limit=ast.pagination.limit,
            offset=ast.pagination.offset,
        )


@dataclass(frozen=True, slots=True)
class SqlModelEmitter(SqlAlchemyEmitter):
    """SQLModel-friendly alias for ``SqlAlchemyEmitter``.

    SQLModel models expose SQLAlchemy-compatible columns, so the behavior is the
    same. This class exists for discoverability in docs and type annotations.
    """

    @classmethod
    def from_model(cls, model: object) -> SqlModelEmitter:
        """Create an emitter for a SQLModel model class."""
        return cls(AttributeColumnResolver(model))


# TODO: Fix the PLR0911 error.
def _filter_expression(  # noqa: PLR0911
    column: SqlAlchemyColumn, operator: str, value: object
) -> SqlAlchemyClause:
    if operator == "eq":
        return column == value
    if operator == "ne":
        return column != value
    if operator == "gt":
        return column > value
    if operator == "gte":
        return column >= value
    if operator == "lt":
        return column < value
    if operator == "lte":
        return column <= value
    if operator == "in":
        return column.in_(_as_tuple(value))
    if operator == "nin":
        return column.not_in(_as_tuple(value))
    msg = f"Unsupported SQLAlchemy operator: {operator!r}."
    raise ValueError(msg)


def _terminal_name(field_name: str) -> str:
    return field_name.rsplit(".", 1)[-1]


def _as_tuple(value: object) -> tuple[object, ...]:
    if isinstance(value, tuple):
        return value  # type: ignore # TODO: Return type, "tuple[Unknown, ...]", is partially unknown
    if isinstance(value, list):
        return tuple(value)  # type: ignore # TODO: Return type, "tuple[Unknown, ...]", is partially unknown
    return (value,)

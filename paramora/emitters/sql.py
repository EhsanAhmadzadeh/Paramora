"""Parameterized SQL emitter for Paramora query AST objects.

This module provides an initial SQL backend that emits SQL fragments and a
separate parameter tuple. It does not depend on any database driver or ORM. The
output is intentionally small so applications can adapt it to DB-API, SQLAlchemy
Core, or another SQL layer.

Only identifiers generated from contract fields or validated loose-mode field
names are interpolated into SQL text. User values are always returned through
``params`` and should be passed to the database driver separately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from paramora.emitters.base import QueryEmitter

if TYPE_CHECKING:
    from paramora.compiled import CompiledContract
    from paramora.query_ast import QueryAst

SqlParamStyle: TypeAlias = Literal["qmark", "numeric", "format", "pyformat"]
SqlParams: TypeAlias = tuple[Any, ...]
SqlOrderBy: TypeAlias = tuple[str, ...]

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")

SQL_OPS: dict[str, str] = {
    "eq": "=",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}


@dataclass(frozen=True, slots=True)
class SqlQuery:
    """Compiled parameterized SQL query fragments.

    Args:
        where: SQL ``WHERE`` expression without the leading ``WHERE`` keyword.
        params: Values that correspond to placeholders inside ``where``.
        order_by: SQL ``ORDER BY`` expressions without the leading keyword.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.
    """

    where: str
    params: SqlParams
    order_by: SqlOrderBy
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class SqlEmitter(QueryEmitter[SqlQuery]):
    """Compiles Paramora AST into safe, parameterized SQL fragments.

    Args:
        param_style: Placeholder style. ``"qmark"`` emits ``?`` placeholders,
            which work with SQLite. ``"format"`` emits ``%s`` placeholders,
            commonly used by psycopg/mysql drivers. ``"numeric"`` emits
            ``:1``, ``:2`` ... placeholders. ``"pyformat"`` emits
            ``%(p1)s``, ``%(p2)s`` ... placeholders while still returning a
            positional tuple so callers can adapt the output as needed.
        quote_identifiers: Whether SQL identifiers should be double-quoted.
    """

    param_style: SqlParamStyle = "qmark"
    quote_identifiers: bool = True

    def emit(self, ast: QueryAst, contract: CompiledContract) -> SqlQuery:
        """Emit parameterized SQL fragments from an AST."""
        fields_get = contract.fields.get
        params: list[Any] = []
        where_parts: list[str] = []
        append_where = where_parts.append
        append_param = params.append

        for node in ast.filters:
            field = fields_get(node.field)
            column = field.backend_name if field is not None else node.field
            sql_column = self._quote_identifier(column)
            operator = node.op

            if operator in {"in", "nin"}:
                values = tuple(node.value)
                placeholders = [
                    self._placeholder(len(params) + index + 1)
                    for index in range(len(values))
                ]
                params.extend(values)
                sql_operator = "IN" if operator == "in" else "NOT IN"
                append_where(f"{sql_column} {sql_operator} ({', '.join(placeholders)})")
                continue

            append_param(node.value)
            placeholder = self._placeholder(len(params))
            append_where(f"{sql_column} {SQL_OPS[operator]} {placeholder}")

        order_by: list[str] = []
        append_order_by = order_by.append
        for node in ast.sort:
            field = fields_get(node.field)
            column = field.backend_name if field is not None else node.field
            direction = "ASC" if node.direction == "asc" else "DESC"
            append_order_by(f"{self._quote_identifier(column)} {direction}")

        return SqlQuery(
            where=" AND ".join(where_parts),
            params=tuple(params),
            order_by=tuple(order_by),
            limit=ast.pagination.limit,
            offset=ast.pagination.offset,
        )

    def _placeholder(self, index: int) -> str:
        if self.param_style == "qmark":
            return "?"
        if self.param_style == "numeric":
            return f":{index}"
        if self.param_style == "format":
            return "%s"
        return f"%(p{index})s"

    def _quote_identifier(self, identifier: str) -> str:
        if not _IDENTIFIER_RE.fullmatch(identifier):
            msg = f"Unsafe SQL identifier: {identifier!r}."
            raise ValueError(msg)
        if not self.quote_identifiers:
            return identifier
        return ".".join(f'"{part}"' for part in identifier.split("."))

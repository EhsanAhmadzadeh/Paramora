"""Raw SQL emitter for Paramora query AST objects.

The SQL backend emits parameterized SQL fragments and small statement helpers for
applications that use DB-API style drivers directly. It does not depend on an
ORM and it does not manage connections, transactions, table ownership,
authorization predicates, joins, or selected columns.

The security model is intentionally conservative:

* user values are always returned separately through ``params``;
* field and alias names are treated as SQL identifiers and validated before they
  are interpolated into SQL text;
* identifiers are double-quoted by default, which is valid for SQLite and
  PostgreSQL;
* raw SQL operators are not accepted from HTTP query parameters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from paramora.emitters.base import QueryEmitter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from paramora.compiled import CompiledContract
    from paramora.query_ast import QueryAst

SqlDialect: TypeAlias = Literal["generic", "sqlite", "postgres"]
SqlParamStyle: TypeAlias = Literal["qmark", "numeric", "format", "dollar"]
SqlParams: TypeAlias = tuple[Any, ...]
SqlOrderBy: TypeAlias = tuple[str, ...]

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_STAR_COLUMNS = frozenset({"*"})

SQL_OPS: dict[str, str] = {
    "eq": "=",
    "ne": "<>",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}

_DEFAULT_STYLE_BY_DIALECT: dict[SqlDialect, SqlParamStyle] = {
    "generic": "qmark",
    "sqlite": "qmark",
    "postgres": "format",
}


@dataclass(frozen=True, slots=True)
class SqlStatement:
    """Complete parameterized SQL statement.

    Args:
        sql: SQL text containing driver-compatible placeholders.
        params: Parameters to pass separately to the database driver.
    """

    sql: str
    params: SqlParams


@dataclass(frozen=True, slots=True)
class SqlQuery:
    """Compiled parameterized SQL query fragments.

    ``SqlQuery`` is intentionally a fragment object. Most production APIs need
    to add authorization predicates, joins, selected columns, tenant filters, or
    connection-specific behavior around Paramora's generated filters. The helper
    methods are safe conveniences for simple raw-SQL use cases.

    Args:
        where: SQL ``WHERE`` expression without the leading ``WHERE`` keyword.
        params: Values that correspond to placeholders inside ``where``.
        order_by: SQL ``ORDER BY`` expressions without the leading keyword.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.
        param_style: Placeholder style used by this query.
        quote_identifiers: Whether generated identifiers were double-quoted.
    """

    where: str
    params: SqlParams
    order_by: SqlOrderBy
    limit: int
    offset: int
    param_style: SqlParamStyle = "qmark"
    quote_identifiers: bool = True

    def where_clause(self) -> str:
        """Return a full ``WHERE`` clause, or an empty string."""
        return f"WHERE {self.where}" if self.where else ""

    def order_by_clause(self) -> str:
        """Return a full ``ORDER BY`` clause, or an empty string."""
        if not self.order_by:
            return ""
        return f"ORDER BY {', '.join(self.order_by)}"

    def limit_offset_clause(self) -> str:
        """Return a parameterized ``LIMIT`` / ``OFFSET`` clause."""
        next_index = len(self.params) + 1
        limit_placeholder = _placeholder(self.param_style, next_index)
        offset_placeholder = _placeholder(self.param_style, next_index + 1)
        return f"LIMIT {limit_placeholder} OFFSET {offset_placeholder}"

    def statement_params(self) -> SqlParams:
        """Return filter params followed by pagination params."""
        return (*self.params, self.limit, self.offset)

    def select_statement(
        self,
        table: str,
        *,
        columns: Sequence[str] = ("*",),
    ) -> SqlStatement:
        """Build a simple ``SELECT`` statement from generated fragments.

        This helper is meant for straightforward raw-SQL endpoints. Complex
        queries should compose ``where``, ``params``, ``order_by``, ``limit``,
        and ``offset`` explicitly in application code.

        Args:
            table: Safe table identifier, for example ``"items"``.
            columns: Safe selected column identifiers. ``"*"`` is allowed.

        Returns:
            A complete parameterized SQL statement and its parameters.

        Raises:
            ValueError: Raised when a table or column identifier is unsafe.
        """
        sql_columns = ", ".join(
            _quote_column(column, quote_identifiers=self.quote_identifiers)
            for column in columns
        )
        parts = [
            "SELECT",
            sql_columns,
            "FROM",
            _quote_identifier(table, quote_identifiers=self.quote_identifiers),
        ]

        where_clause = self.where_clause()
        if where_clause:
            parts.append(where_clause)

        order_by_clause = self.order_by_clause()
        if order_by_clause:
            parts.append(order_by_clause)

        parts.append(self.limit_offset_clause())
        return SqlStatement(sql=" ".join(parts), params=self.statement_params())


@dataclass(frozen=True, slots=True)
class SqlEmitter(QueryEmitter[SqlQuery]):
    """Compiles Paramora AST into safe, parameterized SQL fragments.

    Args:
        dialect: SQL dialect preset. ``"sqlite"`` defaults to ``qmark``
            placeholders. ``"postgres"`` defaults to ``format`` placeholders,
            suitable for psycopg-style drivers. ``"generic"`` defaults to
            ``qmark`` and is useful for tests or custom DB-API drivers.
        param_style: Optional placeholder style override. Use ``"qmark"`` for
            SQLite, ``"format"`` for psycopg, and ``"dollar"`` for drivers that
            expect PostgreSQL-style ``$1`` placeholders.
        quote_identifiers: Whether SQL identifiers should be double-quoted.
    """

    dialect: SqlDialect = "generic"
    param_style: SqlParamStyle | None = None
    quote_identifiers: bool = True

    def emit(self, ast: QueryAst, contract: CompiledContract) -> SqlQuery:
        """Emit parameterized SQL fragments from an AST."""
        resolved_style = self.resolved_param_style
        fields_get = contract.fields.get
        params: list[Any] = []
        where_parts: list[str] = []
        append_where = where_parts.append
        append_param = params.append

        for node in ast.filters:
            field = fields_get(node.field)
            column = field.backend_name if field is not None else node.field
            sql_column = _quote_identifier(
                column, quote_identifiers=self.quote_identifiers
            )
            operator = node.op

            if operator in {"in", "nin"}:
                values = tuple(node.value)
                placeholders = [
                    _placeholder(resolved_style, len(params) + index + 1)
                    for index in range(len(values))
                ]
                params.extend(values)
                sql_operator = "IN" if operator == "in" else "NOT IN"
                append_where(f"{sql_column} {sql_operator} ({', '.join(placeholders)})")
                continue

            append_param(node.value)
            placeholder = _placeholder(resolved_style, len(params))
            append_where(f"{sql_column} {SQL_OPS[operator]} {placeholder}")

        order_by: list[str] = []
        append_order_by = order_by.append
        for node in ast.sort:
            field = fields_get(node.field)
            column = field.backend_name if field is not None else node.field
            direction = "ASC" if node.direction == "asc" else "DESC"
            sql_column = _quote_identifier(
                column, quote_identifiers=self.quote_identifiers
            )
            append_order_by(f"{sql_column} {direction}")

        return SqlQuery(
            where=" AND ".join(where_parts),
            params=tuple(params),
            order_by=tuple(order_by),
            limit=ast.pagination.limit,
            offset=ast.pagination.offset,
            param_style=resolved_style,
            quote_identifiers=self.quote_identifiers,
        )

    @property
    def resolved_param_style(self) -> SqlParamStyle:
        """Return the configured or dialect-default placeholder style."""
        return self.param_style or _DEFAULT_STYLE_BY_DIALECT[self.dialect]


@dataclass(frozen=True, slots=True)
class SqliteEmitter(SqlEmitter):
    """SQLite raw-SQL emitter using ``?`` placeholders by default."""

    dialect: SqlDialect = "sqlite"


@dataclass(frozen=True, slots=True)
class PostgresEmitter(SqlEmitter):
    """PostgreSQL raw-SQL emitter using ``%s`` placeholders by default."""

    dialect: SqlDialect = "postgres"


def _placeholder(param_style: SqlParamStyle, index: int) -> str:
    if param_style == "qmark":
        return "?"
    if param_style == "numeric":
        return f":{index}"
    if param_style == "format":
        return "%s"
    return f"${index}"


def _quote_column(identifier: str, *, quote_identifiers: bool) -> str:
    if identifier in _STAR_COLUMNS:
        return identifier
    return _quote_identifier(identifier, quote_identifiers=quote_identifiers)


def _quote_identifier(identifier: str, *, quote_identifiers: bool) -> str:
    if not _IDENTIFIER_RE.fullmatch(identifier):
        msg = f"Unsafe SQL identifier: {identifier!r}."
        raise ValueError(msg)
    if not quote_identifiers:
        return identifier
    return ".".join(f'"{part}"' for part in identifier.split("."))

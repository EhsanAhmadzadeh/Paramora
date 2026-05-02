from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from paramora import Query, SqlEmitter, SqlQuery

if TYPE_CHECKING:
    from conftest import ItemQueryFactory
    from paramora.compiled import CompiledContract
    from paramora.query_ast import QueryAst


@dataclass(frozen=True, slots=True)
class DebugQuery:
    filter_count: int
    sortable_count: int
    limit: int


class DebugEmitter:
    def emit(self, ast: QueryAst, contract: CompiledContract) -> DebugQuery:
        return DebugQuery(
            filter_count=len(ast.filters),
            sortable_count=len(contract.sortable_fields),
            limit=ast.pagination.limit,
        )


def test_custom_generic_emitter_produces_typed_output() -> None:
    # Arrange
    query = Query(default_limit=25, emitter=DebugEmitter())

    # Act
    compiled = query.parse({"status": "free", "sort": "created_at"})

    # Assert
    assert compiled.output == DebugQuery(filter_count=1, sortable_count=0, limit=25)


def test_sql_emitter_compiles_parameterized_sql(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query: Query[SqlQuery] = make_item_query(emitter=SqlEmitter())
    params = {"price__gte": "10", "status__in": "free,busy", "sort": "-created_at"}

    # Act
    compiled = query.parse(params)

    # Assert
    assert compiled.output == SqlQuery(
        where='"price" >= ? AND "status" IN (?, ?)',
        params=(10.0, "free", "busy"),
        order_by=('"created_at" DESC',),
        limit=20,
        offset=0,
    )

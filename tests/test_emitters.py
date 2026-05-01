from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from paramora import Query

if TYPE_CHECKING:
    from collections.abc import Mapping

    from paramora.fields import QueryField
    from paramora.query_ast import QueryAst


@dataclass(frozen=True, slots=True)
class DebugQuery:
    filter_count: int
    sort_count: int
    limit: int


class DebugEmitter:
    def emit(self, ast: QueryAst, fields: Mapping[str, QueryField]) -> DebugQuery:  # noqa: ARG002
        return DebugQuery(
            filter_count=len(ast.filters),
            sort_count=len(ast.sort),
            limit=ast.pagination.limit,
        )


def test_custom_generic_emitter_can_compile_query_ast() -> None:
    # Arrange
    query = Query(default_limit=25)
    compiled = query.parse({"status": "free", "sort": "created_at"})
    emitter = DebugEmitter()

    # Act
    debug_query = compiled.to(emitter)

    # Assert
    assert debug_query == DebugQuery(filter_count=1, sort_count=1, limit=25)

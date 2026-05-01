"""Generic backend emitter protocol for Paramora.

Emitters compile the backend-neutral ``QueryAst`` into a backend-specific query
object. The generic protocol lets ``CompiledQuery.to(...)`` preserve the return
type of the selected backend emitter without tying core query parsing to MongoDB.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from paramora.fields import QueryField
    from paramora.query_ast import QueryAst


class QueryEmitter[QueryOutputT_co](Protocol):
    """Protocol implemented by backend emitters.

    Type Parameters:
        QueryOutputT_co: Backend-specific query object returned by the emitter.
    """

    def emit(self, ast: QueryAst, fields: Mapping[str, QueryField]) -> QueryOutputT_co:
        """Compile an AST into a backend-specific query object.

        Args:
            ast: Backend-neutral query AST.
            fields: Field declarations by public name.

        Returns:
            Backend-specific query object.
        """
        ...

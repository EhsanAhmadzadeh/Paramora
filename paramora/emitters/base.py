"""Backend emitter protocol for Paramora.

Emitters compile the backend-neutral ``QueryAst`` into a backend-specific query
object. They consume the precompiled contract metadata so request-time emission
can use aliases and backend names without repeating contract introspection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar

if TYPE_CHECKING:
    from paramora.compiled import CompiledContract
    from paramora.query_ast import QueryAst

QueryOutputT_co = TypeVar("QueryOutputT_co", covariant=True)


class QueryEmitter(Protocol[QueryOutputT_co]):
    """Protocol implemented by backend emitters.

    Type Parameters:
        QueryOutputT_co: Backend-specific query object returned by the emitter.
    """

    def emit(self, ast: QueryAst, contract: CompiledContract) -> QueryOutputT_co:
        """Compile an AST into a backend-specific query object.

        Args:
            ast: Backend-neutral query AST.
            contract: Precompiled query contract metadata.

        Returns:
            Backend-specific query object.
        """
        ...

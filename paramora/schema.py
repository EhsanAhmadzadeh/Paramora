"""FastAPI-native query dependency for Paramora.

``Query`` is the main public entry point. ``Query()`` creates a loose query
compiler with no declared contract. ``Query(MyContract)`` creates a strict query
compiler from a Pydantic-like ``QueryContract`` class. The object is callable and
is meant to be passed directly to ``fastapi.Depends``.
"""

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Self

from fastapi import HTTPException, Request

from .compiled import CompiledContract, compile_contract
from .contracts import QueryContract, contract_fields
from .emitters.base import QueryEmitter
from .emitters.mongo import MongoEmitter, MongoQuery
from .errors import QueryValidationError
from .fields import QueryField
from .query_ast import QueryAst
from .query_modes import QueryMode
from .query_parser import QueryParser

_MONGO_EMITTER = MongoEmitter()


@dataclass(frozen=True, slots=True)
class CompiledQuery:
    """Compiled query wrapper returned by ``Query``.

    Args:
        ast: Backend-neutral AST.
        fields: Field declarations used for alias resolution during emission.
        contract: Compiled hot-path contract metadata.
    """

    ast: QueryAst
    fields: Mapping[str, QueryField]
    contract: CompiledContract

    def to[QueryOutputT](self, emitter: QueryEmitter[QueryOutputT]) -> QueryOutputT:
        """Compile this query with a backend emitter.

        Args:
            emitter: Backend emitter that knows how to compile ``QueryAst``.

        Returns:
            Backend-specific query object produced by ``emitter``.
        """
        return emitter.emit(self.ast, self.fields)

    def to_mongo(self) -> MongoQuery:
        """Compile this query to a MongoDB query object.

        Returns:
            A MongoDB query object containing filter, sort, limit, and offset.
        """
        return _MONGO_EMITTER.emit_compiled(self.ast, self.contract)


class Query:
    """FastAPI dependency that compiles request query parameters.

    No contract means loose mode by default. A contract means strict mode by
    default. This keeps prototypes easy while making declared contracts safe.

    Args:
        contract: Optional ``QueryContract`` subclass.
        default_limit: Limit used when the request omits ``limit``.
        max_limit: Maximum accepted request limit.
        mode: Optional explicit validation mode override.
    """

    contract: type[QueryContract] | None
    fields: Mapping[str, QueryField]
    compiled_contract: CompiledContract
    default_limit: int
    max_limit: int
    mode: QueryMode
    _parser: QueryParser

    def __init__(
        self,
        contract: type[QueryContract] | None = None,
        *,
        default_limit: int = 50,
        max_limit: int = 100,
        mode: QueryMode | None = None,
    ) -> None:
        if default_limit < 0:
            raise ValueError("default_limit must be non-negative.")
        if max_limit < 0:
            raise ValueError("max_limit must be non-negative.")
        if default_limit > max_limit:
            raise ValueError("default_limit must be less than or equal to max_limit.")

        fields: Mapping[str, QueryField] = (
            contract_fields(contract) if contract is not None else {}
        )
        resolved_mode: QueryMode = mode or ("strict" if fields else "loose")
        if resolved_mode == "strict" and not fields:
            raise ValueError("Strict mode requires a QueryContract.")

        compiled_contract = compile_contract(fields)
        self.contract = contract
        self.fields = fields
        self.compiled_contract = compiled_contract
        self.default_limit = default_limit
        self.max_limit = max_limit
        self.mode = resolved_mode
        self._parser = QueryParser(
            contract=compiled_contract,
            default_limit=default_limit,
            max_limit=max_limit,
            mode=resolved_mode,
        )

    def __call__(self, request: Request) -> CompiledQuery:
        """Compile the current FastAPI request query parameters.

        Args:
            request: FastAPI request object injected by the dependency system.

        Returns:
            A compiled query wrapper.

        Raises:
            HTTPException: Raised with status code 422 when query validation fails.
        """
        try:
            return self.parse(request.query_params.multi_items())
        except QueryValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.to_list()) from exc

    def parse(
        self, params: Mapping[str, str | Sequence[str]] | Sequence[tuple[str, str]]
    ) -> CompiledQuery:
        """Parse query parameters into a compiled query.

        Args:
            params: Query parameter mapping or repeated key-value pairs.

        Returns:
            A compiled query wrapper.
        """
        ast = self._parser.parse(params)
        return CompiledQuery(
            ast=ast,
            fields=self.fields,
            contract=self.compiled_contract,
        )

    def with_mode(self, mode: QueryMode) -> Self:
        """Return a copy of this query compiler using another validation mode.

        Args:
            mode: New query mode.

        Returns:
            A query compiler copy.
        """
        return type(self)(
            self.contract,
            default_limit=self.default_limit,
            max_limit=self.max_limit,
            mode=mode,
        )

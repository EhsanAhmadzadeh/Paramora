"""FastAPI-native query dependency for Paramora.

``Query`` is the main public entry point. ``Query()`` creates a loose query
compiler with no declared contract. ``Query(MyContract)`` creates a strict query
compiler from a Pydantic-like ``QueryContract`` class. The object is callable and
is meant to be passed directly to ``fastapi.Depends``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from fastapi import HTTPException, Request

from .compiled import CompiledContract, compile_contract
from .contracts import QueryContract, contract_fields
from .emitters.mongo import MongoEmitter, MongoQuery
from .errors import QueryValidationError
from .query_parser import QueryParser

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .emitters.base import QueryEmitter
    from .fields import QueryField
    from .query_ast import QueryAst
    from .query_modes import QueryMode

QueryOutputT = TypeVar("QueryOutputT")

_DEFAULT_EMITTER: QueryEmitter[Any] = MongoEmitter()


@dataclass(frozen=True, slots=True)
class CompiledQuery(Generic[QueryOutputT]):
    """Compiled query wrapper returned by ``Query``.

    The wrapper preserves the backend-neutral AST and the backend-specific
    output. The output type is controlled by the emitter configured on the
    ``Query`` dependency.

    Args:
        ast: Backend-neutral AST.
        output: Backend-specific query object produced by the configured emitter.
    """

    ast: QueryAst
    output: QueryOutputT


class Query(Generic[QueryOutputT]):
    """FastAPI dependency that compiles request query parameters.

    No contract means loose mode by default. A contract means strict mode by
    default. The backend output is selected by the configured emitter. When no
    emitter is provided, Paramora emits ``MongoQuery`` objects.

    Args:
        contract: Optional ``QueryContract`` subclass.
        default_limit: Limit used when the request omits ``limit``.
        max_limit: Maximum accepted request limit.
        mode: Optional explicit validation mode override.
        emitter: Backend emitter used to produce ``CompiledQuery.output``.
    """

    contract: type[QueryContract] | None
    fields: Mapping[str, QueryField]
    compiled_contract: CompiledContract
    default_limit: int
    max_limit: int
    mode: QueryMode
    emitter: QueryEmitter[Any]
    _parser: QueryParser

    @overload
    def __init__(
        self: Query[MongoQuery],
        contract: type[QueryContract] | None = None,
        *,
        default_limit: int = 50,
        max_limit: int = 100,
        mode: QueryMode | None = None,
        emitter: None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        contract: type[QueryContract] | None = None,
        *,
        default_limit: int = 50,
        max_limit: int = 100,
        mode: QueryMode | None = None,
        emitter: QueryEmitter[QueryOutputT],
    ) -> None: ...

    def __init__(
        self,
        contract: type[QueryContract] | None = None,
        *,
        default_limit: int = 50,
        max_limit: int = 100,
        mode: QueryMode | None = None,
        emitter: QueryEmitter[QueryOutputT] | None = None,
    ) -> None:
        if default_limit < 0:
            raise ValueError("default_limit must be non-negative.")
        if max_limit < 0:
            raise ValueError("max_limit must be non-negative.")
        if default_limit > max_limit:
            raise ValueError("default_limit must be less than or equal to max_limit.")

        fields: Mapping[str, QueryField] = (
            {} if contract is None else contract_fields(contract)
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
        self.emitter = emitter if emitter is not None else _DEFAULT_EMITTER
        self._parser = QueryParser(
            contract=compiled_contract,
            default_limit=default_limit,
            max_limit=max_limit,
            mode=resolved_mode,
        )

    def __call__(self, request: Request) -> CompiledQuery[QueryOutputT]:
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
    ) -> CompiledQuery[QueryOutputT]:
        """Parse query parameters into a compiled query.

        Args:
            params: Query parameter mapping or repeated key-value pairs.

        Returns:
            A compiled query wrapper with backend-specific ``output``.
        """
        ast = self._parser.parse(params)
        return CompiledQuery(
            ast=ast,
            output=self.emitter.emit(ast, self.compiled_contract),
        )

    def with_mode(self, mode: QueryMode) -> Query[QueryOutputT]:
        """Return a copy of this query compiler using another validation mode."""
        return type(self)(
            self.contract,
            default_limit=self.default_limit,
            max_limit=self.max_limit,
            mode=mode,
            emitter=self.emitter,
        )

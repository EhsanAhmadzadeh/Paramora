"""Mongo ODM convenience emitter and adapter helpers.

Paramora's core MongoDB output is already compatible with PyMongo-style filters.
This module adds small convenience helpers for ODMs that accept Mongo-style
filter dictionaries but use different sort formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from paramora.emitters.base import QueryEmitter
from paramora.emitters.mongo import MongoEmitter, MongoQuery

if TYPE_CHECKING:
    from paramora.compiled import CompiledContract
    from paramora.query_ast import QueryAst

MongoOdmFilter: TypeAlias = dict[str, Any]
MongoOdmSort: TypeAlias = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MongoOdmQuery:
    """Mongo ODM-friendly query object.

    Args:
        filter: Mongo-style filter dictionary.
        sort: PyMongo-style sort pairs.
        limit: Maximum number of documents to return.
        offset: Number of documents to skip.
    """

    filter: MongoOdmFilter
    sort: list[tuple[str, int]]
    limit: int
    offset: int

    @classmethod
    def from_mongo(cls, query: MongoQuery) -> MongoOdmQuery:
        """Create an ODM query wrapper from a ``MongoQuery``."""
        return cls(
            filter=query.filter,
            sort=query.sort,
            limit=query.limit,
            offset=query.offset,
        )

    def beanie_sort(self) -> MongoOdmSort:
        """Return Beanie-style sort strings.

        Beanie accepts strings such as ``"created_at"`` and
        ``"-created_at"`` for ascending and descending order.
        """
        return tuple(
            _signed_sort_name(field, direction) for field, direction in self.sort
        )

    def mongoengine_order_by(self) -> MongoOdmSort:
        """Return MongoEngine-style ``order_by`` strings."""
        return self.beanie_sort()

    def find_kwargs(self) -> dict[str, object]:
        """Return common keyword arguments for ODM wrappers/helpers."""
        return {
            "filter": self.filter,
            "sort": self.sort,
            "limit": self.limit,
            "skip": self.offset,
        }


@dataclass(frozen=True, slots=True)
class MongoOdmEmitter(QueryEmitter[MongoOdmQuery]):
    """Emit Mongo ODM-friendly query adapters."""

    mongo_emitter: MongoEmitter = field(default_factory=MongoEmitter)

    def emit(self, ast: QueryAst, contract: CompiledContract) -> MongoOdmQuery:
        """Emit a Mongo ODM adapter from an AST."""
        return MongoOdmQuery.from_mongo(self.mongo_emitter.emit(ast, contract))


def _signed_sort_name(field: str, direction: int) -> str:
    return field if direction >= 0 else f"-{field}"

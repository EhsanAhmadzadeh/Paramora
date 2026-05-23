"""MongoDB emitter for Paramora query AST objects.

The emitter converts backend-neutral query nodes into a small PyMongo-compatible
container: ``filter``, ``sort``, ``limit``, and ``offset``. It never accepts raw
HTTP query parameters and never exposes raw Mongo operators through request
syntax.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias

from paramora.emitters.base import QueryEmitter

if TYPE_CHECKING:
    from paramora.compiled import CompiledContract
    from paramora.query_ast import QueryAst

MongoFilter: TypeAlias = dict[str, Any]
MongoSort: TypeAlias = list[tuple[str, int]]

MONGO_OPS: dict[str, str] = {
    "ne": "$ne",
    "gt": "$gt",
    "gte": "$gte",
    "lt": "$lt",
    "lte": "$lte",
    "in": "$in",
    "nin": "$nin",
}


@dataclass(frozen=True, slots=True)
class MongoQuery:
    """Compiled MongoDB query object.

    Args:
        filter: MongoDB filter dictionary.
        sort: PyMongo-compatible sort pairs.
        limit: Maximum number of documents to return.
        offset: Number of documents to skip.
    """

    filter: MongoFilter
    sort: MongoSort
    limit: int
    offset: int


class MongoEmitter(QueryEmitter[MongoQuery]):
    """Compiles Paramora AST into a MongoDB query object."""

    def emit(self, ast: QueryAst, contract: CompiledContract) -> MongoQuery:
        """Emit a MongoDB query using precompiled field metadata."""
        fields = contract.fields
        fields_get = fields.get
        filter_doc: MongoFilter = {}
        filter_get = filter_doc.get

        for node in ast.filters:
            field = fields_get(node.field)
            field_name = field.backend_name if field is not None else node.field
            operator = node.op
            value = node.value

            if operator == "eq":
                existing = filter_get(field_name)
                if isinstance(existing, dict):
                    existing["$eq"] = value
                else:
                    filter_doc[field_name] = value
                continue

            mongo_op = MONGO_OPS[operator]
            existing = filter_get(field_name)
            if existing is None:
                filter_doc[field_name] = {mongo_op: value}
            elif isinstance(existing, dict):
                existing[mongo_op] = value
            else:
                filter_doc[field_name] = {"$eq": existing, mongo_op: value}

        sort: MongoSort = []
        sort_append = sort.append
        for node in ast.sort:
            field = fields_get(node.field)
            field_name = field.backend_name if field is not None else node.field
            sort_append((field_name, 1 if node.direction == "asc" else -1))

        return MongoQuery(
            filter=filter_doc,
            sort=sort,
            limit=ast.pagination.limit,
            offset=ast.pagination.offset,
        )

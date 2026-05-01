"""MongoDB emitter for Paramora query AST objects.

The emitter converts backend-neutral query nodes into a small PyMongo-compatible
container: ``filter``, ``sort``, ``limit``, and ``offset``. It never accepts raw
HTTP query parameters and never exposes raw Mongo operators through request
syntax.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from paramora.emitters.base import QueryEmitter

if TYPE_CHECKING:
    from collections.abc import Mapping

    from paramora.fields import QueryField
    from paramora.query_ast import QueryAst

type MongoFilter = dict[str, Any]
type MongoSort = list[tuple[str, int]]

MONGO_OPS: Mapping[str, str] = {
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

    def emit(self, ast: QueryAst, fields: Mapping[str, QueryField]) -> MongoQuery:
        """Emit a MongoDB query from an AST.

        Args:
            ast: Backend-neutral query AST.
            fields: Schema fields by public name.

        Returns:
            A MongoDB query object.
        """
        filter_doc: MongoFilter = {}
        for node in ast.filters:
            field_name = (
                fields[node.field].backend_name(node.field)
                if node.field in fields
                else node.field
            )
            if node.op == "eq":
                existing = filter_doc.get(field_name)
                if isinstance(existing, dict):
                    existing["$eq"] = node.value
                else:
                    filter_doc[field_name] = node.value
                continue

            mongo_op = MONGO_OPS[node.op]
            existing = filter_doc.get(field_name)
            if existing is None:
                filter_doc[field_name] = {mongo_op: node.value}
            elif isinstance(existing, dict):
                existing[mongo_op] = node.value
            else:
                filter_doc[field_name] = {"$eq": existing, mongo_op: node.value}

        sort: MongoSort = []
        for node in ast.sort:
            field_name = (
                fields[node.field].backend_name(node.field)
                if node.field in fields
                else node.field
            )
            sort.append((field_name, 1 if node.direction == "asc" else -1))

        return MongoQuery(
            filter=filter_doc,
            sort=sort,
            limit=ast.pagination.limit,
            offset=ast.pagination.offset,
        )

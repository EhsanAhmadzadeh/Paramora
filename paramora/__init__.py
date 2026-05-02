"""Paramora public API.

Paramora is a FastAPI-native typed query compiler. Define a ``QueryContract``
class, pass it to ``Query``, and use the resulting object directly with
``fastapi.Depends``. Use ``Query()`` without a contract for loose-mode prototypes.
"""

from __future__ import annotations

from .contracts import QueryContract
from .emitters.mongo import MongoEmitter, MongoQuery
from .emitters.sql import SqlEmitter, SqlQuery
from .errors import QueryErrorDetail, QueryErrorDict, QueryValidationError
from .fields import QueryField, QueryFieldInfo, query_field
from .query_ast import FilterNode, PaginationNode, QueryAst, SortNode
from .schema import CompiledQuery, Query

__all__ = [
    "CompiledQuery",
    "FilterNode",
    "MongoEmitter",
    "MongoQuery",
    "PaginationNode",
    "Query",
    "QueryAst",
    "QueryContract",
    "QueryErrorDetail",
    "QueryErrorDict",
    "QueryField",
    "QueryFieldInfo",
    "QueryValidationError",
    "SortNode",
    "SqlEmitter",
    "SqlQuery",
    "query_field",
]

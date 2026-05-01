from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Annotated

import pytest

from paramora import (
    Query,
    QueryContract,
    QueryErrorDetail,
    QueryValidationError,
    query_field,
    query_modes,
)
from paramora.compiled import coerce_str, make_list_coercer, make_scalar_coercer
from paramora.emitters.mongo import MongoEmitter
from paramora.errors import (
    empty_list,
    enum_type_error,
    invalid_filter_field,
    invalid_filter_operator,
    invalid_sort_field,
    limit_too_large,
    non_negative_int_type,
    non_negative_int_value,
    operator_not_allowed,
    query_error,
    raw_operator_not_allowed,
    required_field,
    sort_not_allowed,
    type_error,
    unknown_field,
    unknown_operator,
    unknown_sort_field,
)
from paramora.fields import QueryField
from paramora.query_ast import FilterNode, PaginationNode, QueryAst, SortNode
from paramora.query_parser import normalize_params


class FloatListContract(QueryContract):
    price: Annotated[float, query_field("in")]


class DatetimeContract(QueryContract):
    created_at: Annotated[datetime, query_field("gte")]


class CustomType:
    pass


class CustomTypeContract(QueryContract):
    custom: CustomType


def error_type(error: QueryErrorDetail) -> str:
    return error.to_dict()["type"]


def test_query_modes_module_exports_supported_literals() -> None:
    # Arrange / Act / Assert
    assert query_modes.__name__ == "paramora.query_modes"


def test_normalize_params_returns_plain_string_dict_without_copy() -> None:
    # Arrange
    params = {"status": "free", "active": "true"}

    # Act
    normalized = normalize_params(params)

    # Assert
    assert normalized is params


def test_normalize_params_uses_last_sequence_value_for_mapping() -> None:
    # Arrange
    params = {"status": ["free", "busy"], "empty": []}

    # Act
    normalized = normalize_params(params)

    # Assert
    assert normalized == {"status": "busy"}


def test_list_coercer_returns_item_level_errors() -> None:
    # Arrange
    query = Query(FloatListContract)

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse({"price__in": "1.5,bad"})

    # Assert
    errors = exc_info.value.to_list()
    assert errors == [
        {
            "loc": ["query", "price__in"],
            "msg": "Expected a float-compatible value.",
            "type": "query.type_error.float",
            "input": "bad",
        }
    ]


def test_invalid_datetime_value_raises_structured_error() -> None:
    # Arrange
    query = Query(DatetimeContract)

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse({"created_at__gte": "not-a-date"})

    # Assert
    assert exc_info.value.to_list()[0]["type"] == "query.type_error.datetime"


def test_unknown_contract_type_falls_back_to_string_coercion() -> None:
    # Arrange
    query = Query(CustomTypeContract)

    # Act
    mongo = query.parse({"custom": "raw"}).to_mongo()

    # Assert
    assert mongo.filter == {"custom": "raw"}


def test_make_scalar_coercer_falls_back_to_string_coercer() -> None:
    # Arrange
    coercer = make_scalar_coercer(object())  # type: ignore

    # Act
    value, error = coercer("raw", "custom")

    # Assert
    assert value == "raw"
    assert error is None


def test_coerce_str_ignores_param_name_by_design() -> None:
    # Arrange / Act
    value, error = coerce_str("raw", "unused")

    # Assert
    assert value == "raw"
    assert error is None


def test_make_list_coercer_ignores_blank_items() -> None:
    # Arrange
    list_coercer = make_list_coercer(coerce_str)

    # Act
    values, errors = list_coercer("free,, busy ,", "status__in")

    # Assert
    assert values == ["free", "busy"]
    assert errors == []


def test_error_factory_helpers_return_stable_error_codes() -> None:
    # Arrange / Act
    errors = [
        query_error("field", "message", "query.custom", "raw"),
        type_error("field", "int", "raw"),
        enum_type_error("field", ["LOW", "HIGH"], "raw"),
        unknown_field("field", "raw"),
        unknown_operator("field__bad", "bad", "raw"),
        operator_not_allowed("field__gte", "field", "gte", "raw"),
        empty_list("field__in", ""),
        invalid_filter_field("__gte", "raw"),
        invalid_filter_operator("field__", "raw"),
        raw_operator_not_allowed("$where", "raw"),
        required_field("tenant_id"),
        unknown_sort_field("name", "name"),
        sort_not_allowed("name", "name"),
        invalid_sort_field("-"),
        non_negative_int_type("limit", "bad"),
        non_negative_int_value("offset", "-1"),
        limit_too_large(100, "101"),
    ]

    # Assert
    assert [error_type(error) for error in errors] == [
        "query.custom",
        "query.type_error.int",
        "query.type_error.enum",
        "query.unknown_field",
        "query.unknown_operator",
        "query.operator_not_allowed",
        "query.empty_list",
        "query.invalid_field",
        "query.invalid_operator",
        "query.raw_operator_not_allowed",
        "query.required",
        "query.unknown_sort_field",
        "query.sort_not_allowed",
        "query.invalid_sort_field",
        "query.type_error.int",
        "query.value_error.non_negative",
        "query.limit_too_large",
    ]


def test_raw_mongo_emitter_applies_aliases_and_sort_direction() -> None:
    # Arrange
    ast = QueryAst(
        filters=(FilterNode("created_at", "gte", 1),),
        sort=(SortNode("created_at", "desc"),),
        pagination=PaginationNode(limit=10, offset=2),
    )
    fields = {"created_at": QueryField(int, alias="createdAt")}

    # Act
    mongo = MongoEmitter().emit(ast, fields)

    # Assert
    assert mongo.filter == {"createdAt": {"$gte": 1}}
    assert mongo.sort == [("createdAt", -1)]
    assert mongo.limit == 10
    assert mongo.offset == 2


def test_raw_mongo_emitter_merges_eq_after_range_filter() -> None:
    # Arrange
    ast = QueryAst(
        filters=(
            FilterNode("price", "gte", 10),
            FilterNode("price", "eq", 20),
        ),
        sort=(),
        pagination=PaginationNode(limit=10, offset=0),
    )

    # Act
    mongo = MongoEmitter().emit(ast, {})

    # Assert
    assert mongo.filter == {"price": {"$gte": 10, "$eq": 20}}


def test_raw_mongo_emitter_merges_range_after_eq_filter() -> None:
    # Arrange
    ast = QueryAst(
        filters=(
            FilterNode("price", "eq", 20),
            FilterNode("price", "lte", 30),
        ),
        sort=(),
        pagination=PaginationNode(limit=10, offset=0),
    )

    # Act
    mongo = MongoEmitter().emit(ast, {})

    # Assert
    assert mongo.filter == {"price": {"$eq": 20, "$lte": 30}}


def test_compiled_mongo_emitter_merges_eq_after_range_filter() -> None:
    # Arrange
    query = Query()
    compiled = query.parse(
        (
            ("price__gte", "10"),
            ("price", "20"),
        )
    )

    # Act
    mongo = compiled.to_mongo()

    # Assert
    assert mongo.filter == {"price": {"$gte": "10", "$eq": "20"}}


def test_compiled_mongo_emitter_merges_range_after_eq_filter() -> None:
    # Arrange
    query = Query()
    compiled = query.parse(
        (
            ("price", "20"),
            ("price__lte", "30"),
        )
    )

    # Act
    mongo = compiled.to_mongo()

    # Assert
    assert mongo.filter == {"price": {"$eq": "20", "$lte": "30"}}


def test_query_constructor_rejects_invalid_limits() -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="default_limit must be non-negative"):
        Query(default_limit=-1)

    with pytest.raises(ValueError, match="max_limit must be non-negative"):
        Query(max_limit=-1)

    with pytest.raises(ValueError, match="default_limit must be less than"):
        Query(default_limit=101, max_limit=100)


def test_query_with_mode_returns_new_query_with_requested_mode() -> None:
    # Arrange
    query = Query(default_limit=7, max_limit=9)

    # Act
    strict_query = query.with_mode("loose")

    # Assert
    assert strict_query is not query
    assert strict_query.mode == "loose"
    assert strict_query.default_limit == 7
    assert strict_query.max_limit == 9

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Annotated

import pytest

from paramora import Query, QueryContract, QueryValidationError, query_field

if TYPE_CHECKING:
    from conftest import ItemQueryFactory


def assert_single_error(
    error: QueryValidationError, *, type_: str, loc: list[str] | None = None
) -> None:
    """Assert that a validation exception contains exactly one expected error."""
    errors = error.to_list()

    assert len(errors) == 1
    assert errors[0].get("type") == type_
    if loc is not None:
        assert errors[0].get("loc") == loc


def test_explicit_equality_filter_compiles_to_mongo_filter(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"status__eq": "free"}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"status": "free"}


def test_bare_field_defaults_to_equality_filter(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"status": "free"}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"status": "free"}


@pytest.mark.parametrize(
    ("params", "expected_filter"),
    [
        ({"status__in": "free,busy"}, {"status": {"$in": ["free", "busy"]}}),
        (
            {"status__nin": "archived,deleted"},
            {"status": {"$nin": ["archived", "deleted"]}},
        ),
    ],
)
def test_list_filter_operators_compile_to_mongo_filters(
    make_item_query: ItemQueryFactory,
    params: dict[str, str],
    expected_filter: dict[str, object],
) -> None:
    # Arrange
    query = make_item_query()

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == expected_filter


@pytest.mark.parametrize(
    ("raw_value", "expected_value"),
    [
        ("10", 10.0),
        ("10.5", 10.5),
    ],
)
def test_float_values_are_coerced_for_declared_numeric_fields(
    make_item_query: ItemQueryFactory,
    raw_value: str,
    expected_value: float,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"price__gte": raw_value}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"price": {"$gte": expected_value}}


@pytest.mark.parametrize(
    ("raw_value", "expected_value"),
    [
        ("true", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("FALSE", False),
        ("0", False),
        ("no", False),
        ("off", False),
    ],
)
def test_boolean_values_are_coerced_case_insensitively(
    make_item_query: ItemQueryFactory,
    raw_value: str,
    expected_value: bool,  # noqa: FBT001
) -> None:
    # Arrange
    query = make_item_query()
    params = {"active": raw_value}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"active": expected_value}


def test_invalid_boolean_values_raise_structured_validation_error(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"active": "maybe"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.type_error.bool", loc=["query", "active"]
    )


@pytest.mark.parametrize(
    ("raw_value", "expected_value"),
    [
        ("2026-01-01T12:30:00", datetime(2026, 1, 1, 12, 30)),
        ("2026-01-01T12:30:00Z", datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)),
    ],
)
def test_iso_datetime_values_are_coerced(
    make_item_query: ItemQueryFactory,
    raw_value: str,
    expected_value: datetime,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"created_at__gte": raw_value}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"created_at": {"$gte": expected_value}}


def test_unknown_filter_field_is_rejected_for_contract_queries(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"password": "secret"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.unknown_field", loc=["query", "password"]
    )


def test_unknown_filter_field_is_allowed_as_string_without_contract() -> None:
    # Arrange
    query = Query()
    params = {"password": "secret"}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"password": "secret"}


def test_unknown_list_filter_field_is_allowed_as_string_list_without_contract() -> None:
    # Arrange
    query = Query()
    params = {"tag__in": "new,featured"}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"tag": {"$in": ["new", "featured"]}}


def test_unsupported_operator_for_declared_field_is_rejected(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"status__gte": "free"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.operator_not_allowed", loc=["query", "status__gte"]
    )


def test_unknown_operator_is_rejected_in_loose_mode() -> None:
    # Arrange
    query = Query()
    params = {"status__raw": "free"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.unknown_operator", loc=["query", "status__raw"]
    )


@pytest.mark.parametrize(
    ("sort_value", "expected_sort"),
    [
        ("created_at", [("created_at", 1)]),
        ("-created_at", [("created_at", -1)]),
    ],
)
def test_sort_parameter_compiles_to_mongo_sort_pairs(
    make_item_query: ItemQueryFactory,
    sort_value: str,
    expected_sort: list[tuple[str, int]],
) -> None:
    # Arrange
    query = make_item_query()
    params = {"sort": sort_value}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.sort == expected_sort


def test_non_sortable_declared_field_is_rejected(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"sort": "status"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.sort_not_allowed", loc=["query", "sort"]
    )


def test_unknown_sort_field_is_allowed_without_contract() -> None:
    # Arrange
    query = Query()
    params = {"sort": "unknown"}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.sort == [("unknown", 1)]


def test_unknown_sort_field_is_rejected_for_contract_queries(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"sort": "unknown"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.unknown_sort_field", loc=["query", "sort"]
    )


def test_pagination_defaults_are_used_when_request_omits_values(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()

    # Act
    mongo = query.parse({}).output

    # Assert
    assert mongo.limit == 20
    assert mongo.offset == 0


def test_pagination_values_are_parsed(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"limit": "10", "offset": "5"}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.limit == 10
    assert mongo.offset == 5


def test_max_limit_is_enforced(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"limit": "101"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.limit_too_large", loc=["query", "limit"]
    )


def test_mongo_range_filters_are_merged(
    make_item_query: ItemQueryFactory,
) -> None:
    # Arrange
    query = make_item_query()
    params = {"price__gte": "10", "price__lt": "20"}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"price": {"$gte": 10.0, "$lt": 20.0}}


def test_field_alias_is_applied_by_mongo_emitter() -> None:
    # Arrange
    class AliasedQuery(QueryContract):
        created_at: Annotated[
            datetime,
            query_field("gte", sortable=True, alias="createdAt"),
        ]

    query = Query(AliasedQuery)
    params = {"created_at__gte": "2026-01-01T00:00:00", "sort": "-created_at"}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"createdAt": {"$gte": datetime(2026, 1, 1)}}
    assert mongo.sort == [("createdAt", -1)]


def test_raw_mongo_operator_field_is_rejected_even_without_contract() -> None:
    # Arrange
    query = Query()
    params = {"$where": "this.price > 10"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value,
        type_="query.raw_operator_not_allowed",
        loc=["query", "$where"],
    )


def test_raw_mongo_operator_suffix_is_rejected_even_without_contract() -> None:
    # Arrange
    query = Query()
    params = {"price__$gte": "10"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value,
        type_="query.raw_operator_not_allowed",
        loc=["query", "price__$gte"],
    )


def test_empty_filter_field_name_is_rejected() -> None:
    # Arrange
    query = Query()
    params = {"__gte": "10"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.invalid_field", loc=["query", "__gte"]
    )


def test_empty_list_filter_is_rejected() -> None:
    # Arrange
    query = Query()
    params = {"status__in": ",,"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.empty_list", loc=["query", "status__in"]
    )


def test_negative_limit_is_rejected(make_item_query: ItemQueryFactory) -> None:
    # Arrange
    query = make_item_query()
    params = {"limit": "-1"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value,
        type_="query.value_error.non_negative",
        loc=["query", "limit"],
    )


def test_non_integer_offset_is_rejected(make_item_query: ItemQueryFactory) -> None:
    # Arrange
    query = make_item_query()
    params = {"offset": "abc"}

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse(params)

    # Assert
    assert_single_error(
        exc_info.value, type_="query.type_error.int", loc=["query", "offset"]
    )


def test_required_contract_field_must_be_present() -> None:
    # Arrange
    class TenantQuery(QueryContract):
        tenant_id: Annotated[str, query_field(required=True)]

    query = Query(TenantQuery)

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse({})

    # Assert
    assert_single_error(
        exc_info.value, type_="query.required", loc=["query", "tenant_id"]
    )


def test_repeated_mapping_values_use_last_value() -> None:
    # Arrange
    query = Query()
    params = {"status": ["free", "busy"]}

    # Act
    mongo = query.parse(params).output

    # Assert
    assert mongo.filter == {"status": "busy"}

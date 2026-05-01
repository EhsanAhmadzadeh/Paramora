from __future__ import annotations

from enum import Enum
from typing import Annotated

import pytest

from paramora import Query, QueryContract, QueryValidationError, query_field


class Priority(Enum):
    LOW = "low"
    HIGH = "high"


class CoercionContract(QueryContract):
    count: int
    priority: Annotated[Priority, query_field("eq", "in")]


def assert_single_error(error: QueryValidationError, *, type_: str) -> None:
    """Assert that a validation exception contains exactly one expected error."""
    errors = error.to_list()

    assert len(errors) == 1
    assert errors[0]["type"] == type_


def test_integer_field_is_coerced_to_int() -> None:
    # Arrange
    query = Query(CoercionContract)

    # Act
    mongo = query.parse({"count": "42"}).to_mongo()

    # Assert
    assert mongo.filter == {"count": 42}


def test_invalid_integer_field_raises_structured_error() -> None:
    # Arrange
    query = Query(CoercionContract)

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse({"count": "forty-two"})

    # Assert
    assert_single_error(exc_info.value, type_="query.type_error.int")


def test_enum_field_is_coerced_from_value() -> None:
    # Arrange
    query = Query(CoercionContract)

    # Act
    mongo = query.parse({"priority": "high"}).to_mongo()

    # Assert
    assert mongo.filter == {"priority": Priority.HIGH}


def test_enum_list_field_is_coerced_from_values() -> None:
    # Arrange
    query = Query(CoercionContract)

    # Act
    mongo = query.parse({"priority__in": "low,high"}).to_mongo()

    # Assert
    assert mongo.filter == {"priority": {"$in": [Priority.LOW, Priority.HIGH]}}


def test_invalid_enum_field_raises_structured_error() -> None:
    # Arrange
    query = Query(CoercionContract)

    # Act
    with pytest.raises(QueryValidationError) as exc_info:
        query.parse({"priority": "medium"})

    # Assert
    assert_single_error(exc_info.value, type_="query.type_error.enum")

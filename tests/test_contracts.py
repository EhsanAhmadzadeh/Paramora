from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Annotated, Any

import pytest

from paramora import Query, QueryContract, query_field


class BaseAuditQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True),
    ]


class ItemQuery(BaseAuditQuery):
    status: Annotated[str, query_field("eq", "in")]
    active: bool


def test_contract_fields_are_resolved_from_annotations_and_metadata() -> None:
    # Arrange / Act
    query = Query(ItemQuery)

    # Assert
    assert query.mode == "strict"
    assert set(query.fields) == {"created_at", "status", "active"}
    assert query.fields["status"].operators == frozenset({"eq", "in"})
    assert query.fields["active"].operators == frozenset({"eq"})
    assert query.fields["created_at"].sortable is True


def test_query_without_contract_defaults_to_loose_mode() -> None:
    # Arrange / Act
    query = Query(default_limit=10, max_limit=50)

    # Assert
    assert query.mode == "loose"
    assert query.fields == {}


def test_query_with_contract_defaults_to_strict_mode() -> None:
    # Arrange / Act
    query = Query(ItemQuery)

    # Assert
    assert query.mode == "strict"


def test_explicit_strict_mode_without_contract_is_rejected() -> None:
    # Arrange / Act
    with pytest.raises(ValueError, match="Strict mode requires a QueryContract"):
        Query(mode="strict")


def test_query_field_rejects_unknown_operators() -> None:
    # Arrange
    invalid_operator: Any = "raw"

    # Act / Assert
    with pytest.raises(ValueError, match="Unknown operator"):
        query_field(invalid_operator)


def test_contract_rejects_regular_default_values() -> None:
    # Arrange
    class BadContract(QueryContract):
        status: str = "free"

    # Act / Assert
    with pytest.raises(ValueError, match="must not assign defaults"):
        Query(BadContract)


def test_contract_rejects_container_annotations() -> None:
    # Arrange
    class BadContract(QueryContract):
        tags: list[str]

    # Act / Assert
    with pytest.raises(ValueError, match="Unsupported query contract annotation"):
        Query(BadContract)

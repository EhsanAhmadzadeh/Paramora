from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from paramora import CompiledQuery, Query

if TYPE_CHECKING:
    from collections.abc import Callable


ITEMS_PATH = "/items"


def create_items_client(query_dependency: Query) -> TestClient:
    """Create a FastAPI test client with the Paramora query dependency mounted.

    Args:
        query_dependency: Paramora query dependency used by the test route.

    Returns:
        A configured FastAPI ``TestClient`` for the ``/items`` endpoint.
    """
    app = FastAPI()

    @app.get(ITEMS_PATH)
    def list_items(query: CompiledQuery = Depends(query_dependency)) -> object:
        """Return the compiled Mongo filter for the current request."""
        return query.to_mongo().filter

    return TestClient(app)


def test_fastapi_dependency_returns_compiled_query_on_valid_request(
    make_item_query: Callable[..., Query],
) -> None:
    """Verify that a valid FastAPI request returns the compiled query filter."""
    # Arrange
    client = create_items_client(make_item_query())
    expected_response = {"price": 12.5}

    # Act
    response = client.get(ITEMS_PATH, params={"price": "12.5"})

    # Assert
    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected_response


def test_fastapi_dependency_returns_422_for_validation_errors(
    make_item_query: Callable[..., Query],
) -> None:
    """Verify that query validation errors are returned as HTTP 422 responses."""
    # Arrange
    client = create_items_client(make_item_query())
    expected_response = {
        "detail": [
            {
                "loc": ["query", "price"],
                "msg": "Expected a float-compatible value.",
                "type": "query.type_error.float",
                "input": "bad",
            }
        ]
    }

    # Act
    response = client.get(ITEMS_PATH, params={"price": "bad"})

    # Assert
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == expected_response


def test_fastapi_dependency_uses_loose_mode_without_contract() -> None:
    """Verify that loose mode preserves undeclared query parameters."""
    # Arrange
    client = create_items_client(Query(default_limit=10, max_limit=50))
    expected_response = {"undeclared": "value"}

    # Act
    response = client.get(ITEMS_PATH, params={"undeclared": "value"})

    # Assert
    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected_response

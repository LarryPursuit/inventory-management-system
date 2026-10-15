import pytest

from app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def new_item():
    return {
        "barcode": "0028400090858",
        "product": {
            "product_name": "Classic Potato Chips",
            "brands": "Lay's",
            "quantity": "1 oz",
            "nutriscore_grade": "D",
        },
        "price": 1.5,
        "stock": 40,
    }

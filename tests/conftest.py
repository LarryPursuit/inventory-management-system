import pytest

from app import create_app
from app.openfoodfacts import ExternalAPIError

ALMOND_MILK = {
    "barcode": "0025293000018",
    "product": {
        "product_name": "Organic Almond Milk",
        "brands": "Silk",
        "ingredients_text": "Filtered water, almonds, cane sugar",
        "nutriscore_grade": "c",
    },
}


class FakeFoodClient:
    """Stands in for OpenFoodFactsClient so route tests never hit the network."""

    def __init__(self, products=(ALMOND_MILK,), fail=False):
        self.products = {p["barcode"]: p for p in products}
        self.fail = fail
        self.calls = []

    def get_product(self, barcode):
        self.calls.append(("get_product", barcode))
        if self.fail:
            raise ExternalAPIError("boom")
        return self.products.get(barcode)

    def search(self, name, limit=5):
        self.calls.append(("search", name, limit))
        if self.fail:
            raise ExternalAPIError("boom")
        needle = name.lower()
        return [p for p in self.products.values() if needle in p["product"]["product_name"].lower()][
            :limit
        ]


@pytest.fixture
def food_client():
    return FakeFoodClient()


@pytest.fixture
def app(food_client):
    return create_app(food_client=food_client)


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

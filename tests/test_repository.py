import pytest

from app.data import SEED_INVENTORY
from app.repository import InventoryRepository


@pytest.fixture
def repo():
    return InventoryRepository()


def test_seed_items_each_have_an_id_and_product_block(repo):
    items = repo.find_all()
    assert len(items) == len(SEED_INVENTORY)
    assert all(isinstance(item["id"], int) for item in items)
    assert all("product_name" in item["product"] for item in items)


def test_find_all_returns_copies(repo):
    repo.find_all()[0]["stock"] = -1
    assert repo.find_by_id(1)["stock"] != -1


def test_find_by_id_and_missing_id(repo):
    assert repo.find_by_id(2)["product"]["product_name"] == "Nutella"
    assert repo.find_by_id(999) is None


def test_find_by_barcode(repo):
    assert repo.find_by_barcode("5449000000996")["id"] == 3
    assert repo.find_by_barcode("nope") is None


def test_search_matches_name_brand_and_category_case_insensitively(repo):
    assert [i["id"] for i in repo.search("NUTELLA")] == [2]
    assert [i["id"] for i in repo.search("silk")] == [1]
    assert [i["id"] for i in repo.search("cereal")] == [4]
    assert repo.search("zzz") == []


def test_low_stock(repo):
    assert [i["id"] for i in repo.low_stock(0)] == [5]
    assert {i["id"] for i in repo.low_stock(12)} == {2, 5}


def test_create_assigns_next_id(repo):
    created = repo.create({"barcode": "1", "product": {"product_name": "X"}, "price": 1, "stock": 1})
    assert created["id"] == 6
    assert repo.create({"barcode": "2", "product": {}, "price": 1, "stock": 1})["id"] == 7
    assert len(repo.find_all()) == 7


def test_empty_repository_starts_ids_at_one():
    assert InventoryRepository(seed=()).create({"product": {}})["id"] == 1


def test_update_merges_top_level_and_product_fields(repo):
    updated = repo.update(1, {"stock": 5, "product": {"brands": "Silk Co"}})
    assert updated["stock"] == 5
    assert updated["product"]["brands"] == "Silk Co"
    assert updated["product"]["product_name"] == "Organic Soymilk"
    assert repo.find_by_id(1) == updated


def test_update_does_not_mutate_previously_returned_records(repo):
    before = repo.find_by_id(1)
    repo.update(1, {"stock": 1})
    assert before["stock"] == 24


def test_update_missing_returns_none(repo):
    assert repo.update(999, {"stock": 1}) is None


def test_delete(repo):
    assert repo.delete(3)["id"] == 3
    assert repo.find_by_id(3) is None
    assert repo.delete(3) is None

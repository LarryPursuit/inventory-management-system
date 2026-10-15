"""In-memory inventory store (repository pattern).

Routes talk to ``InventoryRepository`` instead of touching the list directly,
so the storage could later be swapped for a real database. Records are never
mutated in place: reads return copies and updates replace the stored record
with a new merged dict.
"""

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from app.data import SEED_INVENTORY

Item = dict[str, Any]


class InventoryRepository:
    def __init__(self, seed: Iterable[Item] = SEED_INVENTORY) -> None:
        self._items = [deepcopy(item) for item in seed]
        self._next_id = max((item["id"] for item in self._items), default=0) + 1

    def find_all(self) -> list[Item]:
        return [deepcopy(item) for item in self._items]

    def find_by_id(self, item_id: int) -> Item | None:
        index = self._index_of(item_id)
        return None if index is None else deepcopy(self._items[index])

    def find_by_barcode(self, barcode: str) -> Item | None:
        for item in self._items:
            if item["barcode"] == barcode:
                return deepcopy(item)
        return None

    def search(self, term: str) -> list[Item]:
        """Case-insensitive match against product name, brand, and category."""
        needle = term.lower()
        return [
            deepcopy(item)
            for item in self._items
            if any(
                needle in str(item["product"].get(field, "")).lower()
                for field in ("product_name", "brands", "categories")
            )
        ]

    def low_stock(self, threshold: int) -> list[Item]:
        return [deepcopy(item) for item in self._items if item["stock"] <= threshold]

    def create(self, fields: Item) -> Item:
        item = {"id": self._next_id, **deepcopy(fields)}
        self._items = [*self._items, item]
        self._next_id += 1
        return deepcopy(item)

    def update(self, item_id: int, changes: Item) -> Item | None:
        """Merge ``changes`` into the record; ``product`` keys merge one level deep."""
        index = self._index_of(item_id)
        if index is None:
            return None
        current = self._items[index]
        merged = {
            **current,
            **{key: value for key, value in changes.items() if key != "product"},
            "product": {**current["product"], **changes.get("product", {})},
        }
        self._items = [*self._items[:index], merged, *self._items[index + 1 :]]
        return deepcopy(merged)

    def delete(self, item_id: int) -> Item | None:
        index = self._index_of(item_id)
        if index is None:
            return None
        removed = self._items[index]
        self._items = [*self._items[:index], *self._items[index + 1 :]]
        return deepcopy(removed)

    def _index_of(self, item_id: int) -> int | None:
        for index, item in enumerate(self._items):
            if item["id"] == item_id:
                return index
        return None

"""Interactive menu so employees don't need to remember command flags."""

from collections.abc import Callable
from typing import Any

from inventory_cli.api_client import ApiError, InventoryApiClient
from inventory_cli.display import format_item, format_product, format_search_results, format_table

PRODUCT_PROMPTS = (
    ("product_name", "Product name"),
    ("brands", "Brand"),
    ("quantity", "Size (e.g. 400 g)"),
    ("categories", "Categories"),
    ("nutriscore_grade", "Nutri-Score (a-e)"),
    ("ingredients_text", "Ingredients"),
)

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


class Menu:
    def __init__(self, api: InventoryApiClient, ask: InputFn | None = None, say: OutputFn = print) -> None:
        self.api = api
        # Look up input() at call time so tests can patch it.
        self.ask = ask or (lambda prompt: input(prompt))
        self.say = say
        self.actions: dict[str, tuple[str, Callable[[], None]]] = {
            "1": ("List inventory", self.list_items),
            "2": ("View an item", self.view_item),
            "3": ("Add an item by hand", self.add_item),
            "4": ("Update an item", self.update_item),
            "5": ("Delete an item", self.delete_item),
            "6": ("Look up a barcode on OpenFoodFacts", self.lookup_and_import),
            "7": ("Search OpenFoodFacts by name", self.search_and_import),
            "8": ("Show low-stock items", self.low_stock),
            "q": ("Quit", lambda: None),
        }

    def run(self) -> None:
        while True:
            self.say("\n=== Inventory Admin ===")
            for key, (label, _) in self.actions.items():
                self.say(f" {key}) {label}")
            choice = self.ask("Choose an option: ").strip().lower()
            if choice == "q":
                return
            action = self.actions.get(choice)
            if action is None:
                self.say("Not a valid option.")
                continue
            try:
                action[1]()
            except ApiError as error:
                self.say(f"Error: {error}")
            except ValueError as error:
                self.say(f"Invalid input: {error}")

    # --- CRUD -----------------------------------------------------------

    def list_items(self) -> None:
        search = self.ask("Search (blank for all): ").strip() or None
        self.say(format_table(self.api.list_items(search=search)))

    def view_item(self) -> None:
        self.say(format_item(self.api.get_item(self._ask_int("Item ID: "))))

    def add_item(self) -> None:
        payload = {
            "barcode": self.ask("Barcode: ").strip(),
            "product": self._ask_product_fields(require_name=True),
            "price": self._ask_float("Price: "),
            "stock": self._ask_int("Stock: "),
        }
        item = self.api.create_item(payload)
        self.say(f"Added item #{item['id']}.\n{format_item(item)}")

    def update_item(self) -> None:
        item_id = self._ask_int("Item ID: ")
        self.say(format_item(self.api.get_item(item_id)))
        self.say("Press Enter to keep a value unchanged.")
        changes: dict[str, Any] = {}
        product = self._ask_product_fields(require_name=False)
        if product:
            changes["product"] = product
        price = self.ask("New price: ").strip()
        if price:
            changes["price"] = float(price)
        stock = self.ask("New stock: ").strip()
        if stock:
            changes["stock"] = int(stock)
        if not changes:
            self.say("Nothing changed.")
            return
        updated = self.api.update_item(item_id, changes)
        self.say(f"Updated.\n{format_item(updated)}")

    def delete_item(self) -> None:
        item_id = self._ask_int("Item ID: ")
        if self._confirm(f"Delete item #{item_id}?"):
            self.say(self.api.delete_item(item_id)["message"])
        else:
            self.say("Cancelled.")

    def low_stock(self) -> None:
        threshold = self._ask_int("Show items with stock at or below: ")
        self.say(format_table(self.api.list_items(low_stock=threshold)))

    # --- OpenFoodFacts ---------------------------------------------------

    def lookup_and_import(self) -> None:
        barcode = self.ask("Barcode: ").strip()
        self.say(format_product(self.api.lookup_product(barcode)))
        if self._confirm("Add this product to inventory?"):
            self._import(barcode)

    def search_and_import(self) -> None:
        name = self.ask("Product name: ").strip()
        results = self.api.search_products(name)
        self.say(format_search_results(results))
        if not results:
            return
        choice = self.ask("Number to add to inventory (blank to skip): ").strip()
        if not choice:
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(results):
            self.say("Not a valid result number.")
            return
        self._import(results[int(choice) - 1]["barcode"])

    def _import(self, barcode: str) -> None:
        price = self._ask_float("Price: ")
        stock = self._ask_int("Stock: ")
        item = self.api.import_product(barcode, price, stock)
        self.say(f"Imported as item #{item['id']}.\n{format_item(item)}")

    # --- prompts ---------------------------------------------------------

    def _ask_product_fields(self, require_name: bool) -> dict[str, str]:
        fields = {}
        for key, label in PRODUCT_PROMPTS:
            value = self.ask(f"{label}: ").strip()
            if value:
                fields[key] = value
        if require_name and "product_name" not in fields:
            raise ValueError("product name is required")
        return fields

    def _ask_int(self, prompt: str) -> int:
        return int(self.ask(prompt).strip())

    def _ask_float(self, prompt: str) -> float:
        return float(self.ask(prompt).strip())

    def _confirm(self, prompt: str) -> bool:
        return self.ask(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")


def run_menu(api: InventoryApiClient) -> None:
    Menu(api).run()

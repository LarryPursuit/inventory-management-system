"""Command-line interface for the inventory API.

Run ``python cli.py --help`` for commands, or ``python cli.py`` with no
arguments for the interactive menu.
"""

import argparse
import sys
from collections.abc import Callable
from typing import Any

from inventory_cli.api_client import ApiError, InventoryApiClient
from inventory_cli.display import format_item, format_product, format_search_results, format_table

# CLI flag -> OpenFoodFacts-style field inside an item's "product" block.
PRODUCT_OPTIONS = {
    "name": "product_name",
    "brand": "brands",
    "ingredients": "ingredients_text",
    "categories": "categories",
    "size": "quantity",
    "nutriscore": "nutriscore_grade",
}


def build_product_changes(args: argparse.Namespace) -> dict[str, Any]:
    """Collect only the options the user actually passed into a PATCH/POST body."""
    changes: dict[str, Any] = {
        field: getattr(args, field)
        for field in ("barcode", "price", "stock")
        if getattr(args, field, None) is not None
    }
    product = {
        field: getattr(args, option)
        for option, field in PRODUCT_OPTIONS.items()
        if getattr(args, option, None) is not None
    }
    return {**changes, "product": product} if product else changes


def cmd_health(api: InventoryApiClient, args: argparse.Namespace) -> str:
    status = api.health()
    return f"API is {status['status']} — {status['items']} item(s) in inventory."


def cmd_list(api: InventoryApiClient, args: argparse.Namespace) -> str:
    return format_table(api.list_items(search=args.search, low_stock=args.low_stock))


def cmd_view(api: InventoryApiClient, args: argparse.Namespace) -> str:
    return format_item(api.get_item(args.id))


def cmd_add(api: InventoryApiClient, args: argparse.Namespace) -> str:
    item = api.create_item(build_product_changes(args))
    return f"Added item #{item['id']}.\n{format_item(item)}"


def cmd_update(api: InventoryApiClient, args: argparse.Namespace) -> str:
    changes = build_product_changes(args)
    if not changes:
        raise ApiError("Nothing to update. Pass at least one option, e.g. --stock 10.")
    item = api.update_item(args.id, changes)
    return f"Updated item #{item['id']}.\n{format_item(item)}"


def cmd_delete(api: InventoryApiClient, args: argparse.Namespace) -> str:
    if not args.yes:
        answer = input(f"Delete item #{args.id}? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            return "Cancelled."
    result = api.delete_item(args.id)
    return result["message"]


def cmd_lookup(api: InventoryApiClient, args: argparse.Namespace) -> str:
    return format_product(api.lookup_product(args.barcode))


def cmd_find(api: InventoryApiClient, args: argparse.Namespace) -> str:
    return format_search_results(api.search_products(args.name, args.limit))


def cmd_import(api: InventoryApiClient, args: argparse.Namespace) -> str:
    item = api.import_product(args.barcode, args.price, args.stock)
    return f"Imported from OpenFoodFacts as item #{item['id']}.\n{format_item(item)}"


def cmd_menu(api: InventoryApiClient, args: argparse.Namespace) -> str:
    from inventory_cli.menu import run_menu

    run_menu(api)
    return "Goodbye!"


def _add_product_options(parser: argparse.ArgumentParser, required_name: bool) -> None:
    parser.add_argument("--name", required=required_name, help="product name")
    parser.add_argument("--brand", help="brand name(s)")
    parser.add_argument("--ingredients", help="ingredients text")
    parser.add_argument("--categories", help="comma-separated categories")
    parser.add_argument("--size", help="package size, e.g. '400 g'")
    parser.add_argument("--nutriscore", help="Nutri-Score grade a-e")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inventory",
        description="Manage store inventory through the inventory API.",
    )
    parser.add_argument("--api-url", help="API base URL (default: $INVENTORY_API_URL or http://127.0.0.1:5555/api)")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def command(name: str, handler: Callable, help_text: str) -> argparse.ArgumentParser:
        sub_parser = sub.add_parser(name, help=help_text, description=help_text)
        sub_parser.set_defaults(handler=handler)
        return sub_parser

    command("health", cmd_health, "check that the API is running")

    list_parser = command("list", cmd_list, "list inventory items")
    list_parser.add_argument("--search", help="filter by name, brand, or category")
    list_parser.add_argument("--low-stock", type=int, metavar="N", help="only items with stock <= N")

    command("view", cmd_view, "show one item").add_argument("id", type=int)

    add_parser = command("add", cmd_add, "add an item by hand")
    add_parser.add_argument("--barcode", required=True)
    add_parser.add_argument("--price", type=float, required=True)
    add_parser.add_argument("--stock", type=int, required=True)
    _add_product_options(add_parser, required_name=True)

    update_parser = command("update", cmd_update, "change fields on an item")
    update_parser.add_argument("id", type=int)
    update_parser.add_argument("--barcode")
    update_parser.add_argument("--price", type=float)
    update_parser.add_argument("--stock", type=int)
    _add_product_options(update_parser, required_name=False)

    delete_parser = command("delete", cmd_delete, "remove an item")
    delete_parser.add_argument("id", type=int)
    delete_parser.add_argument("-y", "--yes", action="store_true", help="skip the confirmation prompt")

    command("lookup", cmd_lookup, "look up a barcode on OpenFoodFacts").add_argument("barcode")

    find_parser = command("find", cmd_find, "search OpenFoodFacts by product name")
    find_parser.add_argument("name")
    find_parser.add_argument("--limit", type=int, default=5, help="max results, 1-20 (default 5)")

    import_parser = command("import", cmd_import, "add an OpenFoodFacts product to inventory")
    import_parser.add_argument("barcode")
    import_parser.add_argument("--price", type=float, default=0.0)
    import_parser.add_argument("--stock", type=int, default=0)

    command("menu", cmd_menu, "interactive menu (default when no command is given)")
    return parser


def main(argv: list[str] | None = None, api: InventoryApiClient | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = getattr(args, "handler", cmd_menu)
    api = api or InventoryApiClient(base_url=args.api_url)
    try:
        print(handler(api, args))
    except ApiError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return 130
    return 0

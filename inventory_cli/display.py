"""Turn API responses into readable terminal text."""

from typing import Any

DETAIL_LABELS = (
    ("brands", "Brand"),
    ("quantity", "Size"),
    ("categories", "Categories"),
    ("nutriscore_grade", "Nutri-Score"),
    ("ingredients_text", "Ingredients"),
)
NAME_WIDTH = 28
BRAND_WIDTH = 16


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else f"{text[: width - 1]}…"


def format_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No items found."
    header = f"{'ID':>4}  {'Barcode':<14}  {'Name':<{NAME_WIDTH}}  {'Brand':<{BRAND_WIDTH}}  {'Price':>8}  {'Stock':>5}"
    rows = [header, "-" * len(header)]
    for item in items:
        product = item.get("product", {})
        rows.append(
            f"{item['id']:>4}  {item['barcode']:<14}  "
            f"{_truncate(product.get('product_name', ''), NAME_WIDTH):<{NAME_WIDTH}}  "
            f"{_truncate(product.get('brands', ''), BRAND_WIDTH):<{BRAND_WIDTH}}  "
            f"{'$' + format(item['price'], '.2f'):>8}  {item['stock']:>5}"
        )
    return "\n".join(rows)


def format_product(entry: dict[str, Any]) -> str:
    """Details for an OpenFoodFacts result or an inventory item."""
    product = entry.get("product", {})
    lines = [product.get("product_name", "Unnamed product"), f"  Barcode:     {entry.get('barcode', '')}"]
    for key, label in DETAIL_LABELS:
        if product.get(key):
            value = product[key].upper() if key == "nutriscore_grade" else product[key]
            lines.append(f"  {label + ':':<12} {value}")
    return "\n".join(lines)


def format_item(item: dict[str, Any]) -> str:
    stock_note = " (out of stock)" if item["stock"] == 0 else ""
    return "\n".join(
        [
            f"#{item['id']} {format_product(item)}",
            f"  {'Price:':<12} ${item['price']:.2f}",
            f"  {'Stock:':<12} {item['stock']}{stock_note}",
        ]
    )


def format_search_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No OpenFoodFacts products matched."
    lines = []
    for number, result in enumerate(results, start=1):
        product = result["product"]
        brand = f" — {product['brands']}" if product.get("brands") else ""
        lines.append(f"{number:>2}. {product.get('product_name', 'Unnamed product')}{brand} [{result['barcode']}]")
    return "\n".join(lines)

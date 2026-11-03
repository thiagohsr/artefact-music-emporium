import json
import re
import sqlite3
import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

MAX_RESULTS = 10
CENT = Decimal("0.01")

PRODUCTS = """
SELECT p.name, p.price_brl, p.stock_quantity, p.status, p.specs, c.name AS category,
    (SELECT max(discount_percent) FROM promotions
     WHERE product_id = p.product_id AND is_active = 1) AS discount_percent
FROM products p JOIN categories c USING (category_id)
"""


def fold(text: str) -> str:
    """Compares words as a customer types them, with no accents or capitals."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _stem(word: str) -> str:
    return re.sub(r"(oes|ao|es|s)$", "", word)


def _words(text: str) -> list[str]:
    return re.findall(r"[\w-]+", fold(text))


def _matches(query: str, text: str) -> bool:
    words = _words(text)
    stems = {_stem(word) for word in words}
    return all(_stem(term) in stems or any(term in word for word in words) for term in _words(query))


def money(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _availability(row: sqlite3.Row) -> str:
    if row["status"] == "discontinued":
        return "discontinued"
    if row["status"] == "coming_soon":
        return "not_yet_available"
    return "in_stock" if row["stock_quantity"] > 0 else "out_of_stock"


def _product(row: sqlite3.Row) -> dict[str, Any]:
    original = Decimal(str(row["price_brl"]))
    percent = row["discount_percent"]
    final = original * (100 - percent) / 100 if percent else original
    return {
        "name": row["name"],
        "category": row["category"],
        "price_brl": money(final),
        "stock": row["stock_quantity"],
        "availability": _availability(row),
        "promotion": (
            {"original_price_brl": money(original), "discount_percent": percent, "final_price_brl": money(final)}
            if percent
            else None
        ),
    }


def search_products(
    conn: sqlite3.Connection,
    text: str | None = None,
    category: str | None = None,
    min_price_brl: float | None = None,
    max_price_brl: float | None = None,
    in_stock_only: bool = False,
) -> dict[str, Any]:
    found = []
    for row in conn.execute(PRODUCTS):
        product = _product(row)
        if (
            product["availability"] == "discontinued"
            or (text and not _matches(text, f"{row['name']} {row['category']}"))
            or (category and fold(category) not in fold(row["category"]))
            or (min_price_brl is not None and product["price_brl"] < min_price_brl)
            or (max_price_brl is not None and product["price_brl"] > max_price_brl)
            or (in_stock_only and product["availability"] != "in_stock")
        ):
            continue
        found.append(product)
    found.sort(key=lambda product: product["price_brl"])
    shown = found[:MAX_RESULTS]
    return {"total": len(found), "shown": len(shown), "products": shown}


def get_product(conn: sqlite3.Connection, name: str) -> dict[str, Any]:
    rows = [row for row in conn.execute(PRODUCTS) if _matches(name, f"{row['name']} {row['category']}")]
    if len(rows) != 1:
        return {"found": False, "close_matches": [row["name"] for row in rows]}
    return {"found": True, "product": {**_product(rows[0]), "specs": json.loads(rows[0]["specs"])}}

import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any

NOT_VERIFIED = {
    "verified": False,
    "message": "Não foi possível confirmar esses dados. Confira o número do pedido, o telefone e o e-mail.",
}


@dataclass(frozen=True)
class VerifiedCustomer:
    customer_id: int
    name: str
    phone: str
    email: str


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _days_since(estimate: str | None, today: date) -> int | None:
    return (today - date.fromisoformat(estimate)).days if estimate else None


def get_order_status(
    conn: sqlite3.Connection,
    order_number: str,
    phone: str,
    email: str,
    today: date,
) -> tuple[dict[str, Any], VerifiedCustomer | None]:
    """Starts from the order, because two customers share an email and an email alone identifies nobody."""
    order_id = _digits(order_number)
    order = conn.execute(
        """
        SELECT o.*, c.name, c.phone, c.email
        FROM orders o JOIN customers c USING (customer_id)
        WHERE o.order_id = ?
        """,
        (int(order_id) if order_id else -1,),
    ).fetchone()
    if (
        order is None
        or not _digits(phone)
        or _digits(phone) != _digits(order["phone"])
        or email.strip().casefold() != order["email"].casefold()
    ):
        return NOT_VERIFIED, None
    items = conn.execute(
        "SELECT p.name, i.quantity FROM order_items i JOIN products p USING (product_id) WHERE i.order_id = ?",
        (order["order_id"],),
    )
    result = {
        "verified": True,
        "customer_name": order["name"],
        "order_number": order["order_id"],
        "status": order["status"],
        "order_date": order["order_date"],
        "total_brl": order["total_brl"],
        "payment_method": order["payment_method"],
        "items": [{"name": name, "quantity": quantity} for name, quantity in items],
        "tracking_code": order["tracking_code"],
        "estimated_delivery": order["estimated_delivery"],
        "days_since_estimate": _days_since(order["estimated_delivery"], today),
    }
    customer = VerifiedCustomer(order["customer_id"], order["name"], order["phone"], order["email"])
    return result, customer

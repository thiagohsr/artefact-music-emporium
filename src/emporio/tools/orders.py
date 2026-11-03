import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any

NOT_VERIFIED = {
    "verified": False,
    "message": "Não foi possível confirmar esses dados. Confira o código de rastreamento, o telefone e o e-mail.",
}


@dataclass(frozen=True)
class VerifiedCustomer:
    customer_id: int
    name: str
    phone: str
    email: str


# Manual sections 4.1 and 4.3 count from delivery, and 4.2 from the purchase.
WITHDRAWAL_DAYS = 7
PREFERENCE_EXCHANGE_DAYS = 7
DEFECT_EXCHANGE_DAYS = 30


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _days_since(estimate: str | None, today: date) -> int | None:
    return (today - date.fromisoformat(estimate)).days if estimate else None


def _returns(order: sqlite3.Row, today: date) -> dict[str, bool] | None:
    """Worked out here, because the model misread the dates and offered windows that had closed."""
    since_delivery = _days_since(order["estimated_delivery"], today)
    if order["status"] != "delivered" or since_delivery is None:
        return None
    since_purchase = (today - date.fromisoformat(order["order_date"])).days
    return {
        "withdrawal_open": since_delivery <= WITHDRAWAL_DAYS,
        "preference_exchange_open": since_delivery <= PREFERENCE_EXCHANGE_DAYS,
        "defect_exchange_open": since_purchase <= DEFECT_EXCHANGE_DAYS,
    }


def get_order_status(
    conn: sqlite3.Connection,
    tracking_code: str,
    phone: str,
    email: str,
    today: date,
) -> tuple[dict[str, Any], VerifiedCustomer | None]:
    """Starts from the order, because two customers share an email and an email alone identifies nobody.

    Only the tracking code finds an order: order IDs are sequential, so they're easy to guess.
    """
    code = re.sub(r"[\s#.-]", "", tracking_code).upper()
    order = conn.execute(
        """
        SELECT o.*, c.name, c.phone, c.email
        FROM orders o JOIN customers c USING (customer_id)
        WHERE upper(o.tracking_code) = ?
        """,
        (code,),
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
        "status": order["status"],
        "total_brl": order["total_brl"],
        "payment_method": order["payment_method"],
        "items": [{"name": name, "quantity": quantity} for name, quantity in items],
        "tracking_code": order["tracking_code"],
        "estimated_delivery": order["estimated_delivery"],
        "days_since_estimate": _days_since(order["estimated_delivery"], today),
        "returns": _returns(order, today),
    }
    customer = VerifiedCustomer(order["customer_id"], order["name"], order["phone"], order["email"])
    return result, customer

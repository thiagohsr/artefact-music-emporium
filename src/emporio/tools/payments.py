import sqlite3
from decimal import Decimal
from typing import Any, Literal

from emporio.tools.catalog import get_product, money

MAX_INSTALLMENTS = 12
PIX_DISCOUNT = Decimal("0.05")

Method = Literal["pix", "debit", "boleto", "credit"]


def _minimum(installments: int) -> Decimal:
    """The tiers from docs/stakeholder-clarifications.md, since the manual contradicts itself on them."""
    if installments == 1:
        return Decimal(0)
    if installments <= 3:
        return Decimal(50)
    return Decimal(80) if installments <= 6 else Decimal(100)


def _max_installments(final: Decimal, method: str) -> int:
    limit = MAX_INSTALLMENTS if method == "credit" else 1
    return next((count for count in range(limit, 1, -1) if final / count >= _minimum(count)), 1)


def payment_terms(
    conn: sqlite3.Connection,
    method: Method,
    product_name: str | None = None,
    amount_brl: float | None = None,
    installments: int = 1,
) -> dict[str, Any]:
    on_promotion = False
    if product_name:
        found = get_product(conn, product_name)
        if not found["found"]:
            return {"allowed": False, "reason": "product_not_found"}
        price = Decimal(str(found["product"]["price_brl"]))
        on_promotion = found["product"]["promotion"] is not None
    elif amount_brl is not None:
        price = Decimal(str(amount_brl))
    else:
        return {"allowed": False, "reason": "price_required"}

    final = price * (1 - PIX_DISCOUNT) if method == "pix" and not on_promotion else price
    installment = final / installments
    minimum = _minimum(installments)
    most = _max_installments(final, method)
    reason = None
    if installments > (MAX_INSTALLMENTS if method == "credit" else 1) or installments < 1:
        reason = "too_many_installments"
    elif installment < minimum:
        reason = "below_minimum"
    return {
        "method": method,
        "final_price_brl": money(final),
        "installments": installments,
        "installment_brl": money(installment),
        "minimum_installment_brl": money(minimum),
        "max_installments": most,
        "max_installment_brl": money(final / most),
        "allowed": reason is None,
        "reason": reason,
    }

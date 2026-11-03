import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from evaluators import CalledTool, NeverSays, ReturnedSection, Says
from pydantic_evals import Case, Dataset

from emporio.data.store_db import read_connection

GENERAL_FORBIDDEN = (
    r"\b(get_order_status|get_product|search_products|policy_lookup|payment_terms|finish_conversation)\b",
    r"\b(refund|else|please|order)\b",
)
WITHDRAWAL = r"7 dias|sete dias|7 \(sete\)"


@dataclass(frozen=True)
class Scenario:
    messages: tuple[str, ...]
    today: date | None = None


def _delivered_order(conn: sqlite3.Connection) -> sqlite3.Row:
    return conn.execute(
        """
        SELECT o.tracking_code, o.estimated_delivery, c.name, c.phone, c.email, p.name AS item, o.total_brl
        FROM orders o JOIN customers c USING (customer_id)
        JOIN order_items i USING (order_id) JOIN products p USING (product_id)
        WHERE o.status = 'delivered' ORDER BY o.order_id DESC LIMIT 1
        """
    ).fetchone()


def dataset() -> Dataset:
    with read_connection() as conn:
        order = _delivered_order(conn)
    code, phone, email = order["tracking_code"], order["phone"], order["email"]
    details = {"tracking_code": code, "phone": phone, "email": email}
    asked = f"Quero devolver o pedido {code}, {email}, {phone}"
    three_days_after_delivery = date.fromisoformat(order["estimated_delivery"]) + timedelta(days=3)
    first_name = order["name"].split()[0]
    return Dataset(
        name="returns",
        evaluators=[NeverSays(GENERAL_FORBIDDEN)],
        cases=[
            Case(
                name="return: window closed",
                inputs=Scenario((asked,)),
                evaluators=[
                    CalledTool("get_order_status", details),
                    CalledTool("policy_lookup"),
                    ReturnedSection("4.1"),
                    Says((WITHDRAWAL, r"passou|encerr|expir|fechad|venc|já se")),
                    NeverSays((r"plataforma", r"solicitação formal", r"entregue (em|no dia)", r"24 horas")),
                ],
            ),
            Case(
                name="return: window open",
                inputs=Scenario((asked,), today=three_days_after_delivery),
                evaluators=[
                    CalledTool("get_order_status", details),
                    CalledTool("policy_lookup"),
                    ReturnedSection("4.1"),
                    Says((WITHDRAWAL, r"pode|possível|consegu|dentro do prazo")),
                    NeverSays((r"prazo (já )?(passou|expirou|encerr)", r"não (é|está) mais possível", r"entregue (em|no dia)")),
                ],
            ),
            Case(
                name="return: wrong phone",
                inputs=Scenario((f"Quero devolver o pedido {code}, {email}, (67) 90000-0000",)),
                evaluators=[
                    CalledTool("get_order_status", {"tracking_code": code, "email": email}),
                    Says((r"não foi possível|confirmar|conferir",)),
                    NeverSays((order["item"], first_name, r"159")),
                ],
            ),
        ],
    )

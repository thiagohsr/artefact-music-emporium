import sqlite3
from datetime import date

import pytest

from emporio.tools.orders import NOT_VERIFIED, get_order_status

TODAY = date(2025, 11, 1)
CODE = "BRAB1234567BR"


@pytest.fixture
def conn(store_conn):
    store_conn.row_factory = sqlite3.Row
    return store_conn


def owner(conn, order_id):
    return conn.execute(
        "SELECT c.customer_id, c.name, c.phone, c.email FROM orders o JOIN customers c USING (customer_id) WHERE o.order_id = ?",
        (order_id,),
    ).fetchone()


def test_correct_details_return_the_order(conn):
    customer = owner(conn, 1)

    result, verified = get_order_status(conn, CODE, customer["phone"], customer["email"], TODAY)

    assert result["verified"] is True
    assert result["status"] == "delivered"
    assert "2025-10-15" not in str(result)
    assert result["total_brl"] > 0
    assert result["payment_method"]
    assert result["items"][0]["quantity"] >= 1
    assert result["items"][0]["name"]
    assert result["tracking_code"] == "BRAB1234567BR"
    assert result["estimated_delivery"] == "2025-10-25"
    assert result["days_since_estimate"] == 7
    assert result["customer_name"] == customer["name"]
    assert verified.customer_id == customer["customer_id"]
    assert (verified.name, verified.phone, verified.email) == (customer["name"], customer["phone"], customer["email"])


def test_phone_compares_by_digits_and_email_ignores_case(conn):
    customer = owner(conn, 1)
    digits = "".join(c for c in customer["phone"] if c.isdigit())

    result, _ = get_order_status(conn, f" {CODE} ", digits, f"  {customer['email'].upper()} ", TODAY)

    assert result["verified"] is True


@pytest.mark.parametrize(
    ("order", "phone", "email"),
    [
        (CODE, "(67) 90000-0000", None),
        (CODE, None, "wrong@example.com"),
        (CODE, "", None),
        (CODE, None, ""),
        ("BRZZ9999999BR", None, None),
        ("", None, None),
        ("not a number", None, None),
    ],
)
def test_every_failure_gives_the_same_result(conn, order, phone, email):
    customer = owner(conn, 1)

    result, verified = get_order_status(conn, order, phone if phone is not None else customer["phone"], email if email is not None else customer["email"], TODAY)

    assert result == NOT_VERIFIED
    assert verified is None


def test_the_failure_reveals_nothing_about_the_customer_or_order(conn):
    assert set(NOT_VERIFIED) == {"verified", "message"}


def test_customers_sharing_an_email_cannot_reach_each_others_orders(conn):
    shared = {row["customer_id"]: row for row in conn.execute("SELECT * FROM customers WHERE customer_id IN (11, 43)")}
    assert shared[11]["email"] == shared[43]["email"]
    conn.execute("UPDATE orders SET tracking_code = 'BRZZ1111111BR' WHERE customer_id = 11")

    assert get_order_status(conn, "BRZZ1111111BR", shared[43]["phone"], shared[43]["email"], TODAY) == (NOT_VERIFIED, None)


def test_stored_total_is_never_recalculated(conn):
    customer = owner(conn, 3)

    result, _ = get_order_status(conn, "BRDZ4561230BR", customer["phone"], customer["email"], TODAY)

    assert result["total_brl"] == 3450.0


TRACKING_CODES = (
    "BRAB1234567BR",
    "BRCX9876543BR",
    "BRDZ4561230BR",
    "BRQM7890123BR",
    "BRTP3456789BR",
    "BRVN6543210BR",
    "BRKR1122334BR",
    "BRJL5544332BR",
)


def owner_by_code(conn, code):
    return conn.execute(
        """
        SELECT o.order_id, c.phone, c.email FROM orders o JOIN customers c USING (customer_id)
        WHERE o.tracking_code = ?
        """,
        (code,),
    ).fetchone()


def test_the_list_covers_every_tracking_code_in_the_data(conn):
    rows = conn.execute("SELECT tracking_code FROM orders WHERE tracking_code IS NOT NULL")

    assert {row["tracking_code"] for row in rows} == set(TRACKING_CODES)


@pytest.mark.parametrize("code", TRACKING_CODES)
def test_a_tracking_code_finds_its_order(conn, code):
    customer = owner_by_code(conn, code)

    result, verified = get_order_status(conn, code, customer["phone"], customer["email"], TODAY)

    assert result["verified"] is True
    assert result["tracking_code"] == code
    assert verified is not None


@pytest.mark.parametrize("written", ["brab1234567br", "  BRAB1234567BR ", "BRAB 1234567 BR", "BRAB-1234567-BR"])
def test_a_tracking_code_ignores_case_and_separators(conn, written):
    customer = owner_by_code(conn, "BRAB1234567BR")

    assert get_order_status(conn, written, customer["phone"], customer["email"], TODAY)[0]["verified"] is True


@pytest.mark.parametrize("code", TRACKING_CODES)
def test_a_tracking_code_with_another_customers_details_gives_the_same_failure(conn, code):
    customer = owner_by_code(conn, code)
    other = conn.execute(
        "SELECT phone, email FROM customers WHERE phone <> ? AND email <> ? LIMIT 1",
        (customer["phone"], customer["email"]),
    ).fetchone()

    assert get_order_status(conn, code, other["phone"], customer["email"], TODAY) == (NOT_VERIFIED, None)
    assert get_order_status(conn, code, customer["phone"], other["email"], TODAY) == (NOT_VERIFIED, None)


def test_the_digits_of_a_code_do_not_find_an_order(conn):
    customer = owner(conn, 1)

    assert get_order_status(conn, "BRXX0000001BR", customer["phone"], customer["email"], TODAY) == (NOT_VERIFIED, None)
    assert get_order_status(conn, "A1", customer["phone"], customer["email"], TODAY) == (NOT_VERIFIED, None)



@pytest.mark.parametrize("order_id", range(1, 21))
def test_an_order_id_never_finds_an_order(conn, order_id):
    customer = owner(conn, order_id)

    for written in (str(order_id), f"#{order_id}", f"{order_id:03d}"):
        assert get_order_status(conn, written, customer["phone"], customer["email"], TODAY) == (NOT_VERIFIED, None)


def returns_for(conn, code, today):
    customer = owner_by_code(conn, code)
    return get_order_status(conn, code, customer["phone"], customer["email"], today)[0]["returns"]


def test_every_window_is_open_within_its_days(conn):
    assert returns_for(conn, "BRAB1234567BR", date(2025, 11, 1)) == {
        "withdrawal_open": True,
        "preference_exchange_open": True,
        "defect_exchange_open": True,
    }


def test_withdrawal_and_preference_close_after_7_days_from_the_delivery_estimate(conn):
    returns = returns_for(conn, "BRAB1234567BR", date(2025, 11, 2))

    assert returns["withdrawal_open"] is False
    assert returns["preference_exchange_open"] is False
    assert returns["defect_exchange_open"] is True


def test_a_defect_exchange_closes_after_30_days_from_the_purchase(conn):
    assert returns_for(conn, "BRAB1234567BR", date(2025, 11, 15))["defect_exchange_open"] is False


def test_an_order_not_delivered_yet_has_no_return_windows(conn):
    assert returns_for(conn, "BRJL5544332BR", date(2026, 3, 1)) is None

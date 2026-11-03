import sqlite3
from datetime import date

import pytest

from emporio.tools.orders import NOT_VERIFIED, get_order_status

TODAY = date(2025, 11, 1)


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

    result, verified = get_order_status(conn, "1", customer["phone"], customer["email"], TODAY)

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

    result, _ = get_order_status(conn, "#1", digits, f"  {customer['email'].upper()} ", TODAY)

    assert result["verified"] is True


@pytest.mark.parametrize(
    ("order", "phone", "email"),
    [
        ("1", "(67) 90000-0000", None),
        ("1", None, "wrong@example.com"),
        ("1", "", None),
        ("1", None, ""),
        ("99999", None, None),
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
    orders = conn.execute("SELECT order_id, customer_id FROM orders WHERE customer_id IN (11, 43)").fetchall()
    assert orders

    for order in orders:
        other = shared[43 if order["customer_id"] == 11 else 11]
        result, verified = get_order_status(conn, str(order["order_id"]), other["phone"], other["email"], TODAY)
        assert result == NOT_VERIFIED
        assert verified is None


@pytest.mark.parametrize(("order_id", "total"), [(3, 3450.0), (20, 1400.0)])
def test_stored_total_is_never_recalculated(conn, order_id, total):
    customer = owner(conn, order_id)

    result, _ = get_order_status(conn, str(order_id), customer["phone"], customer["email"], TODAY)

    assert result["total_brl"] == total


def test_order_without_an_estimate_has_no_day_count(conn):
    row = conn.execute("SELECT order_id FROM orders WHERE estimated_delivery IS NULL LIMIT 1").fetchone()
    if row is None:
        pytest.skip("every order has an estimate in this data")
    customer = owner(conn, row["order_id"])

    result, _ = get_order_status(conn, str(row["order_id"]), customer["phone"], customer["email"], TODAY)

    assert result["days_since_estimate"] is None


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
    assert result["order_number"] == customer["order_id"]
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


def test_the_digits_of_a_code_are_not_read_as_an_order_number(conn):
    customer = owner(conn, 1)

    assert get_order_status(conn, "BRXX0000001BR", customer["phone"], customer["email"], TODAY) == (NOT_VERIFIED, None)
    assert get_order_status(conn, "A1", customer["phone"], customer["email"], TODAY) == (NOT_VERIFIED, None)


import sqlite3

import pytest

from emporio.tools.payments import payment_terms


@pytest.fixture
def conn(store_conn):
    store_conn.row_factory = sqlite3.Row
    return store_conn


def test_pix_takes_5_percent_off_the_list_price(conn):
    result = payment_terms(conn, "pix", product_name="Takamine GD20")

    assert result["final_price_brl"] == 2089.05
    assert result["allowed"] is True


def test_pix_gives_no_discount_on_a_promotional_price(conn):
    assert payment_terms(conn, "pix", product_name="Crafter HT-100")["final_price_brl"] == 1967.18


@pytest.mark.parametrize("method", ["debit", "boleto"])
def test_single_payment_methods_keep_the_price(conn, method):
    result = payment_terms(conn, method, product_name="Takamine GD20")

    assert result["final_price_brl"] == 2199.0
    assert result["allowed"] is True


def test_credit_uses_the_promotional_price(conn):
    result = payment_terms(conn, "credit", product_name="Crafter HT-100", installments=3)

    assert result["installment_brl"] == 655.73


def test_twelve_installments(conn):
    result = payment_terms(conn, "credit", product_name="Takamine GD20", installments=12)

    assert result == {
        "method": "credit",
        "final_price_brl": 2199.0,
        "installments": 12,
        "installment_brl": 183.25,
        "minimum_installment_brl": 100.0,
        "max_installments": 12,
        "max_installment_brl": 183.25,
        "allowed": True,
        "reason": None,
    }


def test_below_the_minimum_is_not_allowed(conn):
    result = payment_terms(conn, "credit", amount_brl=500, installments=10)

    assert result["allowed"] is False
    assert result["reason"] == "below_minimum"
    assert result["installment_brl"] == 50.0
    assert result["minimum_installment_brl"] == 100.0


@pytest.mark.parametrize(
    ("amount", "installments", "allowed"),
    [
        (150, 3, True),
        (149.99, 3, False),
        (320, 4, True),
        (319.99, 4, False),
        (480, 6, True),
        (479.99, 6, False),
        (700, 7, True),
        (699.99, 7, False),
        (1200, 12, True),
        (1199.99, 12, False),
    ],
)
def test_minimum_boundaries_per_tier(conn, amount, installments, allowed):
    assert payment_terms(conn, "credit", amount_brl=amount, installments=installments)["allowed"] is allowed


def test_one_installment_has_no_minimum(conn):
    assert payment_terms(conn, "credit", amount_brl=30, installments=1)["allowed"] is True


def test_more_than_twelve_installments_is_not_allowed(conn):
    result = payment_terms(conn, "credit", amount_brl=5000, installments=13)

    assert result["allowed"] is False
    assert result["reason"] == "too_many_installments"


def test_single_payment_methods_have_no_installments(conn):
    result = payment_terms(conn, "pix", amount_brl=5000, installments=2)

    assert result["allowed"] is False
    assert result["reason"] == "too_many_installments"


def test_decimal_rounding_is_exact(conn):
    assert payment_terms(conn, "pix", amount_brl=19.99)["final_price_brl"] == 18.99
    assert payment_terms(conn, "credit", amount_brl=1000, installments=3)["installment_brl"] == 333.33


def test_product_not_found_is_data(conn):
    assert payment_terms(conn, "credit", product_name="Stradivarius", installments=3) == {
        "allowed": False,
        "reason": "product_not_found",
    }


def test_a_price_or_a_product_is_required(conn):
    assert payment_terms(conn, "credit", installments=3)["reason"] == "price_required"


@pytest.mark.parametrize(
    ("amount", "most", "each"),
    [(2199, 12, 183.25), (1200, 12, 100.0), (1199, 11, 109.0), (500, 6, 83.33), (100, 2, 50.0), (49.9, 1, 49.9)],
)
def test_credit_says_how_many_installments_the_price_allows(conn, amount, most, each):
    result = payment_terms(conn, "credit", amount_brl=amount, installments=1)

    assert result["max_installments"] == most
    assert result["max_installment_brl"] == each


def test_a_product_says_how_many_installments_it_allows(conn):
    result = payment_terms(conn, "credit", product_name="Takamine GD20", installments=1)

    assert (result["max_installments"], result["max_installment_brl"]) == (12, 183.25)


@pytest.mark.parametrize("method", ["pix", "debit", "boleto"])
def test_other_methods_allow_a_single_payment(conn, method):
    result = payment_terms(conn, method, amount_brl=500, installments=1)

    assert result["max_installments"] == 1
    assert result["max_installment_brl"] == result["final_price_brl"]

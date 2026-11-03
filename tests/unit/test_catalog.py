import sqlite3

import pytest

from emporio.tools.catalog import MAX_RESULTS, get_product, search_products


def names(result):
    return [product["name"] for product in result["products"]]


@pytest.fixture
def conn(store_conn):
    store_conn.row_factory = sqlite3.Row
    return store_conn


@pytest.mark.parametrize("text", ["violão", "violao", "violões", "Violoes"])
def test_text_matches_a_category_with_or_without_accents_and_plural(conn, text):
    products = search_products(conn, text=text)["products"]

    assert products
    assert {p["category"] for p in products} == {"Violões"}


def test_text_does_not_confuse_a_violin_with_an_acoustic_guitar(conn):
    assert not [p for p in search_products(conn, text="violão")["products"] if "Violino" in p["name"]]


def test_text_finds_a_brand(conn):
    assert all("Takamine" in name for name in names(search_products(conn, text="Takamine")))
    assert len(names(search_products(conn, text="Takamine"))) == 4


def test_filter_by_category(conn):
    assert {p["category"] for p in search_products(conn, category="Guitarras")["products"]} == {"Guitarras"}


def test_price_range_includes_both_limits(conn):
    result = search_products(conn, category="Guitarras", min_price_brl=7500, max_price_brl=12500)

    assert sorted(p["price_brl"] for p in result["products"]) == [7500.0, 12500.0]


def test_price_limits_work_alone(conn):
    assert all(p["price_brl"] <= 1000 for p in search_products(conn, max_price_brl=1000)["products"])
    assert all(p["price_brl"] >= 7000 for p in search_products(conn, min_price_brl=7000)["products"])


def test_range_compares_with_the_final_price_under_a_promotion(conn):
    # Crafter HT-100 costs R$ 2,399.00, and R$ 1,967.18 with its 18% promotion.
    assert "Crafter HT-100 Folk Aço Natural" in names(search_products(conn, text="Crafter", max_price_brl=2000))
    assert "Crafter HT-100 Folk Aço Natural" not in names(search_products(conn, text="Crafter", min_price_brl=2100))


def test_in_stock_only_leaves_out_empty_and_not_yet_available_products(conn):
    products = search_products(conn, in_stock_only=True, text="Giannini")["products"]

    assert "Giannini GF-3D Dreadnought Sunburst" not in [p["name"] for p in products]
    assert not [p for p in search_products(conn, in_stock_only=True, text="Kala")["products"] if p["availability"] == "not_yet_available"]


def test_results_are_limited(conn):
    result = search_products(conn)

    assert len(result["products"]) == MAX_RESULTS
    assert result["total"] > MAX_RESULTS


def test_discontinued_products_are_left_out_of_search(conn):
    assert "Shelby SN-7C 7 Cordas Nylon Natural" not in names(search_products(conn, text="Shelby"))


def test_get_product_returns_one_match_with_specs(conn):
    result = get_product(conn, "Takamine GD20")

    assert result["found"] is True
    assert result["product"]["price_brl"] == 2199.0
    assert result["product"]["availability"] == "in_stock"
    assert result["product"]["specs"]


def test_get_product_ignores_accents_and_case(conn):
    assert get_product(conn, "crafter ht-100 folk aco")["found"] is True


def test_get_product_accepts_the_category_with_the_name(conn):
    assert get_product(conn, "violão Giannini GF-3D")["found"] is True


def test_get_product_gives_close_matches_when_several_fit(conn):
    result = get_product(conn, "Takamine")

    assert result["found"] is False
    assert len(result["close_matches"]) == 4


def test_get_product_not_found_is_data(conn):
    assert get_product(conn, "Stradivarius 1721") == {"found": False, "close_matches": []}


def test_active_promotion_has_original_price_percentage_and_final_price(conn):
    product = get_product(conn, "Crafter HT-100")["product"]

    assert product["promotion"] == {"original_price_brl": 2399.0, "discount_percent": 18, "final_price_brl": 1967.18}
    assert product["price_brl"] == 1967.18


def test_inactive_promotion_is_ignored(conn):
    product = get_product(conn, "Crafter CE-15")["product"]

    assert product["promotion"] is None
    assert product["price_brl"] == 3899.0


@pytest.mark.parametrize(
    ("name", "availability"),
    [
        ("Giannini GF-3D", "out_of_stock"),
        ("Shelby SN-7C", "discontinued"),
        ("Ibanez Bass 2X", "discontinued"),
        ("Kala KA-ABP-CTG", "not_yet_available"),
    ],
)
def test_availability_follows_status_before_stock(conn, name, availability):
    assert get_product(conn, name)["product"]["availability"] == availability


def test_search_says_how_many_results_it_left_out(conn):
    result = search_products(conn, category="Violões", max_price_brl=1000)

    assert result["total"] > result["shown"] == len(result["products"]) == 10


def test_search_shows_every_result_under_the_limit(conn):
    result = search_products(conn, text="Takamine GD20")

    assert result["total"] == result["shown"] == len(result["products"])

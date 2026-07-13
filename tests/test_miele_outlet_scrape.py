"""Tests for miele_outlet_scrape.py.

The `if __name__ == "__main__":` CLI block (argparse wiring, locale/table
printing) is intentionally not covered here -- it isn't factored into a
testable function and isn't worth the effort.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

import miele_outlet_scrape as mos


class FakePage:
    """A fake pypdf page whose extract_text() returns fixed text."""

    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class FakeReader:
    """A fake pypdf.PdfReader with a fixed list of pages."""

    def __init__(self, pages_text):
        self.pages = [FakePage(text) for text in pages_text]


# ---------------------------------------------------------------------------
# parse_pdf
# ---------------------------------------------------------------------------


def test_parse_pdf_builds_matches_and_update_info():
    page1 = "\n".join(
        [
            "Miele Outlet B1 Grade Pricelist - Updated 01/07/2026",
            "This is a random header line that should not match anything",
            "11111111 Duoflex HX1 Terra Red GB Duoflex Outlet B1 Stock "
            "£299.00 £199.00",
            "22222222 Blizzard CX1 EU1 Blizzard Outlet B2 Stock "
            "£499.00 £399.00 £349.00",
        ]
    )
    page2 = "\n".join(
        [
            "Miele Outlet B2 Grade Pricelist - Updated 02/07/2026",
            "11111111 Duoflex HX1 Terra Red GB Duoflex Outlet B1 Stock "
            "£299.00 £249.00",
        ]
    )
    fake_reader = FakeReader([page1, page2])

    with patch.object(mos, "load_pdf", return_value=fake_reader) as mock_load_pdf:
        matches, update_info = mos.parse_pdf()

    mock_load_pdf.assert_called_once()

    # update_info captured per grade, from lines on both pages.
    assert update_info == {"B1": "01/07/2026", "B2": "02/07/2026"}

    # Only the two real product rows were parsed; the header line was ignored.
    assert set(matches.keys()) == {"11111111", "22222222"}

    product = matches["11111111"]
    assert product["url"] == "https://www.miele.co.uk/product/11111111"
    assert product["status"] == "Unknown"
    # The same product id appeared on two different lines/pages.
    assert len(product["available_units"]) == 2

    unit_no_discount, unit_from_page2 = product["available_units"]

    # Row with only rrp + price (no discounted_price column).
    assert unit_no_discount["description"] == "Duoflex HX1 Terra Red"
    assert unit_no_discount["product_name"] == "Duoflex"
    assert unit_no_discount["grade"] == "B1"
    assert unit_no_discount["rrp"] == 299.00
    assert unit_no_discount["price"] == 199.00
    assert unit_no_discount["discounted_price"] == 0
    # discount_rate computed from price when there's no discounted_price.
    assert unit_no_discount["discount_rate"] == pytest.approx(33.44)

    assert unit_from_page2["price"] == 249.00
    assert unit_from_page2["discounted_price"] == 0
    assert unit_from_page2["discount_rate"] == pytest.approx(16.72)

    other_product = matches["22222222"]
    assert len(other_product["available_units"]) == 1
    unit_with_discount = other_product["available_units"][0]

    assert unit_with_discount["description"] == "Blizzard CX1"
    assert unit_with_discount["product_name"] == "Blizzard"
    assert unit_with_discount["grade"] == "B2"
    assert unit_with_discount["rrp"] == 499.00
    assert unit_with_discount["price"] == 399.00
    assert unit_with_discount["discounted_price"] == 349.00
    # discount_rate must be computed from discounted_price, not price.
    assert unit_with_discount["discount_rate"] == pytest.approx(30.06)

    # id and url must not leak into the per-unit dict.
    assert "id" not in unit_with_discount
    assert "url" not in unit_with_discount


def test_parse_pdf_strips_product_sheet_boilerplate_with_marker():
    # Real pricelist rows have a "Product Sheet" hyperlink caption extracted
    # inline right before "Outlet ... Stock" - it must not leak into
    # description/product_name.
    page = (
        "12656400 G 5450 SCVi Active Plus stainless steel GB Fully integrated "
        "dishwashers 60 cm Product Sheet Outlet B1 Stock £1,149.00 £919.20 £749.00"
    )
    fake_reader = FakeReader([page])

    with patch.object(mos, "load_pdf", return_value=fake_reader):
        matches, _update_info = mos.parse_pdf()

    unit = matches["12656400"]["available_units"][0]
    assert unit["description"] == "G 5450 SCVi Active Plus stainless steel"
    assert unit["product_name"] == "Fully integrated dishwashers 60 cm"
    assert "Product Sheet" not in unit["description"]
    assert "Product Sheet" not in unit["product_name"]


def test_parse_pdf_strips_product_sheet_boilerplate_without_marker():
    # Accessory rows have no GB/EU1 marker at all, so the whole description
    # (including the "Product Sheet" suffix) stays in one piece pre-strip.
    page = (
        "10694310 Coffee pot 1,0 l Accessories Coffee Product Sheet "
        "Outlet B1 Stock £200.49 £150.37"
    )
    fake_reader = FakeReader([page])

    with patch.object(mos, "load_pdf", return_value=fake_reader):
        matches, _update_info = mos.parse_pdf()

    unit = matches["10694310"]["available_units"][0]
    assert unit["description"] == "Coffee pot 1,0 l Accessories Coffee"
    assert unit["product_name"] == ""
    assert "Product Sheet" not in unit["description"]


def test_parse_pdf_splits_gb_marker_glued_to_previous_word():
    # Some rows have no space before the marker at all (a PDF text-extraction
    # artifact) - the split must still fire in that case.
    page = (
        "12656400 G 5450 SCVi Active Plus stainless steGB Fully integrated "
        "dishwashers 60 cm Product Sheet Outlet B1 Stock £1,149.00 £919.20 £749.00"
    )
    fake_reader = FakeReader([page])

    with patch.object(mos, "load_pdf", return_value=fake_reader):
        matches, _update_info = mos.parse_pdf()

    unit = matches["12656400"]["available_units"][0]
    assert unit["description"] == "G 5450 SCVi Active Plus stainless ste"
    assert unit["product_name"] == "Fully integrated dishwashers 60 cm"


def test_parse_pdf_ignores_non_matching_lines_only():
    page = "\n".join(
        [
            "Not a product line at all",
            "Another line of noise 123 abc",
        ]
    )
    fake_reader = FakeReader([page])

    with patch.object(mos, "load_pdf", return_value=fake_reader):
        matches, update_info = mos.parse_pdf()

    assert matches == {}
    assert update_info == {}


# ---------------------------------------------------------------------------
# filter_products
# ---------------------------------------------------------------------------


def _make_unit(description, product_name, grade, price, discounted_price=0, rrp=None):
    return {
        "description": description,
        "product_name": product_name,
        "grade": grade,
        "rrp": rrp if rrp is not None else price,
        "price": price,
        "discounted_price": discounted_price,
        "discount_rate": 0,
    }


def _make_products(units_by_id, status="Unknown"):
    """Build a products dict of the shape produced by parse_pdf()."""
    return {
        product_id: {
            "url": f"https://www.miele.co.uk/product/{product_id}",
            "status": status,
            "available_units": list(units),
        }
        for product_id, units in units_by_id.items()
    }


def test_filter_products_empty_filter_matches_everything():
    products = _make_products(
        {
            "1": [_make_unit("Duoflex vacuum", "Duoflex", "B1", 100.0)],
            "2": [_make_unit("Blizzard CX1", "Blizzard", "B2", 200.0)],
        }
    )
    result = mos.filter_products(products, {}, "", "", None, False)

    assert set(result.keys()) == {"1", "2"}


def test_filter_products_filters_by_product_name_case_insensitive():
    products = _make_products(
        {
            "1": [_make_unit("Duoflex vacuum", "Duoflex", "B1", 100.0)],
            "2": [_make_unit("Blizzard CX1", "Blizzard", "B2", 200.0)],
        }
    )
    result = mos.filter_products(products, {}, "duoflex", "", None, False)

    assert set(result.keys()) == {"1"}


def test_filter_products_filters_by_description_case_insensitive():
    products = _make_products(
        {
            "1": [_make_unit("Duoflex vacuum cleaner", "Duoflex", "B1", 100.0)],
            "2": [_make_unit("Blizzard CX1", "Blizzard", "B2", 200.0)],
        }
    )
    # "VACUUM" only appears in the description, not the product_name.
    result = mos.filter_products(products, {}, "VACUUM", "", None, False)

    assert set(result.keys()) == {"1"}


def test_filter_products_grade_filter_restricts_to_matching_grade():
    products = _make_products(
        {
            "1": [_make_unit("Duoflex vacuum", "Duoflex", "B1", 100.0)],
            "2": [_make_unit("Blizzard CX1", "Blizzard", "B2", 200.0)],
        }
    )
    result = mos.filter_products(products, {}, "", "B2", None, False)

    assert set(result.keys()) == {"2"}


def test_filter_products_empty_grade_string_matches_all_grades():
    products = _make_products(
        {
            "1": [_make_unit("Duoflex vacuum", "Duoflex", "B1", 100.0)],
            "2": [_make_unit("Blizzard CX1", "Blizzard", "B2", 200.0)],
        }
    )
    result = mos.filter_products(products, {}, "", "", None, False)

    assert set(result.keys()) == {"1", "2"}


def test_filter_products_max_price_matches_on_price():
    products = _make_products(
        {
            "1": [_make_unit("Duoflex vacuum", "Duoflex", "B1", 100.0)],
        }
    )
    result = mos.filter_products(products, {}, "", "", 150.0, False)

    assert set(result.keys()) == {"1"}


def test_filter_products_max_price_matches_on_discounted_price():
    # price is above max_price, but discounted_price is at/below it.
    products = _make_products(
        {
            "1": [
                _make_unit(
                    "Duoflex vacuum",
                    "Duoflex",
                    "B1",
                    price=300.0,
                    discounted_price=100.0,
                    rrp=400.0,
                )
            ],
        }
    )
    result = mos.filter_products(products, {}, "", "", 150.0, False)

    assert set(result.keys()) == {"1"}


def test_filter_products_max_price_excludes_when_neither_price_qualifies():
    products = _make_products(
        {
            "1": [
                _make_unit(
                    "Duoflex vacuum",
                    "Duoflex",
                    "B1",
                    price=300.0,
                    discounted_price=0,
                    rrp=400.0,
                )
            ],
        }
    )
    result = mos.filter_products(products, {}, "", "", 150.0, False)

    assert result == {}


def test_filter_products_filter_with_regex_metacharacters_does_not_crash():
    # A plain search term containing regex metacharacters must not be
    # interpreted as a regex (previously crashed with an unbalanced group).
    products = _make_products(
        {
            "1": [_make_unit("Washer (8kg)", "Duoflex", "B1", 100.0)],
        }
    )
    result = mos.filter_products(products, {}, "(8kg)", "", None, False)

    assert set(result.keys()) == {"1"}


def test_filter_products_filter_matches_literally_not_as_regex():
    # "." in the filter must match a literal dot, not "any character".
    products = _make_products(
        {
            "1": [_make_unit("Model X.1", "Duoflex", "B1", 100.0)],
            "2": [_make_unit("Model XY1", "Duoflex", "B2", 100.0)],
        }
    )
    result = mos.filter_products(products, {}, "X.1", "", None, False)

    assert set(result.keys()) == {"1"}


def test_filter_products_drops_products_with_no_matching_units():
    products = _make_products(
        {
            "1": [_make_unit("Duoflex vacuum", "Duoflex", "B1", 100.0)],
        }
    )
    # Filter string that matches nothing.
    result = mos.filter_products(products, {}, "nonexistent-product", "", None, False)

    assert result == {}


def test_filter_products_check_status_true_calls_and_stores_status():
    products = _make_products(
        {
            "1": [_make_unit("Duoflex vacuum", "Duoflex", "B1", 100.0)],
        },
        status="Unknown",
    )

    with patch.object(mos, "check_product_status", return_value="Active") as mock_check:
        result = mos.filter_products(products, {}, "", "", None, True)

    mock_check.assert_called_once_with("https://www.miele.co.uk/product/1")
    assert result["1"]["status"] == "Active"


def test_filter_products_check_status_false_leaves_status_untouched():
    products = _make_products(
        {
            "1": [_make_unit("Duoflex vacuum", "Duoflex", "B1", 100.0)],
        },
        status="Unknown",
    )

    with patch.object(mos, "check_product_status") as mock_check:
        result = mos.filter_products(products, {}, "", "", None, False)

    mock_check.assert_not_called()
    assert result["1"]["status"] == "Unknown"


# ---------------------------------------------------------------------------
# check_product_status
# ---------------------------------------------------------------------------


def test_check_product_status_returns_inactive_on_404():
    fake_response = MagicMock(status_code=404)
    with patch.object(mos.requests, "get", return_value=fake_response):
        assert mos.check_product_status("https://example.com/product/1") == "Inactive"


def test_check_product_status_returns_active_on_200():
    fake_response = MagicMock(status_code=200)
    with patch.object(mos.requests, "get", return_value=fake_response):
        assert mos.check_product_status("https://example.com/product/1") == "Active"


def test_check_product_status_returns_error_on_other_status_codes():
    # A 5xx (or any non-200/404) response is not confidently "Active" - it
    # should be surfaced as an error, not silently reported as live.
    fake_response = MagicMock(status_code=500)
    with patch.object(mos.requests, "get", return_value=fake_response):
        assert mos.check_product_status("https://example.com/product/1") == "Error"


def test_check_product_status_returns_error_on_request_exception():
    with patch.object(mos.requests, "get", side_effect=requests.RequestException("boom")):
        assert mos.check_product_status("https://example.com/product/1") == "Error"


def test_check_product_status_passes_a_timeout():
    fake_response = MagicMock(status_code=200)
    with patch.object(mos.requests, "get", return_value=fake_response) as mock_get:
        mos.check_product_status("https://example.com/product/1")

    _args, kwargs = mock_get.call_args
    assert kwargs.get("timeout") is not None


# ---------------------------------------------------------------------------
# load_pdf
# ---------------------------------------------------------------------------


def test_load_pdf_downloads_and_builds_reader():
    fake_content = b"%PDF-1.4 fake pdf bytes"
    fake_response = MagicMock()
    fake_response.content = fake_content

    with (
        patch.object(mos.requests, "get", return_value=fake_response) as mock_get,
        patch.object(mos, "PdfReader") as mock_pdf_reader,
    ):
        result = mos.load_pdf()

    mock_get.assert_called_once()
    _args, kwargs = mock_get.call_args
    assert kwargs.get("timeout") is not None
    fake_response.raise_for_status.assert_called_once()

    mock_pdf_reader.assert_called_once()
    (bytes_io_arg,), _kwargs = mock_pdf_reader.call_args
    assert bytes_io_arg.read() == fake_content
    assert result is mock_pdf_reader.return_value


def test_load_pdf_propagates_raise_for_status_errors():
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = requests.HTTPError("500 error")

    with (
        patch.object(mos.requests, "get", return_value=fake_response),
        patch.object(mos, "PdfReader") as mock_pdf_reader,
    ):
        with pytest.raises(requests.HTTPError):
            mos.load_pdf()

    mock_pdf_reader.assert_not_called()

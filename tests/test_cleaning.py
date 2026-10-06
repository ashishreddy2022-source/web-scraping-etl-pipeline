"""
test_cleaning.py
----------------
Unit tests for the cleaning functions in processing/cleaning.py.

These tests require NO internet connection — they verify pure functions
with hardcoded input/output pairs.

Run with:
    pytest tests/test_cleaning.py -v
"""

import pytest
from processing.cleaning import (
    clean_text,
    strip_quotes,
    clean_price,
    clean_rating,
    clean_tags,
    normalize_url,
    clean_record,
)


# ------------------------------------------------------------------
# clean_text
# ------------------------------------------------------------------
class TestCleanText:
    def test_collapses_whitespace(self):
        assert clean_text("  Hello \n  World ") == "Hello World"

    def test_removes_non_breaking_spaces(self):
        assert clean_text("hello\xa0world") == "hello world"

    def test_strips_tabs_and_newlines(self):
        assert clean_text("\t\nSome\t text\n") == "Some text"

    def test_returns_none_for_none(self):
        assert clean_text(None) is None

    def test_returns_none_for_empty_string(self):
        assert clean_text("   ") is None

    def test_single_word(self):
        assert clean_text("Python") == "Python"


# ------------------------------------------------------------------
# strip_quotes
# ------------------------------------------------------------------
class TestStripQuotes:
    def test_removes_curly_quotes(self):
        assert strip_quotes("\u201cThe world is a book.\u201d") == "The world is a book."

    def test_removes_straight_quotes(self):
        assert strip_quotes('"Hello"') == "Hello"

    def test_returns_none_for_none(self):
        assert strip_quotes(None) is None

    def test_no_quotes_unchanged(self):
        assert strip_quotes("No quotes here") == "No quotes here"


# ------------------------------------------------------------------
# clean_price
# ------------------------------------------------------------------
class TestCleanPrice:
    def test_british_pound(self):
        assert clean_price("£51.77") == 51.77

    def test_with_comma(self):
        assert clean_price("£1,002.50") == 1002.5

    def test_garbled_pound(self):
        """Handles the Â£ encoding artefact."""
        assert clean_price("Â£23.99") == 23.99

    def test_integer_price(self):
        assert clean_price("£10") == 10.0

    def test_returns_none_for_none(self):
        assert clean_price(None) is None

    def test_returns_none_for_empty(self):
        assert clean_price("") is None

    def test_returns_none_for_no_digits(self):
        assert clean_price("free") is None


# ------------------------------------------------------------------
# clean_rating
# ------------------------------------------------------------------
class TestCleanRating:
    @pytest.mark.parametrize("raw,expected", [
        ("star-rating One", 1),
        ("star-rating Two", 2),
        ("star-rating Three", 3),
        ("star-rating Four", 4),
        ("star-rating Five", 5),
    ])
    def test_word_to_int(self, raw, expected):
        assert clean_rating(raw) == expected

    def test_case_insensitive(self):
        assert clean_rating("STAR-RATING THREE") == 3

    def test_returns_none_for_none(self):
        assert clean_rating(None) is None

    def test_returns_none_for_unknown_word(self):
        assert clean_rating("star-rating unknown") is None


# ------------------------------------------------------------------
# clean_tags
# ------------------------------------------------------------------
class TestCleanTags:
    def test_sorts_and_lowercases(self):
        assert clean_tags(["Love", "life", "Inspirational"]) == "inspirational;life;love"

    def test_single_tag(self):
        assert clean_tags(["humor"]) == "humor"

    def test_returns_none_for_empty_list(self):
        assert clean_tags([]) is None

    def test_returns_none_for_none(self):
        assert clean_tags(None) is None

    def test_strips_whitespace_in_tags(self):
        assert clean_tags(["  love ", " life "]) == "life;love"


# ------------------------------------------------------------------
# normalize_url
# ------------------------------------------------------------------
class TestNormalizeUrl:
    def test_absolute_url_unchanged(self):
        url = "https://books.toscrape.com/catalogue/page-1.html"
        assert normalize_url(url) == url

    def test_relative_with_base(self):
        result = normalize_url(
            "../page-2.html",
            "https://books.toscrape.com/catalogue/page-1.html",
        )
        assert result == "https://books.toscrape.com/page-2.html"

    def test_returns_none_for_none(self):
        assert normalize_url(None) is None

    def test_returns_none_for_empty(self):
        assert normalize_url("") is None


# ------------------------------------------------------------------
# clean_record (integration of all cleaners)
# ------------------------------------------------------------------
class TestCleanRecord:
    def test_book_record(self):
        raw = {
            "source": "Books to Scrape",
            "source_url": "https://books.toscrape.com/catalogue/a-book_1/index.html",
            "name_or_title": "  A Great  Book ",
            "category": None,
            "price_raw": "£51.77",
            "rating_raw": "star-rating Three",
            "author": None,
            "tags_raw": None,
            "description": None,
            "scraped_at": "2026-01-01T00:00:00+00:00",
        }
        cleaned = clean_record(raw)
        assert cleaned["name_or_title"] == "A Great Book"
        assert cleaned["price"] == 51.77
        assert cleaned["rating"] == 3
        assert cleaned["author"] is None
        assert cleaned["tags"] is None

    def test_quote_record(self):
        raw = {
            "source": "Quotes to Scrape",
            "source_url": "https://quotes.toscrape.com/author/Author/",
            "name_or_title": "\u201cThe world is a book.\u201d",
            "category": None,
            "price_raw": None,
            "rating_raw": None,
            "author": "  Albert  Einstein ",
            "tags_raw": ["Love", "life"],
            "description": None,
            "scraped_at": "2026-01-01T00:00:00+00:00",
        }
        cleaned = clean_record(raw)
        assert cleaned["name_or_title"] == "The world is a book."
        assert cleaned["price"] is None
        assert cleaned["rating"] is None
        assert cleaned["author"] == "Albert Einstein"
        assert cleaned["tags"] == "life;love"

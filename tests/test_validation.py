"""
test_validation.py
------------------
Unit tests for the validation functions in processing/validation.py.

No internet connection required — all inputs are plain dictionaries.

Run with:
    pytest tests/test_validation.py -v
"""

from processing.validation import validate_record, validate_records


# ------------------------------------------------------------------
# Helper to build a valid base record
# ------------------------------------------------------------------
def _valid_book(**overrides) -> dict:
    """Return a valid book record, optionally overriding specific fields."""
    base = {
        "source": "Books to Scrape",
        "source_url": "https://books.toscrape.com/catalogue/a-book_1/index.html",
        "name_or_title": "A Great Book",
        "category": None,
        "price": 51.77,
        "rating": 3,
        "author": None,
        "tags": None,
        "description": None,
        "scraped_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _valid_quote(**overrides) -> dict:
    """Return a valid quote record, optionally overriding specific fields."""
    base = {
        "source": "Quotes to Scrape",
        "source_url": "https://quotes.toscrape.com/author/Einstein/",
        "name_or_title": "The world is a book.",
        "category": None,
        "price": None,
        "rating": None,
        "author": "Albert Einstein",
        "tags": "inspirational;life",
        "description": None,
        "scraped_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------------
# Single-record validation
# ------------------------------------------------------------------
class TestValidateRecord:
    def test_valid_book_passes(self):
        assert validate_record(_valid_book()) == []

    def test_valid_quote_passes(self):
        assert validate_record(_valid_quote()) == []

    def test_unknown_source(self):
        problems = validate_record(_valid_book(source="Random Site"))
        assert "unknown_source" in problems

    def test_missing_name(self):
        problems = validate_record(_valid_book(name_or_title=""))
        assert "missing_name" in problems

    def test_none_name(self):
        problems = validate_record(_valid_book(name_or_title=None))
        assert "missing_name" in problems

    def test_invalid_url_no_scheme(self):
        problems = validate_record(_valid_book(source_url="books.toscrape.com"))
        assert "invalid_url" in problems

    def test_invalid_url_none(self):
        problems = validate_record(_valid_book(source_url=None))
        assert "invalid_url" in problems

    def test_negative_price(self):
        problems = validate_record(_valid_book(price=-5.0))
        assert "invalid_price" in problems

    def test_price_not_a_number(self):
        problems = validate_record(_valid_book(price="free"))
        assert "invalid_price" in problems

    def test_none_price_is_ok(self):
        """Quotes don't have prices — None must be accepted."""
        assert validate_record(_valid_quote(price=None)) == []

    def test_rating_out_of_range(self):
        problems = validate_record(_valid_book(rating=6))
        assert "invalid_rating" in problems

    def test_rating_zero(self):
        problems = validate_record(_valid_book(rating=0))
        assert "invalid_rating" in problems

    def test_none_rating_is_ok(self):
        """Quotes don't have ratings — None must be accepted."""
        assert validate_record(_valid_quote(rating=None)) == []

    def test_multiple_problems(self):
        """A record can fail on more than one rule at once."""
        problems = validate_record(_valid_book(
            source="Bad",
            name_or_title="",
            source_url="nope",
        ))
        assert "unknown_source" in problems
        assert "missing_name" in problems
        assert "invalid_url" in problems


# ------------------------------------------------------------------
# Batch validation
# ------------------------------------------------------------------
class TestValidateRecords:
    def test_all_valid(self):
        records = [_valid_book(), _valid_quote()]
        valid, rejected, reasons = validate_records(records)
        assert len(valid) == 2
        assert len(rejected) == 0
        assert reasons == {}

    def test_some_rejected(self):
        records = [
            _valid_book(),
            _valid_book(name_or_title=""),  # bad
            _valid_quote(),
        ]
        valid, rejected, reasons = validate_records(records)
        assert len(valid) == 2
        assert len(rejected) == 1
        assert reasons.get("missing_name") == 1

    def test_all_rejected(self):
        records = [
            _valid_book(source="X", name_or_title=""),
            _valid_quote(source_url="nope"),
        ]
        valid, rejected, reasons = validate_records(records)
        assert len(valid) == 0
        assert len(rejected) == 2

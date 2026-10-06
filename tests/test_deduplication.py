"""
test_deduplication.py
---------------------
Unit tests for fingerprint generation and duplicate detection in
processing/deduplication.py.

These tests use deliberately duplicated sample records to prove the
logic works, because the real practice sites contain only unique items
and the actual run will likely find 0 duplicates.

Run with:
    pytest tests/test_deduplication.py -v
"""

from processing.deduplication import make_fingerprint, find_duplicates


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _book(title: str) -> dict:
    return {
        "source": "Books to Scrape",
        "name_or_title": title,
        "author": None,
    }


def _quote(author: str, text: str) -> dict:
    return {
        "source": "Quotes to Scrape",
        "name_or_title": text,
        "author": author,
    }


# ------------------------------------------------------------------
# Fingerprint tests
# ------------------------------------------------------------------
class TestMakeFingerprint:
    def test_same_title_same_fingerprint(self):
        fp1 = make_fingerprint(_book("A Light in the Attic"))
        fp2 = make_fingerprint(_book("A Light in the Attic"))
        assert fp1 == fp2

    def test_case_insensitive(self):
        fp1 = make_fingerprint(_book("Example Book Title"))
        fp2 = make_fingerprint(_book("EXAMPLE BOOK TITLE"))
        assert fp1 == fp2

    def test_whitespace_insensitive(self):
        fp1 = make_fingerprint(_book("Example Book Title"))
        fp2 = make_fingerprint(_book("  Example Book Title "))
        assert fp1 == fp2

    def test_punctuation_insensitive(self):
        fp1 = make_fingerprint(_book("It's a Wonderful Life"))
        fp2 = make_fingerprint(_book("Its a Wonderful Life"))
        assert fp1 == fp2

    def test_different_titles_different_fingerprint(self):
        fp1 = make_fingerprint(_book("Book A"))
        fp2 = make_fingerprint(_book("Book B"))
        assert fp1 != fp2

    def test_quote_fingerprint_uses_author(self):
        """Two quotes with the same text but different authors are distinct."""
        fp1 = make_fingerprint(_quote("Einstein", "Life is beautiful"))
        fp2 = make_fingerprint(_quote("Gandhi", "Life is beautiful"))
        assert fp1 != fp2

    def test_quote_fingerprint_uses_first_50_chars(self):
        """Only the first 50 characters matter — longer tails are ignored."""
        long_text = "A" * 100
        short_text = "A" * 50
        fp1 = make_fingerprint(_quote("Author", long_text))
        fp2 = make_fingerprint(_quote("Author", short_text))
        assert fp1 == fp2


# ------------------------------------------------------------------
# Duplicate detection tests
# ------------------------------------------------------------------
class TestFindDuplicates:
    def test_no_duplicates(self):
        records = [_book("Book A"), _book("Book B"), _book("Book C")]
        unique, dupes = find_duplicates(records)
        assert len(unique) == 3
        assert len(dupes) == 0

    def test_exact_duplicate(self):
        records = [
            _book("Example Book Title"),
            _book("Example Book Title"),
        ]
        unique, dupes = find_duplicates(records)
        assert len(unique) == 1
        assert len(dupes) == 1

    def test_case_and_space_duplicates(self):
        """The classic test from the assignment spec."""
        records = [
            _book("Example Book Title"),
            _book("  Example Book Title "),
            _book("EXAMPLE BOOK TITLE"),
        ]
        unique, dupes = find_duplicates(records)
        assert len(unique) == 1
        assert len(dupes) == 2

    def test_mixed_sources(self):
        """Books and quotes with the same text are NOT duplicates
        because the source is part of the fingerprint."""
        records = [
            _book("Shared Title"),
            _quote("Author", "Shared Title"),
        ]
        unique, dupes = find_duplicates(records)
        assert len(unique) == 2
        assert len(dupes) == 0

    def test_preserves_first_occurrence(self):
        """The first record should always survive deduplication."""
        records = [
            {**_book("Same Title"), "price": 10.0},
            {**_book("Same Title"), "price": 20.0},
        ]
        unique, dupes = find_duplicates(records)
        assert len(unique) == 1
        assert unique[0]["price"] == 10.0   # first one kept

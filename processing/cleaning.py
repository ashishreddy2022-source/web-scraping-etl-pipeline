"""
cleaning.py
-----------
Pure functions that transform a single raw value into a clean value.
None of these functions touch the internet or the filesystem — they
only work on plain strings and numbers, which makes them trivial to
unit-test.

Functions
---------
clean_text       – collapse whitespace, strip non-breaking spaces
strip_quotes     – remove curly quotation marks wrapping quote text
clean_price      – "£51.77" → 51.77
clean_rating     – "star-rating Three" → 3
clean_tags       – ["Love", "life"] → "life;love" (lowered, sorted, joined)
normalize_url    – ensure the URL starts with http:// or https://
clean_record     – apply all relevant cleaners to one raw record dict
"""

import re
from urllib.parse import urljoin

# Maps the word rating found in the HTML class to an integer 1–5
RATING_MAP = {
    "one":   1,
    "two":   2,
    "three": 3,
    "four":  4,
    "five":  5,
}


def clean_text(value: str | None) -> str | None:
    """Collapse all whitespace (including \\xa0) into single spaces, then strip.

    >>> clean_text("  Hello \\n  World ")
    'Hello World'
    >>> clean_text(None)
    """
    if value is None:
        return None
    text = " ".join(value.replace("\xa0", " ").split())
    return text or None   # empty string → None


def strip_quotes(value: str | None) -> str | None:
    """Remove the curly \u201c…\u201d quotation marks that wrap every quote on quotes.toscrape.com.

    >>> strip_quotes('\u201cThe world is a book.\u201d')
    'The world is a book.'
    """
    if value is None:
        return None
    return value.strip("\u201c\u201d\"'  ")


def clean_price(raw: str | None) -> float | None:
    """Extract the first decimal number from a price string.

    >>> clean_price("£51.77")
    51.77
    >>> clean_price("Â£1,002.50")
    1002.5
    >>> clean_price(None)
    """
    if not raw:
        return None
    match = re.search(r"\d+(?:\.\d+)?", raw.replace(",", ""))
    return float(match.group()) if match else None


def clean_rating(raw: str | None) -> int | None:
    """Turn a rating class string like 'star-rating Three' into the integer 3.

    >>> clean_rating("star-rating Three")
    3
    >>> clean_rating(None)
    """
    for word in (raw or "").lower().split():
        if word in RATING_MAP:
            return RATING_MAP[word]
    return None


def clean_tags(tags_raw) -> str | None:
    """Lowercase, sort, and semicolon-join a list of tag strings.

    >>> clean_tags(["Love", "life", "Inspirational"])
    'inspirational;life;love'
    >>> clean_tags(None)
    >>> clean_tags([])
    """
    if not tags_raw:
        return None
    cleaned = sorted(t.strip().lower() for t in tags_raw if t.strip())
    return ";".join(cleaned) or None


def normalize_url(url: str | None, base: str = "") -> str | None:
    """Ensure the URL is absolute (starts with http:// or https://).

    If the URL is relative and a base is provided, urljoin them.
    Returns None for empty or un-fixable values.

    >>> normalize_url("/catalogue/a-book_1/index.html",
    ...              "https://books.toscrape.com/catalogue/page-1.html")
    'https://books.toscrape.com/catalogue/a-book_1/index.html'
    """
    if not url:
        return None
    url = url.strip()
    if url.startswith(("http://", "https://")):
        return url
    if base:
        return urljoin(base, url)
    return None


# ------------------------------------------------------------------
# Record-level cleaning
# ------------------------------------------------------------------
def clean_record(raw: dict) -> dict:
    """Apply all cleaning functions to one raw record and return a new dict
    with the common data-model columns.

    Fields that don't exist for a source (e.g. price for quotes) stay None.
    """
    return {
        "source":        raw.get("source"),
        "source_url":    normalize_url(raw.get("source_url")),
        "name_or_title": strip_quotes(clean_text(raw.get("name_or_title"))),
        "category":      clean_text(raw.get("category")),
        "price":         clean_price(raw.get("price_raw")),
        "rating":        clean_rating(raw.get("rating_raw")),
        "author":        clean_text(raw.get("author")),
        "tags":          clean_tags(raw.get("tags_raw")),
        "description":   clean_text(raw.get("description")),
        "scraped_at":    raw.get("scraped_at"),
    }

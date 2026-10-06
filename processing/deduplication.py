"""
deduplication.py
----------------
Detects duplicate records by building a normalised fingerprint from each
record's identifying fields and keeping a set of fingerprints already seen.

Fingerprint strategy
--------------------
- Books:  source + name_or_title
- Quotes: source + author + first 50 characters of quote text

The fingerprint is case-insensitive, ignores punctuation, collapses
whitespace, and returns a SHA-256 hex digest.  This means:
    "Example Book Title"
    "  Example Book Title "
    "EXAMPLE BOOK TITLE"
all produce the same fingerprint → the later ones are flagged as duplicates.

Design choice: duplicates are **dropped** (not kept with a flag).
Rationale — the assignment asks for "one tidy CSV", and keeping dupes
with a column would force the consumer to filter them out.  This decision
is documented in the README.
"""

import hashlib
import logging
import re

logger = logging.getLogger(__name__)


def make_fingerprint(rec: dict) -> str:
    """Create a normalised SHA-256 fingerprint for duplicate detection."""
    if rec.get("source") == "Books to Scrape":
        key = f'{rec["source"]} {rec.get("name_or_title", "")}'
    else:
        # For quotes, include the author and first 50 chars of the text
        title_slice = (rec.get("name_or_title") or "")[:50]
        key = f'{rec["source"]} {rec.get("author", "")} {title_slice}'

    # Normalise: lowercase → drop punctuation → collapse spaces
    key = re.sub(r"[^\w\s]", "", key.lower())
    key = " ".join(key.split())

    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def find_duplicates(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split records into unique and duplicate lists.

    Parameters
    ----------
    records : list[dict]
        Already-validated records (from both sources combined).

    Returns
    -------
    (unique, duplicates)
        unique     – first occurrence of each fingerprint
        duplicates – every subsequent occurrence
    """
    seen: set[str] = set()
    unique: list[dict] = []
    duplicates: list[dict] = []

    for rec in records:
        fp = make_fingerprint(rec)
        if fp in seen:
            duplicates.append(rec)
            logger.info(
                "Duplicate detected: '%s'",
                (rec.get("name_or_title") or "")[:60],
            )
        else:
            unique.append(rec)
            seen.add(fp)

    logger.info(
        "Deduplication complete: %d unique, %d duplicates",
        len(unique), len(duplicates),
    )
    return unique, duplicates

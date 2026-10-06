"""
validation.py
-------------
Validates one cleaned record against the business rules.

The validate_record() function returns a list of human-readable problem
strings.  An empty list means the record passed all checks and can move
on to deduplication.

Rules
-----
1. source       – must be one of the two allowed site names
2. name_or_title – must not be empty
3. source_url   – must start with http:// or https://
4. price        – if present, must be a number >= 0
5. rating       – if present, must be an integer 1–5
"""

import logging

logger = logging.getLogger(__name__)

VALID_SOURCES = {"Books to Scrape", "Quotes to Scrape"}


def validate_record(rec: dict) -> list[str]:
    """Check one cleaned record against the rules above.

    Returns
    -------
    list[str]
        Empty → record is valid.
        Non-empty → each item is a short reason code explaining what failed.
    """
    problems: list[str] = []

    # 1. Source must be one we recognise
    if rec.get("source") not in VALID_SOURCES:
        problems.append("unknown_source")

    # 2. Every record needs a title / quote text
    if not rec.get("name_or_title"):
        problems.append("missing_name")

    # 3. URL must look like a real web address
    url = str(rec.get("source_url") or "")
    if not url.startswith(("http://", "https://")):
        problems.append("invalid_url")

    # 4. Price is optional, but if it exists it must be a non-negative number
    price = rec.get("price")
    if price is not None:
        if not isinstance(price, (int, float)) or price < 0:
            problems.append("invalid_price")

    # 5. Rating is optional, but if present it must be 1, 2, 3, 4, or 5
    rating = rec.get("rating")
    if rating is not None:
        if rating not in (1, 2, 3, 4, 5):
            problems.append("invalid_rating")

    return problems


def validate_records(records: list[dict]) -> tuple[list[dict], list[dict], dict]:
    """Validate a list of records.

    Returns
    -------
    (valid, rejected, reason_counts)
        valid          – records with no problems
        rejected       – records that failed at least one check
        reason_counts  – {reason_code: count} across all rejected records
    """
    valid: list[dict] = []
    rejected: list[dict] = []
    reason_counts: dict[str, int] = {}

    for rec in records:
        problems = validate_record(rec)
        if problems:
            rejected.append(rec)
            for reason in problems:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            logger.warning(
                "Rejected record '%s': %s",
                (rec.get("name_or_title") or "<no title>")[:60],
                ", ".join(problems),
            )
        else:
            valid.append(rec)

    return valid, rejected, reason_counts

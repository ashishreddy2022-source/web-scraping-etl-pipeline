"""
main.py
-------
Entry point for the scraping pipeline.

Usage:
    python main.py

What it does (in order):
    1. Scrape   — fetch every page of both sites (Books + Quotes)
    2. Clean    — normalise text, prices, ratings, tags, URLs
    3. Validate — reject records that fail the business rules
    4. Dedup    — remove records with identical fingerprints
    5. Save     — write final_dataset.csv, summary_report.json, scraper.log

Each source is wrapped in its own try/except so a failure in one site
does not prevent the other from completing.
"""

import csv
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper
from processing.cleaning import clean_record
from processing.validation import validate_records
from processing.deduplication import find_duplicates

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
CSV_PATH = OUTPUT_DIR / "final_dataset.csv"
JSON_PATH = OUTPUT_DIR / "summary_report.json"
LOG_PATH = LOG_DIR / "scraper.log"

# Column order for the CSV — every row uses this exact set of columns
CSV_COLUMNS = [
    "source",
    "source_url",
    "name_or_title",
    "category",
    "price",
    "rating",
    "author",
    "tags",
    "description",
    "scraped_at",
]


# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
def setup_logging() -> None:
    """Configure logging to write to both the console and a log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Formatter shared by both handlers
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (INFO and above)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root_logger.addHandler(console)

    # File handler (DEBUG and above — captures everything)
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root_logger.addHandler(file_handler)


# ------------------------------------------------------------------
# Output writers
# ------------------------------------------------------------------
def write_csv(records: list[dict], path: Path) -> None:
    """Write the final dataset to a UTF-8 CSV with a fixed column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def write_summary(stats: dict, path: Path) -> None:
    """Write the summary report as a pretty-printed JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------
def main() -> None:
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("=" * 60)
    logger.info("Pipeline started")
    logger.info("=" * 60)

    start_time = time.time()
    start_iso = datetime.now(timezone.utc).isoformat()

    # ---- Stage 1: Scrape ----
    raw_books: list[dict] = []
    raw_quotes: list[dict] = []

    try:
        logger.info("--- Scraping Books to Scrape ---")
        raw_books = BooksScraper(delay=0.5).scrape_all_pages()
        logger.info("Books scraped: %d raw records", len(raw_books))
    except Exception as exc:
        logger.error("Books scraper crashed: %s", exc)

    try:
        logger.info("--- Scraping Quotes to Scrape ---")
        raw_quotes = QuotesScraper(delay=0.5).scrape_all_pages()
        logger.info("Quotes scraped: %d raw records", len(raw_quotes))
    except Exception as exc:
        logger.error("Quotes scraper crashed: %s", exc)

    # ---- Stage 2: Clean ----
    logger.info("--- Cleaning records ---")
    cleaned_books = [clean_record(r) for r in raw_books]
    cleaned_quotes = [clean_record(r) for r in raw_quotes]
    all_cleaned = cleaned_books + cleaned_quotes
    logger.info(
        "Cleaned: %d books + %d quotes = %d total",
        len(cleaned_books), len(cleaned_quotes), len(all_cleaned),
    )

    # ---- Stage 3: Validate ----
    logger.info("--- Validating records ---")
    valid, rejected, reason_counts = validate_records(all_cleaned)
    logger.info("Valid: %d | Rejected: %d", len(valid), len(rejected))
    for reason, count in sorted(reason_counts.items()):
        logger.info("  rejection reason: %-20s  count: %d", reason, count)

    # ---- Stage 4: Deduplicate ----
    logger.info("--- Deduplicating records ---")
    unique, duplicates = find_duplicates(valid)
    logger.info("Unique: %d | Duplicates: %d", len(unique), len(duplicates))

    # ---- Stage 5: Write outputs ----
    logger.info("--- Writing output files ---")
    write_csv(unique, CSV_PATH)
    logger.info("CSV written to %s (%d rows)", CSV_PATH, len(unique))

    end_time = time.time()
    end_iso = datetime.now(timezone.utc).isoformat()
    duration = round(end_time - start_time, 2)

    summary = {
        "run": {
            "start_time": start_iso,
            "end_time": end_iso,
            "duration_seconds": duration,
        },
        "collected_per_source": {
            "Books to Scrape": len(raw_books),
            "Quotes to Scrape": len(raw_quotes),
        },
        "cleaned_per_source": {
            "Books to Scrape": len(cleaned_books),
            "Quotes to Scrape": len(cleaned_quotes),
        },
        "rejected_total": len(rejected),
        "rejected_by_reason": reason_counts,
        "duplicates_detected": len(duplicates),
        "final_record_count": len(unique),
    }
    write_summary(summary, JSON_PATH)
    logger.info("Summary written to %s", JSON_PATH)

    # ---- Done ----
    logger.info("=" * 60)
    logger.info(
        "Pipeline finished in %.1f s — %d records in final dataset",
        duration, len(unique),
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

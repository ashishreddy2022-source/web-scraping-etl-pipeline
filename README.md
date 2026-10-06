# Web Scraping ETL Pipeline — Realisieren Technologies Assignment

A Python program that scrapes data from two practice websites, cleans it, validates it, removes duplicates, and produces one tidy CSV file plus a JSON summary report. One command runs the whole job:

```bash
python main.py
```

---

## Table of Contents

1. [Overview](#overview)  
2. [Project Structure](#project-structure)  
3. [Setup & Installation](#setup--installation)  
4. [How to Run](#how-to-run)  
5. [How Pagination Works](#how-pagination-works)  
6. [HTML Selectors (Page Inspection)](#html-selectors-page-inspection)  
7. [Data Model](#data-model)  
8. [Cleaning Logic](#cleaning-logic)  
9. [Validation Rules](#validation-rules)  
10. [Duplicate Detection](#duplicate-detection)  
11. [Error Handling](#error-handling)  
12. [Running Tests](#running-tests)  
13. [Output Files](#output-files)  
14. [Assumptions & Limitations](#assumptions--limitations)  

---

## Overview

This project builds a small **ETL pipeline** (Extract → Transform → Load) that:

1. **Scrapes** every page of [Books to Scrape](https://books.toscrape.com/) (~1 000 books over 50 pages) and [Quotes to Scrape](https://quotes.toscrape.com/) (~100 quotes over 10 pages) using dynamic "next-link" pagination.
2. **Cleans** messy raw values — removes currency symbols, converts word-ratings to integers, collapses whitespace, strips curly quotes.
3. **Validates** each record against business rules and rejects bad records with reason codes.
4. **Deduplicates** using SHA-256 fingerprints that ignore case, punctuation, and extra whitespace.
5. **Saves** a unified `final_dataset.csv`, a `summary_report.json`, and a `scraper.log` file.

The pipeline is designed so that a failure in one source (e.g., Books) does **not** crash the other (Quotes). Each stage is isolated and independently testable.

---

## Project Structure

```
scraping_assignment/
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py       # shared HTTP session, retries, timeout, delay
│   ├── books_scraper.py      # Books to Scrape selectors + pagination
│   └── quotes_scraper.py     # Quotes to Scrape selectors + pagination
├── processing/
│   ├── __init__.py
│   ├── cleaning.py           # text, price, rating, tag, URL cleaning
│   ├── validation.py         # record checks; returns a list of problems
│   └── deduplication.py      # fingerprint + duplicate detection
├── tests/
│   ├── __init__.py
│   ├── test_cleaning.py
│   ├── test_validation.py
│   └── test_deduplication.py
├── output/                   # created automatically by the program
│   ├── final_dataset.csv
│   └── summary_report.json
├── logs/                     # created automatically by the program
│   └── scraper.log
├── main.py                   # entry point — run this
├── requirements.txt
├── README.md                 # you are here
└── AI_USAGE.md
```

**Design rule:** if a function talks to the internet, it lives in `scrapers/`. If it only transforms data, it lives in `processing/`. If it connects the stages, it lives in `main.py`.

---

## Setup & Installation

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 – 3.12 |
| pip | bundled with Python |
| Internet | required to reach the two practice sites |

### Steps

```bash
# 1. Clone or unzip the project, then enter the folder
cd scraping_assignment

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
#    Windows:
venv\Scripts\activate
#    macOS / Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

After activation your terminal prompt should show `(venv)`.

### Dependencies (from `requirements.txt`)

| Library | Version | Purpose |
|---|---|---|
| `requests` | 2.31.0 | Downloads HTML pages |
| `beautifulsoup4` | 4.12.3 | Parses HTML for data extraction |
| `lxml` | 5.2.2 | Fast parser back-end for BeautifulSoup |
| `pytest` | 8.2.2 | Runs unit tests |

---

## How to Run

```bash
# Make sure the virtual environment is active, then:
python main.py
```

The program prints progress to the console and creates three files:

- `output/final_dataset.csv`
- `output/summary_report.json`
- `logs/scraper.log`

Typical runtime is about **10 minutes** (60 pages × 0.5 s delay per page, plus network latency).

---

## How Pagination Works

Both sites use the same pattern: a `<li class="next">` element at the bottom of each page contains a link to the next page. The scraper:

1. Starts at the known first-page URL.
2. Downloads and parses the page.
3. Extracts all records on that page.
4. Looks for `li.next > a`. If found, converts the relative `href` to an absolute URL using `urllib.parse.urljoin` and repeats. If not found, stops.

This is **dynamic pagination** — the code never hard-codes a page count like `range(1, 51)`. If the site adds or removes pages, the scraper adapts automatically.

```
Page 1 → extract records → find "next" link → Page 2 → … → last page (no "next") → stop
```

---

## HTML Selectors (Page Inspection)

These selectors were found by right-clicking elements in Chrome DevTools (F12):

| Item | Books to Scrape | Quotes to Scrape |
|---|---|---|
| One record | `article.product_pod` | `div.quote` |
| Main text | `h3 > a[title]` — full title is in the `title` attribute, visible text is truncated | `span.text` — wrapped in curly " " quotes |
| Price | `p.price_color` (e.g. `£51.77`) | n/a |
| Rating | class on `p.star-rating` (e.g. `Three`) | n/a |
| Author | n/a | `small.author` |
| Tags | n/a | `a.tag` (zero or more) |
| Link | `h3 > a[href]` (relative path) | `a[href^="/author/"]` (author page) |
| Next page | `li.next > a` | `li.next > a` |

---

## Data Model

Both sources are mapped to one common set of columns. Fields that don't apply are left empty (`None`), never given fake values.

| Column | Type | Books | Quotes |
|---|---|---|---|
| `source` | string | `"Books to Scrape"` | `"Quotes to Scrape"` |
| `source_url` | string | Detail page URL | Author page URL |
| `name_or_title` | string | Book title | Quote text |
| `category` | string | Empty (not on listing page) | Empty |
| `price` | float | e.g. `51.77` | Empty |
| `rating` | int | 1–5 | Empty |
| `author` | string | Empty | Author name |
| `tags` | string | Empty | `"tag1;tag2"` (lowercased, sorted) |
| `description` | string | Empty (not on listing page) | Empty |
| `scraped_at` | ISO 8601 | UTC timestamp | UTC timestamp |

---

## Cleaning Logic

Each cleaning function is a small, pure function in `processing/cleaning.py`:

| Function | What it does | Example |
|---|---|---|
| `clean_text()` | Collapse whitespace, strip `\xa0` | `"  Hello \n World "` → `"Hello World"` |
| `strip_quotes()` | Remove curly `"…"` marks | `"\u201cLife is good.\u201d"` → `"Life is good."` |
| `clean_price()` | Extract numeric value | `"£51.77"` → `51.77` |
| `clean_rating()` | Map word to integer | `"star-rating Three"` → `3` |
| `clean_tags()` | Lowercase, sort, join | `["Love", "life"]` → `"life;love"` |
| `normalize_url()` | Ensure absolute URL | relative path → full `https://…` URL |

The `clean_record()` function applies all relevant cleaners to one raw dict.

---

## Validation Rules

After cleaning, every record is checked by `validate_record()` in `processing/validation.py`. The function returns a list of problem codes — an empty list means the record is valid.

| Rule | Check | Reason code |
|---|---|---|
| Known source | `source` ∈ `{"Books to Scrape", "Quotes to Scrape"}` | `unknown_source` |
| Has a name | `name_or_title` is not empty | `missing_name` |
| Valid URL | `source_url` starts with `http://` or `https://` | `invalid_url` |
| Valid price | If present, is a number ≥ 0 | `invalid_price` |
| Valid rating | If present, is 1, 2, 3, 4, or 5 | `invalid_rating` |

Records that fail validation are **rejected** (excluded from the final CSV). The rejection counts and reasons are recorded in the summary report.

---

## Duplicate Detection

Duplicates are detected using SHA-256 fingerprints in `processing/deduplication.py`.

### Fingerprint strategy

| Source | Identifying fields |
|---|---|
| Books | `source` + `name_or_title` |
| Quotes | `source` + `author` + first 50 characters of `name_or_title` |

Before hashing, the combined key is:
1. Lowercased
2. Stripped of punctuation
3. Collapsed to single spaces

This means `"Example Book Title"`, `"  Example Book Title "`, and `"EXAMPLE BOOK TITLE"` all produce the **same** fingerprint.

### Design decision: drop duplicates

Duplicates are **removed** (not flagged with a column). Rationale: the assignment asks for "one tidy CSV", and keeping duplicates with an extra column would force the consumer to filter them out.

> **Note:** Both practice sites contain only unique items, so a real run typically finds **0 duplicates**. The unit tests in `test_deduplication.py` use deliberately duplicated sample records to prove the logic works.

---

## Error Handling

| Scenario | What happens |
|---|---|
| HTTP error (404, 500, etc.) | Logged as ERROR; that source stops, but the other source still runs |
| Network timeout | Retried up to 3 times with exponential back-off (1 s → 2 s → 4 s) |
| Rate limiting (429) | Retried automatically by the session adapter |
| Missing HTML element | `.select_one()` returns `None`; checked before access, field set to `None` |
| One bad record on a page | Wrapped in `try/except`, logged as WARNING, skipped; rest of page continues |
| One whole source fails | Wrapped in `try/except` in `main.py`; the other source still runs |

A 0.5-second delay between requests keeps the scraper polite to the servers.

---

## Running Tests

```bash
# Run all unit tests (no internet needed)
pytest tests/ -v

# Run a specific test file
pytest tests/test_cleaning.py -v
```

The test suite covers:
- **Cleaning:** whitespace, prices, ratings, tags, URLs, full-record integration
- **Validation:** every rule, edge cases (None, negative, out-of-range), multiple failures
- **Deduplication:** case/space/punctuation insensitivity, cross-source distinction, first-occurrence preservation

---

## Output Files

| File | Description |
|---|---|
| `output/final_dataset.csv` | One row per unique, valid record from both sites. Fixed column order, UTF-8 encoded. |
| `output/summary_report.json` | Counts: raw records per source, cleaned, rejected (with reasons), duplicates, final total, run duration. |
| `logs/scraper.log` | Timestamped log of every request, page change, warning, and error. |

### Sample summary report structure

```json
{
    "run": {
        "start_time": "2026-01-01T00:00:00+00:00",
        "end_time": "2026-01-01T00:10:12+00:00",
        "duration_seconds": 612.4
    },
    "collected_per_source": {
        "Books to Scrape": 1000,
        "Quotes to Scrape": 100
    },
    "cleaned_per_source": {
        "Books to Scrape": 1000,
        "Quotes to Scrape": 100
    },
    "rejected_total": 0,
    "rejected_by_reason": {},
    "duplicates_detected": 0,
    "final_record_count": 1100
}
```

The numbers must reconcile: **raw − rejected − duplicates = final count**.

---

## Assumptions & Limitations

1. **Category and description are left empty for books.** The listing pages don't show these fields. Fetching each book's detail page would require ~1 000 extra requests, which I chose to skip to keep the scraper fast and polite. This is a known trade-off, not a bug.

2. **The `source_url` for quotes is the author's page URL**, not the page where the quote appeared. This was a design choice documented in the data model above.

3. **The program expects an internet connection.** If both sites are unreachable, the CSV will be empty and the summary will show 0 records.

4. **Both practice sites currently contain only unique items**, so the duplicate count will normally be 0. The deduplication logic is proven correct by unit tests with deliberately duplicated data.

5. **Python 3.10+ is required** for the `X | Y` type-union syntax used in type hints.

6. **Why Requests + BeautifulSoup (not Selenium)?** Both target sites are plain server-rendered HTML — no JavaScript needs to run. Selenium or Playwright would only add startup time, memory, and a browser dependency with no benefit.

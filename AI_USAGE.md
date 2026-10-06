# AI Usage Disclosure

This document describes how AI tools were used during the development of this web scraping assignment, what was changed after reviewing the AI's output, and how the final code was tested.

---

## Tools Used

| Tool | What I used it for |
|---|---|
| Google Gemini (Antigravity IDE) | Code generation, debugging, brainstorming the data model, writing documentation |

---

## How AI Helped

### 1. Project structure and boilerplate

I asked the AI to help scaffold the project folder structure based on the assignment spec. It generated the initial `__init__.py` files, the folder layout, and the `requirements.txt`. I reviewed the structure against Section 4 of the assignment and confirmed it matched.

### 2. HTTP session with retries

**Prompt (paraphrased):** *"Create a requests session with a User-Agent header, 10-second timeout, and automatic retries for 429/5xx errors with exponential back-off."*

The AI produced the `create_session()` function using `HTTPAdapter` and `urllib3.util.Retry`. I verified it against the `requests` documentation and tested it manually by hitting `https://books.toscrape.com/` — status code 200 returned correctly.

### 3. Cleaning functions

**Prompt (paraphrased):** *"Write small pure functions to clean price strings like £51.77 into floats, rating words like Three into integers, and whitespace from text."*

The AI gave me the `clean_price`, `clean_rating`, and `clean_text` functions. I added `strip_quotes` myself after inspecting the Quotes to Scrape site and noticing the curly quotation marks around every quote — the AI's initial version didn't handle those.

### 4. Duplicate fingerprinting

**Prompt (paraphrased):** *"How can I detect duplicates across records where spacing and capitalisation differ?"*

The AI suggested normalising the identifying fields (lowercase, strip punctuation, collapse spaces) and hashing with SHA-256. I adapted this to use different field combinations for books vs. quotes, as specified in the assignment (source + title for books, source + author + first 50 chars for quotes).

### 5. Documentation

The AI helped draft sections of this README and the inline docstrings. I rewrote the "Assumptions & Limitations" and "How Pagination Works" sections in my own words to make sure they match what the code actually does.

---

## What I Changed After Reviewing AI Output

1. **Curly-quote stripping:** The AI's initial `clean_text` function didn't remove the `"…"` marks wrapping quote text on Quotes to Scrape. I added the `strip_quotes()` function and integrated it into `clean_record()`.

2. **Book title from `title` attribute:** The AI initially used `.get_text()` on the `<a>` tag, which returns truncated text (e.g., `"A Light in the ..."`) instead of the full title. After inspecting the HTML, I changed it to `link.get("title")` which contains the full, untruncated title.

3. **`response.encoding = "utf-8"`:** The AI's first scraper version didn't set the encoding, which caused `£` to appear as `Â£` on some systems. I added this line after debugging a garbled price in my initial test run.

4. **Logging levels:** The AI used `print()` statements for status messages. I replaced them with proper `logging` calls at the correct levels (INFO for progress, WARNING for rejected records, ERROR for failed requests) and configured dual output (console + file).

5. **Test data:** The AI generated generic test cases. I added specific edge cases I encountered during development — for example, `clean_price("Â£23.99")` for the encoding artefact, and a test proving that books and quotes with the same text are NOT duplicates because the source differs.

---

## Mistakes Found in AI Suggestions

1. The AI suggested using `Selenium` at first — unnecessary for static HTML sites and would add a browser dependency.
2. It hard-coded `range(1, 51)` for pagination instead of following the "next" link dynamically.
3. The deduplication function originally didn't account for the `source` field in the fingerprint, which could have merged a book and a quote with the same title.

All three were caught during my code review and fixed before submission.

---

## How I Tested the Final Code

1. **Unit tests (offline):** Ran `pytest tests/ -v` to verify all cleaning, validation, and deduplication functions with no internet connection.
2. **Full pipeline run:** Ran `python main.py` and checked:
   - The CSV contains rows from both sources (~1 000 books + ~100 quotes).
   - Prices are plain numbers (no `£` symbol).
   - Ratings are integers 1–5.
   - The JSON summary's `final_record_count` matches the CSV row count.
3. **Fresh environment:** Deleted `venv/`, created a new one, installed from `requirements.txt`, and ran the pipeline again to confirm reproducibility.
4. **Log review:** Opened `logs/scraper.log` to confirm every page was logged with its URL and that no ERRORs appeared during a normal run.

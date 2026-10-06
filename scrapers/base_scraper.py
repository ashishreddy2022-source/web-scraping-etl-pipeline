"""
base_scraper.py
---------------
Shared networking layer for all scrapers.

Creates a single requests.Session with:
  - a custom User-Agent so the target site knows we're a polite learning bot
  - automatic retries (3 attempts) with exponential back-off for transient
    HTTP errors (429, 500, 502, 503, 504)
  - a default 10-second timeout on every request
  - a configurable delay between consecutive requests (default 0.5 s)

Both BooksScraper and QuotesScraper inherit from BaseScraper so the
networking logic is written once and tested once.
"""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def create_session() -> requests.Session:
    """Build a resilient HTTP session with retries and a polite User-Agent."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "ScrapingAssignment/1.0 (learning project)"
    })

    # Retry up to 3 times on temporary server errors, waiting 1s → 2s → 4s
    retries = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class BaseScraper:
    """Common scraping behaviour shared by every site-specific scraper.

    Subclasses must implement:
      - parse_page(soup, page_url)  →  list[dict]
    """

    def __init__(self, start_url: str, delay: float = 0.5):
        self.start_url = start_url
        self.delay = delay
        self.session = create_session()

    # ------------------------------------------------------------------
    # Dynamic pagination
    # ------------------------------------------------------------------
    def scrape_all_pages(self) -> list[dict]:
        """Follow the 'next' link until there are no more pages.

        Returns a list of raw dictionaries — one per scraped item —
        exactly as the HTML provided them (no cleaning yet).
        """
        url = self.start_url
        page_number = 1
        all_records: list[dict] = []

        while url:
            logger.info("Page %d: %s", page_number, url)
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                response.encoding = "utf-8"         # keeps £ sign correct
            except requests.RequestException as exc:
                logger.error("Failed to fetch %s: %s", url, exc)
                break   # stop THIS source; main.py keeps the program alive

            soup = BeautifulSoup(response.text, "lxml")

            # Let the subclass decide how to pull items out of the page
            try:
                page_records = self.parse_page(soup, url)
                all_records.extend(page_records)
                logger.info(
                    "  → extracted %d records (running total: %d)",
                    len(page_records), len(all_records),
                )
            except Exception as exc:
                logger.error(
                    "Error parsing page %d (%s): %s", page_number, url, exc
                )

            # Find the "next" link — same CSS selector on both sites
            next_link = soup.select_one("li.next > a")
            url = urljoin(url, next_link["href"]) if next_link else None
            page_number += 1
            time.sleep(self.delay)

        logger.info(
            "Finished scraping %s — %d total records",
            self.start_url, len(all_records),
        )
        return all_records

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------
    def parse_page(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        """Extract every item on a single page.  Override in subclass."""
        raise NotImplementedError

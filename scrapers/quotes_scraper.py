"""
quotes_scraper.py
-----------------
Scraper for https://quotes.toscrape.com/

HTML structure (found via browser Inspect):
  - Each quote block:  <div class="quote">
  - Quote text:        span.text   (wrapped in curly "…" quotation marks)
  - Author:            small.author
  - Tags:              a.tag       (zero or more per quote)
  - Author page link:  a[href^="/author/"]
  - Next page:         li.next > a

Quotes have no price, rating, category, or description, so those columns
are left as None in the common data model.
"""

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

QUOTES_START_URL = "https://quotes.toscrape.com/page/1/"


class QuotesScraper(BaseScraper):
    """Extract every quote from quotes.toscrape.com with dynamic pagination."""

    def __init__(self, delay: float = 0.5):
        super().__init__(start_url=QUOTES_START_URL, delay=delay)

    def parse_page(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        """Return one raw dict per <div class="quote"> on the page."""
        records = []
        quote_divs = soup.select("div.quote")

        for div in quote_divs:
            try:
                record = self._parse_one_quote(div, page_url)
                records.append(record)
            except Exception as exc:
                logger.warning("Skipping a quote on %s: %s", page_url, exc)

        return records

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_one_quote(div: Tag, page_url: str) -> dict:
        """Pull text, author, tags, and link from a single quote block."""
        text_tag = div.select_one("span.text")
        author_tag = div.select_one("small.author")
        tag_links = div.select("a.tag")
        author_link = div.select_one('a[href^="/author/"]')

        quote_text = text_tag.get_text(strip=True) if text_tag else None
        author = author_tag.get_text(strip=True) if author_tag else None
        tags = [t.get_text(strip=True) for t in tag_links] if tag_links else []

        # Use the author-page URL as the source_url for this record
        href = (
            urljoin(page_url, author_link["href"])
            if author_link and author_link.get("href")
            else page_url
        )

        return {
            "source":        "Quotes to Scrape",
            "source_url":    href,
            "name_or_title": quote_text,
            "category":      None,
            "price_raw":     None,
            "rating_raw":    None,
            "author":        author,
            "tags_raw":      tags,          # list; cleaned later to "a;b;c"
            "description":   None,
            "scraped_at":    datetime.now(timezone.utc).isoformat(),
        }

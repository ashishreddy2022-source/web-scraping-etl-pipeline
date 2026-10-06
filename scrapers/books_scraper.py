"""
books_scraper.py
----------------
Scraper for https://books.toscrape.com/

HTML structure (found via browser Inspect):
  - Each book card:  <article class="product_pod">
  - Title:           h3 > a[title]  (the visible text is truncated with "…")
  - Price:           p.price_color  (e.g. "£51.77")
  - Rating:          p.star-rating  class list includes the word (e.g. "Three")
  - Detail link:     h3 > a[href]   (relative URL)
  - Next page:       li.next > a

The listing page does NOT show category or description, so those fields
are left empty.  This trade-off avoids ~1 000 extra HTTP requests and is
documented in the README.
"""

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BOOKS_START_URL = "https://books.toscrape.com/catalogue/page-1.html"


class BooksScraper(BaseScraper):
    """Extract every book from books.toscrape.com with dynamic pagination."""

    def __init__(self, delay: float = 0.5):
        super().__init__(start_url=BOOKS_START_URL, delay=delay)

    def parse_page(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        """Return one raw dict per <article class="product_pod"> on the page."""
        records = []
        articles = soup.select("article.product_pod")

        for article in articles:
            try:
                record = self._parse_one_book(article, page_url)
                records.append(record)
            except Exception as exc:
                # One broken card must not kill the whole page
                logger.warning("Skipping a book card on %s: %s", page_url, exc)

        return records

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_one_book(article: Tag, page_url: str) -> dict:
        """Pull title, price, rating, and link out of a single book card."""
        link_tag = article.select_one("h3 > a")
        price_tag = article.select_one("p.price_color")
        rating_tag = article.select_one("p.star-rating")

        # The full title is in the 'title' attribute, not the visible text
        title = link_tag.get("title") if link_tag else None

        # Build the full detail-page URL from the relative href
        href = (
            urljoin(page_url, link_tag["href"])
            if link_tag and link_tag.get("href")
            else None
        )

        # Price text looks like "£51.77"
        price_raw = price_tag.get_text(strip=True) if price_tag else None

        # BeautifulSoup returns the class attribute as a list,
        # e.g. ["star-rating", "Three"], so we join it into one string.
        rating_raw = (
            " ".join(rating_tag.get("class", []))
            if rating_tag
            else None
        )

        return {
            "source":        "Books to Scrape",
            "source_url":    href,
            "name_or_title": title,
            "category":      None,          # not on the listing page
            "price_raw":     price_raw,
            "rating_raw":    rating_raw,
            "author":        None,          # books don't have an author field
            "tags_raw":      None,          # books don't have tags
            "description":   None,          # not on the listing page
            "scraped_at":    datetime.now(timezone.utc).isoformat(),
        }

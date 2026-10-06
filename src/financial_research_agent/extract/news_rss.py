"""News RSS and Atom feed extractor."""

import hashlib
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx

from financial_research_agent.extract.schemas import RawDocumentMetadata, RawNewsArticle


class NewsExtractionError(Exception):
    """Base exception for news feed extraction errors."""


class EmptyFeedError(NewsExtractionError):
    """Raised when an RSS or Atom feed contains no articles."""


class NewsRSSExtractor:
    """Extracts and standardizes news articles from RSS and Atom feeds."""

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        default_publisher: str | None = None,
    ) -> None:
        self.default_publisher = default_publisher
        self._owned_client = http_client is None
        self._client = http_client or httpx.Client(
            headers={"User-Agent": "FinancialResearchAgent/1.0"},
            timeout=30.0,
        )

    def close(self) -> None:
        """Close the underlying HTTP client if created internally."""
        if self._owned_client:
            self._client.close()

    def __enter__(self) -> "NewsRSSExtractor":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @staticmethod
    def _parse_timestamp(entry: Any) -> datetime:
        """Convert feedparser struct_time into UTC-aware datetime."""
        struct_time = getattr(entry, "published_parsed", None) or getattr(
            entry, "updated_parsed", None
        )
        if struct_time:
            return datetime(
                struct_time.tm_year,
                struct_time.tm_mon,
                struct_time.tm_mday,
                struct_time.tm_hour,
                struct_time.tm_min,
                struct_time.tm_sec,
                tzinfo=UTC,
            )
        return datetime.now(UTC)

    def parse_feed_content(
        self,
        xml_content: str,
        source_uri: str = "direct://content",
        publisher: str | None = None,
    ) -> list[RawNewsArticle]:
        """Parse raw XML text from an RSS/Atom feed into RawNewsArticle models."""
        parsed = feedparser.parse(xml_content)
        entries = getattr(parsed, "entries", [])
        if not entries:
            raise EmptyFeedError(f"No articles found in feed from '{source_uri}'.")

        feed_title = getattr(getattr(parsed, "feed", None), "title", None)
        feed_publisher = publisher or self.default_publisher or feed_title or "Unknown Publisher"

        articles: list[RawNewsArticle] = []
        for entry in entries:
            title = str(getattr(entry, "title", "")).strip()
            if not title:
                continue

            link = str(getattr(entry, "link", "")).strip() or str(getattr(entry, "id", "")).strip()
            if not link:
                link = source_uri

            summary = str(
                getattr(entry, "summary", "") or getattr(entry, "description", "")
            ).strip()

            full_text: str | None = None
            content_list = getattr(entry, "content", None)
            if content_list and isinstance(content_list, list) and len(content_list) > 0:
                full_text = str(content_list[0].get("value", "")).strip() or None

            pub_date = self._parse_timestamp(entry)

            hash_payload = f"{title}|{link}|{pub_date.isoformat()}|{summary}"
            content_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()
            extracted_at = datetime.now(UTC)

            metadata = RawDocumentMetadata(
                source_uri=source_uri,
                extracted_at=extracted_at,
                content_hash=content_hash,
                extra_attributes={"entry_id": getattr(entry, "id", None)},
            )

            articles.append(
                RawNewsArticle(
                    title=title,
                    publisher=feed_publisher,
                    published_at=pub_date,
                    url=link,
                    summary=summary,
                    full_text=full_text,
                    metadata=metadata,
                )
            )

        if not articles:
            raise EmptyFeedError(f"Feed at '{source_uri}' contained no valid article entries.")

        return articles

    def fetch_and_parse(
        self,
        feed_url: str,
        publisher: str | None = None,
    ) -> list[RawNewsArticle]:
        """Fetch an external RSS feed via HTTP and return parsed RawNewsArticle models."""
        try:
            response = self._client.get(feed_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise NewsExtractionError(f"Failed to fetch RSS feed from '{feed_url}': {exc}") from exc

        return self.parse_feed_content(
            xml_content=response.text,
            source_uri=feed_url,
            publisher=publisher,
        )

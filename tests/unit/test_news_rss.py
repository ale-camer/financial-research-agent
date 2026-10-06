"""Unit tests for RSS and Atom news feed extractor."""

from datetime import UTC, datetime

import httpx
import pytest

from financial_research_agent.extract.news_rss import (
    EmptyFeedError,
    NewsExtractionError,
    NewsRSSExtractor,
)
from financial_research_agent.extract.schemas import RawNewsArticle

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Financial Times Headlines</title>
    <link>https://www.ft.com</link>
    <description>Latest business news</description>
    <item>
      <title>Markets Rally on Tech Earnings</title>
      <link>https://www.ft.com/content/markets-rally-123</link>
      <description>Global stocks advanced following strong quarterly results.</description>
      <pubDate>Thu, 02 Nov 2023 15:30:00 GMT</pubDate>
      <guid>ft-item-123</guid>
    </item>
    <item>
      <title>Central Banks Hold Rates Steady</title>
      <link>https://www.ft.com/content/rates-steady-456</link>
      <description>Policy makers signal prolonged pause.</description>
      <pubDate>Fri, 03 Nov 2023 10:00:00 GMT</pubDate>
      <guid>ft-item-456</guid>
    </item>
  </channel>
</rss>
"""

SAMPLE_ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>SEC Press Releases</title>
  <link href="https://www.sec.gov/news/pressreleases"/>
  <updated>2023-11-03T18:00:00Z</updated>
  <entry>
    <title>SEC Announces Enforcement Action</title>
    <link href="https://www.sec.gov/news/press-release/2023-230"/>
    <id>urn:sec:pr:2023-230</id>
    <updated>2023-11-03T18:00:00Z</updated>
    <summary>Commission charges entity with reporting violations.</summary>
    <content type="html">&lt;p&gt;Full details of the action...&lt;/p&gt;</content>
  </entry>
</feed>
"""


@pytest.mark.issue_4
def test_parse_rss_20_feed() -> None:
    extractor = NewsRSSExtractor()
    articles = extractor.parse_feed_content(
        xml_content=SAMPLE_RSS_XML,
        source_uri="https://www.ft.com/rss",
    )

    assert len(articles) == 2
    first = articles[0]
    assert isinstance(first, RawNewsArticle)
    assert first.title == "Markets Rally on Tech Earnings"
    assert first.publisher == "Financial Times Headlines"
    assert first.url == "https://www.ft.com/content/markets-rally-123"
    assert first.summary.startswith("Global stocks advanced")
    assert first.published_at == datetime(2023, 11, 2, 15, 30, 0, tzinfo=UTC)
    assert first.metadata.content_hash is not None
    assert len(first.metadata.content_hash) == 64


@pytest.mark.issue_4
def test_parse_atom_feed_with_custom_publisher() -> None:
    extractor = NewsRSSExtractor(default_publisher="SEC Newsroom")
    articles = extractor.parse_feed_content(
        xml_content=SAMPLE_ATOM_XML,
        source_uri="https://www.sec.gov/atom",
        publisher="Custom SEC Outlet",
    )

    assert len(articles) == 1
    article = articles[0]
    assert article.title == "SEC Announces Enforcement Action"
    assert article.publisher == "Custom SEC Outlet"
    assert article.url == "https://www.sec.gov/news/press-release/2023-230"
    assert article.published_at == datetime(2023, 11, 3, 18, 0, 0, tzinfo=UTC)
    assert article.full_text is not None
    assert "Full details" in article.full_text


@pytest.mark.issue_4
def test_parse_empty_feed_raises_error() -> None:
    empty_xml = "<rss version='2.0'><channel><title>Empty</title></channel></rss>"
    extractor = NewsRSSExtractor()
    with pytest.raises(EmptyFeedError, match="No articles found"):
        extractor.parse_feed_content(empty_xml)


@pytest.mark.issue_4
def test_parse_feed_without_titles_raises_error() -> None:
    invalid_xml = """<rss version='2.0'><channel><title>Bad</title>
    <item><link>https://example.com</link></item>
    </channel></rss>"""
    extractor = NewsRSSExtractor()
    with pytest.raises(EmptyFeedError, match="no valid article entries"):
        extractor.parse_feed_content(invalid_xml)


@pytest.mark.issue_4
def test_fetch_and_parse_with_mock_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "news.xml" in str(request.url):
            return httpx.Response(200, text=SAMPLE_RSS_XML)
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)

    with NewsRSSExtractor(http_client=mock_http) as extractor:
        articles = extractor.fetch_and_parse("https://mock.news/news.xml")
        assert len(articles) == 2

        with pytest.raises(NewsExtractionError, match="Failed to fetch RSS feed"):
            extractor.fetch_and_parse("https://mock.news/missing.xml")

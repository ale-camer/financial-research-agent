"""Integration tests for the complete extraction and raw storage pipeline."""

from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pandas as pd
import pytest

from financial_research_agent.extract import (
    DocumentType,
    MarketDataExtractor,
    NewsRSSExtractor,
    RawDocument,
    RawMarketData,
    RawNewsArticle,
    RawSECFiling,
    RawStorageWriter,
    SECEdgarClient,
)

SAMPLE_TICKERS = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
SAMPLE_SUBMISSIONS = {
    "cik": "0000320193",
    "name": "Apple Inc.",
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-23-000106"],
            "filingDate": ["2023-11-03"],
            "form": ["10-K"],
            "primaryDocument": ["aapl-20230930.htm"],
        }
    },
}
SAMPLE_HTML = "<html><body><h1>Apple 10-K Ingestion Test</h1></body></html>"
SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Integration News Feed</title>
    <item>
      <title>Tech Giant Outperforms Estimates</title>
      <link>https://news.example.com/tech-outperform</link>
      <description>Quarterly report details revenue growth.</description>
      <pubDate>Fri, 03 Nov 2023 18:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


@pytest.mark.issue_5
def test_end_to_end_extraction_pipeline_to_storage(tmp_path: Path) -> None:
    # 1. Setup storage writer
    writer = RawStorageWriter(base_dir=tmp_path)

    # 2. Extract and persist SEC Filing
    def sec_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "company_tickers.json" in url:
            return httpx.Response(200, json=SAMPLE_TICKERS)
        if "CIK0000320193.json" in url:
            return httpx.Response(200, json=SAMPLE_SUBMISSIONS)
        if "aapl-20230930.htm" in url:
            return httpx.Response(200, text=SAMPLE_HTML)
        return httpx.Response(404, text="Not Found")

    sec_transport = httpx.MockTransport(sec_handler)
    sec_client = SECEdgarClient(
        user_agent="PipelineTest test@example.com",
        http_client=httpx.Client(transport=sec_transport),
    )
    raw_filing = sec_client.fetch_filing(ticker="AAPL", form_type="10-K")
    sec_doc = RawDocument(
        document_id=f"sec_{raw_filing.ticker}_{raw_filing.accession_number}",
        document_type=DocumentType.SEC_FILING,
        payload=raw_filing,
        metadata=raw_filing.metadata,
    )
    sec_file_path = writer.write(sec_doc)
    assert sec_file_path.is_file()

    # 3. Extract and persist Market Data
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame(
        {
            "Open": [175.0],
            "High": [178.0],
            "Low": [174.0],
            "Close": [177.5],
            "Volume": [50000000],
        },
        index=[pd.Timestamp("2023-11-03 16:00:00", tz="UTC")],
    )
    market_extractor = MarketDataExtractor(ticker_factory=lambda _: mock_ticker)
    raw_mkt = market_extractor.extract_history(ticker="AAPL", period="1d", interval="1d")
    mkt_doc = RawDocument(
        document_id="mkt_AAPL_1d_20231103",
        document_type=DocumentType.MARKET_DATA,
        payload=raw_mkt,
        metadata=raw_mkt.metadata,
    )
    mkt_file_path = writer.write(mkt_doc)
    assert mkt_file_path.is_file()

    # 4. Extract and persist News Article
    news_extractor = NewsRSSExtractor()
    news_articles = news_extractor.parse_feed_content(
        xml_content=SAMPLE_RSS,
        source_uri="https://news.example.com/rss",
    )
    assert len(news_articles) == 1
    raw_news = news_articles[0]
    news_doc = RawDocument(
        document_id="news_article_tech_outperform",
        document_type=DocumentType.NEWS_ARTICLE,
        payload=raw_news,
        metadata=raw_news.metadata,
    )
    news_file_path = writer.write(news_doc)
    assert news_file_path.is_file()

    # 5. Read back from disk and verify contracts
    loaded_sec = writer.read(sec_file_path)
    assert loaded_sec.document_type == DocumentType.SEC_FILING
    assert isinstance(loaded_sec.payload, RawSECFiling)
    assert loaded_sec.payload.raw_content == SAMPLE_HTML

    loaded_mkt = writer.read(mkt_file_path)
    assert loaded_mkt.document_type == DocumentType.MARKET_DATA
    assert isinstance(loaded_mkt.payload, RawMarketData)
    assert loaded_mkt.payload.records[0].close == 177.5

    loaded_news = writer.read(news_file_path)
    assert loaded_news.document_type == DocumentType.NEWS_ARTICLE
    assert isinstance(loaded_news.payload, RawNewsArticle)
    assert loaded_news.payload.title == "Tech Giant Outperforms Estimates"

"""Ingestion pipeline orchestrator coordinating raw financial extraction and storage."""

import hashlib
import uuid
from datetime import UTC, datetime

from financial_research_agent.extract.market_data import (
    MarketDataError,
    MarketDataExtractor,
)
from financial_research_agent.extract.news_rss import (
    NewsExtractionError,
    NewsRSSExtractor,
)
from financial_research_agent.extract.schemas import (
    DocumentType,
    RawDocument,
)
from financial_research_agent.extract.sec_edgar import (
    SECEdgarClient,
    SECEdgarError,
)
from financial_research_agent.extract.storage import (
    RawStorageWriter,
    StorageError,
)
from financial_research_agent.orchestration.schemas import (
    IngestionConfig,
    IngestionResult,
    IngestionTaskSummary,
)


class IngestionError(Exception):
    """Base exception for data ingestion pipeline failures."""


class IngestionPipeline:
    """Orchestrates extraction of SEC filings, market data, and RSS news to raw storage."""

    def __init__(
        self,
        config: IngestionConfig | None = None,
        sec_client: SECEdgarClient | None = None,
        market_extractor: MarketDataExtractor | None = None,
        news_extractor: NewsRSSExtractor | None = None,
        storage_writer: RawStorageWriter | None = None,
    ) -> None:
        self.config = config or IngestionConfig()
        self.sec_client = sec_client or SECEdgarClient(user_agent=self.config.sec_user_agent)
        self.market_extractor = market_extractor or MarketDataExtractor()
        self.news_extractor = news_extractor or NewsRSSExtractor()
        self.storage_writer = storage_writer or RawStorageWriter(
            base_dir=self.config.raw_storage_dir
        )

    def ingest_sec_filings(
        self,
        tickers: list[str] | None = None,
        form_types: list[str] | None = None,
        limit_per_form: int | None = None,
    ) -> IngestionTaskSummary:
        """Extract and persist raw SEC filings for the specified tickers and form types."""
        target_tickers = tickers if tickers is not None else self.config.tickers
        target_forms = form_types if form_types is not None else self.config.sec_form_types

        written_paths: list[str] = []
        errors: list[str] = []
        ingested_count = 0

        for ticker in target_tickers:
            for form in target_forms:
                try:
                    filing = self.sec_client.fetch_filing(
                        ticker=ticker,
                        form_type=form,
                    )
                    clean_acc = filing.accession_number.replace("-", "_")
                    doc_id = f"sec_{ticker.upper()}_{form}_{clean_acc}"
                    raw_doc = RawDocument(
                        document_id=doc_id,
                        document_type=DocumentType.SEC_FILING,
                        payload=filing,
                        metadata=filing.metadata,
                    )
                    saved_path = self.storage_writer.write(
                        document=raw_doc,
                        overwrite=self.config.overwrite,
                    )
                    written_paths.append(str(saved_path))
                    ingested_count += 1
                except (SECEdgarError, StorageError, Exception) as exc:
                    errors.append(f"Failed ingesting {ticker} {form}: {exc}")

        return IngestionTaskSummary(
            task_name="ingest_sec_filings",
            documents_ingested=ingested_count,
            written_paths=written_paths,
            errors=errors,
        )

    def ingest_market_data(
        self,
        tickers: list[str] | None = None,
        period: str | None = None,
        interval: str | None = None,
    ) -> IngestionTaskSummary:
        """Extract and persist raw historical OHLCV market series for specified tickers."""
        target_tickers = tickers if tickers is not None else self.config.tickers
        target_period = period or self.config.market_period
        target_interval = interval or self.config.market_interval

        written_paths: list[str] = []
        errors: list[str] = []
        ingested_count = 0

        for ticker in target_tickers:
            try:
                raw_mkt = self.market_extractor.extract_history(
                    ticker=ticker,
                    period=target_period,
                    interval=target_interval,
                )
                start_str = raw_mkt.start_date.strftime("%Y%m%d")
                end_str = raw_mkt.end_date.strftime("%Y%m%d")
                doc_id = f"mkt_{ticker.upper()}_{target_interval}_{start_str}_{end_str}"
                raw_doc = RawDocument(
                    document_id=doc_id,
                    document_type=DocumentType.MARKET_DATA,
                    payload=raw_mkt,
                    metadata=raw_mkt.metadata,
                )
                saved_path = self.storage_writer.write(
                    document=raw_doc,
                    overwrite=self.config.overwrite,
                )
                written_paths.append(str(saved_path))
                ingested_count += 1
            except (MarketDataError, StorageError, Exception) as exc:
                errors.append(f"Failed ingesting market data for {ticker}: {exc}")

        return IngestionTaskSummary(
            task_name="ingest_market_data",
            documents_ingested=ingested_count,
            written_paths=written_paths,
            errors=errors,
        )

    def ingest_news_rss(
        self,
        feed_urls: list[str] | None = None,
        limit_per_feed: int | None = None,
    ) -> IngestionTaskSummary:
        """Fetch and persist news articles from configured RSS feeds."""
        target_feeds = feed_urls if feed_urls is not None else self.config.news_feed_urls
        limit = limit_per_feed if limit_per_feed is not None else self.config.news_limit_per_feed

        written_paths: list[str] = []
        errors: list[str] = []
        ingested_count = 0

        for url in target_feeds:
            try:
                articles = self.news_extractor.fetch_and_parse(feed_url=url)
                if limit is not None:
                    articles = articles[:limit]
                for article in articles:
                    url_hash = hashlib.sha256(article.url.encode()).hexdigest()[:12]
                    doc_id = f"news_{url_hash}"
                    raw_doc = RawDocument(
                        document_id=doc_id,
                        document_type=DocumentType.NEWS_ARTICLE,
                        payload=article,
                        metadata=article.metadata,
                    )
                    saved_path = self.storage_writer.write(
                        document=raw_doc,
                        overwrite=self.config.overwrite,
                    )
                    written_paths.append(str(saved_path))
                    ingested_count += 1
            except (NewsExtractionError, StorageError, Exception) as exc:
                errors.append(f"Failed ingesting news feed '{url}': {exc}")

        return IngestionTaskSummary(
            task_name="ingest_news_rss",
            documents_ingested=ingested_count,
            written_paths=written_paths,
            errors=errors,
        )

    def run(self, config: IngestionConfig | None = None) -> IngestionResult:
        """Execute the full raw data ingestion pipeline and return aggregate telemetry."""
        if config is not None:
            self.config = config
            self.storage_writer = RawStorageWriter(base_dir=self.config.raw_storage_dir)

        run_id = f"ingest_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        started_at = datetime.now(UTC)

        sec_summary = self.ingest_sec_filings()
        mkt_summary = self.ingest_market_data()
        news_summary = self.ingest_news_rss()

        completed_at = datetime.now(UTC)
        duration = max(0.0, (completed_at - started_at).total_seconds())

        task_summaries = [sec_summary, mkt_summary, news_summary]
        all_written = (
            sec_summary.written_paths + mkt_summary.written_paths + news_summary.written_paths
        )
        total_ingested = (
            sec_summary.documents_ingested
            + mkt_summary.documents_ingested
            + news_summary.documents_ingested
        )
        total_errors = sum(len(s.errors) for s in task_summaries)

        if total_errors == 0:
            status = "success"
        elif total_ingested > 0:
            status = "partial_success"
        else:
            status = "failed"

        return IngestionResult(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=round(duration, 4),
            sec_filings_count=sec_summary.documents_ingested,
            market_data_count=mkt_summary.documents_ingested,
            news_articles_count=news_summary.documents_ingested,
            total_documents_ingested=total_ingested,
            written_files=all_written,
            task_summaries=task_summaries,
            status=status,
        )

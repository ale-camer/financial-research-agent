"""Unit tests for the ingestion DAG and IngestionPipeline orchestrator."""

from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dags.ingestion_dag import (
    financial_ingestion_dag,
    run_market_data_ingestion,
    run_news_ingestion,
    run_sec_ingestion,
)

from financial_research_agent.extract.market_data import MarketDataExtractor
from financial_research_agent.extract.news_rss import NewsRSSExtractor
from financial_research_agent.extract.schemas import (
    MarketDataPoint,
    RawDocumentMetadata,
    RawMarketData,
    RawNewsArticle,
    RawSECFiling,
)
from financial_research_agent.extract.sec_edgar import SECEdgarClient, SECEdgarError
from financial_research_agent.extract.storage import RawStorageWriter
from financial_research_agent.orchestration import (
    IngestionConfig,
    IngestionPipeline,
    IngestionResult,
)


@pytest.fixture
def mock_sec_filing() -> RawSECFiling:
    meta = RawDocumentMetadata(
        source_uri="https://data.sec.gov/filing",
        extracted_at=datetime(2023, 11, 3, 12, 0, 0, tzinfo=UTC),
        content_hash="mock_sec_hash",
    )
    return RawSECFiling(
        ticker="AAPL",
        cik="0000320193",
        form_type="10-K",
        filing_date=date(2023, 11, 3),
        accession_number="0000320193-23-000106",
        raw_content="<html>SEC 10-K body</html>",
        metadata=meta,
    )


@pytest.fixture
def mock_market_data() -> RawMarketData:
    meta = RawDocumentMetadata(
        source_uri="yfinance://AAPL",
        extracted_at=datetime(2023, 11, 3, 16, 0, 0, tzinfo=UTC),
        content_hash="mock_mkt_hash",
    )
    point = MarketDataPoint(
        timestamp=datetime(2023, 11, 3, 16, 0, 0, tzinfo=UTC),
        open=170.0,
        high=175.0,
        low=169.0,
        close=173.0,
        volume=1000000,
    )
    return RawMarketData(
        ticker="AAPL",
        interval="1d",
        start_date=point.timestamp,
        end_date=point.timestamp,
        records=[point],
        metadata=meta,
    )


@pytest.fixture
def mock_news_article() -> RawNewsArticle:
    meta = RawDocumentMetadata(
        source_uri="https://news.example.com/rss",
        extracted_at=datetime(2023, 11, 3, 14, 0, 0, tzinfo=UTC),
        content_hash="mock_news_hash",
    )
    return RawNewsArticle(
        title="Apple Reports Record Earnings",
        publisher="Reuters",
        published_at=datetime(2023, 11, 3, 13, 0, 0, tzinfo=UTC),
        url="https://news.example.com/aapl-earnings",
        summary="Quarterly profits beat analyst consensus.",
        metadata=meta,
    )


@pytest.mark.issue_17
def test_ingestion_config_defaults_and_custom() -> None:
    config = IngestionConfig()
    assert "AAPL" in config.tickers
    assert "10-K" in config.sec_form_types
    assert config.raw_storage_dir == "./data/raw"

    custom = IngestionConfig(
        tickers=["GOOGL"],
        sec_form_types=["8-K"],
        raw_storage_dir="/tmp/test_raw",
    )
    assert custom.tickers == ["GOOGL"]
    assert custom.sec_form_types == ["8-K"]


@pytest.mark.issue_17
def test_ingest_sec_filings_task(
    tmp_path: Path,
    mock_sec_filing: RawSECFiling,
) -> None:
    mock_sec_client = MagicMock(spec=SECEdgarClient)
    mock_sec_client.fetch_filing.return_value = mock_sec_filing

    storage = RawStorageWriter(base_dir=tmp_path)
    pipeline = IngestionPipeline(
        sec_client=mock_sec_client,
        storage_writer=storage,
    )

    summary = pipeline.ingest_sec_filings(tickers=["AAPL"], form_types=["10-K"])
    assert summary.documents_ingested == 1
    assert len(summary.written_paths) == 1
    assert len(summary.errors) == 0

    saved_file = Path(summary.written_paths[0])
    assert saved_file.is_file()
    assert "sec_filing" in str(saved_file)


@pytest.mark.issue_17
def test_ingest_market_data_task(
    tmp_path: Path,
    mock_market_data: RawMarketData,
) -> None:
    mock_extractor = MagicMock(spec=MarketDataExtractor)
    mock_extractor.extract_history.return_value = mock_market_data

    storage = RawStorageWriter(base_dir=tmp_path)
    pipeline = IngestionPipeline(
        market_extractor=mock_extractor,
        storage_writer=storage,
    )

    summary = pipeline.ingest_market_data(tickers=["AAPL"])
    assert summary.documents_ingested == 1
    assert len(summary.written_paths) == 1
    assert len(summary.errors) == 0

    saved_file = Path(summary.written_paths[0])
    assert saved_file.is_file()
    assert "market_data" in str(saved_file)


@pytest.mark.issue_17
def test_ingest_news_rss_task(
    tmp_path: Path,
    mock_news_article: RawNewsArticle,
) -> None:
    mock_news = MagicMock(spec=NewsRSSExtractor)
    mock_news.fetch_and_parse.return_value = [mock_news_article]

    storage = RawStorageWriter(base_dir=tmp_path)
    pipeline = IngestionPipeline(
        news_extractor=mock_news,
        storage_writer=storage,
    )

    summary = pipeline.ingest_news_rss(feed_urls=["https://feed.example.com"])
    assert summary.documents_ingested == 1
    assert len(summary.written_paths) == 1
    assert len(summary.errors) == 0

    saved_file = Path(summary.written_paths[0])
    assert saved_file.is_file()
    assert "news_article" in str(saved_file)


@pytest.mark.issue_17
def test_full_pipeline_run_success(
    tmp_path: Path,
    mock_sec_filing: RawSECFiling,
    mock_market_data: RawMarketData,
    mock_news_article: RawNewsArticle,
) -> None:
    mock_sec = MagicMock(spec=SECEdgarClient)
    mock_sec.fetch_filing.return_value = mock_sec_filing

    mock_mkt = MagicMock(spec=MarketDataExtractor)
    mock_mkt.extract_history.return_value = mock_market_data

    mock_news = MagicMock(spec=NewsRSSExtractor)
    mock_news.fetch_and_parse.return_value = [mock_news_article]

    config = IngestionConfig(
        tickers=["AAPL"],
        sec_form_types=["10-K"],
        news_feed_urls=["https://feed.example.com"],
        raw_storage_dir=str(tmp_path),
    )
    pipeline = IngestionPipeline(
        config=config,
        sec_client=mock_sec,
        market_extractor=mock_mkt,
        news_extractor=mock_news,
    )

    result = pipeline.run()

    assert isinstance(result, IngestionResult)
    assert result.status == "success"
    assert result.sec_filings_count == 1
    assert result.market_data_count == 1
    assert result.news_articles_count == 1
    assert result.total_documents_ingested == 3
    assert len(result.written_files) == 3
    assert result.duration_seconds >= 0.0


@pytest.mark.issue_17
def test_pipeline_partial_failure(
    tmp_path: Path,
    mock_market_data: RawMarketData,
) -> None:
    mock_sec = MagicMock(spec=SECEdgarClient)
    mock_sec.fetch_filing.side_effect = SECEdgarError("EDGAR connection timed out")

    mock_mkt = MagicMock(spec=MarketDataExtractor)
    mock_mkt.extract_history.return_value = mock_market_data

    config = IngestionConfig(
        tickers=["AAPL"],
        sec_form_types=["10-K"],
        raw_storage_dir=str(tmp_path),
    )
    pipeline = IngestionPipeline(
        config=config,
        sec_client=mock_sec,
        market_extractor=mock_mkt,
    )

    result = pipeline.run()
    assert result.status == "partial_success"
    assert result.sec_filings_count == 0
    assert result.market_data_count == 1
    assert len(result.task_summaries[0].errors) == 1


@pytest.mark.issue_17
def test_dag_structure_and_task_callables(tmp_path: Path) -> None:
    dag = financial_ingestion_dag
    assert dag.dag_id == "financial_ingestion_dag"

    task_ids = [t.task_id for t in dag.tasks]
    assert "task_ingest_sec_filings" in task_ids
    assert "task_ingest_market_data" in task_ids
    assert "task_ingest_news_rss" in task_ids

    # Verify task callables run and return dict summaries
    mock_pipeline = MagicMock()
    mock_summary = MagicMock()
    mock_summary.model_dump.return_value = {"documents_ingested": 0}
    mock_pipeline.ingest_sec_filings.return_value = mock_summary
    mock_pipeline.ingest_market_data.return_value = mock_summary
    mock_pipeline.ingest_news_rss.return_value = mock_summary

    import dags.ingestion_dag as dag_mod

    orig_pipeline = dag_mod.IngestionPipeline
    dag_mod.IngestionPipeline = lambda: mock_pipeline  # type: ignore[misc]
    try:
        sec_dict = run_sec_ingestion()
        mkt_dict = run_market_data_ingestion()
        news_dict = run_news_ingestion()
        assert "documents_ingested" in sec_dict
        assert "documents_ingested" in mkt_dict
        assert "documents_ingested" in news_dict
    finally:
        dag_mod.IngestionPipeline = orig_pipeline

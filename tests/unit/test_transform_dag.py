"""Unit tests for the transform and indexing DAG and TransformPipeline orchestrator."""

from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dags.transform_dag import (
    financial_transform_dag,
    run_chunk_and_index,
    run_normalize_metrics,
    run_parse_filings,
)
from pydantic import ValidationError

from financial_research_agent.extract.schemas import (
    DocumentType,
    MarketDataPoint,
    RawDocument,
    RawDocumentMetadata,
    RawMarketData,
    RawSECFiling,
)
from financial_research_agent.extract.storage import RawStorageWriter
from financial_research_agent.orchestration import (
    TransformConfig,
    TransformPipeline,
    TransformResult,
)
from financial_research_agent.transform.chunker import DocumentChunker
from financial_research_agent.transform.embeddings import EmbeddingGenerator
from financial_research_agent.transform.normalizer import MetricsNormalizer
from financial_research_agent.transform.schemas import CleanDocument
from financial_research_agent.transform.vector_store import VectorStore


@pytest.fixture
def sample_sec_filing() -> RawSECFiling:
    meta = RawDocumentMetadata(
        source_uri="https://data.sec.gov/filing/0000320193-23-000106",
        extracted_at=datetime(2023, 11, 3, 12, 0, 0, tzinfo=UTC),
        content_hash="mock_hash_sec",
    )
    raw_html = """
    <html>
        <body>
            <h1>ITEM 1. BUSINESS</h1>
            <p>Apple designs and develops personal computers and electronic devices.</p>
            <h1>ITEM 1A. RISK FACTORS</h1>
            <p>Operations are subject to supply chain constraints and trade risks.</p>
        </body>
    </html>
    """
    return RawSECFiling(
        ticker="AAPL",
        cik="0000320193",
        form_type="10-K",
        filing_date=date(2023, 11, 3),
        accession_number="0000320193-23-000106",
        raw_content=raw_html,
        metadata=meta,
    )


@pytest.fixture
def sample_market_data() -> RawMarketData:
    meta = RawDocumentMetadata(
        source_uri="yfinance://AAPL?interval=1d",
        extracted_at=datetime(2023, 11, 3, 16, 0, 0, tzinfo=UTC),
        content_hash="mock_hash_mkt",
    )
    points = [
        MarketDataPoint(
            timestamp=datetime(2023, 11, 1, 16, 0, tzinfo=UTC),
            open=100.0,
            high=105.0,
            low=99.0,
            close=100.0,
            volume=1000,
        ),
        MarketDataPoint(
            timestamp=datetime(2023, 11, 2, 16, 0, tzinfo=UTC),
            open=101.0,
            high=108.0,
            low=100.0,
            close=105.0,
            volume=2000,
        ),
        MarketDataPoint(
            timestamp=datetime(2023, 11, 3, 16, 0, tzinfo=UTC),
            open=106.0,
            high=112.0,
            low=104.0,
            close=110.0,
            volume=3000,
        ),
    ]
    return RawMarketData(
        ticker="AAPL",
        interval="1d",
        start_date=points[0].timestamp,
        end_date=points[-1].timestamp,
        records=points,
        metadata=meta,
    )


@pytest.fixture
def mock_embedding_generator() -> EmbeddingGenerator:
    def _mock_embed(batch: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in batch]

    return EmbeddingGenerator(dimensions=4, embed_fn=_mock_embed)


@pytest.mark.issue_18
def test_transform_config_defaults_and_validation() -> None:
    config = TransformConfig()
    assert config.raw_storage_dir == "./data/raw"
    assert config.processed_storage_dir == "./data/processed"
    assert config.vector_store_path == "./data/vector_store/index.json"
    assert config.chunk_max_tokens == 500
    assert config.chunk_overlap_tokens == 50
    assert config.embedding_dimensions == 1536
    assert config.overwrite is True

    # Validate extra attributes rejected
    with pytest.raises(ValidationError):
        TransformConfig(invalid_param="bad")  # type: ignore[call-arg]

    custom = TransformConfig(
        chunk_max_tokens=200,
        embedding_dimensions=4,
        tickers=["AAPL"],
    )
    assert custom.chunk_max_tokens == 200
    assert custom.embedding_dimensions == 4
    assert custom.tickers == ["AAPL"]


@pytest.mark.issue_18
def test_parse_filings_task(
    tmp_path: Path,
    sample_sec_filing: RawSECFiling,
) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"

    # Write raw document
    storage = RawStorageWriter(base_dir=raw_dir)
    raw_doc = RawDocument(
        document_id="sec_AAPL_10-K_0000320193_23_000106",
        document_type=DocumentType.SEC_FILING,
        payload=sample_sec_filing,
        metadata=sample_sec_filing.metadata,
    )
    storage.write(raw_doc)

    config = TransformConfig(
        raw_storage_dir=str(raw_dir),
        processed_storage_dir=str(processed_dir),
    )
    pipeline = TransformPipeline(config=config, storage_reader=storage)

    summary = pipeline.parse_filings()
    assert summary.items_processed == 1
    assert summary.items_produced == 1
    assert len(summary.output_paths) == 1
    assert len(summary.errors) == 0

    saved_file = Path(summary.output_paths[0])
    assert saved_file.is_file()
    clean_doc = CleanDocument.model_validate_json(saved_file.read_text(encoding="utf-8"))
    assert clean_doc.ticker == "AAPL"
    assert len(clean_doc.sections) >= 1


@pytest.mark.issue_18
def test_chunk_and_index_task(
    tmp_path: Path,
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    processed_dir = tmp_path / "processed"
    parsed_dir = processed_dir / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    index_path = tmp_path / "vector_store" / "index.json"

    # Create dummy parsed CleanDocument
    clean_doc = CleanDocument(
        document_id="clean_AAPL_test",
        source_document_id="src_123",
        ticker="AAPL",
        form_type="10-K",
        filing_date=date(2023, 11, 3),
        clean_text="Apple Inc. reports record revenue across services and mobile segments.",
        sections=[],
    )
    (parsed_dir / f"{clean_doc.document_id}.json").write_text(
        clean_doc.model_dump_json(), encoding="utf-8"
    )

    vector_store = VectorStore(storage_path=index_path)
    chunker = DocumentChunker(max_tokens=20, overlap_tokens=5)

    config = TransformConfig(
        processed_storage_dir=str(processed_dir),
        vector_store_path=str(index_path),
        embedding_dimensions=4,
    )
    pipeline = TransformPipeline(
        config=config,
        chunker=chunker,
        embedding_generator=mock_embedding_generator,
        vector_store=vector_store,
    )

    summary = pipeline.chunk_and_index()
    assert summary.items_processed == 1
    assert summary.items_produced >= 1
    assert len(summary.output_paths) == 1
    assert index_path.is_file()
    assert vector_store.count() >= 1


@pytest.mark.issue_18
def test_normalize_metrics_task(
    tmp_path: Path,
    sample_market_data: RawMarketData,
) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"

    storage = RawStorageWriter(base_dir=raw_dir)
    raw_doc = RawDocument(
        document_id="mkt_AAPL_1d_20231101_20231103",
        document_type=DocumentType.MARKET_DATA,
        payload=sample_market_data,
        metadata=sample_market_data.metadata,
    )
    storage.write(raw_doc)

    config = TransformConfig(
        raw_storage_dir=str(raw_dir),
        processed_storage_dir=str(processed_dir),
    )
    normalizer = MetricsNormalizer(trading_days_per_year=252)
    pipeline = TransformPipeline(
        config=config,
        normalizer=normalizer,
        storage_reader=storage,
    )

    summary = pipeline.normalize_metrics()
    assert summary.items_processed == 1
    assert summary.items_produced == 1
    assert len(summary.output_paths) == 1
    assert len(summary.errors) == 0

    saved_file = Path(summary.output_paths[0])
    assert saved_file.is_file()
    assert "metrics_AAPL" in saved_file.name


@pytest.mark.issue_18
def test_full_transform_pipeline_run_success(
    tmp_path: Path,
    sample_sec_filing: RawSECFiling,
    sample_market_data: RawMarketData,
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    index_path = tmp_path / "vector_store" / "index.json"

    storage = RawStorageWriter(base_dir=raw_dir)
    # Store raw SEC filing
    storage.write(
        RawDocument(
            document_id="sec_AAPL_10-K_0000320193_23_000106",
            document_type=DocumentType.SEC_FILING,
            payload=sample_sec_filing,
            metadata=sample_sec_filing.metadata,
        )
    )
    # Store raw market data
    storage.write(
        RawDocument(
            document_id="mkt_AAPL_1d_20231101_20231103",
            document_type=DocumentType.MARKET_DATA,
            payload=sample_market_data,
            metadata=sample_market_data.metadata,
        )
    )

    config = TransformConfig(
        raw_storage_dir=str(raw_dir),
        processed_storage_dir=str(processed_dir),
        vector_store_path=str(index_path),
        embedding_dimensions=4,
    )
    pipeline = TransformPipeline(
        config=config,
        embedding_generator=mock_embedding_generator,
        storage_reader=storage,
    )

    result = pipeline.run()

    assert isinstance(result, TransformResult)
    assert result.status == "success"
    assert result.documents_parsed == 1
    assert result.chunks_created >= 1
    assert result.chunks_indexed >= 1
    assert result.metrics_normalized == 1
    assert result.duration_seconds >= 0.0
    assert len(result.task_summaries) == 3


@pytest.mark.issue_18
def test_transform_pipeline_partial_failure(
    tmp_path: Path,
    sample_market_data: RawMarketData,
) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"

    storage = RawStorageWriter(base_dir=raw_dir)
    storage.write(
        RawDocument(
            document_id="mkt_AAPL_1d_20231101_20231103",
            document_type=DocumentType.MARKET_DATA,
            payload=sample_market_data,
            metadata=sample_market_data.metadata,
        )
    )

    config = TransformConfig(
        raw_storage_dir=str(raw_dir),
        processed_storage_dir=str(processed_dir),
    )
    # Mock normalizer to fail
    mock_normalizer = MagicMock(spec=MetricsNormalizer)
    mock_normalizer.compute_market_metrics.side_effect = RuntimeError(
        "Normalization numerical overflow"
    )

    pipeline = TransformPipeline(
        config=config,
        normalizer=mock_normalizer,
        storage_reader=storage,
    )

    result = pipeline.run()
    # No documents were parsed (0) and normalizer failed with error, chunks 0 -> status failed
    assert result.status == "failed"
    assert result.metrics_normalized == 0
    assert len(result.task_summaries[2].errors) == 1


@pytest.mark.issue_18
def test_dag_structure_and_task_callables() -> None:
    dag = financial_transform_dag
    assert dag.dag_id == "financial_transform_dag"

    task_ids = [t.task_id for t in dag.tasks]
    assert "task_parse_filings" in task_ids
    assert "task_chunk_and_index" in task_ids
    assert "task_normalize_metrics" in task_ids

    parse_task = next(t for t in dag.tasks if t.task_id == "task_parse_filings")
    chunk_task = next(t for t in dag.tasks if t.task_id == "task_chunk_and_index")
    assert chunk_task in parse_task.downstream_list

    # Verify task callables execute and return dictionary summaries
    mock_pipeline = MagicMock()
    mock_summary = MagicMock()
    mock_summary.model_dump.return_value = {"items_produced": 0}
    mock_pipeline.parse_filings.return_value = mock_summary
    mock_pipeline.chunk_and_index.return_value = mock_summary
    mock_pipeline.normalize_metrics.return_value = mock_summary

    import dags.transform_dag as dag_mod

    orig_pipeline = dag_mod.TransformPipeline
    dag_mod.TransformPipeline = lambda: mock_pipeline  # type: ignore[misc]
    try:
        parse_dict = run_parse_filings()
        chunk_dict = run_chunk_and_index()
        metrics_dict = run_normalize_metrics()
        assert "items_produced" in parse_dict
        assert "items_produced" in chunk_dict
        assert "items_produced" in metrics_dict
    finally:
        dag_mod.TransformPipeline = orig_pipeline

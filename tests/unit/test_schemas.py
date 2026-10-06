"""Unit tests for extraction layer Pydantic schemas."""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from financial_research_agent.extract.schemas import (
    DocumentType,
    MarketDataPoint,
    RawDocument,
    RawDocumentMetadata,
    RawMarketData,
    RawNewsArticle,
    RawSECFiling,
)


@pytest.fixture
def sample_metadata() -> RawDocumentMetadata:
    return RawDocumentMetadata(
        source_uri=(
            "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm"
        ),
        extracted_at=datetime(2023, 11, 3, 12, 0, 0, tzinfo=UTC),
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        extra_attributes={"format": "htm", "bytes": 1024},
    )


@pytest.mark.issue_1
def test_raw_document_metadata_immutability(sample_metadata: RawDocumentMetadata) -> None:
    assert sample_metadata.content_hash.startswith("e3b0")
    with pytest.raises(ValidationError):
        # Frozen models prohibit mutation
        sample_metadata.content_hash = "modified"  # type: ignore[misc]


@pytest.mark.issue_1
def test_raw_sec_filing_creation_and_json_roundtrip(sample_metadata: RawDocumentMetadata) -> None:
    filing = RawSECFiling(
        ticker="AAPL",
        cik="0000320193",
        form_type="10-K",
        filing_date=date(2023, 11, 3),
        accession_number="0000320193-23-000106",
        raw_content="<DOCUMENT>Sample 10-K content</DOCUMENT>",
        metadata=sample_metadata,
    )

    json_str = filing.model_dump_json()
    restored = RawSECFiling.model_validate_json(json_str)

    assert restored.ticker == "AAPL"
    assert restored.form_type == "10-K"
    assert restored.filing_date == date(2023, 11, 3)
    assert restored.accession_number == "0000320193-23-000106"
    assert restored.metadata.source_uri == sample_metadata.source_uri


@pytest.mark.issue_1
def test_raw_sec_filing_validation_error() -> None:
    with pytest.raises(ValidationError):
        # Missing required raw_content and metadata
        RawSECFiling(  # type: ignore[call-arg]
            ticker="AAPL",
            cik="0000320193",
            form_type="10-K",
            filing_date=date(2023, 11, 3),
            accession_number="0000320193-23-000106",
        )


@pytest.mark.issue_1
def test_raw_market_data_serialization(sample_metadata: RawDocumentMetadata) -> None:
    point = MarketDataPoint(
        timestamp=datetime(2023, 11, 3, 16, 0, 0, tzinfo=UTC),
        open=175.5,
        high=177.0,
        low=174.8,
        close=176.65,
        volume=54321000,
    )
    market_data = RawMarketData(
        ticker="AAPL",
        interval="1d",
        start_date=datetime(2023, 11, 3, 9, 30, 0, tzinfo=UTC),
        end_date=datetime(2023, 11, 3, 16, 0, 0, tzinfo=UTC),
        records=[point],
        metadata=sample_metadata,
    )

    data_dict = market_data.model_dump()
    assert data_dict["ticker"] == "AAPL"
    assert len(data_dict["records"]) == 1
    assert data_dict["records"][0]["close"] == 176.65

    # Extra field forbidden check
    with pytest.raises(ValidationError):
        RawMarketData(
            ticker="AAPL",
            interval="1d",
            start_date=datetime(2023, 11, 3, 9, 30, 0, tzinfo=UTC),
            end_date=datetime(2023, 11, 3, 16, 0, 0, tzinfo=UTC),
            records=[],
            metadata=sample_metadata,
            unexpected_field="disallowed",  # type: ignore[call-arg]
        )


@pytest.mark.issue_1
def test_raw_news_article_parsing(sample_metadata: RawDocumentMetadata) -> None:
    article = RawNewsArticle(
        title="Apple Reports Fourth Quarter Results",
        publisher="Reuters",
        published_at=datetime(2023, 11, 2, 20, 30, 0, tzinfo=UTC),
        url="https://www.reuters.com/technology/apple-q4-results-2023-11-02/",
        summary="Apple announced financial results for its fiscal 2023 fourth quarter.",
        full_text=None,
        metadata=sample_metadata,
    )

    assert article.full_text is None
    assert article.publisher == "Reuters"
    assert article.title.startswith("Apple Reports")


@pytest.mark.issue_1
def test_raw_document_envelope(sample_metadata: RawDocumentMetadata) -> None:
    filing = RawSECFiling(
        ticker="MSFT",
        cik="0000789019",
        form_type="8-K",
        filing_date=date(2023, 10, 24),
        accession_number="0000789019-23-000085",
        raw_content="Item 2.02 Results of Operations",
        metadata=sample_metadata,
    )

    doc = RawDocument(
        document_id="doc-sec-msft-8k-20231024",
        document_type=DocumentType.SEC_FILING,
        payload=filing,
        metadata=sample_metadata,
    )

    assert doc.document_type == DocumentType.SEC_FILING
    assert isinstance(doc.payload, RawSECFiling)
    assert doc.payload.ticker == "MSFT"

    json_envelope = doc.model_dump_json()
    restored_doc = RawDocument.model_validate_json(json_envelope)
    assert restored_doc.document_id == "doc-sec-msft-8k-20231024"
    assert restored_doc.document_type == DocumentType.SEC_FILING

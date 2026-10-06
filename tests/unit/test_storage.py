"""Unit tests for RawStorageWriter."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from financial_research_agent.extract.schemas import (
    DocumentType,
    RawDocument,
    RawDocumentMetadata,
    RawSECFiling,
)
from financial_research_agent.extract.storage import RawStorageWriter, StorageError


@pytest.fixture
def sample_document() -> RawDocument:
    meta = RawDocumentMetadata(
        source_uri="https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm",
        extracted_at=datetime(2023, 11, 3, 14, 30, 0, tzinfo=UTC),
        content_hash="abc123hash",
    )
    filing = RawSECFiling(
        ticker="AAPL",
        cik="0000320193",
        form_type="10-K",
        filing_date=date(2023, 11, 3),
        accession_number="0000320193-23-000106",
        raw_content="<html>10-K Body</html>",
        metadata=meta,
    )
    return RawDocument(
        document_id="sec-aapl-10k-2023",
        document_type=DocumentType.SEC_FILING,
        payload=filing,
        metadata=meta,
    )


@pytest.mark.issue_5
def test_resolve_path_partitioning(tmp_path: Path, sample_document: RawDocument) -> None:
    writer = RawStorageWriter(base_dir=tmp_path)
    target = writer.resolve_path(sample_document)

    expected = tmp_path / "sec_filing" / "2023" / "11" / "sec-aapl-10k-2023.json"
    assert target == expected


@pytest.mark.issue_5
def test_write_and_read_roundtrip(tmp_path: Path, sample_document: RawDocument) -> None:
    writer = RawStorageWriter(base_dir=tmp_path)

    assert not writer.exists(sample_document)
    saved_path = writer.write(sample_document)
    assert saved_path.is_file()
    assert writer.exists(sample_document)

    loaded = writer.read(saved_path)
    assert loaded.document_id == sample_document.document_id
    assert loaded.document_type == sample_document.document_type
    assert isinstance(loaded.payload, RawSECFiling)
    assert loaded.payload.ticker == "AAPL"


@pytest.mark.issue_5
def test_write_without_overwrite_raises_error(tmp_path: Path, sample_document: RawDocument) -> None:
    writer = RawStorageWriter(base_dir=tmp_path)
    writer.write(sample_document)

    with pytest.raises(StorageError, match="already exists"):
        writer.write(sample_document, overwrite=False)


@pytest.mark.issue_5
def test_read_missing_file_raises_error(tmp_path: Path) -> None:
    writer = RawStorageWriter(base_dir=tmp_path)
    with pytest.raises(StorageError, match="does not exist"):
        writer.read(tmp_path / "nonexistent.json")


@pytest.mark.issue_5
def test_read_corrupt_file_raises_error(tmp_path: Path) -> None:
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{invalid json", encoding="utf-8")

    writer = RawStorageWriter(base_dir=tmp_path)
    with pytest.raises(StorageError, match="Failed to read or validate"):
        writer.read(corrupt_file)

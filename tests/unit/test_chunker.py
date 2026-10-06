"""Unit tests for DocumentChunker."""

import pytest

from financial_research_agent.transform.chunker import ChunkerError, DocumentChunker
from financial_research_agent.transform.schemas import (
    CleanDocument,
    DocumentChunk,
    FilingSection,
)


@pytest.fixture
def chunker() -> DocumentChunker:
    # Use smaller limits for fast and transparent unit testing
    return DocumentChunker(max_tokens=20, overlap_tokens=5)


@pytest.mark.issue_7
def test_chunker_parameter_validation() -> None:
    with pytest.raises(ChunkerError, match="max_tokens must be positive"):
        DocumentChunker(max_tokens=0)

    with pytest.raises(ChunkerError, match="overlap_tokens cannot be negative"):
        DocumentChunker(max_tokens=100, overlap_tokens=-1)

    with pytest.raises(ChunkerError, match="strictly less than"):
        DocumentChunker(max_tokens=50, overlap_tokens=50)


@pytest.mark.issue_7
def test_chunk_short_text(chunker: DocumentChunker) -> None:
    text = "Short overview."
    chunks = chunker.chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0] == text
    assert chunker.count_tokens(chunks[0]) <= chunker.max_tokens


@pytest.mark.issue_7
def test_chunk_long_text_sliding_window(chunker: DocumentChunker) -> None:
    long_text = (
        "Apple designs and manufactures mobile communication devices and personal computers. "
        "The company also provides digital content streaming and payment services. "
        "Global operations are subject to regional macroeconomic conditions "
        "and foreign exchange risk."
    )
    chunks = chunker.chunk_text(long_text)

    assert len(chunks) > 1
    for chunk in chunks:
        tokens = chunker.count_tokens(chunk)
        assert tokens <= chunker.max_tokens


@pytest.mark.issue_7
def test_chunk_document_with_sections() -> None:
    chunker = DocumentChunker(max_tokens=15, overlap_tokens=4)
    doc = CleanDocument(
        document_id="clean_AAPL_10k_2023",
        source_document_id="0000320193-23-000106",
        ticker="AAPL",
        form_type="10-K",
        clean_text="Combined text",
        sections=[
            FilingSection(
                section_id="item_1",
                title="Item 1: Business",
                content=(
                    "Apple sells personal computers and mobile devices with integrated "
                    "operating systems and cloud services globally."
                ),
                char_count=120,
            ),
            FilingSection(
                section_id="item_1a",
                title="Item 1A: Risk Factors",
                content=(
                    "Supply chain dependencies across Asian markets expose manufacturing "
                    "lines to unexpected delays and export restrictions."
                ),
                char_count=130,
            ),
        ],
        metadata={"year": 2023},
    )

    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 2
    for idx, c in enumerate(chunks):
        assert isinstance(c, DocumentChunk)
        assert c.chunk_index == idx
        assert c.chunk_id == f"clean_AAPL_10k_2023_{idx:04d}"
        assert c.token_count <= chunker.max_tokens
        assert c.ticker == "AAPL"
        assert c.section_id in ("item_1", "item_1a")
        assert "section_title" in c.metadata
        assert c.metadata["year"] == 2023


@pytest.mark.issue_7
def test_chunk_document_without_sections() -> None:
    chunker = DocumentChunker(max_tokens=15, overlap_tokens=3)
    doc = CleanDocument(
        document_id="clean_MSFT_8k",
        source_document_id="0000789019-23-000085",
        ticker="MSFT",
        form_type="8-K",
        clean_text="Microsoft announced quarterly dividend and management changes.",
        sections=[],
    )

    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 1
    assert chunks[0].section_id is None
    assert chunks[0].document_id == "clean_MSFT_8k"


@pytest.mark.issue_7
def test_chunk_empty_document_raises_error(chunker: DocumentChunker) -> None:
    empty_doc = CleanDocument(
        document_id="empty_doc",
        source_document_id="src_empty",
        ticker="EMPTY",
        form_type="10-K",
        clean_text="   ",
        sections=[],
    )

    with pytest.raises(ChunkerError, match="contains no text"):
        chunker.chunk_document(empty_doc)

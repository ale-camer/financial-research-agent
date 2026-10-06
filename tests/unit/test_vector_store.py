"""Unit tests for VectorStore."""

from pathlib import Path

import pytest

from financial_research_agent.transform.schemas import EmbeddedChunk, SearchResult
from financial_research_agent.transform.vector_store import (
    VectorStore,
    VectorStoreError,
    cosine_similarity,
)


@pytest.fixture
def sample_chunks() -> list[EmbeddedChunk]:
    return [
        EmbeddedChunk(
            chunk_id="chunk_aapl_1",
            document_id="doc_aapl",
            ticker="AAPL",
            form_type="10-K",
            section_id="item_1",
            chunk_index=0,
            content="Apple designs and sells consumer hardware.",
            embedding=[1.0, 0.0, 0.0],
            embedding_model="test-embed",
            dimensions=3,
            metadata={"year": 2023},
        ),
        EmbeddedChunk(
            chunk_id="chunk_aapl_2",
            document_id="doc_aapl",
            ticker="AAPL",
            form_type="10-K",
            section_id="item_1a",
            chunk_index=1,
            content="Apple supply chain disruptions across Asia.",
            embedding=[0.0, 1.0, 0.0],
            embedding_model="test-embed",
            dimensions=3,
            metadata={"year": 2023},
        ),
        EmbeddedChunk(
            chunk_id="chunk_msft_1",
            document_id="doc_msft",
            ticker="MSFT",
            form_type="10-Q",
            section_id="item_1",
            chunk_index=0,
            content="Microsoft cloud computing and enterprise software.",
            embedding=[0.7071, 0.7071, 0.0],
            embedding_model="test-embed",
            dimensions=3,
            metadata={"year": 2023},
        ),
    ]


@pytest.mark.issue_9
def test_cosine_similarity_calculation() -> None:
    assert pytest.approx(cosine_similarity([1.0, 0.0], [1.0, 0.0])) == 1.0
    assert pytest.approx(cosine_similarity([1.0, 0.0], [0.0, 1.0])) == 0.0
    assert pytest.approx(cosine_similarity([1.0, 0.0], [-1.0, 0.0])) == -1.0

    with pytest.raises(VectorStoreError, match="dimension mismatch"):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


@pytest.mark.issue_9
def test_vector_store_add_and_get(sample_chunks: list[EmbeddedChunk]) -> None:
    store = VectorStore()
    assert store.count() == 0

    added = store.add(sample_chunks)
    assert added == 3
    assert store.count() == 3

    chunk = store.get("chunk_aapl_1")
    assert chunk is not None
    assert chunk.ticker == "AAPL"

    assert store.get("nonexistent") is None


@pytest.mark.issue_9
def test_vector_store_cosine_search_ranking(sample_chunks: list[EmbeddedChunk]) -> None:
    store = VectorStore()
    store.add(sample_chunks)

    # Query pointing exactly towards [1.0, 0.0, 0.0] (chunk_aapl_1)
    results = store.search(query_vector=[1.0, 0.0, 0.0], top_k=2)

    assert len(results) == 2
    assert isinstance(results[0], SearchResult)
    assert results[0].chunk.chunk_id == "chunk_aapl_1"
    assert pytest.approx(results[0].score, 0.001) == 1.0

    # Second result should be MSFT (cosine approx 0.707)
    assert results[1].chunk.chunk_id == "chunk_msft_1"
    assert results[1].score > 0.7


@pytest.mark.issue_9
def test_vector_store_metadata_filtering(sample_chunks: list[EmbeddedChunk]) -> None:
    store = VectorStore()
    store.add(sample_chunks)

    # Filter by ticker MSFT
    msft_results = store.search(query_vector=[1.0, 0.0, 0.0], top_k=5, ticker="MSFT")
    assert len(msft_results) == 1
    assert msft_results[0].chunk.ticker == "MSFT"

    # Filter by section_id item_1a
    risk_results = store.search(query_vector=[0.0, 1.0, 0.0], top_k=5, section_id="item_1a")
    assert len(risk_results) == 1
    assert risk_results[0].chunk.section_id == "item_1a"


@pytest.mark.issue_9
def test_vector_store_search_validation() -> None:
    store = VectorStore()
    with pytest.raises(VectorStoreError, match="top_k must be positive"):
        store.search(query_vector=[1.0, 0.0], top_k=0)


@pytest.mark.issue_9
def test_vector_store_save_and_load(tmp_path: Path, sample_chunks: list[EmbeddedChunk]) -> None:
    save_file = tmp_path / "index.json"
    store = VectorStore(storage_path=save_file)
    store.add(sample_chunks)

    saved_path = store.save()
    assert saved_path == save_file
    assert save_file.is_file()

    # Load in new store
    new_store = VectorStore(storage_path=save_file)
    assert new_store.count() == 3

    results = new_store.search(query_vector=[1.0, 0.0, 0.0], top_k=1)
    assert len(results) == 1
    assert results[0].chunk.chunk_id == "chunk_aapl_1"


@pytest.mark.issue_9
def test_vector_store_load_missing_file_raises_error(tmp_path: Path) -> None:
    store = VectorStore()
    with pytest.raises(VectorStoreError, match="does not exist"):
        store.load(tmp_path / "missing.json")

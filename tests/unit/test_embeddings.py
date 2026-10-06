"""Unit tests for EmbeddingGenerator."""

from unittest.mock import MagicMock

import pytest

from financial_research_agent.transform.embeddings import (
    EmbeddingError,
    EmbeddingGenerator,
)
from financial_research_agent.transform.schemas import DocumentChunk, EmbeddedChunk


@pytest.fixture
def mock_embed_fn() -> MagicMock:
    def _fn(batch: list[str]) -> list[list[float]]:
        # Return 4-dimensional mock vector for each string
        return [[0.1, 0.2, 0.3, 0.4] for _ in batch]

    return MagicMock(side_effect=_fn)


@pytest.mark.issue_8
def test_embedding_generator_parameter_validation() -> None:
    with pytest.raises(EmbeddingError, match="batch_size must be positive"):
        EmbeddingGenerator(batch_size=0)

    with pytest.raises(EmbeddingError, match="dimensions must be positive"):
        EmbeddingGenerator(dimensions=-1)


@pytest.mark.issue_8
def test_generate_embeddings_empty_list() -> None:
    generator = EmbeddingGenerator(dimensions=4, embed_fn=lambda _: [])
    assert generator.generate_embeddings([]) == []


@pytest.mark.issue_8
def test_generate_embeddings_batching(mock_embed_fn: MagicMock) -> None:
    generator = EmbeddingGenerator(
        dimensions=4,
        batch_size=2,
        embed_fn=mock_embed_fn,
    )
    texts = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]

    vectors = generator.generate_embeddings(texts)

    assert len(vectors) == 5
    assert all(len(v) == 4 for v in vectors)
    # 5 items with batch_size 2 => 3 batch calls (2, 2, 1)
    assert mock_embed_fn.call_count == 3


@pytest.mark.issue_8
def test_generate_embeddings_dimension_mismatch() -> None:
    def bad_embed_fn(batch: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in batch]

    generator = EmbeddingGenerator(dimensions=4, embed_fn=bad_embed_fn)

    with pytest.raises(EmbeddingError, match="dimension mismatch"):
        generator.generate_embeddings(["Sample text"])


@pytest.mark.issue_8
def test_embed_chunks_mapping(mock_embed_fn: MagicMock) -> None:
    generator = EmbeddingGenerator(
        model="text-embedding-3-small",
        dimensions=4,
        embed_fn=mock_embed_fn,
    )
    chunks = [
        DocumentChunk(
            chunk_id="chunk_001",
            document_id="doc_aapl",
            ticker="AAPL",
            form_type="10-K",
            section_id="item_1",
            chunk_index=0,
            token_count=10,
            content="Apple business operations",
            metadata={"year": 2023},
        ),
        DocumentChunk(
            chunk_id="chunk_002",
            document_id="doc_aapl",
            ticker="AAPL",
            form_type="10-K",
            section_id="item_1a",
            chunk_index=1,
            token_count=12,
            content="Apple supply chain risks",
            metadata={"year": 2023},
        ),
    ]

    embedded = generator.embed_chunks(chunks)

    assert len(embedded) == 2
    for orig, emb in zip(chunks, embedded, strict=True):
        assert isinstance(emb, EmbeddedChunk)
        assert emb.chunk_id == orig.chunk_id
        assert emb.document_id == orig.document_id
        assert emb.ticker == orig.ticker
        assert emb.section_id == orig.section_id
        assert emb.embedding_model == "text-embedding-3-small"
        assert emb.dimensions == 4
        assert emb.embedding == [0.1, 0.2, 0.3, 0.4]
        assert emb.metadata["year"] == 2023


@pytest.mark.issue_8
def test_api_client_error_handling() -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = RuntimeError("OpenAI API rate limit")

    generator = EmbeddingGenerator(dimensions=4, client=mock_client)
    with pytest.raises(EmbeddingError, match="API call to embedding model failed"):
        generator.generate_embeddings(["Any text"])

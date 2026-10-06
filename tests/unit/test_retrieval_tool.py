"""Unit tests for RetrievalTool and associated schemas."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from financial_research_agent.agent import (
    Citation,
    RetrievalError,
    RetrievalQuery,
    RetrievalResult,
    RetrievalTool,
)
from financial_research_agent.transform.embeddings import (
    EmbeddingError,
    EmbeddingGenerator,
)
from financial_research_agent.transform.schemas import EmbeddedChunk
from financial_research_agent.transform.vector_store import (
    VectorStore,
    VectorStoreError,
)


@pytest.fixture
def sample_chunks() -> list[EmbeddedChunk]:
    """Sample embedded chunks representing multiple tickers and sections."""
    return [
        EmbeddedChunk(
            chunk_id="chunk_aapl_1",
            document_id="doc_aapl_2023",
            ticker="AAPL",
            form_type="10-K",
            section_id="item_1",
            chunk_index=0,
            content="Apple Inc. designs, manufactures, and markets smartphones and computers.",
            embedding=[1.0, 0.0, 0.0],
            embedding_model="test-embed",
            dimensions=3,
            metadata={"fiscal_year": 2023},
        ),
        EmbeddedChunk(
            chunk_id="chunk_aapl_2",
            document_id="doc_aapl_2023",
            ticker="AAPL",
            form_type="10-K",
            section_id="item_1a",
            chunk_index=1,
            content="Global supply chain disruptions and component shortages pose business risks.",
            embedding=[0.0, 1.0, 0.0],
            embedding_model="test-embed",
            dimensions=3,
            metadata={"fiscal_year": 2023},
        ),
        EmbeddedChunk(
            chunk_id="chunk_msft_1",
            document_id="doc_msft_2023",
            ticker="MSFT",
            form_type="10-Q",
            section_id="item_1",
            chunk_index=0,
            content="Microsoft Intelligent Cloud segment experienced strong Azure growth.",
            embedding=[0.0, 0.0, 1.0],
            embedding_model="test-embed",
            dimensions=3,
            metadata={"fiscal_year": 2023},
        ),
    ]


@pytest.fixture
def populated_vector_store(sample_chunks: list[EmbeddedChunk]) -> VectorStore:
    """In-memory VectorStore populated with sample chunks."""
    store = VectorStore()
    store.add(sample_chunks)
    return store


@pytest.fixture
def mock_embedding_generator() -> EmbeddingGenerator:
    """Mock EmbeddingGenerator mapping text terms to distinct 3D unit vectors."""

    def _embed(batch: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in batch:
            lowered = text.lower()
            if "supply" in lowered or "risk" in lowered:
                results.append([0.0, 1.0, 0.0])
            elif "cloud" in lowered or "azure" in lowered:
                results.append([0.0, 0.0, 1.0])
            elif "hardware" in lowered or "smartphones" in lowered or "apple" in lowered:
                results.append([1.0, 0.0, 0.0])
            else:
                results.append([0.577, 0.577, 0.577])
        return results

    return EmbeddingGenerator(dimensions=3, embed_fn=_embed)


@pytest.mark.issue_11
def test_retrieval_query_valid_and_immutable() -> None:
    query = RetrievalQuery(
        query="What are the main risks?",
        top_k=3,
        ticker="AAPL",
        form_type="10-K",
        section_id="item_1a",
        min_score=0.7,
    )
    assert query.query == "What are the main risks?"
    assert query.top_k == 3
    assert query.ticker == "AAPL"
    assert query.form_type == "10-K"
    assert query.section_id == "item_1a"
    assert query.min_score == 0.7

    with pytest.raises(ValidationError):
        query.query = "new query"  # type: ignore[misc]


@pytest.mark.issue_11
def test_retrieval_query_validation_errors() -> None:
    with pytest.raises(ValidationError, match="Query string cannot be empty"):
        RetrievalQuery(query="")

    with pytest.raises(ValidationError, match="Query string cannot be empty"):
        RetrievalQuery(query="   \n\t  ")

    with pytest.raises(ValidationError):
        RetrievalQuery(query="valid query", top_k=0)


@pytest.mark.issue_11
def test_citation_schema_and_reference() -> None:
    citation = Citation(
        chunk_id="chunk_123",
        document_id="doc_456",
        ticker="AAPL",
        form_type="10-K",
        section_id="item_1a",
        chunk_index=2,
        score=0.9521,
        content="Risk factors excerpt.",
        metadata={"year": 2023},
    )
    assert citation.chunk_id == "chunk_123"
    assert citation.reference == "[AAPL 10-K item_1a #2]"
    assert citation.score == 0.9521

    citation_no_section = Citation(
        chunk_id="chunk_124",
        document_id="doc_456",
        ticker="MSFT",
        form_type="10-Q",
        chunk_index=0,
        score=0.88,
        content="Overview excerpt.",
    )
    assert citation_no_section.reference == "[MSFT 10-Q #0]"

    with pytest.raises(ValidationError):
        citation.score = 0.5  # type: ignore[misc]


@pytest.mark.issue_11
def test_retrieval_result_schema() -> None:
    result = RetrievalResult(
        query="cloud revenue",
        citations=[],
        formatted_context="No relevant filing chunks found for the query.",
        total_results=0,
    )
    assert result.query == "cloud revenue"
    assert result.total_results == 0
    assert "No relevant" in result.formatted_context

    with pytest.raises(ValidationError):
        result.total_results = 5  # type: ignore[misc]


@pytest.mark.issue_11
def test_retrieval_tool_initialization_validation(
    populated_vector_store: VectorStore,
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    tool = RetrievalTool(
        vector_store=populated_vector_store,
        embedding_generator=mock_embedding_generator,
        default_top_k=5,
    )
    assert tool.default_top_k == 5
    assert tool.name == "retrieve_filing_chunks"

    with pytest.raises(RetrievalError, match="default_top_k must be positive"):
        RetrievalTool(
            vector_store=populated_vector_store,
            embedding_generator=mock_embedding_generator,
            default_top_k=0,
        )


@pytest.mark.issue_11
def test_retrieval_tool_spec(
    populated_vector_store: VectorStore,
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    tool = RetrievalTool(
        vector_store=populated_vector_store,
        embedding_generator=mock_embedding_generator,
    )
    spec = tool.tool_spec

    assert spec["type"] == "function"
    assert spec["function"]["name"] == "retrieve_filing_chunks"
    params = spec["function"]["parameters"]
    assert params["type"] == "object"
    assert "query" in params["required"]
    assert "query" in params["properties"]
    assert "ticker" in params["properties"]
    assert "form_type" in params["properties"]
    assert "section_id" in params["properties"]
    assert "top_k" in params["properties"]
    assert "min_score" in params["properties"]


@pytest.mark.issue_11
def test_retrieval_tool_semantic_search(
    populated_vector_store: VectorStore,
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    tool = RetrievalTool(
        vector_store=populated_vector_store,
        embedding_generator=mock_embedding_generator,
    )

    result = tool.run(query="What are the supply chain risks?")

    assert isinstance(result, RetrievalResult)
    assert result.query == "What are the supply chain risks?"
    assert result.total_results == 3
    assert len(result.citations) == 3

    # Most relevant chunk should be chunk_aapl_2 ([0, 1, 0] matches risk query [0, 1, 0])
    top_citation = result.citations[0]
    assert top_citation.chunk_id == "chunk_aapl_2"
    assert top_citation.ticker == "AAPL"
    assert top_citation.section_id == "item_1a"
    assert top_citation.score == 1.0
    assert "supply chain" in top_citation.content

    # Formatted context check
    assert "[1] Source: AAPL 10-K | Section: item_1a" in result.formatted_context
    assert "supply chain disruptions" in result.formatted_context


@pytest.mark.issue_11
def test_retrieval_tool_with_query_model_and_callable(
    populated_vector_store: VectorStore,
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    tool = RetrievalTool(
        vector_store=populated_vector_store,
        embedding_generator=mock_embedding_generator,
    )

    query_obj = RetrievalQuery(query="azure cloud growth", ticker="MSFT", top_k=2)
    # Test __call__
    result = tool(query=query_obj)

    assert result.total_results == 1
    assert result.citations[0].chunk_id == "chunk_msft_1"
    assert result.citations[0].ticker == "MSFT"


@pytest.mark.issue_11
def test_retrieval_tool_filtering(
    populated_vector_store: VectorStore,
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    tool = RetrievalTool(
        vector_store=populated_vector_store,
        embedding_generator=mock_embedding_generator,
    )

    # Filter by ticker
    aapl_results = tool.run(query="general overview", ticker="AAPL")
    assert all(c.ticker == "AAPL" for c in aapl_results.citations)
    assert len(aapl_results.citations) == 2

    # Filter by section_id
    item1_results = tool.run(query="general overview", section_id="item_1")
    assert all(c.section_id == "item_1" for c in item1_results.citations)
    assert len(item1_results.citations) == 2

    # Filter by form_type
    ten_q_results = tool.run(query="general overview", form_type="10-Q")
    assert all(c.form_type == "10-Q" for c in ten_q_results.citations)
    assert len(ten_q_results.citations) == 1
    assert ten_q_results.citations[0].ticker == "MSFT"


@pytest.mark.issue_11
def test_retrieval_tool_min_score_filter(
    populated_vector_store: VectorStore,
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    tool = RetrievalTool(
        vector_store=populated_vector_store,
        embedding_generator=mock_embedding_generator,
    )

    result = tool.run(query="azure cloud growth", min_score=0.9)
    assert result.total_results == 1
    assert result.citations[0].chunk_id == "chunk_msft_1"
    assert result.citations[0].score >= 0.9


@pytest.mark.issue_11
def test_retrieval_tool_empty_results(
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    empty_store = VectorStore()
    tool = RetrievalTool(
        vector_store=empty_store,
        embedding_generator=mock_embedding_generator,
    )

    result = tool.run(query="any search term")
    assert result.total_results == 0
    assert len(result.citations) == 0
    assert result.formatted_context == "No relevant filing chunks found for the query."


@pytest.mark.issue_11
def test_retrieval_tool_invalid_inputs(
    populated_vector_store: VectorStore,
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    tool = RetrievalTool(
        vector_store=populated_vector_store,
        embedding_generator=mock_embedding_generator,
    )

    # Empty string
    with pytest.raises(RetrievalError, match="Invalid retrieval parameters"):
        tool.run(query="")

    # Non-string / non-RetrievalQuery
    with pytest.raises(RetrievalError, match="Query must be str or RetrievalQuery"):
        tool.run(query=123)  # type: ignore[arg-type]


@pytest.mark.issue_11
def test_retrieval_tool_embedding_failure(
    populated_vector_store: VectorStore,
) -> None:
    bad_generator = EmbeddingGenerator(
        dimensions=3,
        embed_fn=MagicMock(side_effect=EmbeddingError("API down")),
    )
    tool = RetrievalTool(
        vector_store=populated_vector_store,
        embedding_generator=bad_generator,
    )

    with pytest.raises(RetrievalError, match="Embedding generation failed"):
        tool.run(query="Apple risk factors")


@pytest.mark.issue_11
def test_retrieval_tool_vector_store_failure(
    mock_embedding_generator: EmbeddingGenerator,
) -> None:
    store = VectorStore()
    store.search = MagicMock(side_effect=VectorStoreError("Index corrupted"))  # type: ignore[method-assign]
    tool = RetrievalTool(
        vector_store=store,
        embedding_generator=mock_embedding_generator,
    )

    with pytest.raises(RetrievalError, match="Vector search failed"):
        tool.run(query="Apple risk factors")

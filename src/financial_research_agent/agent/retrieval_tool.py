"""Vector retrieval tool connecting embedding generation and vector search."""

from typing import Any

from financial_research_agent.agent.schemas import (
    Citation,
    RetrievalQuery,
    RetrievalResult,
)
from financial_research_agent.transform.embeddings import (
    EmbeddingError,
    EmbeddingGenerator,
)
from financial_research_agent.transform.vector_store import (
    VectorStore,
    VectorStoreError,
)


class RetrievalError(Exception):
    """Base exception for retrieval tool execution failures."""


class RetrievalTool:
    """Semantic retrieval tool executing vector search over indexed filing chunks."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_generator: EmbeddingGenerator,
        default_top_k: int = 5,
        name: str = "retrieve_filing_chunks",
        description: str | None = None,
    ) -> None:
        if default_top_k <= 0:
            raise RetrievalError(f"default_top_k must be positive, got {default_top_k}")

        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.default_top_k = default_top_k
        self.name = name
        self.description = (
            description
            or "Search indexed SEC filing text chunks using semantic vector similarity. "
            "Returns relevant excerpts with citations and relevance scores."
        )

    @property
    def tool_spec(self) -> dict[str, Any]:
        """Return an OpenAI-compatible function calling tool schema specification."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Natural language search query describing the information "
                                "needed from SEC filings (e.g. 'risk factors related to AI')."
                            ),
                        },
                        "ticker": {
                            "type": "string",
                            "description": (
                                "Optional equity ticker symbol to filter chunks (e.g. 'AAPL')."
                            ),
                        },
                        "form_type": {
                            "type": "string",
                            "description": (
                                "Optional SEC filing form type filter (e.g. '10-K', '10-Q')."
                            ),
                        },
                        "section_id": {
                            "type": "string",
                            "description": (
                                "Optional filing section identifier (e.g. 'item_1', 'item_1a')."
                            ),
                        },
                        "top_k": {
                            "type": "integer",
                            "description": (
                                "Maximum number of relevant chunks to retrieve (default: 5)."
                            ),
                        },
                        "min_score": {
                            "type": "number",
                            "description": (
                                "Optional minimum similarity score threshold between 0.0 and 1.0."
                            ),
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    def format_context(self, citations: list[Citation]) -> str:
        """Format a list of citations into a readable string suitable for LLM context prompts."""
        if not citations:
            return "No relevant filing chunks found for the query."

        blocks: list[str] = []
        for idx, citation in enumerate(citations, start=1):
            section_info = f" | Section: {citation.section_id}" if citation.section_id else ""
            header = (
                f"[{idx}] Source: {citation.ticker} {citation.form_type}{section_info} "
                f"(Score: {citation.score:.4f}, Chunk ID: {citation.chunk_id})"
            )
            blocks.append(f"{header}\n{citation.content}")

        return "\n\n".join(blocks)

    def run(
        self,
        query: str | RetrievalQuery,
        top_k: int | None = None,
        ticker: str | None = None,
        form_type: str | None = None,
        section_id: str | None = None,
        min_score: float | None = None,
    ) -> RetrievalResult:
        """Execute semantic search and return structured citations with formatted context."""
        if isinstance(query, str):
            try:
                query_obj = RetrievalQuery(
                    query=query,
                    top_k=top_k if top_k is not None else self.default_top_k,
                    ticker=ticker,
                    form_type=form_type,
                    section_id=section_id,
                    min_score=min_score,
                )
            except Exception as exc:
                raise RetrievalError(f"Invalid retrieval parameters: {exc}") from exc
        elif isinstance(query, RetrievalQuery):
            query_obj = query
        else:
            raise RetrievalError(f"Query must be str or RetrievalQuery, got {type(query).__name__}")

        try:
            vectors = self.embedding_generator.generate_embeddings([query_obj.query])
            if not vectors:
                raise RetrievalError(f"No embedding vector returned for query: {query_obj.query!r}")
            query_vector = vectors[0]
        except EmbeddingError as exc:
            raise RetrievalError(f"Embedding generation failed: {exc}") from exc
        except Exception as exc:
            raise RetrievalError(f"Unexpected error during query embedding: {exc}") from exc

        try:
            raw_results = self.vector_store.search(
                query_vector=query_vector,
                top_k=query_obj.top_k,
                ticker=query_obj.ticker,
                form_type=query_obj.form_type,
                section_id=query_obj.section_id,
            )
        except VectorStoreError as exc:
            raise RetrievalError(f"Vector search failed: {exc}") from exc
        except Exception as exc:
            raise RetrievalError(f"Unexpected error during vector search: {exc}") from exc

        if query_obj.min_score is not None:
            raw_results = [r for r in raw_results if r.score >= query_obj.min_score]

        citations = [
            Citation(
                chunk_id=res.chunk.chunk_id,
                document_id=res.chunk.document_id,
                ticker=res.chunk.ticker,
                form_type=res.chunk.form_type,
                section_id=res.chunk.section_id,
                chunk_index=res.chunk.chunk_index,
                score=res.score,
                content=res.chunk.content,
                metadata=res.chunk.metadata,
            )
            for res in raw_results
        ]

        formatted_context = self.format_context(citations)

        return RetrievalResult(
            query=query_obj.query,
            citations=citations,
            formatted_context=formatted_context,
            total_results=len(citations),
        )

    def __call__(
        self,
        query: str | RetrievalQuery,
        top_k: int | None = None,
        ticker: str | None = None,
        form_type: str | None = None,
        section_id: str | None = None,
        min_score: float | None = None,
    ) -> RetrievalResult:
        """Allow calling the instance directly as a callable."""
        return self.run(
            query=query,
            top_k=top_k,
            ticker=ticker,
            form_type=form_type,
            section_id=section_id,
            min_score=min_score,
        )

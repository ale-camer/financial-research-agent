"""Schemas for retrieval queries, citations, and search results."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RetrievalQuery(BaseModel):
    """Parameters for executing a semantic retrieval query against indexed chunks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(description="Natural language search query text")
    top_k: int = Field(default=5, ge=1, description="Maximum number of chunks to retrieve")
    ticker: str | None = Field(
        default=None,
        description="Optional equity ticker filter (e.g. AAPL)",
    )
    form_type: str | None = Field(
        default=None,
        description="Optional SEC filing form type filter (e.g. 10-K, 10-Q)",
    )
    section_id: str | None = Field(
        default=None,
        description="Optional filing section identifier filter (e.g. item_1, item_1a, item_7)",
    )
    min_score: float | None = Field(
        default=None,
        description="Optional minimum cosine similarity score threshold",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Validate query text is not empty or whitespace only."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Query string cannot be empty or whitespace only.")
        return cleaned


class Citation(BaseModel):
    """Structured attribution and text excerpt retrieved from a filing chunk."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(description="Unique identifier of the source chunk")
    document_id: str = Field(description="Parent document or filing accession identifier")
    ticker: str = Field(description="Company equity ticker symbol")
    form_type: str = Field(description="Filing form type (e.g. 10-K, 10-Q)")
    section_id: str | None = Field(
        default=None,
        description="Origin filing section ID if available",
    )
    chunk_index: int = Field(
        description="Zero-based index of the chunk in the parent document",
    )
    score: float = Field(description="Cosine similarity score for the retrieved chunk")
    content: str = Field(description="Text excerpt of the chunk")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Associated chunk metadata",
    )

    @property
    def reference(self) -> str:
        """Return a compact human-readable citation label."""
        section_part = f" {self.section_id}" if self.section_id else ""
        return f"[{self.ticker} {self.form_type}{section_part} #{self.chunk_index}]"


class RetrievalResult(BaseModel):
    """Output of retrieval operation including structured citations and prompt context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(description="Search query string that produced this result")
    citations: list[Citation] = Field(
        default_factory=list,
        description="Retrieved citations ranked by relevance score",
    )
    formatted_context: str = Field(
        description="Pre-formatted text representation of citations for LLM prompt context",
    )
    total_results: int = Field(description="Total number of citations retrieved")

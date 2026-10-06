"""Schemas for transformed documents, extracted filing sections, chunks, and embeddings."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FilingSection(BaseModel):
    """Cleaned text segment belonging to a recognized filing item or section."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    section_id: str = Field(description="Normalized identifier (e.g. item_1, item_1a, item_7)")
    title: str = Field(description="Original or normalized section heading title")
    content: str = Field(description="Cleaned text content of the section")
    char_count: int = Field(description="Character length of the section content")


class CleanDocument(BaseModel):
    """Cleaned, parsed document ready for chunking and embedding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(description="Unique identifier for the cleaned document")
    source_document_id: str = Field(description="Identifier of the origin raw document/accession")
    ticker: str = Field(description="Company ticker symbol")
    form_type: str = Field(description="Filing or document form type (e.g. 10-K, 10-Q)")
    filing_date: date | None = Field(default=None, description="Official filing date if available")
    clean_text: str = Field(description="Consolidated cleaned text of the document")
    sections: list[FilingSection] = Field(
        default_factory=list,
        description="Structured sections extracted from the filing",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary provenance or processing metadata",
    )


class DocumentChunk(BaseModel):
    """A discrete, token-bounded text snippet for embedding and vector search."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(description="Unique identifier for the chunk")
    document_id: str = Field(description="Parent CleanDocument identifier")
    ticker: str = Field(description="Company equity ticker symbol")
    form_type: str = Field(description="Origin filing or document type")
    section_id: str | None = Field(
        default=None,
        description="Identifier of the origin filing section if applicable",
    )
    chunk_index: int = Field(description="Zero-based sequential index of the chunk")
    token_count: int = Field(description="Number of tokens in the chunk content")
    content: str = Field(description="Raw text content of the chunk")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Associated metadata for search filtering",
    )


class EmbeddedChunk(BaseModel):
    """A document chunk enriched with a dense vector embedding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(description="Unique identifier for the chunk")
    document_id: str = Field(description="Parent CleanDocument identifier")
    ticker: str = Field(description="Company equity ticker symbol")
    form_type: str = Field(description="Origin filing or document type")
    section_id: str | None = Field(
        default=None,
        description="Identifier of the origin filing section if applicable",
    )
    chunk_index: int = Field(description="Zero-based sequential index of the chunk")
    content: str = Field(description="Raw text content of the chunk")
    embedding: list[float] = Field(description="Dense vector embedding representation")
    embedding_model: str = Field(description="Model used to generate the embedding")
    dimensions: int = Field(description="Dimensionality of the embedding vector")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Associated metadata for search filtering",
    )


class SearchResult(BaseModel):
    """A retrieved embedded chunk paired with its query similarity score."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk: EmbeddedChunk = Field(description="Retrieved chunk containing content and metadata")
    score: float = Field(description="Cosine similarity score (higher indicates greater relevance)")


class NormalizedMetrics(BaseModel):
    """Standardized financial and statistical metrics derived from raw market data."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str = Field(description="Company equity ticker symbol")
    calculated_at: datetime = Field(description="UTC timestamp when metrics were calculated")
    observation_count: int = Field(description="Number of price observations evaluated")
    current_price: float = Field(description="Latest closing price in the series")
    total_return: float = Field(description="Total cumulative percentage return across the period")
    annualized_volatility: float = Field(
        description="Annualized standard deviation of daily returns (252-day basis)"
    )
    high_period: float = Field(description="Highest price observation across the period")
    low_period: float = Field(description="Lowest price observation across the period")
    average_volume: float = Field(description="Mean trading volume across the period")
    sma_20: float | None = Field(default=None, description="20-period simple moving average")
    sma_50: float | None = Field(default=None, description="50-period simple moving average")
    additional_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Optional additional statistical metrics (e.g. max_drawdown)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary calculation metadata",
    )

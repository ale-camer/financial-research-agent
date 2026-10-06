"""Schemas for transformed documents, extracted filing sections, chunks, and embeddings."""

from datetime import date
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

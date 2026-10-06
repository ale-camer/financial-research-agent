"""Schemas for transformed documents and extracted filing sections."""

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

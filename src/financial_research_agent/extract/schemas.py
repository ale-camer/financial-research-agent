"""Pydantic schemas for raw financial documents and metadata."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    """Enumeration of supported raw document types."""

    SEC_FILING = "sec_filing"
    MARKET_DATA = "market_data"
    NEWS_ARTICLE = "news_article"


class RawDocumentMetadata(BaseModel):
    """Metadata attached to an extracted raw document artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_uri: str = Field(description="Origin URL or identifier of the extracted content")
    extracted_at: datetime = Field(description="UTC timestamp when the extraction took place")
    content_hash: str = Field(description="SHA-256 hash or digest of the raw content payload")
    extra_attributes: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Optional source-specific metadata key-value pairs",
    )


class RawSECFiling(BaseModel):
    """Raw SEC filing document payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str = Field(description="Company equity ticker symbol")
    cik: str = Field(
        description="SEC Central Index Key (10-digit zero-padded string or integer string)"
    )
    form_type: str = Field(description="SEC form type (e.g. 10-K, 10-Q, 8-K)")
    filing_date: date = Field(description="Official filing date as recorded by the SEC")
    accession_number: str = Field(description="Unique SEC EDGAR filing accession number")
    raw_content: str = Field(description="Raw text, XML, or HTML body of the filing")
    metadata: RawDocumentMetadata = Field(description="Extraction metadata")


class MarketDataPoint(BaseModel):
    """Single historical price and volume observation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(description="Timestamp of the observation interval")
    open: float = Field(description="Opening price")
    high: float = Field(description="Highest price")
    low: float = Field(description="Lowest price")
    close: float = Field(description="Closing price")
    volume: int = Field(description="Trading volume")


class RawMarketData(BaseModel):
    """Historical or intraday market price dataset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str = Field(description="Asset ticker symbol")
    interval: str = Field(description="Sampling interval (e.g. 1d, 1h, 5m)")
    start_date: datetime = Field(description="Start time of the extracted series")
    end_date: datetime = Field(description="End time of the extracted series")
    records: list[MarketDataPoint] = Field(
        default_factory=list,
        description="Ordered time series observations",
    )
    metadata: RawDocumentMetadata = Field(description="Extraction metadata")


class RawNewsArticle(BaseModel):
    """Raw news article extracted from an RSS feed or financial news site."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(description="Headline or title of the news article")
    publisher: str = Field(description="Publishing outlet or news agency")
    published_at: datetime = Field(description="Publication timestamp")
    url: str = Field(description="Canonical URL of the article")
    summary: str = Field(description="Short synopsis or RSS description")
    full_text: str | None = Field(default=None, description="Full article text if retrieved")
    metadata: RawDocumentMetadata = Field(description="Extraction metadata")


RawPayload = RawSECFiling | RawMarketData | RawNewsArticle


class RawDocument(BaseModel):
    """Generic envelope wrapping any validated raw financial artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(description="Unique system identifier for the document")
    document_type: DocumentType = Field(description="Classification of the enclosed document")
    payload: RawPayload = Field(description="Typed raw payload matching document_type")
    metadata: RawDocumentMetadata = Field(description="Extraction metadata")

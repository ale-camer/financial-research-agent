"""Request and response schemas for the FastAPI delivery service."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """System liveness and metadata response."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str = Field(default="ok", description="Health status string")
    version: str = Field(default="0.1.0", description="API package version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Current server timestamp in UTC",
    )


class ResearchRequest(BaseModel):
    """Payload requesting an agentic financial equity research report."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str = Field(min_length=1, description="Company equity ticker symbol")
    query: str = Field(
        default="Summarize company financial performance and principal business risks.",
        description="Specific research prompt or question",
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum agent reasoning steps",
    )
    format: str = Field(
        default="markdown",
        description="Report output format ('markdown' or 'json')",
    )
    mock: bool = Field(
        default=False,
        description="Whether to run using mock client for offline testing",
    )


class ResearchResponse(BaseModel):
    """Response payload enclosing the generated research report and citations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str = Field(description="Company equity ticker symbol")
    query: str = Field(description="Original research question")
    title: str = Field(description="Title of the generated report")
    executive_summary: str = Field(description="Executive summary synthesis")
    markdown_report: str = Field(description="Full formatted report in Markdown")
    citations_count: int = Field(ge=0, description="Total verified citations cited")
    generated_at: datetime = Field(description="Report generation timestamp in UTC")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution telemetry and model metadata",
    )


class IngestRequest(BaseModel):
    """Payload to trigger raw document data ingestion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tickers: list[str] = Field(
        default_factory=lambda: ["AAPL", "MSFT", "NVDA"],
        description="Equity tickers to ingest",
    )
    sec_form_types: list[str] = Field(
        default_factory=lambda: ["10-K", "10-Q"],
        description="SEC forms to fetch",
    )
    market_period: str = Field(
        default="1y",
        description="Historical price history period",
    )
    raw_storage_dir: str = Field(
        default="./data/raw",
        description="Target raw artifacts storage directory",
    )


class TransformRequest(BaseModel):
    """Payload to trigger document transformation and vector indexing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_storage_dir: str = Field(
        default="./data/raw",
        description="Source directory of raw documents",
    )
    processed_storage_dir: str = Field(
        default="./data/processed",
        description="Destination directory for processed documents and metrics",
    )
    vector_store_path: str = Field(
        default="./data/vector_store/index.json",
        description="Path for vector store index file",
    )
    tickers: list[str] | None = Field(
        default=None,
        description="Optional filter for specific company tickers",
    )

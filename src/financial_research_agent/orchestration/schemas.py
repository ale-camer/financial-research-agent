"""Schemas for ingestion DAG configuration, task summaries, and execution results."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IngestionConfig(BaseModel):
    """Configuration parameters for raw financial data ingestion tasks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tickers: list[str] = Field(
        default_factory=lambda: ["AAPL", "MSFT", "NVDA"],
        description="List of company equity tickers to ingest",
    )
    sec_form_types: list[str] = Field(
        default_factory=lambda: ["10-K", "10-Q"],
        description="SEC filing form types to extract per ticker",
    )
    sec_limit_per_form: int = Field(
        default=1,
        ge=1,
        description="Maximum filings per form type to fetch per ticker",
    )
    sec_user_agent: str = Field(
        default="FinancialResearchAgent admin@example.com",
        description="User-Agent string adhering to SEC guidelines",
    )
    market_period: str = Field(
        default="1y",
        description="Historical time range for price observations",
    )
    market_interval: str = Field(
        default="1d",
        description="Frequency interval for price series",
    )
    news_feed_urls: list[str] = Field(
        default_factory=list,
        description="RSS feed URLs to poll for financial news",
    )
    news_limit_per_feed: int = Field(
        default=10,
        ge=1,
        description="Maximum news articles to extract per feed",
    )
    raw_storage_dir: str = Field(
        default="./data/raw",
        description="Base directory path for partitioned raw document storage",
    )
    overwrite: bool = Field(
        default=True,
        description="Whether to overwrite existing artifacts in raw storage",
    )


class IngestionTaskSummary(BaseModel):
    """Execution metrics and artifact paths for a specific ingestion sub-task."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_name: str = Field(description="Name of the ingestion task")
    documents_ingested: int = Field(
        default=0,
        ge=0,
        description="Count of raw documents ingested by this task",
    )
    written_paths: list[str] = Field(
        default_factory=list,
        description="Absolute or relative file paths of persisted artifacts",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages encountered during task execution",
    )


class IngestionResult(BaseModel):
    """Aggregate execution summary and telemetry for an ingestion pipeline run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(description="Unique identifier for the ingestion pipeline run")
    started_at: datetime = Field(description="UTC timestamp when the pipeline started")
    completed_at: datetime = Field(description="UTC timestamp when the pipeline completed")
    duration_seconds: float = Field(
        ge=0.0,
        description="Total elapsed pipeline execution time in seconds",
    )
    sec_filings_count: int = Field(
        default=0,
        ge=0,
        description="Total SEC filings successfully ingested",
    )
    market_data_count: int = Field(
        default=0,
        ge=0,
        description="Total market data series ingested",
    )
    news_articles_count: int = Field(
        default=0,
        ge=0,
        description="Total news articles ingested",
    )
    total_documents_ingested: int = Field(
        default=0,
        ge=0,
        description="Sum of all raw artifacts written to storage",
    )
    written_files: list[str] = Field(
        default_factory=list,
        description="File paths of all persisted raw documents",
    )
    task_summaries: list[IngestionTaskSummary] = Field(
        default_factory=list,
        description="Granular performance summaries per ingestion task",
    )
    status: str = Field(
        default="success",
        description="Overall pipeline status ('success', 'partial_success', 'failed')",
    )

"""Unit tests for ReportGenerator and FinancialResearchReport schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from financial_research_agent.agent import (
    AgentRunResult,
    AgentStep,
    ChatMessage,
    Citation,
    FinancialResearchReport,
    ReportGenerator,
    ReportGeneratorError,
    ReportSection,
    TokenUsage,
)
from financial_research_agent.transform.schemas import NormalizedMetrics


@pytest.fixture
def sample_citations() -> list[Citation]:
    """Sample citation models for testing report sources."""
    return [
        Citation(
            chunk_id="chunk_aapl_1",
            document_id="doc_aapl_2023",
            ticker="AAPL",
            form_type="10-K",
            section_id="item_1",
            chunk_index=0,
            score=0.9234,
            content="Apple Inc. designs, manufactures, and markets smartphones.",
        ),
        Citation(
            chunk_id="chunk_aapl_2",
            document_id="doc_aapl_2023",
            ticker="AAPL",
            form_type="10-K",
            section_id="item_1a",
            chunk_index=1,
            score=0.8911,
            content="Global supply chain disruptions pose potential business risks.",
        ),
    ]


@pytest.fixture
def sample_metrics() -> NormalizedMetrics:
    """Sample NormalizedMetrics model."""
    return NormalizedMetrics(
        ticker="AAPL",
        calculated_at=datetime(2023, 11, 3, 16, 0, 0, tzinfo=UTC),
        observation_count=252,
        current_price=175.50,
        total_return=0.152,
        annualized_volatility=0.224,
        high_period=180.00,
        low_period=140.00,
        average_volume=55000000.0,
        sma_20=172.30,
        sma_50=168.10,
        additional_metrics={"max_drawdown": 0.085},
    )


@pytest.mark.issue_15
def test_report_schemas_immutability(sample_citations: list[Citation]) -> None:
    section = ReportSection(
        title="Business Overview",
        content="Overview content",
        citations=sample_citations,
    )
    with pytest.raises(ValidationError):
        section.title = "New Title"  # type: ignore[misc]

    report = FinancialResearchReport(
        ticker="AAPL",
        title="Apple Research",
        generated_at=datetime.now(UTC),
        executive_summary="Summary",
        raw_query="Analyze AAPL",
    )
    with pytest.raises(ValidationError):
        report.ticker = "MSFT"  # type: ignore[misc]


@pytest.mark.issue_15
def test_citation_deduplication(sample_citations: list[Citation]) -> None:
    generator = ReportGenerator()
    duplicated_list = [
        sample_citations[0],
        sample_citations[1],
        sample_citations[0],  # Duplicate chunk_id
    ]

    deduped = generator.deduplicate_citations(duplicated_list)
    assert len(deduped) == 2
    assert deduped[0].chunk_id == "chunk_aapl_1"
    assert deduped[1].chunk_id == "chunk_aapl_2"


@pytest.mark.issue_15
def test_parse_markdown_sections() -> None:
    generator = ReportGenerator()

    # Plain text without headers
    sections_plain = generator.parse_markdown_sections("Just a single paragraph.")
    assert len(sections_plain) == 1
    assert sections_plain[0].title == "Analysis & Findings"
    assert sections_plain[0].content == "Just a single paragraph."

    # Multi-section markdown text
    markdown_doc = """Preamble context before first heading.

## Business Overview
Apple designs high-end consumer technology.

## Financial Risks
Supply chain dependencies across foreign markets."""

    sections = generator.parse_markdown_sections(markdown_doc)
    assert len(sections) == 3
    assert sections[0].title == "Overview"
    assert sections[0].content == "Preamble context before first heading."
    assert sections[1].title == "Business Overview"
    assert "consumer technology" in sections[1].content
    assert sections[2].title == "Financial Risks"
    assert "Supply chain" in sections[2].content


@pytest.mark.issue_15
def test_build_report_direct(
    sample_citations: list[Citation],
    sample_metrics: NormalizedMetrics,
) -> None:
    generator = ReportGenerator()
    section = ReportSection(
        title="Competitive Advantage",
        content="Ecosystem lock-in is robust.",
        citations=[sample_citations[0]],
    )

    report = generator.build_report(
        ticker="aapl",
        query="Evaluate Apple moat",
        executive_summary="Apple maintains a wide moat.",
        sections=[section],
        key_metrics=sample_metrics,
        citations=sample_citations,
    )

    assert report.ticker == "AAPL"
    assert report.title == "Financial Research Report: AAPL"
    assert report.executive_summary == "Apple maintains a wide moat."
    assert len(report.sections) == 1
    assert report.key_metrics is not None
    assert report.key_metrics.current_price == 175.50
    assert len(report.citations) == 2


@pytest.mark.issue_15
def test_generate_from_run(
    sample_citations: list[Citation],
    sample_metrics: NormalizedMetrics,
) -> None:
    generator = ReportGenerator()

    trajectory_text = """## Executive Summary
Apple demonstrates resilient revenue growth.

## Core Growth Drivers
Services segment margins expanded significantly."""

    run_result = AgentRunResult(
        query="Analyze Apple performance",
        final_response=trajectory_text,
        steps=[
            AgentStep(
                step_number=1,
                assistant_message=ChatMessage.assistant(content=trajectory_text),
                tool_executions=[],
                tokens_used=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
            )
        ],
        total_tokens=TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
        iterations=1,
        messages=[],
    )

    report = generator.generate_from_run(
        ticker="AAPL",
        run_result=run_result,
        key_metrics=sample_metrics,
        citations=sample_citations,
    )

    assert report.ticker == "AAPL"
    assert report.executive_summary == "Apple demonstrates resilient revenue growth."
    assert len(report.sections) == 1
    assert report.sections[0].title == "Core Growth Drivers"
    assert report.metadata["total_tokens"] == 80
    assert report.metadata["iterations"] == 1


@pytest.mark.issue_15
def test_to_markdown_full(
    sample_citations: list[Citation],
    sample_metrics: NormalizedMetrics,
) -> None:
    generator = ReportGenerator()
    section = ReportSection(
        title="Risk Analysis",
        content="Antitrust scrutiny in the App Store.",
        citations=[sample_citations[1]],
    )

    report = generator.build_report(
        ticker="AAPL",
        query="Assess regulatory risk",
        executive_summary="Regulatory pressures represent a key headwind.",
        sections=[section],
        key_metrics=sample_metrics,
        citations=sample_citations,
    )

    md = report.to_markdown()

    # Assert Title and metadata
    assert "# Financial Research Report: AAPL (AAPL)" in md
    assert "Query: Assess regulatory risk" in md

    # Assert Executive summary
    assert "## Executive Summary" in md
    assert "Regulatory pressures represent a key headwind." in md

    # Assert Market metrics table
    assert "## Key Market Metrics" in md
    assert "| Current Price | $175.50 |" in md
    assert "| Total Return | 15.20% |" in md
    assert "| Annualized Volatility | 22.40% |" in md
    assert "| 20-Day SMA | $172.30 |" in md
    assert "| Max Drawdown | 8.50% |" in md

    # Assert Sections
    assert "## Risk Analysis" in md
    assert "Antitrust scrutiny in the App Store." in md

    # Assert Sources & Citations table
    assert "## Sources & Citations" in md
    assert "| # | Reference | Form | Section | Chunk ID | Score | Excerpt Preview |" in md
    assert "| 1 | [AAPL 10-K item_1 #0] | 10-K | item_1 | `chunk_aapl_1` | 0.9234 |" in md
    assert "| 2 | [AAPL 10-K item_1a #1] | 10-K | item_1a | `chunk_aapl_2` | 0.8911 |" in md


@pytest.mark.issue_15
def test_to_markdown_without_metrics_and_citations() -> None:
    generator = ReportGenerator()
    report = generator.build_report(
        ticker="MSFT",
        query="Quick overview",
        executive_summary="Brief overview without extra metrics.",
    )

    md = report.to_markdown()
    assert "# Financial Research Report: MSFT (MSFT)" in md
    assert "## Executive Summary" in md
    assert "## Key Market Metrics" not in md
    assert "## Sources & Citations" in md
    assert "*No external SEC filing citations recorded.*" in md


@pytest.mark.issue_15
def test_report_generator_validation_errors() -> None:
    generator = ReportGenerator()

    # Empty ticker
    with pytest.raises(ReportGeneratorError, match="Ticker cannot be empty"):
        generator.build_report(ticker="", query="q", executive_summary="Summary")

    # Empty summary
    with pytest.raises(ReportGeneratorError, match="Executive summary cannot be empty"):
        generator.build_report(ticker="AAPL", query="q", executive_summary="   ")

    # Empty run result
    empty_run = AgentRunResult(
        query="q",
        final_response="   ",
        steps=[],
        total_tokens=TokenUsage(),
        iterations=0,
        messages=[],
    )
    with pytest.raises(ReportGeneratorError, match="contains empty final response"):
        generator.generate_from_run(ticker="AAPL", run_result=empty_run)

"""Structured financial research report generator with verifiable source citations."""

import re
from datetime import UTC, datetime
from typing import Any

from financial_research_agent.agent.llm_client import BaseLLMClient
from financial_research_agent.agent.schemas import (
    AgentRunResult,
    Citation,
    FinancialResearchReport,
    ReportSection,
)
from financial_research_agent.transform.schemas import NormalizedMetrics


class ReportGeneratorError(Exception):
    """Base exception for report generator failures."""


class ReportGenerator:
    """Assembles structured, auditable financial research reports with citations."""

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    @staticmethod
    def deduplicate_citations(citations: list[Citation]) -> list[Citation]:
        """Deduplicate citations by chunk_id while preserving order of occurrence."""
        seen: set[str] = set()
        unique: list[Citation] = []
        for cit in citations:
            if cit.chunk_id not in seen:
                seen.add(cit.chunk_id)
                unique.append(cit)
        return unique

    @staticmethod
    def parse_markdown_sections(markdown_text: str) -> list[ReportSection]:
        """Parse markdown text containing '## ' headers into ReportSection instances."""
        if not markdown_text.strip():
            return []

        # Split by level-2 markdown headings
        pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        splits = pattern.split(markdown_text)

        sections: list[ReportSection] = []
        if len(splits) == 1:
            sections.append(
                ReportSection(
                    title="Analysis & Findings",
                    content=markdown_text.strip(),
                )
            )
            return sections

        # If there is preamble text before the first heading
        preamble = splits[0].strip()
        if preamble:
            sections.append(ReportSection(title="Overview", content=preamble))

        # Pairs of (heading, content)
        for i in range(1, len(splits), 2):
            title = splits[i].strip()
            content = splits[i + 1].strip() if i + 1 < len(splits) else ""
            if title and content:
                sections.append(ReportSection(title=title, content=content))

        return sections

    def build_report(
        self,
        ticker: str,
        query: str,
        executive_summary: str,
        sections: list[ReportSection] | None = None,
        key_metrics: NormalizedMetrics | None = None,
        citations: list[Citation] | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FinancialResearchReport:
        """Construct a FinancialResearchReport from explicitly structured components."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            raise ReportGeneratorError("Ticker cannot be empty.")

        clean_summary = executive_summary.strip()
        if not clean_summary:
            raise ReportGeneratorError("Executive summary cannot be empty.")

        report_title = title or f"Financial Research Report: {clean_ticker}"
        deduped_citations = self.deduplicate_citations(citations or [])

        return FinancialResearchReport(
            ticker=clean_ticker,
            title=report_title,
            generated_at=datetime.now(UTC),
            executive_summary=clean_summary,
            sections=sections or [],
            key_metrics=key_metrics,
            citations=deduped_citations,
            raw_query=query,
            metadata=metadata or {},
        )

    def generate_from_run(
        self,
        ticker: str,
        run_result: AgentRunResult,
        title: str | None = None,
        key_metrics: NormalizedMetrics | None = None,
        citations: list[Citation] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FinancialResearchReport:
        """Synthesize a publication-ready report from an executed AgentRunResult trajectory."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            raise ReportGeneratorError("Ticker cannot be empty.")

        raw_text = run_result.final_response.strip()
        if not raw_text:
            raise ReportGeneratorError("AgentRunResult contains empty final response.")

        parsed_sections = self.parse_markdown_sections(raw_text)

        # Extract executive summary from parsed sections or first paragraphs
        exec_summary = ""
        remaining_sections: list[ReportSection] = []
        for sec in parsed_sections:
            if not exec_summary and (
                "executive summary" in sec.title.lower() or "summary" in sec.title.lower()
            ):
                exec_summary = sec.content
                continue
            remaining_sections.append(sec)

        if not exec_summary:
            # Use the first section or first paragraph as summary
            if remaining_sections:
                exec_summary = remaining_sections[0].content
                remaining_sections = remaining_sections[1:]
            else:
                exec_summary = raw_text

        all_citations: list[Citation] = []
        if citations:
            all_citations.extend(citations)

        run_metadata = dict(metadata or {})
        run_metadata["total_tokens"] = run_result.total_tokens.total_tokens
        run_metadata["iterations"] = run_result.iterations

        return self.build_report(
            ticker=clean_ticker,
            query=run_result.query,
            executive_summary=exec_summary,
            sections=remaining_sections,
            key_metrics=key_metrics,
            citations=all_citations,
            title=title or f"Research Report: {clean_ticker}",
            metadata=run_metadata,
        )

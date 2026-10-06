"""Agent evaluation harness for benchmarking research performance and tool adherence."""

import re
import time
from typing import Any

from financial_research_agent.agent.loop import ResearchAgent
from financial_research_agent.agent.schemas import (
    EvaluationCase,
    EvaluationResult,
    EvaluationSummary,
)


class EvaluationError(Exception):
    """Base exception for evaluation harness errors."""


class AgentEvaluator:
    """Evaluates ResearchAgent performance across tool usage, keywords, and citations."""

    def __init__(self, agent: ResearchAgent) -> None:
        self.agent = agent

    @staticmethod
    def count_citations(run_result: Any) -> int:
        """Count citation occurrences in tool executions and final response."""
        total_citations = 0

        # Count citations in retrieve_filing_chunks tool outputs
        for step in run_result.steps:
            for execution in step.tool_executions:
                if execution.tool_call.function.name == "retrieve_filing_chunks":
                    # Count citation entries formatted like "[1] Source:" or chunk occurrences
                    matches = re.findall(r"\[\d+\]\s+Source:", execution.output)
                    total_citations += len(matches)

        # If none found from headers, inspect citation bracket references in final text
        if total_citations == 0:
            bracket_refs = re.findall(
                r"\[[A-Z]+\s+(?:10-K|10-Q)[^\]]*\]", run_result.final_response
            )
            total_citations = len(bracket_refs)

        return total_citations

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        """Run the agent on an EvaluationCase and score tool usage, keywords, and citations."""
        start_time = time.perf_counter()
        try:
            run_result = self.agent.run(case.query)
        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            return EvaluationResult(
                case_id=case.case_id,
                passed=False,
                tool_usage_score=0.0,
                keyword_coverage=0.0,
                citation_count=0,
                citation_score=0.0,
                iterations=0,
                tokens_used=0,
                error_message=f"Agent execution failed: {exc}",
                details={"exception": str(exc), "latency_seconds": round(elapsed, 4)},
            )

        elapsed = time.perf_counter() - start_time

        # 1. Tool usage score
        called_tools: set[str] = set()
        for step in run_result.steps:
            for rec in step.tool_executions:
                called_tools.add(rec.tool_call.function.name)

        if case.expected_tools:
            matched_tools = [t for t in case.expected_tools if t in called_tools]
            tool_score = len(matched_tools) / len(case.expected_tools)
        else:
            tool_score = 1.0

        # 2. Keyword coverage score
        response_lower = run_result.final_response.lower()
        if case.required_keywords:
            matched_kws = [kw for kw in case.required_keywords if kw.lower() in response_lower]
            keyword_score = len(matched_kws) / len(case.required_keywords)
        else:
            matched_kws = []
            keyword_score = 1.0

        # 3. Citation score
        citation_count = self.count_citations(run_result)
        if case.min_citations > 0:
            citation_score = min(1.0, citation_count / case.min_citations)
        else:
            citation_score = 1.0

        # Evaluation criteria passed check
        passed = bool(tool_score >= 1.0 and keyword_score >= 1.0 and citation_score >= 1.0)

        return EvaluationResult(
            case_id=case.case_id,
            passed=passed,
            tool_usage_score=round(tool_score, 4),
            keyword_coverage=round(keyword_score, 4),
            citation_count=citation_count,
            citation_score=round(citation_score, 4),
            iterations=run_result.iterations,
            tokens_used=run_result.total_tokens.total_tokens,
            details={
                "latency_seconds": round(elapsed, 4),
                "called_tools": list(called_tools),
                "matched_keywords": matched_kws,
                "missing_keywords": [kw for kw in case.required_keywords if kw not in matched_kws],
            },
        )

    def evaluate_suite(self, suite: list[EvaluationCase]) -> EvaluationSummary:
        """Run and summarize evaluation metrics across an entire test suite."""
        if not suite:
            raise EvaluationError("Evaluation suite cannot be empty.")

        results: list[EvaluationResult] = []
        for case in suite:
            results.append(self.evaluate_case(case))

        total_cases = len(results)
        passed_cases = sum(1 for r in results if r.passed)
        pass_rate = round(passed_cases / total_cases, 4)

        avg_tool = round(sum(r.tool_usage_score for r in results) / total_cases, 4)
        avg_kw = round(sum(r.keyword_coverage for r in results) / total_cases, 4)
        avg_cit = round(sum(r.citation_score for r in results) / total_cases, 4)

        return EvaluationSummary(
            total_cases=total_cases,
            passed_cases=passed_cases,
            pass_rate=pass_rate,
            average_tool_score=avg_tool,
            average_keyword_score=avg_kw,
            average_citation_score=avg_cit,
            results=results,
        )


def get_default_eval_suite() -> list[EvaluationCase]:
    """Return standard benchmark test cases across equity market and SEC retrieval domains."""
    return [
        EvaluationCase(
            case_id="eval_market_01",
            query="What is the current stock price and annualized volatility of AAPL?",
            ticker="AAPL",
            expected_tools=["get_market_data"],
            required_keywords=["price", "volatility"],
            description="Benchmark equity price and volatility retrieval tool usage.",
        ),
        EvaluationCase(
            case_id="eval_sec_01",
            query=(
                "What principal risk factors related to supply chains are "
                "disclosed in Apple's 10-K?"
            ),
            ticker="AAPL",
            expected_tools=["retrieve_filing_chunks"],
            required_keywords=["risk", "supply chain"],
            min_citations=1,
            description="Benchmark filing chunk retrieval and risk factor identification.",
        ),
        EvaluationCase(
            case_id="eval_multi_01",
            query="Analyze Apple's market performance metrics and business overview from filings.",
            ticker="AAPL",
            expected_tools=["get_market_data", "retrieve_filing_chunks"],
            required_keywords=["return", "apple"],
            min_citations=1,
            description="Benchmark multi-tool orchestration combining market data and filings.",
        ),
    ]

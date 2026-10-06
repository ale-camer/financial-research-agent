"""Unit tests for AgentEvaluator and evaluation schemas."""

import pytest
from pydantic import ValidationError

from financial_research_agent.agent import (
    AgentEvaluator,
    EvaluationCase,
    EvaluationError,
    EvaluationResult,
    EvaluationSummary,
    MockLLMClient,
    ResearchAgent,
    get_default_eval_suite,
)


class MockTool:
    """Mock tool providing tool_spec and execution for evaluation harness tests."""

    def __init__(self, name: str, output: str) -> None:
        self.name = name
        self.output = output

    @property
    def tool_spec(self) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": f"Mock {self.name}",
                "parameters": {"type": "object"},
            },
        }

    def run(self, **kwargs: object) -> str:
        return self.output


@pytest.mark.issue_16
def test_evaluation_schemas_immutability() -> None:
    case = EvaluationCase(
        case_id="case_1",
        query="What is AAPL's PE ratio?",
        ticker="AAPL",
        expected_tools=["get_market_data"],
        required_keywords=["ratio"],
    )
    with pytest.raises(ValidationError):
        case.ticker = "MSFT"  # type: ignore[misc]

    result = EvaluationResult(
        case_id="case_1",
        passed=True,
        tool_usage_score=1.0,
        keyword_coverage=1.0,
        citation_count=1,
        citation_score=1.0,
        iterations=1,
        tokens_used=50,
    )
    with pytest.raises(ValidationError):
        result.passed = False  # type: ignore[misc]

    summary = EvaluationSummary(
        total_cases=1,
        passed_cases=1,
        pass_rate=1.0,
        average_tool_score=1.0,
        average_keyword_score=1.0,
        average_citation_score=1.0,
        results=[result],
    )
    with pytest.raises(ValidationError):
        summary.pass_rate = 0.5  # type: ignore[misc]


@pytest.mark.issue_16
def test_get_default_eval_suite() -> None:
    suite = get_default_eval_suite()
    assert len(suite) == 3
    assert all(isinstance(case, EvaluationCase) for case in suite)
    assert suite[0].case_id == "eval_market_01"
    assert "get_market_data" in suite[0].expected_tools


@pytest.mark.issue_16
def test_evaluate_case_successful_run() -> None:
    client = MockLLMClient()
    client.add_tool_call_response(
        tool_name="get_market_data",
        arguments={"ticker": "AAPL"},
        call_id="call_mkt_1",
    )
    client.add_response("AAPL current price is $180 with low volatility.")

    market_tool = MockTool(name="get_market_data", output="Current Price: $180.00")
    agent = ResearchAgent(llm_client=client, tools=[market_tool])
    evaluator = AgentEvaluator(agent=agent)

    case = EvaluationCase(
        case_id="eval_01",
        query="What is AAPL's price and volatility?",
        ticker="AAPL",
        expected_tools=["get_market_data"],
        required_keywords=["price", "volatility"],
    )

    result = evaluator.evaluate_case(case)
    assert result.passed is True
    assert result.tool_usage_score == 1.0
    assert result.keyword_coverage == 1.0
    assert result.citation_score == 1.0
    assert result.iterations == 2
    assert result.error_message is None


@pytest.mark.issue_16
def test_evaluate_case_missing_expected_tools() -> None:
    client = MockLLMClient(
        responses=["Direct answer without invoking tools."],
    )
    agent = ResearchAgent(llm_client=client)
    evaluator = AgentEvaluator(agent=agent)

    case = EvaluationCase(
        case_id="eval_tool_miss",
        query="Query needing market tool",
        ticker="AAPL",
        expected_tools=["get_market_data"],
        required_keywords=["direct"],
    )

    result = evaluator.evaluate_case(case)
    assert result.passed is False
    assert result.tool_usage_score == 0.0
    assert result.keyword_coverage == 1.0


@pytest.mark.issue_16
def test_evaluate_case_missing_required_keywords() -> None:
    client = MockLLMClient()
    client.add_tool_call_response(
        tool_name="get_market_data",
        arguments={"ticker": "AAPL"},
    )
    client.add_response("Analysis completed with numbers.")

    tool = MockTool(name="get_market_data", output="Data")
    agent = ResearchAgent(llm_client=client, tools=[tool])
    evaluator = AgentEvaluator(agent=agent)

    case = EvaluationCase(
        case_id="eval_kw_miss",
        query="Financial query",
        ticker="AAPL",
        expected_tools=["get_market_data"],
        required_keywords=["volatility", "drawdown"],
    )

    result = evaluator.evaluate_case(case)
    assert result.passed is False
    assert result.tool_usage_score == 1.0
    assert result.keyword_coverage == 0.0
    assert "volatility" in result.details["missing_keywords"]


@pytest.mark.issue_16
def test_evaluate_case_citations_scoring() -> None:
    client = MockLLMClient()
    # Tool output contains 2 citations formatted with "[1] Source:" and "[2] Source:"
    tool_output = (
        "[1] Source: AAPL 10-K (Chunk ID: chunk_1)\nRisk info.\n\n"
        "[2] Source: AAPL 10-K (Chunk ID: chunk_2)\nSupply chain."
    )
    client.add_tool_call_response(
        tool_name="retrieve_filing_chunks",
        arguments={"query": "supply chain"},
    )
    client.add_response("Risks include supply chain disruptions.")

    retrieval_tool = MockTool(name="retrieve_filing_chunks", output=tool_output)
    agent = ResearchAgent(llm_client=client, tools=[retrieval_tool])
    evaluator = AgentEvaluator(agent=agent)

    case = EvaluationCase(
        case_id="eval_cit_pass",
        query="Supply chain risks",
        ticker="AAPL",
        expected_tools=["retrieve_filing_chunks"],
        required_keywords=["supply chain"],
        min_citations=2,
    )

    result = evaluator.evaluate_case(case)
    assert result.passed is True
    assert result.citation_count == 2
    assert result.citation_score == 1.0

    # If min_citations was 4, citation_score should be 2/4 = 0.5
    case_strict = EvaluationCase(
        case_id="eval_cit_fail",
        query="Supply chain risks",
        ticker="AAPL",
        expected_tools=["retrieve_filing_chunks"],
        required_keywords=["supply chain"],
        min_citations=4,
    )
    # Reset mock responses
    client.add_tool_call_response(
        tool_name="retrieve_filing_chunks",
        arguments={"query": "supply chain"},
    )
    client.add_response("Risks include supply chain disruptions.")
    result_strict = evaluator.evaluate_case(case_strict)
    assert result_strict.passed is False
    assert result_strict.citation_score == 0.5


@pytest.mark.issue_16
def test_evaluate_case_agent_failure_handled() -> None:
    client = MockLLMClient()
    agent = ResearchAgent(llm_client=client)
    evaluator = AgentEvaluator(agent=agent)

    # Empty query causes AgentError
    case = EvaluationCase(
        case_id="eval_err",
        query="   ",
        ticker="AAPL",
    )

    result = evaluator.evaluate_case(case)
    assert result.passed is False
    assert result.error_message is not None
    assert "Agent query cannot be empty" in result.error_message


@pytest.mark.issue_16
def test_evaluate_suite_aggregation() -> None:
    client = MockLLMClient()
    # Case 1: passes
    client.add_response("Direct answer with keyword pass.")
    # Case 2: fails keywords
    client.add_response("Unrelated answer.")

    agent = ResearchAgent(llm_client=client)
    evaluator = AgentEvaluator(agent=agent)

    suite = [
        EvaluationCase(
            case_id="case_pass",
            query="Query 1",
            ticker="AAPL",
            required_keywords=["pass"],
        ),
        EvaluationCase(
            case_id="case_fail",
            query="Query 2",
            ticker="AAPL",
            required_keywords=["must_have_term"],
        ),
    ]

    summary = evaluator.evaluate_suite(suite)
    assert summary.total_cases == 2
    assert summary.passed_cases == 1
    assert summary.pass_rate == 0.5
    assert summary.average_keyword_score == 0.5
    assert len(summary.results) == 2


@pytest.mark.issue_16
def test_evaluate_suite_empty_raises_error() -> None:
    client = MockLLMClient()
    agent = ResearchAgent(llm_client=client)
    evaluator = AgentEvaluator(agent=agent)

    with pytest.raises(EvaluationError, match="Evaluation suite cannot be empty"):
        evaluator.evaluate_suite([])

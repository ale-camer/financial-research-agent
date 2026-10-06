"""Unit tests for ResearchAgent loop and tool execution orchestration."""

from unittest.mock import MagicMock

import pytest

from financial_research_agent.agent import (
    AgentError,
    AgentMaxIterationsError,
    AgentRunResult,
    AgentStep,
    MockLLMClient,
    ResearchAgent,
    ToolCall,
    ToolExecutionError,
)


class DummyTool:
    """Mock tool providing tool_spec and run method."""

    def __init__(self, name: str = "dummy_tool", output: str = "dummy result") -> None:
        self.name = name
        self.output = output
        self.call_count = 0
        self.last_kwargs: dict[str, str] = {}

    @property
    def tool_spec(self) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Dummy tool for testing",
                "parameters": {"type": "object"},
            },
        }

    def run(self, **kwargs: str) -> str:
        self.call_count += 1
        self.last_kwargs = kwargs
        return self.output


@pytest.mark.issue_14
def test_agent_initialization_validation() -> None:
    client = MockLLMClient()
    with pytest.raises(AgentError, match="max_iterations must be positive"):
        ResearchAgent(llm_client=client, max_iterations=0)

    # Registering an object without name or tool_spec
    with pytest.raises(AgentError, match="does not expose tool_spec or name attribute"):
        ResearchAgent(llm_client=client, tools=[object()])


@pytest.mark.issue_14
def test_agent_empty_query_validation() -> None:
    client = MockLLMClient()
    agent = ResearchAgent(llm_client=client)
    with pytest.raises(AgentError, match="Agent query cannot be empty"):
        agent.run("")

    with pytest.raises(AgentError, match="Agent query cannot be empty"):
        agent.run("   \n\t  ")


@pytest.mark.issue_14
def test_agent_run_direct_answer_no_tools() -> None:
    client = MockLLMClient(
        responses=["Direct synthesized answer."],
    )
    agent = ResearchAgent(llm_client=client)

    result = agent.run("What is a 10-K filing?")

    assert isinstance(result, AgentRunResult)
    assert result.query == "What is a 10-K filing?"
    assert result.final_response == "Direct synthesized answer."
    assert result.iterations == 1
    assert len(result.steps) == 1

    step1: AgentStep = result.steps[0]
    assert step1.step_number == 1
    assert step1.assistant_message.content == "Direct synthesized answer."
    assert step1.tool_executions == []

    # Messages history: system + user + assistant
    assert len(result.messages) == 3
    assert result.messages[0].role == "system"
    assert result.messages[1].role == "user"
    assert result.messages[2].role == "assistant"
    assert result.total_tokens.total_tokens > 0


@pytest.mark.issue_14
def test_agent_run_single_tool_call() -> None:
    client = MockLLMClient()
    tool = DummyTool(name="get_stock_price", output="Price is $180.00")

    # Step 1: LLM calls tool
    client.add_tool_call_response(
        tool_name="get_stock_price",
        arguments={"ticker": "AAPL"},
        call_id="call_001",
    )
    # Step 2: LLM generates final answer
    client.add_response("AAPL is trading at $180.00 according to latest data.")

    agent = ResearchAgent(llm_client=client, tools=[tool])
    result = agent.run("What is AAPL trading at?")

    assert result.iterations == 2
    assert len(result.steps) == 2
    assert result.final_response == "AAPL is trading at $180.00 according to latest data."

    # Verify tool execution
    assert tool.call_count == 1
    assert tool.last_kwargs == {"ticker": "AAPL"}

    # Verify step 1
    step1 = result.steps[0]
    assert len(step1.tool_executions) == 1
    exec_record = step1.tool_executions[0]
    assert exec_record.tool_call.id == "call_001"
    assert exec_record.output == "Price is $180.00"
    assert not exec_record.is_error

    # Verify messages: system, user, assistant (tool_calls), tool (response), assistant (final)
    assert len(result.messages) == 5
    assert result.messages[2].role == "assistant"
    assert len(result.messages[2].tool_calls) == 1
    assert result.messages[3].role == "tool"
    assert result.messages[3].content == "Price is $180.00"
    assert result.messages[4].role == "assistant"


@pytest.mark.issue_14
def test_agent_run_multi_tool_calls_same_turn() -> None:
    client = MockLLMClient()
    tool1 = DummyTool(name="tool_a", output="Data A")
    tool2 = DummyTool(name="tool_b", output="Data B")

    # Queue an assistant response with two tool calls in the same turn
    from financial_research_agent.agent import FunctionCall, LLMResponse

    tc1 = ToolCall(
        id="call_a",
        type="function",
        function=FunctionCall(name="tool_a", arguments='{"param": "val_a"}'),
    )
    tc2 = ToolCall(
        id="call_b",
        type="function",
        function=FunctionCall(name="tool_b", arguments='{"param": "val_b"}'),
    )
    client.add_response(
        LLMResponse(
            content=None,
            tool_calls=[tc1, tc2],
            finish_reason="tool_calls",
        )
    )
    client.add_response("Combined summary of Data A and Data B.")

    agent = ResearchAgent(llm_client=client, tools=[tool1, tool2])
    result = agent.run("Fetch A and B")

    assert result.iterations == 2
    assert tool1.call_count == 1
    assert tool2.call_count == 1
    assert len(result.steps[0].tool_executions) == 2
    assert result.final_response == "Combined summary of Data A and Data B."


@pytest.mark.issue_14
def test_agent_max_iterations_exceeded() -> None:
    client = MockLLMClient()
    tool = DummyTool(name="dummy_tool")

    # Repeatedly ask for tool calls
    for i in range(5):
        client.add_tool_call_response(
            tool_name="dummy_tool",
            arguments={"step": str(i)},
            call_id=f"call_{i}",
        )

    agent = ResearchAgent(llm_client=client, tools=[tool], max_iterations=3)

    with pytest.raises(AgentMaxIterationsError, match="maximum iterations \\(3\\)"):
        agent.run("Infinite loop query")


@pytest.mark.issue_14
def test_agent_tool_error_handling_graceful() -> None:
    client = MockLLMClient()
    failing_tool = MagicMock()
    failing_tool.name = "failing_tool"
    failing_tool.tool_spec = {
        "type": "function",
        "function": {"name": "failing_tool", "parameters": {}},
    }
    failing_tool.run.side_effect = ValueError("Service unavailable")

    client.add_tool_call_response(
        tool_name="failing_tool",
        arguments={},
        call_id="call_fail_1",
    )
    client.add_response("The tool failed, so I provide this fallback answer.")

    agent = ResearchAgent(
        llm_client=client,
        tools=[failing_tool],
        raise_on_tool_error=False,
    )
    result = agent.run("Try failing tool")

    assert result.iterations == 2
    assert result.steps[0].tool_executions[0].is_error
    assert "Error executing tool 'failing_tool'" in result.steps[0].tool_executions[0].output
    assert result.final_response == "The tool failed, so I provide this fallback answer."


@pytest.mark.issue_14
def test_agent_tool_error_handling_raise() -> None:
    client = MockLLMClient()
    failing_tool = MagicMock()
    failing_tool.name = "failing_tool"
    failing_tool.tool_spec = {
        "type": "function",
        "function": {"name": "failing_tool", "parameters": {}},
    }
    failing_tool.run.side_effect = RuntimeError("Fatal crash")

    client.add_tool_call_response(
        tool_name="failing_tool",
        arguments={},
        call_id="call_fail_2",
    )

    agent = ResearchAgent(
        llm_client=client,
        tools=[failing_tool],
        raise_on_tool_error=True,
    )
    with pytest.raises(ToolExecutionError, match="Fatal crash"):
        agent.run("Trigger crash")


@pytest.mark.issue_14
def test_agent_unregistered_tool_call() -> None:
    client = MockLLMClient()
    client.add_tool_call_response(
        tool_name="unknown_tool",
        arguments={},
        call_id="call_unk",
    )
    client.add_response("Tool not found, continuing.")

    agent = ResearchAgent(llm_client=client, raise_on_tool_error=False)
    result = agent.run("Use missing tool")

    assert result.steps[0].tool_executions[0].is_error
    assert "Tool 'unknown_tool' is not registered" in result.steps[0].tool_executions[0].output

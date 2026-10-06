"""Unit tests for LLMClient abstractions, implementations, and message schemas."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from financial_research_agent.agent import (
    BaseLLMClient,
    ChatMessage,
    FunctionCall,
    LLMAPIError,
    LLMConfigError,
    LLMResponse,
    MessageRole,
    MockLLMClient,
    OpenAILLMClient,
    TokenUsage,
    ToolCall,
)


@pytest.mark.issue_13
def test_message_schemas_and_constructors() -> None:
    sys_msg = ChatMessage.system("You are a financial analyst.")
    assert sys_msg.role == MessageRole.SYSTEM
    assert sys_msg.content == "You are a financial analyst."
    assert sys_msg.to_openai_dict() == {
        "role": "system",
        "content": "You are a financial analyst.",
    }

    user_msg = ChatMessage.user("Analyze AAPL.")
    assert user_msg.role == MessageRole.USER
    assert user_msg.to_openai_dict() == {"role": "user", "content": "Analyze AAPL."}

    fn = FunctionCall(name="get_market_data", arguments='{"ticker": "AAPL"}')
    tc = ToolCall(id="call_123", type="function", function=fn)
    asst_msg = ChatMessage.assistant(content="Checking market data...", tool_calls=[tc])
    assert asst_msg.role == MessageRole.ASSISTANT
    assert len(asst_msg.tool_calls) == 1

    asst_dict = asst_msg.to_openai_dict()
    assert asst_dict["role"] == "assistant"
    assert asst_dict["content"] == "Checking market data..."
    assert len(asst_dict["tool_calls"]) == 1
    assert asst_dict["tool_calls"][0]["id"] == "call_123"
    assert asst_dict["tool_calls"][0]["function"]["name"] == "get_market_data"

    tool_msg = ChatMessage.tool_response(
        tool_call_id="call_123",
        content="Current price: $150",
        name="get_market_data",
    )
    assert tool_msg.role == MessageRole.TOOL
    assert tool_msg.tool_call_id == "call_123"
    assert tool_msg.to_openai_dict() == {
        "role": "tool",
        "content": "Current price: $150",
        "name": "get_market_data",
        "tool_call_id": "call_123",
    }


@pytest.mark.issue_13
def test_schemas_immutability() -> None:
    msg = ChatMessage.user("Hello")
    with pytest.raises(ValidationError):
        msg.content = "Changed"  # type: ignore[misc]

    usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    with pytest.raises(ValidationError):
        usage.total_tokens = 50  # type: ignore[misc]

    resp = LLMResponse(content="Done")
    with pytest.raises(ValidationError):
        resp.finish_reason = "length"  # type: ignore[misc]


@pytest.mark.issue_13
def test_mock_llm_client_basic_flow() -> None:
    client = MockLLMClient(
        responses=["First canned response", "Second canned response"],
        default_response="Default answer",
    )
    assert isinstance(client, BaseLLMClient)

    # First call
    resp1 = client.generate([ChatMessage.user("Question 1")])
    assert resp1.content == "First canned response"
    assert resp1.finish_reason == "stop"

    # Second call
    resp2 = client.generate([ChatMessage.user("Question 2")])
    assert resp2.content == "Second canned response"

    # Third call (queue empty, falls back to default)
    resp3 = client.generate([ChatMessage.user("Question 3")])
    assert resp3.content == "Default answer"

    # Check recorded calls
    assert len(client.calls) == 3
    assert client.calls[0]["messages"][0].content == "Question 1"


@pytest.mark.issue_13
def test_mock_llm_client_tool_call_queuing() -> None:
    client = MockLLMClient()
    client.add_tool_call_response(
        tool_name="retrieve_filing_chunks",
        arguments={"query": "risk factors", "ticker": "AAPL"},
        call_id="call_retrieval_01",
    )
    client.add_response("Final report generated.")

    resp1 = client.generate([ChatMessage.user("Find AAPL risks")])
    assert resp1.finish_reason == "tool_calls"
    assert len(resp1.tool_calls) == 1
    assert resp1.tool_calls[0].id == "call_retrieval_01"
    assert resp1.tool_calls[0].function.name == "retrieve_filing_chunks"
    assert "risk factors" in resp1.tool_calls[0].function.arguments

    resp2 = client.generate([ChatMessage.user("Continue")])
    assert resp2.finish_reason == "stop"
    assert resp2.content == "Final report generated."


@pytest.mark.issue_13
def test_mock_llm_client_empty_messages_validation() -> None:
    client = MockLLMClient()
    with pytest.raises(LLMConfigError, match="Messages list cannot be empty"):
        client.generate([])


@pytest.mark.issue_13
def test_openai_llm_client_validation() -> None:
    with pytest.raises(LLMConfigError, match="default_temperature cannot be negative"):
        OpenAILLMClient(default_temperature=-0.5)

    client = OpenAILLMClient()
    with pytest.raises(LLMConfigError, match="Messages list cannot be empty"):
        client.generate([])


@pytest.mark.issue_13
def test_openai_llm_client_generate_text() -> None:
    mock_choice = MagicMock()
    mock_choice.message.content = "Apple has strong gross margins."
    mock_choice.message.tool_calls = None
    mock_choice.finish_reason = "stop"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 25
    mock_usage.completion_tokens = 15
    mock_usage.total_tokens = 40

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = mock_usage
    mock_completion.model = "gpt-4o-mini-2024-07-18"

    mock_sdk_client = MagicMock()
    mock_sdk_client.chat.completions.create.return_value = mock_completion

    client = OpenAILLMClient(client=mock_sdk_client, model="gpt-4o-mini")
    response = client.generate(
        messages=[ChatMessage.user("Summarize margins")],
        temperature=0.2,
        max_tokens=100,
    )

    assert isinstance(response, LLMResponse)
    assert response.content == "Apple has strong gross margins."
    assert response.finish_reason == "stop"
    assert response.usage.prompt_tokens == 25
    assert response.usage.completion_tokens == 15
    assert response.usage.total_tokens == 40
    assert response.model == "gpt-4o-mini-2024-07-18"
    assert response.tool_calls == []

    mock_sdk_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Summarize margins"}],
        temperature=0.2,
        max_tokens=100,
    )


@pytest.mark.issue_13
def test_openai_llm_client_generate_tool_calls() -> None:
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_xyz987"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "get_market_data"
    mock_tool_call.function.arguments = '{"ticker": "MSFT", "period": "1mo"}'

    mock_choice = MagicMock()
    mock_choice.message.content = None
    mock_choice.message.tool_calls = [mock_tool_call]
    mock_choice.finish_reason = "tool_calls"

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = None
    mock_completion.model = "gpt-4o-mini"

    mock_sdk_client = MagicMock()
    mock_sdk_client.chat.completions.create.return_value = mock_completion

    client = OpenAILLMClient(client=mock_sdk_client)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_market_data",
                "parameters": {"type": "object"},
            },
        }
    ]
    response = client.generate(
        messages=[ChatMessage.user("What is Microsoft's price?")],
        tools=tools,
    )

    assert response.finish_reason == "tool_calls"
    assert len(response.tool_calls) == 1
    tc = response.tool_calls[0]
    assert tc.id == "call_xyz987"
    assert tc.function.name == "get_market_data"
    assert tc.function.arguments == '{"ticker": "MSFT", "period": "1mo"}'

    mock_sdk_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "What is Microsoft's price?"}],
        temperature=0.0,
        tools=tools,
        tool_choice="auto",
    )


@pytest.mark.issue_13
def test_openai_llm_client_api_error() -> None:
    mock_sdk_client = MagicMock()
    mock_sdk_client.chat.completions.create.side_effect = RuntimeError("Network timeout")

    client = OpenAILLMClient(client=mock_sdk_client)
    with pytest.raises(LLMAPIError, match="OpenAI chat completion failed: Network timeout"):
        client.generate(messages=[ChatMessage.user("Hello")])

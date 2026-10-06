"""LLM client abstraction and implementations for chat completions and tool calling."""

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from openai import OpenAI

from financial_research_agent.agent.schemas import (
    ChatMessage,
    FunctionCall,
    LLMResponse,
    TokenUsage,
    ToolCall,
)


class LLMError(Exception):
    """Base exception for LLM client failures."""


class LLMAPIError(LLMError):
    """Raised when an external LLM API request fails."""


class LLMConfigError(LLMError):
    """Raised when client configuration or parameters are invalid."""


class BaseLLMClient(ABC):
    """Abstract base class for Large Language Model clients."""

    @abstractmethod
    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a chat completion response from the language model."""


class OpenAILLMClient(BaseLLMClient):
    """OpenAI Chat Completions API client with support for tool calling."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        client: Any | None = None,
        default_temperature: float = 0.0,
    ) -> None:
        if default_temperature < 0.0:
            raise LLMConfigError("default_temperature cannot be negative.")

        self.model = model
        self.default_temperature = default_temperature

        if client is not None:
            self._client = client
        else:
            key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY", "mock-key")
            self._client = OpenAI(api_key=key, base_url=base_url)

    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute a chat completion request via OpenAI API."""
        if not messages:
            raise LLMConfigError("Messages list cannot be empty.")

        temp = self.default_temperature if temperature is None else temperature
        openai_messages = [msg.to_openai_dict() for msg in messages]

        params: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temp,
            **kwargs,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        try:
            completion = self._client.chat.completions.create(**params)
        except Exception as exc:
            raise LLMAPIError(f"OpenAI chat completion failed: {exc}") from exc

        choice = completion.choices[0]
        choice_msg = choice.message
        content: str | None = choice_msg.content

        tool_calls: list[ToolCall] = []
        if getattr(choice_msg, "tool_calls", None):
            for tc in choice_msg.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        type=tc.type,
                        function=FunctionCall(
                            name=tc.function.name,
                            arguments=tc.function.arguments,
                        ),
                    )
                )

        usage = TokenUsage()
        if getattr(completion, "usage", None):
            usage = TokenUsage(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                total_tokens=completion.usage.total_tokens,
            )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=getattr(choice, "finish_reason", "stop") or "stop",
            usage=usage,
            model=getattr(completion, "model", self.model) or self.model,
        )


class MockLLMClient(BaseLLMClient):
    """Deterministic mock client for unit testing and offline agent evaluation."""

    def __init__(
        self,
        responses: list[LLMResponse | str] | None = None,
        default_response: str = "Mock assistant response.",
        model: str = "mock-model",
    ) -> None:
        self.default_response = default_response
        self.model = model
        self._responses: list[LLMResponse] = []
        self.calls: list[dict[str, Any]] = []

        if responses:
            for resp in responses:
                self.add_response(resp)

    def add_response(self, response: LLMResponse | str) -> None:
        """Add a planned response to the mock queue."""
        if isinstance(response, str):
            self._responses.append(
                LLMResponse(
                    content=response,
                    finish_reason="stop",
                    model=self.model,
                    usage=TokenUsage(
                        prompt_tokens=10,
                        completion_tokens=len(response.split()),
                        total_tokens=10 + len(response.split()),
                    ),
                )
            )
        else:
            self._responses.append(response)

    def add_tool_call_response(
        self,
        tool_name: str,
        arguments: dict[str, Any] | str,
        call_id: str = "mock_call_1",
    ) -> None:
        """Helper to queue a tool calling response."""
        args_str = arguments if isinstance(arguments, str) else json.dumps(arguments)
        tool_call = ToolCall(
            id=call_id,
            type="function",
            function=FunctionCall(name=tool_name, arguments=args_str),
        )
        self._responses.append(
            LLMResponse(
                content=None,
                tool_calls=[tool_call],
                finish_reason="tool_calls",
                model=self.model,
                usage=TokenUsage(prompt_tokens=15, completion_tokens=15, total_tokens=30),
            )
        )

    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Record the call and return the next queued response or default response."""
        if not messages:
            raise LLMConfigError("Messages list cannot be empty.")

        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "kwargs": kwargs,
            }
        )

        if self._responses:
            return self._responses.pop(0)

        return LLMResponse(
            content=self.default_response,
            finish_reason="stop",
            model=self.model,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

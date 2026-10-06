"""Agent loop managing iterative reasoning, tool calling, and execution tracking."""

import json
from typing import Any

from financial_research_agent.agent.llm_client import BaseLLMClient
from financial_research_agent.agent.schemas import (
    AgentRunResult,
    AgentStep,
    ChatMessage,
    MarketDataResult,
    RetrievalResult,
    TokenUsage,
    ToolCall,
    ToolExecutionRecord,
)

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert financial research agent specializing in SEC filings and market data. "
    "Use the provided tools to retrieve factual filing excerpts and performance metrics. "
    "Always provide objective, data-backed insights with clear citations."
)


class AgentError(Exception):
    """Base exception for agent loop operations."""


class AgentMaxIterationsError(AgentError):
    """Raised when the agent exceeds maximum allowed iterations without finishing."""


class ToolExecutionError(AgentError):
    """Raised when a tool execution fails and errors are configured to raise."""


class ResearchAgent:
    """Multi-turn financial research agent coordinating LLM reasoning with tool execution."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: list[Any] | None = None,
        system_prompt: str | None = None,
        max_iterations: int = 10,
        raise_on_tool_error: bool = False,
    ) -> None:
        if max_iterations <= 0:
            raise AgentError(f"max_iterations must be positive, got {max_iterations}")

        self.llm_client = llm_client
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.max_iterations = max_iterations
        self.raise_on_tool_error = raise_on_tool_error

        self._tools: dict[str, Any] = {}
        self._tool_specs: list[dict[str, Any]] = []

        if tools:
            for tool in tools:
                self.register_tool(tool)

    def register_tool(self, tool: Any) -> None:
        """Register a tool instance for tool-calling dispatch."""
        if hasattr(tool, "tool_spec"):
            spec = tool.tool_spec
            name = spec.get("function", {}).get("name")
        elif hasattr(tool, "name"):
            name = tool.name
            spec = getattr(tool, "tool_spec", None)
        else:
            raise AgentError(f"Tool {tool!r} does not expose tool_spec or name attribute.")

        if not name:
            raise AgentError(f"Could not determine tool name from {tool!r}")

        self._tools[name] = tool
        if spec:
            self._tool_specs.append(spec)

    def execute_tool(self, tool_call: ToolCall) -> tuple[str, bool]:
        """Dispatch a single tool call to the corresponding registered tool."""
        func_name = tool_call.function.name
        tool = self._tools.get(func_name)

        if tool is None:
            err_msg = f"Tool '{func_name}' is not registered."
            if self.raise_on_tool_error:
                raise ToolExecutionError(err_msg)
            return err_msg, True

        try:
            raw_args = tool_call.function.arguments
            kwargs = json.loads(raw_args) if raw_args else {}
            if not isinstance(kwargs, dict):
                kwargs = {"query": str(kwargs)}
        except json.JSONDecodeError as exc:
            err_msg = f"Invalid JSON arguments for tool '{func_name}': {exc}"
            if self.raise_on_tool_error:
                raise ToolExecutionError(err_msg) from exc
            return err_msg, True

        try:
            if hasattr(tool, "run"):
                result = tool.run(**kwargs)
            elif callable(tool):
                result = tool(**kwargs)
            else:
                raise AgentError(f"Tool '{func_name}' is neither callable nor implements 'run'.")

            # Convert result into string representation for observation message
            if isinstance(result, RetrievalResult):
                output_str = result.formatted_context
            elif isinstance(result, MarketDataResult):
                output_str = result.formatted_summary
            elif isinstance(result, str):
                output_str = result
            elif hasattr(result, "model_dump_json"):
                output_str = str(result.model_dump_json())
            else:
                output_str = str(result)

            return output_str, False

        except Exception as exc:
            err_msg = f"Error executing tool '{func_name}': {exc}"
            if self.raise_on_tool_error:
                raise ToolExecutionError(err_msg) from exc
            return err_msg, True

    def run(
        self,
        query: str,
        system_prompt: str | None = None,
        max_iterations: int | None = None,
    ) -> AgentRunResult:
        """Run the agent loop until the LLM completes reasoning or iteration limit is reached."""
        clean_query = query.strip()
        if not clean_query:
            raise AgentError("Agent query cannot be empty.")

        limit = max_iterations if max_iterations is not None else self.max_iterations
        if limit <= 0:
            raise AgentError(f"max_iterations must be positive, got {limit}")

        sys_prompt = system_prompt or self.system_prompt
        messages: list[ChatMessage] = [
            ChatMessage.system(sys_prompt),
            ChatMessage.user(clean_query),
        ]

        steps: list[AgentStep] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for iteration in range(1, limit + 1):
            response = self.llm_client.generate(
                messages=messages,
                tools=self._tool_specs if self._tool_specs else None,
            )

            total_prompt_tokens += response.usage.prompt_tokens
            total_completion_tokens += response.usage.completion_tokens

            asst_msg = ChatMessage.assistant(
                content=response.content,
                tool_calls=response.tool_calls,
            )
            messages.append(asst_msg)

            # If no tool calls were initiated, this is the final answer
            if not response.tool_calls:
                step = AgentStep(
                    step_number=iteration,
                    assistant_message=asst_msg,
                    tool_executions=[],
                    tokens_used=response.usage,
                )
                steps.append(step)

                total_tokens = TokenUsage(
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                    total_tokens=total_prompt_tokens + total_completion_tokens,
                )
                return AgentRunResult(
                    query=clean_query,
                    final_response=response.content or "",
                    steps=steps,
                    total_tokens=total_tokens,
                    iterations=iteration,
                    messages=messages,
                )

            # Process requested tool calls
            tool_records: list[ToolExecutionRecord] = []
            for tc in response.tool_calls:
                output_str, is_error = self.execute_tool(tc)
                tool_records.append(
                    ToolExecutionRecord(tool_call=tc, output=output_str, is_error=is_error)
                )
                messages.append(
                    ChatMessage.tool_response(
                        tool_call_id=tc.id,
                        content=output_str,
                        name=tc.function.name,
                    )
                )

            step = AgentStep(
                step_number=iteration,
                assistant_message=asst_msg,
                tool_executions=tool_records,
                tokens_used=response.usage,
            )
            steps.append(step)

        raise AgentMaxIterationsError(
            f"Agent reached maximum iterations ({limit}) without synthesizing a final answer."
        )

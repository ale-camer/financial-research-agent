from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from financial_research_agent.transform.schemas import NormalizedMetrics


class RetrievalQuery(BaseModel):
    """Parameters for executing a semantic retrieval query against indexed chunks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(description="Natural language search query text")
    top_k: int = Field(default=5, ge=1, description="Maximum number of chunks to retrieve")
    ticker: str | None = Field(
        default=None,
        description="Optional equity ticker filter (e.g. AAPL)",
    )
    form_type: str | None = Field(
        default=None,
        description="Optional SEC filing form type filter (e.g. 10-K, 10-Q)",
    )
    section_id: str | None = Field(
        default=None,
        description="Optional filing section identifier filter (e.g. item_1, item_1a, item_7)",
    )
    min_score: float | None = Field(
        default=None,
        description="Optional minimum cosine similarity score threshold",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Validate query text is not empty or whitespace only."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Query string cannot be empty or whitespace only.")
        return cleaned


class Citation(BaseModel):
    """Structured attribution and text excerpt retrieved from a filing chunk."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(description="Unique identifier of the source chunk")
    document_id: str = Field(description="Parent document or filing accession identifier")
    ticker: str = Field(description="Company equity ticker symbol")
    form_type: str = Field(description="Filing form type (e.g. 10-K, 10-Q)")
    section_id: str | None = Field(
        default=None,
        description="Origin filing section ID if available",
    )
    chunk_index: int = Field(
        description="Zero-based index of the chunk in the parent document",
    )
    score: float = Field(description="Cosine similarity score for the retrieved chunk")
    content: str = Field(description="Text excerpt of the chunk")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Associated chunk metadata",
    )

    @property
    def reference(self) -> str:
        """Return a compact human-readable citation label."""
        section_part = f" {self.section_id}" if self.section_id else ""
        return f"[{self.ticker} {self.form_type}{section_part} #{self.chunk_index}]"


class RetrievalResult(BaseModel):
    """Output of retrieval operation including structured citations and prompt context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(description="Search query string that produced this result")
    citations: list[Citation] = Field(
        default_factory=list,
        description="Retrieved citations ranked by relevance score",
    )
    formatted_context: str = Field(
        description="Pre-formatted text representation of citations for LLM prompt context",
    )
    total_results: int = Field(description="Total number of citations retrieved")


class MarketDataQuery(BaseModel):
    """Parameters for querying equity market data and financial metrics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str = Field(description="Equity ticker symbol (e.g. AAPL)")
    period: str = Field(
        default="1y",
        description="Time period for historical price extraction (e.g. 1mo, 3mo, 6mo, 1y, 2y, 5y)",
    )
    interval: str = Field(
        default="1d",
        description="Data observation interval (e.g. 1d, 1wk)",
    )

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        """Validate and normalize equity ticker symbol."""
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Ticker symbol cannot be empty.")
        return cleaned


class MarketDataResult(BaseModel):
    """Normalized market data metrics and formatted summary for research agents."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str = Field(description="Equity ticker symbol")
    period: str = Field(description="Historical evaluation period requested")
    interval: str = Field(description="Data observation interval")
    metrics: NormalizedMetrics = Field(
        description="Normalized financial and statistical metrics",
    )
    formatted_summary: str = Field(
        description="Human and LLM-readable structured performance summary",
    )


class MessageRole(StrEnum):
    """Supported roles in a chat interaction turn."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FunctionCall(BaseModel):
    """Representation of a function call invocation requested by an LLM."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Name of the function to invoke")
    arguments: str = Field(description="JSON-formatted function argument string")


class ToolCall(BaseModel):
    """OpenAI-compatible tool call instance within an assistant response."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="Unique tool call identifier generated by the provider")
    type: str = Field(default="function", description="Tool call type (default: 'function')")
    function: FunctionCall = Field(description="The function call details")


class ChatMessage(BaseModel):
    """Normalized chat message exchange turn."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: MessageRole = Field(description="Message author role")
    content: str | None = Field(default=None, description="Text body of the message")
    name: str | None = Field(
        default=None,
        description="Optional participant or tool name for role attribution",
    )
    tool_call_id: str | None = Field(
        default=None,
        description="ID of the tool call this message is responding to (role='tool')",
    )
    tool_calls: list[ToolCall] = Field(
        default_factory=list,
        description="List of tool calls initiated by an assistant message",
    )

    def to_openai_dict(self) -> dict[str, Any]:
        """Convert to an OpenAI API chat message payload dictionary."""
        payload: dict[str, Any] = {"role": self.role.value}
        if self.content is not None:
            payload["content"] = self.content
        elif self.role == MessageRole.ASSISTANT and self.tool_calls:
            payload["content"] = None
        if self.name is not None:
            payload["name"] = self.name
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        return payload

    @classmethod
    def system(cls, content: str) -> "ChatMessage":
        """Create a system chat message."""
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        """Create a user chat message."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(
        cls,
        content: str | None = None,
        tool_calls: list[ToolCall] | None = None,
    ) -> "ChatMessage":
        """Create an assistant chat message."""
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls or [],
        )

    @classmethod
    def tool_response(
        cls,
        tool_call_id: str,
        content: str,
        name: str | None = None,
    ) -> "ChatMessage":
        """Create a tool execution result message."""
        return cls(
            role=MessageRole.TOOL,
            tool_call_id=tool_call_id,
            content=content,
            name=name,
        )


class TokenUsage(BaseModel):
    """Token consumption statistics for an LLM generation call."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt_tokens: int = Field(default=0, ge=0, description="Tokens consumed in prompt")
    completion_tokens: int = Field(default=0, ge=0, description="Tokens generated in completion")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")


class LLMResponse(BaseModel):
    """Standardized LLM generation output."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content: str | None = Field(default=None, description="Generated text message content")
    tool_calls: list[ToolCall] = Field(
        default_factory=list,
        description="List of tool calls requested by the model",
    )
    finish_reason: str = Field(
        default="stop",
        description="Reason for generation termination (e.g. 'stop', 'tool_calls')",
    )
    usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description="Token usage metrics for this completion",
    )
    model: str = Field(default="", description="Name or identifier of the responding model")

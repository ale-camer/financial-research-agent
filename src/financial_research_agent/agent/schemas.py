from datetime import datetime
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


class ToolExecutionRecord(BaseModel):
    """Execution output and telemetry for a single tool call."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_call: ToolCall = Field(description="The tool call requested by the model")
    output: str = Field(description="The string result produced by the tool")
    is_error: bool = Field(default=False, description="Whether the tool execution failed")


class AgentStep(BaseModel):
    """Record of a single reasoning and tool execution iteration within the agent loop."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_number: int = Field(description="1-based iteration step counter")
    assistant_message: ChatMessage = Field(
        description="The assistant response message generated in this step",
    )
    tool_executions: list[ToolExecutionRecord] = Field(
        default_factory=list,
        description="Tool executions triggered in this step",
    )
    tokens_used: TokenUsage = Field(
        default_factory=TokenUsage,
        description="Tokens consumed during this step",
    )


class AgentRunResult(BaseModel):
    """Complete trajectory and synthesized answer from an agent execution run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(description="Original user query input")
    final_response: str = Field(description="Final answer synthesized by the agent")
    steps: list[AgentStep] = Field(
        default_factory=list,
        description="Sequence of reasoning and tool execution steps",
    )
    total_tokens: TokenUsage = Field(
        default_factory=TokenUsage,
        description="Total tokens consumed across all steps",
    )
    iterations: int = Field(description="Number of loop iterations completed")
    messages: list[ChatMessage] = Field(
        default_factory=list,
        description="Complete message history",
    )


class ReportSection(BaseModel):
    """A distinct analytical section within a financial research report."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(description="Section heading title")
    content: str = Field(description="Body content in markdown format")
    citations: list[Citation] = Field(
        default_factory=list,
        description="Citations directly referenced in this section",
    )


class FinancialResearchReport(BaseModel):
    """Structured publication-ready equity research report with audit citations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str = Field(description="Company equity ticker symbol")
    title: str = Field(description="Title of the research report")
    generated_at: datetime = Field(
        description="UTC timestamp when the report was generated",
    )
    executive_summary: str = Field(
        description="Executive summary synthesizing principal findings",
    )
    sections: list[ReportSection] = Field(
        default_factory=list,
        description="Structured sections of the report",
    )
    key_metrics: NormalizedMetrics | None = Field(
        default=None,
        description="Quantitative equity performance metrics if available",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Deduplicated list of source filing citations referenced",
    )
    raw_query: str = Field(description="Original research question or prompt")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Associated execution and provenance metadata",
    )

    def to_markdown(self) -> str:
        """Render the complete research report into standard publication markdown."""
        date_str = self.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        blocks: list[str] = [
            f"# {self.title} ({self.ticker})",
            f"*Generated on: {date_str} | Query: {self.raw_query}*",
            f"## Executive Summary\n\n{self.executive_summary}",
        ]

        if self.key_metrics is not None:
            km = self.key_metrics
            sma_20_str = f"${km.sma_20:.2f}" if km.sma_20 is not None else "N/A"
            sma_50_str = f"${km.sma_50:.2f}" if km.sma_50 is not None else "N/A"
            max_dd = km.additional_metrics.get("max_drawdown")
            max_dd_str = f"{max_dd:.2%}" if max_dd is not None else "N/A"

            metrics_table = [
                "## Key Market Metrics",
                "| Metric | Value |",
                "|:---|:---|",
                f"| Current Price | ${km.current_price:.2f} |",
                f"| Total Return | {km.total_return:.2%} |",
                f"| Annualized Volatility | {km.annualized_volatility:.2%} |",
                f"| Period Range | ${km.low_period:.2f} - ${km.high_period:.2f} |",
                f"| Average Daily Volume | {km.average_volume:,.0f} |",
                f"| 20-Day SMA | {sma_20_str} |",
                f"| 50-Day SMA | {sma_50_str} |",
                f"| Max Drawdown | {max_dd_str} |",
            ]
            blocks.append("\n".join(metrics_table))

        for section in self.sections:
            blocks.append(f"## {section.title}\n\n{section.content}")

        blocks.append("## Sources & Citations")
        if self.citations:
            table_lines = [
                "| # | Reference | Form | Section | Chunk ID | Score | Excerpt Preview |",
                "|:---|:---|:---|:---|:---|:---|:---|",
            ]
            for idx, cit in enumerate(self.citations, start=1):
                clean_sec = cit.section_id or "N/A"
                snippet = cit.content.strip().replace("\n", " ")
                if len(snippet) > 80:
                    snippet = snippet[:77] + "..."
                snippet = snippet.replace("|", "\\|")
                table_lines.append(
                    f"| {idx} | {cit.reference} | {cit.form_type} | {clean_sec} | "
                    f"`{cit.chunk_id}` | {cit.score:.4f} | {snippet} |"
                )
            blocks.append("\n".join(table_lines))
        else:
            blocks.append("*No external SEC filing citations recorded.*")

        return "\n\n".join(blocks)

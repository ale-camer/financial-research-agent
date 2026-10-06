"""Market data tool connecting historical price extraction and metrics normalization."""

from typing import Any

from financial_research_agent.agent.schemas import (
    MarketDataQuery,
    MarketDataResult,
)
from financial_research_agent.extract.market_data import (
    MarketDataError,
    MarketDataExtractor,
)
from financial_research_agent.transform.normalizer import (
    MetricsNormalizer,
    NormalizerError,
)
from financial_research_agent.transform.schemas import NormalizedMetrics


class MarketDataToolError(Exception):
    """Base exception for market data tool failures."""


class MarketDataTool:
    """Agent tool fetching historical equity observations and returning normalized metrics."""

    def __init__(
        self,
        extractor: MarketDataExtractor | None = None,
        normalizer: MetricsNormalizer | None = None,
        name: str = "get_market_data",
        description: str | None = None,
    ) -> None:
        self.extractor = extractor or MarketDataExtractor()
        self.normalizer = normalizer or MetricsNormalizer()
        self.name = name
        self.description = description or (
            "Fetch historical market data and compute standardized financial performance "
            "metrics (current price, return, volatility, moving averages, drawdown)."
        )

    @property
    def tool_spec(self) -> dict[str, Any]:
        """Return an OpenAI-compatible function calling tool schema specification."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": (
                                "Equity ticker symbol to fetch market performance metrics "
                                "for (e.g. 'AAPL', 'MSFT', 'NVDA')."
                            ),
                        },
                        "period": {
                            "type": "string",
                            "description": (
                                "Historical time range for price evaluation "
                                "(e.g. '1mo', '3mo', '6mo', '1y', '2y', '5y'). Default: '1y'."
                            ),
                        },
                        "interval": {
                            "type": "string",
                            "description": (
                                "Observation frequency interval (e.g. '1d', '1wk'). Default: '1d'."
                            ),
                        },
                    },
                    "required": ["ticker"],
                },
            },
        }

    def format_summary(self, metrics: NormalizedMetrics, period: str, interval: str) -> str:
        """Format normalized financial metrics into a human and LLM-readable summary."""
        sma_20_str = f"${metrics.sma_20:.2f}" if metrics.sma_20 is not None else "N/A"
        sma_50_str = f"${metrics.sma_50:.2f}" if metrics.sma_50 is not None else "N/A"
        max_dd = metrics.additional_metrics.get("max_drawdown")
        max_dd_str = f"{max_dd:.2%}" if max_dd is not None else "N/A"

        lines = [
            f"Market Data Summary for {metrics.ticker} (Period: {period}, Interval: {interval}):",
            f"- Current Price: ${metrics.current_price:.2f}",
            f"- Total Return: {metrics.total_return:.2%}",
            f"- Annualized Volatility: {metrics.annualized_volatility:.2%}",
            f"- Period Range (Low - High): ${metrics.low_period:.2f} - ${metrics.high_period:.2f}",
            f"- Average Volume: {metrics.average_volume:,.0f}",
            f"- SMA (20-day): {sma_20_str}",
            f"- SMA (50-day): {sma_50_str}",
            f"- Max Drawdown: {max_dd_str}",
        ]
        return "\n".join(lines)

    def run(
        self,
        ticker: str | MarketDataQuery,
        period: str | None = None,
        interval: str | None = None,
    ) -> MarketDataResult:
        """Execute market data retrieval and compute standardized performance metrics."""
        if isinstance(ticker, str):
            try:
                query_obj = MarketDataQuery(
                    ticker=ticker,
                    period=period or "1y",
                    interval=interval or "1d",
                )
            except Exception as exc:
                raise MarketDataToolError(f"Invalid market data query parameters: {exc}") from exc
        elif isinstance(ticker, MarketDataQuery):
            query_obj = ticker
        else:
            raise MarketDataToolError(
                f"ticker must be str or MarketDataQuery, got {type(ticker).__name__}"
            )

        try:
            raw_data = self.extractor.extract_history(
                ticker=query_obj.ticker,
                period=query_obj.period,
                interval=query_obj.interval,
            )
        except MarketDataError as exc:
            raise MarketDataToolError(f"Failed to extract market data: {exc}") from exc
        except Exception as exc:
            raise MarketDataToolError(f"Unexpected error extracting market data: {exc}") from exc

        try:
            metrics = self.normalizer.compute_market_metrics(raw_data)
        except NormalizerError as exc:
            raise MarketDataToolError(f"Failed to normalize market metrics: {exc}") from exc
        except Exception as exc:
            raise MarketDataToolError(
                f"Unexpected error calculating market metrics: {exc}"
            ) from exc

        formatted_summary = self.format_summary(
            metrics=metrics,
            period=query_obj.period,
            interval=query_obj.interval,
        )

        return MarketDataResult(
            ticker=query_obj.ticker,
            period=query_obj.period,
            interval=query_obj.interval,
            metrics=metrics,
            formatted_summary=formatted_summary,
        )

    def __call__(
        self,
        ticker: str | MarketDataQuery,
        period: str | None = None,
        interval: str | None = None,
    ) -> MarketDataResult:
        """Allow calling the instance directly as a callable."""
        return self.run(ticker=ticker, period=period, interval=interval)

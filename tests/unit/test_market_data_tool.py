"""Unit tests for MarketDataTool and related schemas."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from financial_research_agent.agent import (
    MarketDataQuery,
    MarketDataResult,
    MarketDataTool,
    MarketDataToolError,
)
from financial_research_agent.extract.market_data import (
    EmptyMarketDataError,
    MarketDataExtractor,
)
from financial_research_agent.extract.schemas import (
    MarketDataPoint,
    RawDocumentMetadata,
    RawMarketData,
)
from financial_research_agent.transform.normalizer import (
    MetricsNormalizer,
    NormalizerError,
)


@pytest.fixture
def sample_raw_market_data() -> RawMarketData:
    """Fixture providing raw market data observations for AAPL."""
    meta = RawDocumentMetadata(
        source_uri="yfinance://AAPL?interval=1d",
        extracted_at=datetime(2023, 11, 3, 16, 0, 0, tzinfo=UTC),
        content_hash="mock_hash_market",
    )
    records = [
        MarketDataPoint(
            timestamp=datetime(2023, 11, 1, 16, 0, tzinfo=UTC),
            open=100.0,
            high=105.0,
            low=99.0,
            close=100.0,
            volume=1000,
        ),
        MarketDataPoint(
            timestamp=datetime(2023, 11, 2, 16, 0, tzinfo=UTC),
            open=101.0,
            high=108.0,
            low=100.0,
            close=105.0,
            volume=2000,
        ),
        MarketDataPoint(
            timestamp=datetime(2023, 11, 3, 16, 0, tzinfo=UTC),
            open=106.0,
            high=112.0,
            low=104.0,
            close=110.0,
            volume=3000,
        ),
    ]
    return RawMarketData(
        ticker="AAPL",
        interval="1d",
        start_date=records[0].timestamp,
        end_date=records[-1].timestamp,
        records=records,
        metadata=meta,
    )


@pytest.mark.issue_12
def test_market_data_query_validation() -> None:
    query = MarketDataQuery(ticker="aapl")
    assert query.ticker == "AAPL"
    assert query.period == "1y"
    assert query.interval == "1d"

    custom_query = MarketDataQuery(ticker="msft", period="6mo", interval="1wk")
    assert custom_query.ticker == "MSFT"
    assert custom_query.period == "6mo"
    assert custom_query.interval == "1wk"

    with pytest.raises(ValidationError):
        MarketDataQuery(ticker="")

    with pytest.raises(ValidationError):
        MarketDataQuery(ticker="   ")

    with pytest.raises(ValidationError):
        query.ticker = "GOOGL"  # type: ignore[misc]


@pytest.mark.issue_12
def test_market_data_result_immutability(
    sample_raw_market_data: RawMarketData,
) -> None:
    normalizer = MetricsNormalizer()
    metrics = normalizer.compute_market_metrics(sample_raw_market_data)

    result = MarketDataResult(
        ticker="AAPL",
        period="1mo",
        interval="1d",
        metrics=metrics,
        formatted_summary="Sample summary",
    )
    assert result.ticker == "AAPL"
    assert result.metrics.current_price == 110.0

    with pytest.raises(ValidationError):
        result.ticker = "MSFT"  # type: ignore[misc]


@pytest.mark.issue_12
def test_market_data_tool_initialization() -> None:
    tool = MarketDataTool()
    assert isinstance(tool.extractor, MarketDataExtractor)
    assert isinstance(tool.normalizer, MetricsNormalizer)
    assert tool.name == "get_market_data"
    assert "Fetch historical market data" in tool.description

    custom_extractor = MarketDataExtractor()
    custom_normalizer = MetricsNormalizer(trading_days_per_year=365)
    custom_tool = MarketDataTool(
        extractor=custom_extractor,
        normalizer=custom_normalizer,
        name="custom_tool",
        description="Custom description",
    )
    assert custom_tool.name == "custom_tool"
    assert custom_tool.description == "Custom description"
    assert custom_tool.normalizer.trading_days_per_year == 365


@pytest.mark.issue_12
def test_market_data_tool_spec() -> None:
    tool = MarketDataTool()
    spec = tool.tool_spec

    assert spec["type"] == "function"
    assert spec["function"]["name"] == "get_market_data"
    params = spec["function"]["parameters"]
    assert params["type"] == "object"
    assert "ticker" in params["required"]
    assert "ticker" in params["properties"]
    assert "period" in params["properties"]
    assert "interval" in params["properties"]


@pytest.mark.issue_12
def test_market_data_tool_run_success(
    sample_raw_market_data: RawMarketData,
) -> None:
    mock_extractor = MagicMock(spec=MarketDataExtractor)
    mock_extractor.extract_history.return_value = sample_raw_market_data

    tool = MarketDataTool(extractor=mock_extractor)
    result = tool.run(ticker="AAPL", period="1mo", interval="1d")

    assert isinstance(result, MarketDataResult)
    assert result.ticker == "AAPL"
    assert result.period == "1mo"
    assert result.interval == "1d"
    assert result.metrics.current_price == 110.0
    assert result.metrics.total_return == 0.10

    # Verify summary formatting
    assert "Market Data Summary for AAPL (Period: 1mo, Interval: 1d):" in result.formatted_summary
    assert "Current Price: $110.00" in result.formatted_summary
    assert "Total Return: 10.00%" in result.formatted_summary
    assert "Range (Low - High): $99.00 - $112.00" in result.formatted_summary

    mock_extractor.extract_history.assert_called_once_with(
        ticker="AAPL",
        period="1mo",
        interval="1d",
    )


@pytest.mark.issue_12
def test_market_data_tool_with_query_object_and_call(
    sample_raw_market_data: RawMarketData,
) -> None:
    mock_extractor = MagicMock(spec=MarketDataExtractor)
    mock_extractor.extract_history.return_value = sample_raw_market_data

    tool = MarketDataTool(extractor=mock_extractor)
    query = MarketDataQuery(ticker="aapl", period="3mo", interval="1d")

    # Test callable syntax __call__
    result = tool(ticker=query)

    assert result.ticker == "AAPL"
    assert result.period == "3mo"
    mock_extractor.extract_history.assert_called_once_with(
        ticker="AAPL",
        period="3mo",
        interval="1d",
    )


@pytest.mark.issue_12
def test_market_data_tool_invalid_argument() -> None:
    tool = MarketDataTool()
    with pytest.raises(MarketDataToolError, match="ticker must be str or MarketDataQuery"):
        tool.run(ticker=123)  # type: ignore[arg-type]


@pytest.mark.issue_12
def test_market_data_tool_extraction_failure() -> None:
    mock_extractor = MagicMock(spec=MarketDataExtractor)
    mock_extractor.extract_history.side_effect = EmptyMarketDataError("No price records")

    tool = MarketDataTool(extractor=mock_extractor)
    with pytest.raises(MarketDataToolError, match="Failed to extract market data"):
        tool.run(ticker="INVALID")


@pytest.mark.issue_12
def test_market_data_tool_normalizer_failure(
    sample_raw_market_data: RawMarketData,
) -> None:
    mock_extractor = MagicMock(spec=MarketDataExtractor)
    mock_extractor.extract_history.return_value = sample_raw_market_data

    mock_normalizer = MagicMock(spec=MetricsNormalizer)
    mock_normalizer.compute_market_metrics.side_effect = NormalizerError("Normalization failed")

    tool = MarketDataTool(extractor=mock_extractor, normalizer=mock_normalizer)
    with pytest.raises(MarketDataToolError, match="Failed to normalize market metrics"):
        tool.run(ticker="AAPL")

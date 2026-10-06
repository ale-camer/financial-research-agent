"""Unit tests for yfinance market data extractor."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from financial_research_agent.extract.market_data import (
    EmptyMarketDataError,
    MarketDataError,
    MarketDataExtractor,
)
from financial_research_agent.extract.schemas import RawMarketData


@pytest.fixture
def sample_ohlcv_dataframe() -> pd.DataFrame:
    timestamps = [
        pd.Timestamp("2023-11-01 09:30:00", tz="America/New_York"),
        pd.Timestamp("2023-11-02 09:30:00", tz="America/New_York"),
        pd.Timestamp("2023-11-03 09:30:00", tz="America/New_York"),
    ]
    data = {
        "Open": [170.0, 172.5, 174.0],
        "High": [173.0, 174.0, 176.5],
        "Low": [169.5, 171.8, 173.2],
        "Close": [172.0, 173.5, 175.8],
        "Volume": [45000000, 52000000, 61000000],
    }
    return pd.DataFrame(data, index=timestamps)


@pytest.mark.issue_3
def test_extract_history_success(sample_ohlcv_dataframe: pd.DataFrame) -> None:
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = sample_ohlcv_dataframe

    extractor = MarketDataExtractor(ticker_factory=lambda _: mock_ticker)
    result = extractor.extract_history(ticker="aapl", period="5d", interval="1d")

    assert isinstance(result, RawMarketData)
    assert result.ticker == "AAPL"
    assert result.interval == "1d"
    assert len(result.records) == 3
    assert result.records[0].open == 170.0
    assert result.records[-1].close == 175.8
    assert result.records[0].timestamp.tzinfo == UTC
    assert result.start_date == result.records[0].timestamp
    assert result.end_date == result.records[-1].timestamp
    assert result.metadata.source_uri == "yfinance://AAPL?interval=1d"
    assert result.metadata.content_hash is not None
    assert len(result.metadata.content_hash) == 64

    mock_ticker.history.assert_called_once_with(period="5d", interval="1d")


@pytest.mark.issue_3
def test_extract_history_with_date_range(sample_ohlcv_dataframe: pd.DataFrame) -> None:
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = sample_ohlcv_dataframe

    extractor = MarketDataExtractor(ticker_factory=lambda _: mock_ticker)
    start_dt = datetime(2023, 11, 1, tzinfo=UTC)
    end_dt = datetime(2023, 11, 4, tzinfo=UTC)
    extractor.extract_history(ticker="AAPL", interval="1d", start=start_dt, end=end_dt)

    mock_ticker.history.assert_called_once_with(interval="1d", start=start_dt, end=end_dt)


@pytest.mark.issue_3
def test_extract_history_empty_dataframe() -> None:
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    extractor = MarketDataExtractor(ticker_factory=lambda _: mock_ticker)
    with pytest.raises(EmptyMarketDataError, match="No market data returned for ticker 'NVDA'"):
        extractor.extract_history(ticker="NVDA")


@pytest.mark.issue_3
def test_extract_history_empty_ticker() -> None:
    extractor = MarketDataExtractor()
    with pytest.raises(MarketDataError, match="Ticker symbol cannot be empty"):
        extractor.extract_history(ticker="   ")


@pytest.mark.issue_3
def test_extract_history_missing_columns() -> None:
    incomplete_df = pd.DataFrame(
        {"Open": [100.0], "Close": [105.0]},
        index=[pd.Timestamp("2023-11-01", tz="UTC")],
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = incomplete_df

    extractor = MarketDataExtractor(ticker_factory=lambda _: mock_ticker)
    with pytest.raises(MarketDataError, match="missing required columns"):
        extractor.extract_history(ticker="AAPL")


@pytest.mark.issue_3
def test_extract_history_tz_naive_index() -> None:
    naive_df = pd.DataFrame(
        {
            "Open": [10.0],
            "High": [12.0],
            "Low": [9.0],
            "Close": [11.0],
            "Volume": [1000],
        },
        index=[pd.Timestamp("2023-11-01 14:00:00")],  # naive timestamp
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = naive_df

    extractor = MarketDataExtractor(ticker_factory=lambda _: mock_ticker)
    result = extractor.extract_history(ticker="TEST")
    assert result.records[0].timestamp.tzinfo == UTC

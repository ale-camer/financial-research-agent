"""Unit tests for MetricsNormalizer."""

from datetime import UTC, datetime

import pytest

from financial_research_agent.extract.schemas import (
    MarketDataPoint,
    RawDocumentMetadata,
    RawMarketData,
)
from financial_research_agent.transform.normalizer import (
    MetricsNormalizer,
    NormalizerError,
)
from financial_research_agent.transform.schemas import NormalizedMetrics


@pytest.fixture
def normalizer() -> MetricsNormalizer:
    return MetricsNormalizer(trading_days_per_year=252)


@pytest.fixture
def sample_market_data() -> RawMarketData:
    meta = RawDocumentMetadata(
        source_uri="yfinance://AAPL?interval=1d",
        extracted_at=datetime(2023, 11, 3, 16, 0, 0, tzinfo=UTC),
        content_hash="mock_hash",
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


@pytest.mark.issue_10
def test_compute_market_metrics_success(
    normalizer: MetricsNormalizer, sample_market_data: RawMarketData
) -> None:
    metrics = normalizer.compute_market_metrics(sample_market_data)

    assert isinstance(metrics, NormalizedMetrics)
    assert metrics.ticker == "AAPL"
    assert metrics.observation_count == 3
    assert metrics.current_price == 110.0
    # From 100 to 110: 10% total return
    assert pytest.approx(metrics.total_return, 0.0001) == 0.10
    assert metrics.high_period == 112.0
    assert metrics.low_period == 99.0
    assert metrics.average_volume == 2000.0
    assert metrics.annualized_volatility > 0.0


@pytest.mark.issue_10
def test_compute_sma(normalizer: MetricsNormalizer) -> None:
    prices = [10.0, 20.0, 30.0, 40.0]
    assert normalizer.compute_sma(prices, 2) == 35.0  # (30 + 40) / 2
    assert normalizer.compute_sma(prices, 4) == 25.0
    assert normalizer.compute_sma(prices, 5) is None


@pytest.mark.issue_10
def test_compute_max_drawdown(normalizer: MetricsNormalizer) -> None:
    prices = [100.0, 120.0, 90.0, 110.0]
    # Peak is 120, trough is 90 -> drawdown = (120 - 90) / 120 = 25% (0.25)
    max_dd = normalizer.compute_max_drawdown(prices)
    assert pytest.approx(max_dd, 0.0001) == 0.25


@pytest.mark.issue_10
def test_compute_cagr(normalizer: MetricsNormalizer) -> None:
    # 100 grows to 144 in 2 years -> (144 / 100)^(0.5) - 1 = 1.2 - 1 = 0.20
    cagr = normalizer.compute_cagr(initial_value=100.0, final_value=144.0, years=2.0)
    assert pytest.approx(cagr, 0.0001) == 0.20

    with pytest.raises(NormalizerError, match="positive"):
        normalizer.compute_cagr(-10.0, 100.0, 1.0)


@pytest.mark.issue_10
def test_insufficient_records_raises_error(normalizer: MetricsNormalizer) -> None:
    meta = RawDocumentMetadata(
        source_uri="yfinance://TEST",
        extracted_at=datetime.now(UTC),
        content_hash="mock",
    )
    single_record = RawMarketData(
        ticker="TEST",
        interval="1d",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        records=[
            MarketDataPoint(
                timestamp=datetime.now(UTC),
                open=10.0,
                high=10.0,
                low=10.0,
                close=10.0,
                volume=10,
            )
        ],
        metadata=meta,
    )
    with pytest.raises(NormalizerError, match="At least 2 price observations"):
        normalizer.compute_market_metrics(single_record)

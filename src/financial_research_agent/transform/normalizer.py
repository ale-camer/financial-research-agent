"""Financial metrics normalizer for market data time series."""

import math
from datetime import UTC, datetime

from financial_research_agent.extract.schemas import RawMarketData
from financial_research_agent.transform.schemas import NormalizedMetrics


class NormalizerError(Exception):
    """Base exception for metrics normalization errors."""


class MetricsNormalizer:
    """Computes standardized statistical and financial metrics from raw market series."""

    def __init__(self, trading_days_per_year: int = 252) -> None:
        if trading_days_per_year <= 0:
            raise NormalizerError("trading_days_per_year must be positive.")
        self.trading_days_per_year = trading_days_per_year

    @staticmethod
    def compute_sma(prices: list[float], window: int) -> float | None:
        """Compute the Simple Moving Average over the trailing window."""
        if window <= 0 or len(prices) < window:
            return None
        return round(sum(prices[-window:]) / window, 4)

    @staticmethod
    def compute_max_drawdown(prices: list[float]) -> float:
        """Compute maximum peak-to-trough percentage drawdown."""
        if not prices:
            return 0.0

        peak = prices[0]
        max_dd = 0.0
        for price in prices:
            if price > peak:
                peak = price
            drawdown = (peak - price) / peak if peak > 0 else 0.0
            if drawdown > max_dd:
                max_dd = drawdown

        return round(max_dd, 6)

    @staticmethod
    def compute_cagr(initial_value: float, final_value: float, years: float) -> float:
        """Calculate the Compound Annual Growth Rate."""
        if initial_value <= 0 or final_value <= 0 or years <= 0:
            raise NormalizerError("Initial value, final value, and years must all be positive.")
        return float(round((final_value / initial_value) ** (1.0 / years) - 1.0, 6))

    def compute_market_metrics(self, market_data: RawMarketData) -> NormalizedMetrics:
        """Derive standard equity metrics from raw market time series observations."""
        records = market_data.records
        if len(records) < 2:
            raise NormalizerError(
                f"At least 2 price observations are required for ticker '{market_data.ticker}', "
                f"got {len(records)}."
            )

        sorted_records = sorted(records, key=lambda r: r.timestamp)
        closes = [r.close for r in sorted_records]
        initial_price = closes[0]
        current_price = closes[-1]

        if initial_price <= 0:
            raise NormalizerError("Initial close price must be strictly positive.")

        total_return = (current_price - initial_price) / initial_price

        daily_returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
        mean_return = sum(daily_returns) / len(daily_returns)

        if len(daily_returns) > 1:
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        else:
            variance = 0.0

        daily_std = math.sqrt(variance)
        annualized_volatility = daily_std * math.sqrt(self.trading_days_per_year)

        high_period = max(r.high for r in sorted_records)
        low_period = min(r.low for r in sorted_records)
        avg_volume = sum(r.volume for r in sorted_records) / len(sorted_records)

        sma_20 = self.compute_sma(closes, 20)
        sma_50 = self.compute_sma(closes, 50)
        max_drawdown = self.compute_max_drawdown(closes)

        return NormalizedMetrics(
            ticker=market_data.ticker,
            calculated_at=datetime.now(UTC),
            observation_count=len(sorted_records),
            current_price=round(current_price, 4),
            total_return=round(total_return, 6),
            annualized_volatility=round(annualized_volatility, 6),
            high_period=round(high_period, 4),
            low_period=round(low_period, 4),
            average_volume=round(avg_volume, 2),
            sma_20=sma_20,
            sma_50=sma_50,
            additional_metrics={"max_drawdown": max_drawdown},
            metadata={"interval": market_data.interval},
        )

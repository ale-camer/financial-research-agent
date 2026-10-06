"""Market data extractor leveraging yfinance for price histories."""

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

import pandas as pd
import yfinance as yf

from financial_research_agent.extract.schemas import (
    MarketDataPoint,
    RawDocumentMetadata,
    RawMarketData,
)


class MarketDataError(Exception):
    """Base exception for market data extraction errors."""


class EmptyMarketDataError(MarketDataError):
    """Raised when the requested ticker history returns no price records."""


class MarketDataExtractor:
    """Extracts historical asset price and volume series using yfinance."""

    def __init__(self, ticker_factory: Callable[[str], Any] | None = None) -> None:
        self._ticker_factory = ticker_factory or yf.Ticker

    @staticmethod
    def _normalize_timestamp(ts: Any) -> datetime:
        """Convert a pandas Timestamp or date to UTC-aware datetime."""
        if isinstance(ts, datetime):
            py_dt = ts
        elif hasattr(ts, "to_pydatetime"):
            py_dt = cast(datetime, ts.to_pydatetime())
        else:
            py_dt = cast(datetime, pd.to_datetime(ts).to_pydatetime())

        if py_dt.tzinfo is None:
            return py_dt.replace(tzinfo=UTC)
        return py_dt.astimezone(UTC)

    def extract_history(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
        start: str | datetime | None = None,
        end: str | datetime | None = None,
    ) -> RawMarketData:
        """Fetch historical OHLCV records for a ticker symbol."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            raise MarketDataError("Ticker symbol cannot be empty.")

        try:
            ticker_obj = self._ticker_factory(clean_ticker)
            kwargs: dict[str, Any] = {"interval": interval}
            if start is not None or end is not None:
                kwargs["start"] = start
                kwargs["end"] = end
            else:
                kwargs["period"] = period

            df: pd.DataFrame = ticker_obj.history(**kwargs)
        except Exception as exc:
            raise MarketDataError(
                f"Failed to fetch market data for ticker '{clean_ticker}': {exc}"
            ) from exc

        if df is None or df.empty:
            raise EmptyMarketDataError(
                f"No market data returned for ticker '{clean_ticker}' "
                f"(period={period}, interval={interval})"
            )

        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise MarketDataError(
                f"Market data DataFrame missing required columns: {sorted(missing_cols)}"
            )

        records: list[MarketDataPoint] = []
        for index_val, row in df.iterrows():
            ts = self._normalize_timestamp(index_val)
            records.append(
                MarketDataPoint(
                    timestamp=ts,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                )
            )

        records.sort(key=lambda p: p.timestamp)
        start_date = records[0].timestamp
        end_date = records[-1].timestamp

        records_payload = [
            {
                "timestamp": r.timestamp.isoformat(),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in records
        ]
        serialized_str = json.dumps(records_payload, sort_keys=True)
        content_hash = hashlib.sha256(serialized_str.encode("utf-8")).hexdigest()
        extracted_at = datetime.now(UTC)

        metadata = RawDocumentMetadata(
            source_uri=f"yfinance://{clean_ticker}?interval={interval}",
            extracted_at=extracted_at,
            content_hash=content_hash,
            extra_attributes={
                "record_count": len(records),
                "interval": interval,
            },
        )

        return RawMarketData(
            ticker=clean_ticker,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            records=records,
            metadata=metadata,
        )

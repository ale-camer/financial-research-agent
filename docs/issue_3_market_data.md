# Issue 3: Market Data Extractor (yfinance)

**Branch**: `feature/issue-3-market-data`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #3)
**Milestone**: M1 - Extraction

## Objective
Implement a market data extractor leveraging `yfinance` to fetch historical OHLCV price series and asset summaries for given tickers, returning validated `RawMarketData` models with timezone-aware timestamps and content hashing.

## Acceptance Criteria
- [x] `src/financial_research_agent/extract/market_data.py` exposes `MarketDataExtractor` and `MarketDataError`
- [x] `src/financial_research_agent/extract/__init__.py` exports `MarketDataExtractor` and `MarketDataError`
- [x] `tests/unit/test_market_data.py` covers historical OHLCV extraction, interval parsing, and empty series error handling using mocked ticker data (marked `@pytest.mark.issue_3`)
- [x] `pyproject.toml` registers the `issue_3` marker
- [x] `make check` and `make test-issue ID=3` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=3 NAME=market-data
```

### 2. Market data extractor implementation
- **File**: `src/financial_research_agent/extract/market_data.py`
- **Change**: Implement `MarketDataExtractor` and `MarketDataError` to query historical prices via `yfinance.Ticker`, convert DataFrame rows into `MarketDataPoint` objects, calculate SHA-256 digests, and return validated `RawMarketData` instances.

### 3. Package exports
- **File**: `src/financial_research_agent/extract/__init__.py`
- **Change**: Export `MarketDataExtractor` and `MarketDataError` in `__all__`.

### 4. Market data extractor unit tests
- **File**: `tests/unit/test_market_data.py`
- **Change**: Add unit tests with mocked `yfinance` historical DataFrames verifying data transformation, empty data validation, and metadata generation, marked with `@pytest.mark.issue_3`.

### 5. Verification & Quality Gates
```bash
make test-issue ID=3
make check
```

### 6. Git & Issue Finish
```bash
make finish-issue ID=3 MSG="feat(extract): implement market data extractor"
```

## Decisions
- `MarketDataExtractor` accepts an optional ticker factory or provider function to allow injecting mocked `Ticker` instances during unit tests without network access.
- Configured `mypy.overrides` for `pandas.*` and `yfinance.*` in `pyproject.toml` to ignore missing imports for these untyped external packages under strict type checking.

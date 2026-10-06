# Issue 10: Financial Metrics Normalizer

**Branch**: `feature/issue-10-metrics-normalizer`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #10)
**Milestone**: M2 - Transformation

## Objective
Implement a financial metrics normalizer to compute standardized price statistics, returns, annualized volatility, and moving averages from `RawMarketData` into structured `NormalizedMetrics` models, completing Milestone 2.

## Acceptance Criteria
- [x] `src/financial_research_agent/transform/schemas.py` defines `NormalizedMetrics`
- [x] `src/financial_research_agent/transform/normalizer.py` exposes `MetricsNormalizer` and `NormalizerError`
- [x] `src/financial_research_agent/transform/__init__.py` exports `NormalizedMetrics`, `MetricsNormalizer`, and `NormalizerError`
- [x] `tests/unit/test_metrics_normalizer.py` covers return calculations, annualized volatility, moving averages, and insufficient data validation (marked `@pytest.mark.issue_10`)
- [x] `pyproject.toml` registers the `issue_10` marker
- [x] `make check` and `make test-issue ID=10` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=10 NAME=metrics-normalizer
```

### 2. Normalized metrics schema definition
- **File**: `src/financial_research_agent/transform/schemas.py`
- **Change**: Define `NormalizedMetrics` Pydantic model with frozen configuration, storing current price, total return, annualized volatility, moving averages, and period price ranges.

### 3. Metrics normalizer implementation
- **File**: `src/financial_research_agent/transform/normalizer.py`
- **Change**: Implement `MetricsNormalizer` and `NormalizerError` computing returns, annualized volatility (252-day basis), simple moving averages, and CAGR from `RawMarketData` series.

### 4. Package exports
- **File**: `src/financial_research_agent/transform/__init__.py`
- **Change**: Export `NormalizedMetrics`, `MetricsNormalizer`, and `NormalizerError` in `__all__`.

### 5. Metrics normalizer unit tests
- **File**: `tests/unit/test_metrics_normalizer.py`
- **Change**: Add unit tests verifying numerical formulas, volatility scaling, SMA windowing, and minimum observation constraints, marked with `@pytest.mark.issue_10`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=10
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=10 MSG="feat(transform): implement financial metrics normalizer"
```

### 8. Milestone Finish
```bash
make finish-milestone MILESTONE=M2
```

## Decisions
- `MetricsNormalizer` calculates volatility using a standard 252 annual trading days multiplier (`math.sqrt(252)`) and uses sample variance (N-1 degrees of freedom) for unbiased volatility estimates.

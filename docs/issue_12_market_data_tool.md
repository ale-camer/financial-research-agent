# Issue 12: Market Data Tool

**Branch**: `feature/issue-12-market-data-tool`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #12)
**Milestone**: M3 - Research Agent

## Objective
Implement an agent market data tool connecting the market data extractor and metrics normalizer to fetch historical equity observations, calculate standardized financial metrics, generate formatted prompt summaries, and expose an OpenAI-compatible function calling tool schema.

## Acceptance Criteria
- [x] `src/financial_research_agent/agent/schemas.py` defines `MarketDataQuery` and `MarketDataResult`
- [x] `src/financial_research_agent/agent/market_data_tool.py` exposes `MarketDataTool` and `MarketDataToolError` with LLM tool specification
- [x] `src/financial_research_agent/agent/__init__.py` exports market data tool schemas and classes
- [x] `tests/unit/test_market_data_tool.py` covers market data extraction, metrics calculation, formatting, and error handling (marked `@pytest.mark.issue_12`)
- [x] `pyproject.toml` registers the `issue_12` marker
- [x] `make check` and `make test-issue ID=12` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=12 NAME=market-data-tool
```

### 2. Market data tool schema definition
- **File**: `src/financial_research_agent/agent/schemas.py`
- **Change**: Define `MarketDataQuery` and `MarketDataResult` Pydantic models with immutable configuration (`frozen=True, extra="forbid"`) to represent equity market queries and structured calculation outputs with prompt summaries.

### 3. Market data tool implementation
- **File**: `src/financial_research_agent/agent/market_data_tool.py`
- **Change**: Implement `MarketDataTool` and `MarketDataToolError` wrapping `MarketDataExtractor` and `MetricsNormalizer`, providing typed execution (`run`), human-readable formatted summary generation, and an OpenAI-compatible function calling tool schema (`tool_spec`).

### 4. Package exports
- **File**: `src/financial_research_agent/agent/__init__.py`
- **Change**: Export `MarketDataTool`, `MarketDataToolError`, `MarketDataQuery`, and `MarketDataResult` in `__all__`.

### 5. Market data tool unit tests
- **File**: `tests/unit/test_market_data_tool.py`
- **Change**: Add unit tests using mock market data extractors testing query parameter validation, metrics normalization, formatted prompt summary generation, and exception handling, marked with `@pytest.mark.issue_12`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=12
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=12 MSG="feat(agent): implement market data tool"
```

## Decisions
- `MarketDataTool` encapsulates both historical price extraction and metrics normalization, exposing typed execution (`run`) and an OpenAI function schema (`tool_spec`) to provide rich quantitative context directly to LLM research agents.

# Issue 2: SEC EDGAR Filings Extractor

**Branch**: `feature/issue-2-sec-extractor`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #2)
**Milestone**: M1 - Extraction

## Objective
Implement an SEC EDGAR client and extractor to retrieve company submissions, map tickers to CIKs, and fetch filing contents (e.g. 10-K, 10-Q, 8-K) producing validated `RawSECFiling` objects.

## Acceptance Criteria
- [x] `src/financial_research_agent/extract/sec_edgar.py` exposes `SECEdgarClient` with custom user-agent validation, CIK lookup, and filing extraction returning `RawSECFiling`
- [x] `src/financial_research_agent/extract/__init__.py` exports `SECEdgarClient` and custom exceptions
- [x] `tests/unit/test_sec_edgar.py` covers CIK resolution, filing extraction, error conditions, and user-agent checks with mocked HTTP requests (marked `@pytest.mark.issue_2`)
- [x] `pyproject.toml` registers the `issue_2` marker
- [x] `make check` and `make test-issue ID=2` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=2 NAME=sec-extractor
```

### 2. SEC EDGAR extractor implementation
- **File**: `src/financial_research_agent/extract/sec_edgar.py`
- **Change**: Implement `SECEdgarClient` and `SECEdgarError` using `httpx` to resolve ticker to CIK, query submissions JSON, fetch raw filing documents, and construct validated `RawSECFiling` models.

### 3. Package exports
- **File**: `src/financial_research_agent/extract/__init__.py`
- **Change**: Export `SECEdgarClient` and `SECEdgarError` in `__all__`.

### 4. SEC EDGAR extractor unit tests
- **File**: `tests/unit/test_sec_edgar.py`
- **Change**: Add unit tests with mocked `httpx` responses covering CIK resolution, filing fetching, missing filing errors, and user-agent validation, marked with `@pytest.mark.issue_2`.

### 5. Verification & Quality Gates
```bash
make test-issue ID=2
make check
```

### 6. Git & Issue Finish
```bash
make finish-issue ID=2 MSG="feat(extract): implement sec edgar filings extractor"
```

## Decisions
- `SECEdgarClient` accepts an optional `httpx.Client` parameter for dependency injection, allowing unit tests to run deterministically with mocked HTTP transports without external network calls.

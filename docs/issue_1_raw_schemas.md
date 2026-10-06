# Issue 1: Raw Document Pydantic Schemas

**Branch**: `feature/issue-1-raw-schemas`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #1)
**Milestone**: M1 - Extraction

## Objective
Define core Pydantic data models for raw financial documents (SEC filings, market data, news articles, and metadata envelopes) to establish a strict, validated data contract for all extractors and downstream storage.

## Acceptance Criteria
- [x] `src/financial_research_agent/extract/schemas.py` exposes `DocumentType`, `RawDocumentMetadata`, `RawSECFiling`, `RawMarketData`, `RawNewsArticle`, and `RawDocument`
- [x] `src/financial_research_agent/extract/__init__.py` exports all public schema symbols in `__all__`
- [x] `tests/unit/test_schemas.py` covers valid serialization, deserialization, and validation errors (marked `@pytest.mark.issue_1`)
- [x] `pyproject.toml` registers the `issue_1` marker
- [x] `make check` and `make test-issue ID=1` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=1 NAME=raw-schemas
```

### 2. Define extraction data models
- **File**: `src/financial_research_agent/extract/schemas.py`
- **Change**: Implement `DocumentType` enum and Pydantic models `RawDocumentMetadata`, `RawSECFiling`, `RawMarketData`, `RawNewsArticle`, and `RawDocument` with frozen configuration and strict validation.

### 3. Package exports
- **File**: `src/financial_research_agent/extract/__init__.py`
- **Change**: Export all public schema classes and enums in `__all__`, replacing the placeholder `.gitkeep` file.

### 4. Schema unit tests
- **File**: `tests/unit/test_schemas.py`
- **Change**: Add unit tests for successful instantiation, JSON serialization roundtrip, and validation errors on malformed payloads, marked with `@pytest.mark.issue_1`.

### 5. Verification & Quality Gates
```bash
make test-issue ID=1
make check
```

### 6. Git & Issue Finish
```bash
make finish-issue ID=1 MSG="feat(extract): add raw document pydantic schemas"
```

## Decisions
- Models use `ConfigDict(frozen=True, extra="forbid")` to ensure raw extracted payloads remain immutable and strictly conform to the expected schema without unexpected fields.

# Issue 6: Filing Parser and Text Cleaner

**Branch**: `feature/issue-6-filing-parser`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #6)
**Milestone**: M2 - Transformation

## Objective
Implement HTML parsing and text sanitization utilities using BeautifulSoup to strip boilerplate, scripts, and XBRL tags from raw SEC filings while extracting standard financial sections (e.g. Item 1, Item 1A, Item 7) into structured clean documents.

## Acceptance Criteria
- [x] `src/financial_research_agent/transform/schemas.py` defines `CleanDocument` and `FilingSection`
- [x] `src/financial_research_agent/transform/parser.py` exposes `FilingParser` and `ParserError` with HTML cleaning and section extraction
- [x] `src/financial_research_agent/transform/__init__.py` exports transform models and parser classes
- [x] `tests/unit/test_filing_parser.py` covers tag stripping, whitespace normalization, and section parsing (marked `@pytest.mark.issue_6`)
- [x] `pyproject.toml` registers the `issue_6` marker
- [x] `make check` and `make test-issue ID=6` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=6 NAME=filing-parser
```

### 2. Transformation models
- **File**: `src/financial_research_agent/transform/schemas.py`
- **Change**: Define `CleanDocument` and `FilingSection` Pydantic models with immutable configuration, holding cleaned body text, extracted sections, and source provenance metadata.

### 3. Filing parser and cleaner implementation
- **File**: `src/financial_research_agent/transform/parser.py`
- **Change**: Implement `FilingParser` and `ParserError` using BeautifulSoup to remove scripts/styles/XBRL tags, normalize whitespace, extract standard SEC Item sections (Item 1, Item 1A, Item 7), and construct `CleanDocument` instances.

### 4. Package exports
- **File**: `src/financial_research_agent/transform/__init__.py`
- **Change**: Export `CleanDocument`, `FilingSection`, `FilingParser`, and `ParserError` in `__all__`, replacing `.gitkeep`.

### 5. Filing parser unit tests
- **File**: `tests/unit/test_filing_parser.py`
- **Change**: Add unit tests using realistic SEC HTML filing snippets testing tag removal, section detection, text normalization, and empty content error handling, marked with `@pytest.mark.issue_6`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=6
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=6 MSG="feat(transform): implement filing parser and text cleaner"
```

## Decisions
- `FilingParser` attempts to parse HTML with `lxml` and falls back to Python's built-in `html.parser` if `lxml` is unavailable, ensuring maximum portability across environments.

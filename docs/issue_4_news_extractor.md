# Issue 4: News RSS Extractor

**Branch**: `feature/issue-4-news-extractor`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #4)
**Milestone**: M1 - Extraction

## Objective
Implement a financial news RSS/Atom feed extractor utilizing `feedparser` to parse syndicated headlines, normalize published timestamps to UTC, and return lists of validated `RawNewsArticle` instances with content hashing.

## Acceptance Criteria
- [x] `src/financial_research_agent/extract/news_rss.py` exposes `NewsRSSExtractor` and `NewsExtractionError`
- [x] `src/financial_research_agent/extract/__init__.py` exports `NewsRSSExtractor` and `NewsExtractionError`
- [x] `tests/unit/test_news_rss.py` covers RSS/Atom parsing, publication date normalization, and error handling for empty or malformed feeds (marked `@pytest.mark.issue_4`)
- [x] `pyproject.toml` registers the `issue_4` marker
- [x] `make check` and `make test-issue ID=4` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=4 NAME=news-extractor
```

### 2. News RSS extractor implementation
- **File**: `src/financial_research_agent/extract/news_rss.py`
- **Change**: Implement `NewsRSSExtractor` and `NewsExtractionError` using `feedparser` and `httpx` to retrieve and parse RSS/Atom feeds, map feed entries to `RawNewsArticle` objects, standardize dates into UTC `datetime`, and generate SHA-256 hashes.

### 3. Package exports
- **File**: `src/financial_research_agent/extract/__init__.py`
- **Change**: Export `NewsRSSExtractor` and `NewsExtractionError` in `__all__`.

### 4. News RSS extractor unit tests
- **File**: `tests/unit/test_news_rss.py`
- **Change**: Add unit tests with static sample RSS and Atom XML fixtures verifying entry mapping, timestamp parsing, missing field handling, and empty feed exceptions, marked with `@pytest.mark.issue_4`.

### 5. Verification & Quality Gates
```bash
make test-issue ID=4
make check
```

### 6. Git & Issue Finish
```bash
make finish-issue ID=4 MSG="feat(extract): implement news rss extractor"
```

## Decisions
- `NewsRSSExtractor` supports passing an optional `httpx.Client` or direct XML strings to `parse_feed_content` to enable deterministic offline unit testing.
- Added `feedparser.*` to `mypy.overrides` in `pyproject.toml` because `feedparser` does not bundle type stubs.

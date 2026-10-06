# Issue 5: Raw Storage Writer and Extractor Fixtures Tests

**Branch**: `feature/issue-5-storage-writer`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #5)
**Milestone**: M1 - Extraction

## Objective
Implement a raw document storage writer that persists typed `RawDocument` artifacts to disk partitioned by date and type with atomic writes, and add integration tests connecting extractors to storage before closing Milestone 1.

## Acceptance Criteria
- [x] `src/financial_research_agent/extract/storage.py` exposes `RawStorageWriter` and `StorageError` with partitioned directory writing
- [x] `src/financial_research_agent/extract/__init__.py` exports `RawStorageWriter` and `StorageError`
- [x] `tests/unit/test_storage.py` covers atomic file persistence, path partitioning, and retrieval (marked `@pytest.mark.issue_5`)
- [x] `tests/integration/test_extract_pipeline.py` covers end-to-end extractor to storage flow (marked `@pytest.mark.issue_5`)
- [x] `pyproject.toml` registers the `issue_5` marker
- [x] `make check` and `make test-issue ID=5` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=5 NAME=storage-writer
```

### 2. Raw storage writer implementation
- **File**: `src/financial_research_agent/extract/storage.py`
- **Change**: Implement `RawStorageWriter` and `StorageError` to serialize `RawDocument` models into partitioned directories (`<base_dir>/<doc_type>/<YYYY>/<MM>/<doc_id>.json`) with atomic file writes.

### 3. Package exports
- **File**: `src/financial_research_agent/extract/__init__.py`
- **Change**: Export `RawStorageWriter` and `StorageError` in `__all__`.

### 4. Storage writer unit tests
- **File**: `tests/unit/test_storage.py`
- **Change**: Add unit tests using temporary directories verifying partitioned file structure, atomic writing, content reading, and error conditions, marked with `@pytest.mark.issue_5`.

### 5. Extractor pipeline integration tests
- **File**: `tests/integration/test_extract_pipeline.py`
- **Change**: Add integration tests connecting SEC EDGAR, market data, and news extractors to `RawStorageWriter` using mock transports and verifying stored payloads, removing `tests/integration/.gitkeep`, marked with `@pytest.mark.issue_5`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=5
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=5 MSG="feat(extract): implement raw storage writer and integration tests"
```

### 8. Milestone Finish
```bash
make finish-milestone MILESTONE=M1
```

## Decisions
- `RawStorageWriter` writes to a temporary sibling file and performs an atomic rename (`os.replace`) to ensure no corrupt or partially written files exist if a process crashes mid-write.

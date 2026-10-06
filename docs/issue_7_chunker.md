# Issue 7: Document Chunker

**Branch**: `feature/issue-7-chunker`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #7)
**Milestone**: M2 - Transformation

## Objective
Implement a token-aware recursive text chunker utilizing `tiktoken` to split `CleanDocument` instances into overlapping chunks (`DocumentChunk`), preserving section context, token limits, and document provenance for vector retrieval.

## Acceptance Criteria
- [x] `src/financial_research_agent/transform/schemas.py` defines `DocumentChunk`
- [x] `src/financial_research_agent/transform/chunker.py` exposes `DocumentChunker` and `ChunkerError` with token-based recursive splitting and overlap
- [x] `src/financial_research_agent/transform/__init__.py` exports `DocumentChunk`, `DocumentChunker`, and `ChunkerError`
- [x] `tests/unit/test_chunker.py` covers token bounding, chunk overlap, section preservation, and metadata propagation (marked `@pytest.mark.issue_7`)
- [x] `pyproject.toml` registers the `issue_7` marker
- [x] `make check` and `make test-issue ID=7` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=7 NAME=chunker
```

### 2. Document chunk schema definition
- **File**: `src/financial_research_agent/transform/schemas.py`
- **Change**: Define `DocumentChunk` Pydantic model with frozen configuration, capturing chunk index, token count, parent document ID, section identifier, content, and metadata.

### 3. Document chunker implementation
- **File**: `src/financial_research_agent/transform/chunker.py`
- **Change**: Implement `DocumentChunker` and `ChunkerError` using `tiktoken` to recursively partition clean text into overlapping chunks respecting max token budgets and section boundaries.

### 4. Package exports
- **File**: `src/financial_research_agent/transform/__init__.py`
- **Change**: Export `DocumentChunk`, `DocumentChunker`, and `ChunkerError` in `__all__`.

### 5. Document chunker unit tests
- **File**: `tests/unit/test_chunker.py`
- **Change**: Add unit tests verifying token limits, sliding window overlaps, section-aware splitting, and empty document rejection, marked with `@pytest.mark.issue_7`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=7
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=7 MSG="feat(transform): implement document chunker"
```

## Decisions
- `DocumentChunker` splits section-by-section when sections exist so chunks do not blend disparate SEC items (e.g. Risk Factors and Financials), preserving retrieval precision.
- Built-in `create_offline_byte_encoder` automatically falls back to an offline byte-level `tiktoken.Encoding` when remote BPE downloads are unreachable, ensuring tests and pipelines remain resilient in sandboxed environments.

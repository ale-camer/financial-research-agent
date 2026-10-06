# Issue 8: Embedding Generator

**Branch**: `feature/issue-8-embedding-generator`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #8)
**Milestone**: M2 - Transformation

## Objective
Implement an embedding generation client supporting batching and vector dimension validation to convert `DocumentChunk` instances into `EmbeddedChunk` models containing dense vector representations for vector search.

## Acceptance Criteria
- [x] `src/financial_research_agent/transform/schemas.py` defines `EmbeddedChunk`
- [x] `src/financial_research_agent/transform/embeddings.py` exposes `EmbeddingGenerator` and `EmbeddingError` with batching and client injection
- [x] `src/financial_research_agent/transform/__init__.py` exports `EmbeddedChunk`, `EmbeddingGenerator`, and `EmbeddingError`
- [x] `tests/unit/test_embeddings.py` covers batch embedding, vector assignment, empty input handling, and dimension verification (marked `@pytest.mark.issue_8`)
- [x] `pyproject.toml` registers the `issue_8` marker
- [x] `make check` and `make test-issue ID=8` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=8 NAME=embedding-generator
```

### 2. Embedded chunk schema definition
- **File**: `src/financial_research_agent/transform/schemas.py`
- **Change**: Define `EmbeddedChunk` Pydantic model with frozen configuration, storing dense embedding float vectors, dimension metadata, and parent chunk identifiers.

### 3. Embedding generator implementation
- **File**: `src/financial_research_agent/transform/embeddings.py`
- **Change**: Implement `EmbeddingGenerator` and `EmbeddingError` supporting batched API requests, dimension checks, and dependency-injected clients for offline testing.

### 4. Package exports
- **File**: `src/financial_research_agent/transform/__init__.py`
- **Change**: Export `EmbeddedChunk`, `EmbeddingGenerator`, and `EmbeddingError` in `__all__`.

### 5. Embedding generator unit tests
- **File**: `tests/unit/test_embeddings.py`
- **Change**: Add unit tests using mock embedding clients verifying batch splitting, dimension conformity, and `EmbeddedChunk` generation, marked with `@pytest.mark.issue_8`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=8
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=8 MSG="feat(transform): implement embedding generator"
```

## Decisions
- `EmbeddingGenerator` accepts an optional embedding callable or client to allow running full unit tests deterministically offline without requiring network calls or paid API keys.

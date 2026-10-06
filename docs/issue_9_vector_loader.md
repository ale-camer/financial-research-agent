# Issue 9: Vector Store Loader

**Branch**: `feature/issue-9-vector-loader`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #9)
**Milestone**: M2 - Transformation

## Objective
Implement an in-memory and persistent vector index loader supporting upsert, cosine similarity search, metadata filtering, and file persistence for `EmbeddedChunk` collections to enable vector search for research agent tools.

## Acceptance Criteria
- [x] `src/financial_research_agent/transform/schemas.py` defines `SearchResult`
- [x] `src/financial_research_agent/transform/vector_store.py` exposes `VectorStore` and `VectorStoreError` with similarity search and persistence
- [x] `src/financial_research_agent/transform/__init__.py` exports `SearchResult`, `VectorStore`, and `VectorStoreError`
- [x] `tests/unit/test_vector_store.py` covers chunk insertion, similarity ranking, metadata filtering, and save/load roundtrips (marked `@pytest.mark.issue_9`)
- [x] `pyproject.toml` registers the `issue_9` marker
- [x] `make check` and `make test-issue ID=9` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=9 NAME=vector-loader
```

### 2. Search result schema definition
- **File**: `src/financial_research_agent/transform/schemas.py`
- **Change**: Define `SearchResult` Pydantic model with frozen configuration, coupling retrieved `EmbeddedChunk` instances with numeric similarity scores.

### 3. Vector store loader implementation
- **File**: `src/financial_research_agent/transform/vector_store.py`
- **Change**: Implement `VectorStore` and `VectorStoreError` providing in-memory vector storage, cosine similarity ranking, ticker/section filtering, and disk persistence.

### 4. Package exports
- **File**: `src/financial_research_agent/transform/__init__.py`
- **Change**: Export `SearchResult`, `VectorStore`, and `VectorStoreError` in `__all__`.

### 5. Vector store unit tests
- **File**: `tests/unit/test_vector_store.py`
- **Change**: Add unit tests verifying cosine distance calculations, top-k ranking, attribute filtering, and save/load serialization, marked with `@pytest.mark.issue_9`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=9
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=9 MSG="feat(transform): implement vector store loader"
```

## Decisions
- `VectorStore` uses self-contained vectorized cosine similarity and JSON persistence to allow full local execution and testing without external database dependencies or server processes.

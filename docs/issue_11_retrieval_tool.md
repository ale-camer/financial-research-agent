# Issue 11: Retrieval Tool

**Branch**: `feature/issue-11-retrieval-tool`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #11)
**Milestone**: M3 - Research Agent

## Objective
Implement a vector retrieval tool connecting the embedding generator and vector store to search indexed filing chunks, returning structured citations and formatted context snippets for the research agent.

## Acceptance Criteria
- [x] `src/financial_research_agent/agent/schemas.py` defines `RetrievalQuery`, `Citation`, and `RetrievalResult`
- [x] `src/financial_research_agent/agent/retrieval_tool.py` exposes `RetrievalTool` and `RetrievalError` with LLM tool specification
- [x] `src/financial_research_agent/agent/__init__.py` exports retrieval schemas and tool classes
- [x] `tests/unit/test_retrieval_tool.py` covers semantic query retrieval, citation generation, and filtering (marked `@pytest.mark.issue_11`)
- [x] `pyproject.toml` registers the `issue_11` marker
- [x] `make check` and `make test-issue ID=11` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=11 NAME=retrieval-tool
```

### 2. Retrieval tool schema definition
- **File**: `src/financial_research_agent/agent/schemas.py`
- **Change**: Define `RetrievalQuery`, `Citation`, and `RetrievalResult` Pydantic models with immutable configuration to represent query requests, source citations, and assembled prompt context.

### 3. Retrieval tool implementation
- **File**: `src/financial_research_agent/agent/retrieval_tool.py`
- **Change**: Implement `RetrievalTool` and `RetrievalError` to embed incoming queries via `EmbeddingGenerator`, query `VectorStore`, format citations with similarity scores, and provide an OpenAI-compatible function calling tool schema.

### 4. Package exports
- **File**: `src/financial_research_agent/agent/__init__.py`
- **Change**: Export `RetrievalTool`, `RetrievalError`, `RetrievalQuery`, `Citation`, and `RetrievalResult` in `__all__`, replacing `.gitkeep`.

### 5. Retrieval tool unit tests
- **File**: `tests/unit/test_retrieval_tool.py`
- **Change**: Add unit tests using in-memory VectorStore and mock EmbeddingGenerator testing query embedding, metadata filtering, citation generation, and empty search results, marked with `@pytest.mark.issue_11`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=11
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=11 MSG="feat(agent): implement vector retrieval tool"
```

## Decisions
- `RetrievalTool` exposes both a typed execution method (`run`) and an OpenAI-compatible JSON function definition (`tool_spec`) to allow seamless integration into automated tool-calling LLM loops.

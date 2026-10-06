# Issue 18: Transform and Indexing DAG

**Branch**: `feature/issue-18-transform-dag`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #18)
**Milestone**: M4 - Orchestration & Delivery

## Objective
Implement a transformation and indexing orchestrator pipeline and Airflow DAG coordinating document parsing of raw SEC filings, chunking and embedding text into vector storage, and normalizing historical market data series into quantitative metrics.

## Acceptance Criteria
- [x] `src/financial_research_agent/orchestration/schemas.py` defines `TransformConfig`, `TransformTaskSummary`, and `TransformResult`
- [x] `src/financial_research_agent/orchestration/transform.py` exposes `TransformPipeline` and `TransformError`
- [x] `dags/transform_dag.py` defines `financial_transform_dag` with tasks for parsing, indexing, and normalizing
- [x] `src/financial_research_agent/orchestration/__init__.py` exports transform pipeline classes and schemas
- [x] `tests/unit/test_transform_dag.py` covers transform task execution, vector indexing, metrics normalization, error handling, and DAG structure (marked `@pytest.mark.issue_18`)
- [x] `pyproject.toml` registers the `issue_18` marker
- [x] `make check` and `make test-issue ID=18` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=18 NAME=transform-dag
```

### 2. Transformation pipeline schema definition
- **File**: `src/financial_research_agent/orchestration/schemas.py`
- **Change**: Define `TransformConfig`, `TransformTaskSummary`, and `TransformResult` Pydantic models with immutable configuration (`frozen=True, extra="forbid"`) to configure storage directories, chunking limits, embedding models, vector store paths, and report execution telemetry.

### 3. Transformation pipeline orchestrator implementation
- **File**: `src/financial_research_agent/orchestration/transform.py`
- **Change**: Implement `TransformPipeline` and `TransformError` coordinating:
  - Reading raw SEC filings and parsing them into clean sectioned documents via `FilingParser`.
  - Chunking clean documents with `DocumentChunker`, embedding them with `EmbeddingGenerator`, and loading them into `VectorStore`.
  - Reading raw market data series and computing risk/return metrics via `MetricsNormalizer`.
  - Atomic persistence of processed outputs to partitioned storage paths.

### 4. Airflow DAG definition
- **File**: `dags/transform_dag.py`
- **Change**: Implement `financial_transform_dag` defining tasks:
  - `task_parse_filings`: parses raw SEC documents.
  - `task_chunk_and_index`: chunks and embeds parsed documents into the vector store (depends on `task_parse_filings`).
  - `task_normalize_metrics`: normalizes market data time series.
  - Graceful fallback stubs (`DummyDAG`, `DummyOperator`) when Apache Airflow is not installed in the Python runtime.

### 5. Package exports
- **File**: `src/financial_research_agent/orchestration/__init__.py`
- **Change**: Export `TransformPipeline`, `TransformError`, `TransformConfig`, `TransformTaskSummary`, and `TransformResult` in `__all__`.

### 6. Transform DAG unit tests
- **File**: `tests/unit/test_transform_dag.py`
- **Change**: Add comprehensive unit tests covering individual transform tasks, vector store persistence, metric calculation, pipeline error tolerance, and DAG operator dependencies (marked `@pytest.mark.issue_18`).

### 7. Verification & Quality Gates
```bash
make test-issue ID=18
make check
```

### 8. Git & Issue Finish
```bash
make finish-issue ID=18 MSG="feat(orchestration): implement transform and indexing DAG"
```

## Decisions
- `TransformPipeline` provides a standalone Python class capable of executing transformation workflows directly in CLI or script environments, while `dags/transform_dag.py` exposes standard Airflow operators for enterprise scheduled runs.
- Chunking and indexing explicitly depends on filing parsing completion, while market metrics normalization executes in parallel as an independent task.
- Processed artifacts are persisted partitioned under `data/processed/` and the vector index under `data/vector_store/index.json`.

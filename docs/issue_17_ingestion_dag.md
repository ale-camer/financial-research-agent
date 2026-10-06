# Issue 17: Ingestion DAG

**Branch**: `feature/issue-17-ingestion-dag`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #17)
**Milestone**: M4 - Orchestration & Delivery

## Objective
Implement an ingestion DAG and orchestrator pipeline that coordinates extraction of SEC filings, market data, and financial news RSS feeds, writing raw document artifacts partitioned by type and extraction date into storage.

## Acceptance Criteria
- [x] `src/financial_research_agent/orchestration/schemas.py` defines `IngestionConfig` and `IngestionResult`
- [x] `src/financial_research_agent/orchestration/ingestion.py` exposes `IngestionPipeline` and `IngestionError`
- [x] `dags/ingestion_dag.py` defines `financial_ingestion_dag` with distinct extraction tasks
- [x] `src/financial_research_agent/orchestration/__init__.py` exports ingestion pipeline classes and schemas
- [x] `tests/unit/test_ingestion_dag.py` covers ingestion task execution, storage writing, and DAG configuration (marked `@pytest.mark.issue_17`)
- [x] `pyproject.toml` registers the `issue_17` marker
- [x] `make check` and `make test-issue ID=17` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=17 NAME=ingestion-dag
```

### 2. Ingestion pipeline schema definition
- **File**: `src/financial_research_agent/orchestration/schemas.py`
- **Change**: Define `IngestionConfig` and `IngestionResult` Pydantic models with immutable configuration (`frozen=True, extra="forbid"`) to configure target tickers, form types, feed URLs, and report execution metrics.

### 3. Ingestion pipeline orchestrator implementation
- **File**: `src/financial_research_agent/orchestration/ingestion.py`
- **Change**: Implement `IngestionPipeline` and `IngestionError` to run discrete ingestion tasks (SEC filings, market series, news articles) and write raw documents via `RawStorageWriter`.

### 4. Airflow DAG definition
- **File**: `dags/ingestion_dag.py`
- **Change**: Implement `financial_ingestion_dag` defining tasks for SEC EDGAR, market data, and RSS news ingestion with graceful fallback when running in environments without Airflow installed.

### 5. Package exports
- **File**: `src/financial_research_agent/orchestration/__init__.py`
- **Change**: Export `IngestionPipeline`, `IngestionError`, `IngestionConfig`, and `IngestionResult` in `__all__`, removing `.gitkeep`.

### 6. Ingestion DAG unit tests
- **File**: `tests/unit/test_ingestion_dag.py`
- **Change**: Add unit tests verifying individual ingestion tasks, partitioned storage writing, pipeline coordination, and DAG structure (marked `@pytest.mark.issue_17`).

### 7. Verification & Quality Gates
```bash
make test-issue ID=17
make check
```

### 8. Git & Issue Finish
```bash
make finish-issue ID=17 MSG="feat(orchestration): implement raw data ingestion DAG"
```

## Decisions
- `IngestionPipeline` provides a standalone Python interface so ingestion tasks can execute without requiring Apache Airflow runtime dependencies (which are constrained on Python 3.14+), while `dags/ingestion_dag.py` exposes standard Airflow DAG operators when Airflow is available.

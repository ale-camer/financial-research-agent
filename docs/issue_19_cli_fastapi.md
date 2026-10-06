# Issue 19: CLI and FastAPI Endpoint

**Branch**: `feature/issue-19-cli-fastapi`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #19)
**Milestone**: M4 - Orchestration & Delivery

## Objective
Provide user-facing delivery interfaces for the financial research system via a command-line interface (CLI) and a FastAPI HTTP REST service, allowing users and external clients to trigger data ingestion, run document transformation/indexing, query the research agent for structured cited reports, and monitor service health.

## Acceptance Criteria
- [x] `src/financial_research_agent/cli.py` implements the CLI with subcommands `research`, `ingest`, and `transform` using standard library `argparse`
- [x] `src/financial_research_agent/api/schemas.py` defines API request and response models with strict Pydantic validation
- [x] `src/financial_research_agent/api/app.py` exposes REST endpoints (`GET /health`, `POST /research`, `POST /ingest`, `POST /transform`) with dependency injection and error handling
- [x] `src/financial_research_agent/api/__init__.py` exports the API application factory and schemas
- [x] `pyproject.toml` registers the console script `financial-research-agent = "financial_research_agent.cli:main"`
- [x] `tests/unit/test_cli.py` and `tests/unit/test_api.py` cover CLI command dispatch, parameter parsing, REST route responses, and error handling (marked `@pytest.mark.issue_19`)
- [x] `pyproject.toml` registers the `issue_19` marker
- [x] `make check` and `make test-issue ID=19` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=19 NAME=cli-fastapi
```

### 2. Command-line interface implementation
- **File**: `src/financial_research_agent/cli.py`
- **Change**: Implement a robust standard-library `argparse` CLI offering:
  - `research`: queries the agent with `--ticker`, `--query`, `--max-iterations`, and `--format` (markdown or json) and outputs cited research reports.
  - `ingest`: triggers `IngestionPipeline` with `--tickers` and `--raw-dir`.
  - `transform`: triggers `TransformPipeline` with `--raw-dir`, `--processed-dir`, and `--index-path`.
  - Provide `main(argv: list[str] | None = None) -> int` returning exit codes 0 on success, non-zero on failure.

### 3. API request and response schemas definition
- **File**: `src/financial_research_agent/api/schemas.py`
- **Change**: Define Pydantic models with immutable configuration (`frozen=True, extra="forbid"`):
  - `HealthResponse`: service status, version, and timestamp.
  - `ResearchRequest` and `ResearchResponse`: ticker, research question, max iterations, report content, citations, and summary metrics.
  - `IngestRequest` and `TransformRequest`: configuration parameters for triggering orchestration runs.

### 4. FastAPI REST service implementation
- **File**: `src/financial_research_agent/api/app.py`
- **Change**: Implement `create_app()` returning a FastAPI application exposing:
  - `GET /health`: liveness probe.
  - `POST /research`: runs the agent loop and returns a generated report.
  - `POST /ingest`: triggers raw document ingestion and returns `IngestionResult`.
  - `POST /transform`: triggers transformation and indexing and returns `TransformResult`.
  - Graceful fallback structure for testability and portability in environments without FastAPI installed.

### 5. Package exports and console script registration
- **File**: `src/financial_research_agent/api/__init__.py`, `pyproject.toml`
- **Change**: Export API application factory and schemas from `api` subpackage. Add `[project.scripts]` in `pyproject.toml` for `financial-research-agent = "financial_research_agent.cli:main"`.

### 6. Delivery layer unit tests
- **File**: `tests/unit/test_cli.py`, `tests/unit/test_api.py`
- **Change**: Add unit tests verifying CLI arguments parsing, command execution, error propagation, REST endpoint routes, validation errors, and health endpoint status (marked `@pytest.mark.issue_19`).

### 7. Verification & Quality Gates
```bash
make test-issue ID=19
make check
```

### 8. Git & Issue Finish
```bash
make finish-issue ID=19 MSG="feat(delivery): implement CLI and FastAPI endpoints"
```

## Decisions
- Standard library `argparse` is chosen for the CLI to guarantee zero external dependency overhead and instant startup times across all environments.
- API endpoints delegate domain logic directly to `FinancialResearchAgent`, `IngestionPipeline`, and `TransformPipeline` without duplicate business rules.
- Fallback stubbing in `api/app.py` enables unit testing and standalone execution even if optional web framework dependencies are not yet installed in the active environment.

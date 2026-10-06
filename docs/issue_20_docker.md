# Issue 20: Dockerfile and docker-compose

**Branch**: `feature/issue-20-docker`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #20)
**Milestone**: M4 - Orchestration & Delivery

## Objective
Package the financial research agent system for containerized execution by providing a production-grade, secure, multi-stage or slim `Dockerfile`, build context filtering via `.dockerignore`, and a `docker-compose.yml` configuration orchestrating the FastAPI HTTP API service and interactive CLI execution with volume persistence and health monitoring.

## Acceptance Criteria
- [x] `.dockerignore` excludes unnecessary files (caches, virtualenvs, secrets, data, build artifacts) from the Docker build context
- [x] `Dockerfile` packages the application with Python 3.11+, runs as a non-root user, exposes port 8000, defines a healthcheck on `/health`, and defaults to serving the FastAPI application via uvicorn
- [x] `docker-compose.yml` configures the `api` service (port 8000, volume mount for `./data`, environment variables, healthcheck) and a `cli` service for ad-hoc agent/pipeline runs
- [x] `tests/unit/test_docker.py` verifies the structure, syntax, and security configurations of `Dockerfile`, `.dockerignore`, and `docker-compose.yml` (marked `@pytest.mark.issue_20`)
- [x] `make check` and `make test-issue ID=20` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=20 NAME=docker
```

### 2. Container ignore specification
- **File**: `.dockerignore`
- **Change**: Define clean exclusions for Docker build context including `.git`, `.venv`, `__pycache__`, `*.pyc`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.env`, `data/`, `build/`, `dist/`, and coverage artifacts.

### 3. Production container image definition
- **File**: `Dockerfile`
- **Change**: Implement an optimized Dockerfile using `python:3.11-slim`:
  - Set standard environment flags (`PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`).
  - Install runtime dependencies (e.g., `curl` for container healthcheck).
  - Create a dedicated non-privileged system user (`appuser` with UID 10001).
  - Install Python dependencies (`pip install --no-cache-dir .[all]`).
  - Copy repository source files with non-root ownership.
  - Expose port 8000.
  - Configure `HEALTHCHECK` against `http://localhost:8000/health`.
  - Set default `CMD` to run `uvicorn financial_research_agent.api.app:create_app --factory --host 0.0.0.0 --port 8000`.

### 4. Multi-service orchestration composition
- **File**: `docker-compose.yml`
- **Change**: Provide Compose specification defining:
  - `api`: builds local Dockerfile, maps `8000:8000`, mounts `./data:/app/data`, loads `.env` or defaults, and configures container health checks.
  - `cli`: complementary one-off service definition sharing the base image to execute CLI research, ingestion, or transform subcommands.

### 5. Docker configuration unit tests
- **File**: `tests/unit/test_docker.py`
- **Change**: Implement unit tests validating:
  - `Dockerfile` directives: non-root `USER`, `EXPOSE 8000`, base image, `WORKDIR /app`, `HEALTHCHECK`, and startup command.
  - `.dockerignore` exclusions: presence of git, venv, caches, and local data directory.
  - `docker-compose.yml` structure: valid YAML parsing, services (`api`, `cli`), port mappings, volume mount points, and healthcheck specification (marked `@pytest.mark.issue_20`).

### 6. Verification & Quality Gates
```bash
make test-issue ID=20
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=20 MSG="feat(infra): add Dockerfile and docker-compose configuration"
```

## Decisions
- `python:3.11-slim` is chosen as the container base image to ensure minimal container size, rapid builds, and full compatibility with Python 3.11+ dependencies.
- A dedicated non-root user (`appuser`, UID 10001) is created and enforced via `USER appuser` to uphold container security best practices.
- `docker-compose.yml` provides both an `api` HTTP daemon service and a `cli` service profile for flexible interactive execution without separate tooling.

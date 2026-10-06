# Issue 21: GitHub Actions CI workflow

**Branch**: `feature/issue-21-ci-workflow`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #21)
**Milestone**: M4 - Orchestration & Delivery

## Objective
Establish automated continuous integration using GitHub Actions to enforce code quality, static type safety, security compliance, test suite execution, and container buildability on every pull request and push to `main` and `develop`.

## Acceptance Criteria
- [x] `.github/workflows/ci.yml` defines automated workflows triggered on push and pull_request to `main` and `develop`
- [x] CI pipeline includes linting, format check (`ruff`), strict type checking (`mypy`), and test suite execution across Python versions
- [x] CI pipeline includes security audits (`pip-audit`, `bandit`) and Docker build validation
- [x] `tests/unit/test_ci_workflow.py` validates workflow YAML schema, triggers, jobs, steps, and command parity with Makefile (marked `@pytest.mark.issue_21`)
- [x] `make check` and `make test-issue ID=21` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=21 NAME=ci-workflow
```

### 2. GitHub Actions CI workflow definition
- **File**: `.github/workflows/ci.yml`
- **Change**: Define an automated GitHub Actions workflow triggered on push and pull requests against `main` and `develop`. Implement modular jobs:
  - `lint-and-typecheck`: checkout, setup Python with pip cache, install dev dependencies, run `ruff check`, `ruff format --check`, and `mypy src`.
  - `test`: matrix across Python 3.11 and 3.12, install package dependencies, execute `pytest` with coverage.
  - `security`: run `pip-audit` for dependency vulnerabilities and `bandit` for security analysis.
  - `docker-build`: validate container image build with build caching.

### 3. CI workflow unit tests
- **File**: `tests/unit/test_ci_workflow.py`
- **Change**: Add unit tests verifying workflow syntax, YAML validity, trigger configurations for `develop` and `main`, presence of required jobs and steps, action versions (`actions/checkout@v4`, `actions/setup-python@v5`), and alignment with `Makefile` quality targets (marked `@pytest.mark.issue_21`).

### 4. Verification & Quality Gates
```bash
make test-issue ID=21
make check
```

### 5. Git & Issue Finish
```bash
make finish-issue ID=21 MSG="ci: configure GitHub Actions automated workflow"
```

## Decisions
- A multi-job architecture (`lint-and-typecheck`, `test`, `security`, `docker-build`) is used to provide rapid feedback on syntax/lint issues while running tests and container builds in parallel.
- Python 3.11 and 3.12 matrix testing ensures runtime compatibility across supported minor versions without unnecessary CI overhead.
- Action dependencies are pinned to major versions (`actions/checkout@v4`, `actions/setup-python@v5`, `docker/build-push-action@v6`) adhering to GitHub security best practices.

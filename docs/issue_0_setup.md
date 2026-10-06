# Issue 0: Day 0 Scaffolding

**Branch**: `feature/issue-0-setup`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (no "Closes": issue 0 does not exist on GitHub)
**Milestone**: M0 - Day 0 Scaffolding (local only, not created on GitHub)

## Objective
Deliver the empty project skeleton: repository layout, tooling configuration, a complete self-documenting Makefile, a smoke test, initial documentation, the living workflow rules and the GitHub bootstrap script. No business logic is written in this issue.

## Acceptance Criteria
- [x] `src/financial_research_agent/__init__.py` exists and only declares the package (no business logic)
- [x] `tests/unit/test_smoke.py` only imports the package (marked `@pytest.mark.issue_0`)
- [x] `pyproject.toml` registers the markers `issue_0` to `issue_22`, uses `--strict-markers` and defines the `dev`, `extract`, `transform`, `agent`, `orchestration` and `all` groups
- [x] `Makefile` is complete (default target `help`; lifecycle, environment, quality and test targets, all calling `.venv/bin/` binaries)
- [x] `.gitignore`, `.env.example`, `README.md`, `docs/roadmap.md` and `.agents/rules/workflow.md` exist and are written in English
- [x] `scripts/bootstrap_github.sh` creates the public repo, pushes `main` and `develop`, and creates 4 milestones and all 22 roadmap issues (#1 to #22)
- [x] Empty folders `dags/`, `infra/`, `scripts/`, `tests/integration/` are tracked with `.gitkeep`
- [x] `make check` and `make test-issue ID=0` pass

## Implementation Tasks

### 1. Preparation & Branching
Issue 0 runs before the Makefile exists, so these are the STEP ZERO commands (run by the user):
```bash
git init -b main
git commit --allow-empty -m "chore: initial commit"
git checkout -b develop
git checkout -b feature/issue-0-setup
```

### 2. Ignore and environment templates
- **File**: `.gitignore`, `.env.example`
- **Change**: `.gitignore` covers `.venv/`, `__pycache__/`, `*.egg-info/`, `build/`, `dist/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `.env`, `data/`, IDE folders and Airflow runtime files. `.env.example` lists placeholder variables only (no real secrets): `LLM_API_KEY`, `LLM_MODEL`, `SEC_USER_AGENT`, `VECTOR_STORE_URL`, `DATA_DIR`, `LOG_LEVEL`.

### 3. Project configuration
- **File**: `pyproject.toml`
- **Change**: Define project metadata (`financial-research-agent`, Python >=3.11, setuptools with `src` layout). Optional dependency groups: `dev` (ruff, mypy, pytest, pytest-cov), `extract` (httpx, pydantic, yfinance, feedparser), `transform` (beautifulsoup4, lxml, tiktoken), `agent` (openai SDK or equivalent, pydantic), `orchestration` (apache-airflow), `all` (union of all layers). Configure ruff (lint + format), mypy (strict) and pytest (`--strict-markers`, `testpaths`, markers `issue_0` to `issue_22` registered with descriptions).

### 4. Folder skeleton
- **File**: `src/financial_research_agent/__init__.py`, `src/financial_research_agent/{extract,transform,agent,orchestration}/.gitkeep`, `dags/.gitkeep`, `infra/.gitkeep`, `scripts/.gitkeep`, `tests/integration/.gitkeep`, `tests/unit/.gitkeep`
- **Change**: Create the empty structure. `__init__.py` contains only a module docstring and `__version__`. Layer folders are empty (`.gitkeep`) until their milestones.

### 5. Smoke test
- **File**: `tests/unit/test_smoke.py`
- **Change**: One test marked `@pytest.mark.issue_0` that imports `financial_research_agent` and asserts it exposes `__version__`. No other logic.

### 6. Makefile
- **File**: `Makefile`
- **Change**: Complete, self-documenting file (`.DEFAULT_GOAL := help`, each target documented with `## description`). All tools are called via `.venv/bin/`. Targets:
  - Lifecycle: `start-issue` (ID, NAME, optional TYPE), `finish-issue` (ID, MSG; verifies branch, runs `make check`, commit, push, PR, squash merge, deletes branches, closes the issue; ID=0 skips "Closes" and `gh issue close`), `finish-milestone` (MILESTONE; PR `develop` → `main`, merge commit, tag, close milestone). Every target validates required parameters and aborts with a clear message.
  - Environment and quality: `venv`, `deps`, `lint`, `format`, `typecheck`, `check`, `clean`, `security` (pip-audit + bandit).
  - Tests: `test`, `test-unit`, `test-integration`, `test-issue ID=X` (fails if no tests are marked), `ci` (check + test).

### 7. Living workflow rules
- **File**: `.agents/rules/workflow.md`
- **Change**: Document all rules that apply beyond Day 0: Git Flow and Conventional Commits, two-phase cycle, mandatory issue format, Makefile and pyproject conventions, English-only, autonomy and `## Decisions`, who runs what, quality gate, communication format, internal plans policy, and the "living document" update rule.

### 8. Draft README
- **File**: `README.md`
- **Change**: Project description, proposed architecture (extract → transform → vector store → research agent → report/API, orchestrated by Airflow), ASCII or mermaid diagram, tech stack, repository layout, quickstart (`make venv`, `make deps`, `make ci`), and a link to `docs/roadmap.md`.

### 9. Roadmap
- **File**: `docs/roadmap.md`
- **Change**: Table milestone → issues (source of truth for which issue closes each milestone):
  - **M1 - Extraction**: #1 Raw document Pydantic schemas · #2 SEC EDGAR filings extractor · #3 Market data extractor (yfinance) · #4 News RSS extractor · #5 Raw storage writer and extractor fixtures tests
  - **M2 - Transformation**: #6 Filing parser and text cleaner · #7 Document chunker · #8 Embedding generator · #9 Vector store loader · #10 Financial metrics normalizer
  - **M3 - Research Agent**: #11 Retrieval tool · #12 Market data tool · #13 LLM client abstraction · #14 Agent loop with tool calling · #15 Structured report generator with citations · #16 Agent evaluation harness
  - **M4 - Orchestration & Delivery**: #17 Ingestion DAG · #18 Transform and indexing DAG · #19 CLI and FastAPI endpoint · #20 Dockerfile and docker-compose · #21 GitHub Actions CI workflow · #22 Final documentation and demo

### 10. GitHub bootstrap script
- **File**: `scripts/bootstrap_github.sh`
- **Change**: Executable bash script (`set -euo pipefail`), run by the user. It runs `gh repo create financial-research-agent --public --source=. --remote=origin`, pushes `main` and `develop`, creates the 4 milestones, then creates issues #1 to #22 in order, each assigned to its milestone, with titles matching `docs/roadmap.md`. It must run before the first PR so issue numbers match the roadmap.

### 11. Verification & Quality Gates
```bash
make venv
make deps        # needs network: the agent will ask for permission
make test-issue ID=0
make check
make ci
```

### 12. Git & Issue Finish
```bash
./scripts/bootstrap_github.sh   # run by the user before the first PR
make finish-issue ID=0 MSG="chore(setup): day 0 scaffolding"
```

## Decisions
- Package name `financial_research_agent` and layers `extract`, `transform`, `agent`, `orchestration`: they map one-to-one to the roadmap milestones.
- Issue 0 uses a local-only `M0` milestone: the 4 GitHub milestones (M1 to M4) hold the 22 roadmap issues.
- Markers `issue_0` to `issue_22` are registered upfront: `--strict-markers` breaks the suite on unregistered markers and the roadmap size is fixed.
- `apache-airflow` in the `orchestration` group has the marker `python_version < '3.14'`: the local interpreter is 3.14, which Airflow does not support yet, so `make deps` would fail otherwise.
- `tests/unit/.gitkeep` is not created: the folder already tracks `test_smoke.py`.

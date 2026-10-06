# Issue 15: Structured Report Generator with Citations

**Branch**: `feature/issue-15-report-generator`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #15)
**Milestone**: M3 - Research Agent

## Objective
Implement a structured financial report generator that transforms agent reasoning trajectories, filing citations, and market metrics into formatted, auditable equity research reports with verified source citations and markdown export.

## Acceptance Criteria
- [x] `src/financial_research_agent/agent/schemas.py` defines `ReportSection` and `FinancialResearchReport` with `to_markdown()` rendering
- [x] `src/financial_research_agent/agent/report_generator.py` exposes `ReportGenerator` and `ReportGeneratorError`
- [x] `src/financial_research_agent/agent/__init__.py` exports report generator classes and schemas
- [x] `tests/unit/test_report_generator.py` covers structured report assembly, citation deduplication, markdown rendering, and error handling (marked `@pytest.mark.issue_15`)
- [x] `pyproject.toml` registers the `issue_15` marker
- [x] `make check` and `make test-issue ID=15` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=15 NAME=report-generator
```

### 2. Structured report schema definition
- **File**: `src/financial_research_agent/agent/schemas.py`
- **Change**: Define `ReportSection` and `FinancialResearchReport` Pydantic models with immutable configuration (`frozen=True, extra="forbid"`), managing structured sections, metadata, citation registries, and markdown document generation.

### 3. Report generator implementation
- **File**: `src/financial_research_agent/agent/report_generator.py`
- **Change**: Implement `ReportGenerator` and `ReportGeneratorError` assembling structured reports from agent trajectories, extracting and deduplicating citations, structuring sections (Executive Summary, Market Analysis, SEC Disclosures), and generating citation appendices.

### 4. Package exports
- **File**: `src/financial_research_agent/agent/__init__.py`
- **Change**: Export `ReportGenerator`, `ReportGeneratorError`, `ReportSection`, and `FinancialResearchReport` in `__all__`.

### 5. Report generator unit tests
- **File**: `tests/unit/test_report_generator.py`
- **Change**: Add unit tests verifying structured report synthesis, citation aggregation and deduplication, markdown report generation with source tables, and error handling, marked with `@pytest.mark.issue_15`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=15
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=15 MSG="feat(agent): implement structured report generator with citations"
```

## Decisions
- `FinancialResearchReport` provides `to_markdown()` to render clean equity research reports featuring metric summary tables, section breakdowns, and an auditable source citations appendix with SEC filing chunk references.

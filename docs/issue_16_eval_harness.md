# Issue 16: Agent Evaluation Harness

**Branch**: `feature/issue-16-eval-harness`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #16)
**Milestone**: M3 - Research Agent

## Objective
Implement an agent evaluation harness to benchmark and evaluate agent performance, tool calling adherence, citation fidelity, and factual keyword coverage against standardized financial research test cases.

## Acceptance Criteria
- [x] `src/financial_research_agent/agent/schemas.py` defines `EvaluationCase`, `EvaluationResult`, and `EvaluationSummary`
- [x] `src/financial_research_agent/agent/evaluation.py` exposes `AgentEvaluator`, `EvaluationError`, and `get_default_eval_suite()`
- [x] `src/financial_research_agent/agent/__init__.py` exports evaluation harness classes and schemas
- [x] `tests/unit/test_evaluation.py` covers single case evaluation, test suite aggregation, score calculations, and failure modes (marked `@pytest.mark.issue_16`)
- [x] `pyproject.toml` registers the `issue_16` marker
- [x] `make check` and `make test-issue ID=16` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=16 NAME=eval-harness
```

### 2. Evaluation harness schema definition
- **File**: `src/financial_research_agent/agent/schemas.py`
- **Change**: Define `EvaluationCase`, `EvaluationResult`, and `EvaluationSummary` Pydantic models with immutable configuration (`frozen=True, extra="forbid"`) to represent test cases, metrics, and suite benchmark reports.

### 3. Agent evaluation harness implementation
- **File**: `src/financial_research_agent/agent/evaluation.py`
- **Change**: Implement `AgentEvaluator`, `EvaluationError`, and `get_default_eval_suite()` to execute `ResearchAgent` runs, score tool dispatch adherence, evaluate citation presence, calculate keyword coverage, and generate aggregate evaluation summaries.

### 4. Package exports
- **File**: `src/financial_research_agent/agent/__init__.py`
- **Change**: Export `AgentEvaluator`, `EvaluationError`, `EvaluationCase`, `EvaluationResult`, `EvaluationSummary`, and `get_default_eval_suite` in `__all__`.

### 5. Evaluation harness unit tests
- **File**: `tests/unit/test_evaluation.py`
- **Change**: Add unit tests using `MockLLMClient` testing individual case evaluation, suite execution, metric calculations (tool score, citation score, keyword score), and error handling, marked with `@pytest.mark.issue_16`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=16
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=16 MSG="feat(agent): implement agent evaluation harness"
```

### 8. Milestone Finish
```bash
make finish-milestone MILESTONE=M3
```

## Decisions
- `AgentEvaluator` evaluates agent runs deterministically without requiring live LLM calls by running against `ResearchAgent` with configurable clients (`MockLLMClient` or live models), scoring tool usage adherence, citation presence, and keyword coverage.

# Issue 14: Agent Loop with Tool Calling

**Branch**: `feature/issue-14-agent-loop4`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #14)
**Milestone**: M3 - Research Agent

## Objective
Implement an iterative agent loop that coordinates LLM reasoning with tool execution, dynamically dispatching function calls to registered tools (retrieval, market data), tracking conversation history and token usage, and terminating upon final synthesis or maximum iterations.

## Acceptance Criteria
- [x] `src/financial_research_agent/agent/schemas.py` defines `AgentStep` and `AgentRunResult`
- [x] `src/financial_research_agent/agent/loop.py` exposes `ResearchAgent`, `AgentError`, `AgentMaxIterationsError`, and `ToolExecutionError`
- [x] `src/financial_research_agent/agent/__init__.py` exports agent loop classes and trajectory schemas
- [x] `tests/unit/test_agent_loop.py` covers multi-turn tool calling, argument dispatch, max iteration limits, and trajectory tracking (marked `@pytest.mark.issue_14`)
- [x] `pyproject.toml` registers the `issue_14` marker
- [x] `make check` and `make test-issue ID=14` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=14 NAME=agent-loop
```

### 2. Agent trajectory and step schema definition
- **File**: `src/financial_research_agent/agent/schemas.py`
- **Change**: Define `AgentStep` and `AgentRunResult` Pydantic models with immutable configuration (`frozen=True, extra="forbid"`) to record tool execution history, message state, accumulated token usage, and final response synthesis.

### 3. Agent loop and tool dispatcher implementation
- **File**: `src/financial_research_agent/agent/loop.py`
- **Change**: Implement `ResearchAgent` orchestrating multi-turn conversation loops with `BaseLLMClient`, dispatching function calls to registered tools, updating message history, accumulating token usage, and raising `AgentMaxIterationsError` if limits are exceeded.

### 4. Package exports
- **File**: `src/financial_research_agent/agent/__init__.py`
- **Change**: Export `ResearchAgent`, `AgentError`, `AgentMaxIterationsError`, `ToolExecutionError`, `AgentStep`, and `AgentRunResult` in `__all__`.

### 5. Agent loop unit tests
- **File**: `tests/unit/test_agent_loop.py`
- **Change**: Add unit tests using `MockLLMClient` verifying multi-turn tool calling sequences, dynamic tool dispatch, max iteration enforcement, step recording, and error handling, marked with `@pytest.mark.issue_14`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=14
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=14 MSG="feat(agent): implement agent loop with tool calling"
```

## Decisions
- `ResearchAgent` dynamically inspects registered tool objects via their `tool_spec` and dispatches arguments to their execution method, converting structured outputs into textual observation messages for LLM context.

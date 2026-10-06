# Issue 13: LLM Client Abstraction

**Branch**: `feature/issue-13-llm-client`
**Status**: Done
**PR**: opened by `make finish-issue` → `develop` (Closes #13)
**Milestone**: M3 - Research Agent

## Objective
Implement an extensible LLM client abstraction supporting chat completions, tool/function calling, token usage tracking, and a mock client for offline testing and agent evaluation.

## Acceptance Criteria
- [x] `src/financial_research_agent/agent/schemas.py` defines `ChatMessage`, `MessageRole`, `ToolCall`, `FunctionCall`, `TokenUsage`, and `LLMResponse`
- [x] `src/financial_research_agent/agent/llm_client.py` exposes `BaseLLMClient`, `OpenAILLMClient`, `MockLLMClient`, and `LLMError`
- [x] `src/financial_research_agent/agent/__init__.py` exports LLM client classes and message schemas
- [x] `tests/unit/test_llm_client.py` covers chat generation, tool calling response parsing, mock responses, and error handling (marked `@pytest.mark.issue_13`)
- [x] `pyproject.toml` registers the `issue_13` marker
- [x] `make check` and `make test-issue ID=13` pass

## Implementation Tasks

### 1. Preparation & Branching
```bash
make start-issue ID=13 NAME=llm-client
```

### 2. LLM message and response schema definition
- **File**: `src/financial_research_agent/agent/schemas.py`
- **Change**: Define `MessageRole` enum, `ChatMessage`, `FunctionCall`, `ToolCall`, `TokenUsage`, and `LLMResponse` Pydantic models with immutable configuration (`frozen=True, extra="forbid"`).

### 3. LLM client abstraction and implementations
- **File**: `src/financial_research_agent/agent/llm_client.py`
- **Change**: Implement `BaseLLMClient` protocol/abstract class, `OpenAILLMClient` for OpenAI Chat Completions with tool calling support, `MockLLMClient` for predictable offline execution, and `LLMError` hierarchy.

### 4. Package exports
- **File**: `src/financial_research_agent/agent/__init__.py`
- **Change**: Export LLM client classes, error types, and message models in `__all__`.

### 5. LLM client unit tests
- **File**: `tests/unit/test_llm_client.py`
- **Change**: Add unit tests verifying prompt/chat completion, tool calling payload parsing, token usage metrics, mock response queuing, and error mapping, marked with `@pytest.mark.issue_13`.

### 6. Verification & Quality Gates
```bash
make test-issue ID=13
make check
```

### 7. Git & Issue Finish
```bash
make finish-issue ID=13 MSG="feat(agent): implement LLM client abstraction"
```

## Decisions
- `OpenAILLMClient` accepts an optional custom client or API key, while `MockLLMClient` allows configuring scripted responses and tool calls for deterministic agent testing without network or OpenAI credentials.

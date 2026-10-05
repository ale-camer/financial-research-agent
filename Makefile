SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

BIN := .venv/bin
PYTHON := $(BIN)/python
PIP := $(BIN)/pip
RUFF := $(BIN)/ruff
MYPY := $(BIN)/mypy
PYTEST := $(BIN)/pytest

TYPE ?= feature
BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null)

# require VAR "usage hint": abort with a clear message if VAR is empty.
define require
test -n "$($(1))" || { echo 'ERROR: missing parameter $(1). Usage: $(2)' >&2; exit 1; }
endef

.PHONY: help start-issue finish-issue finish-milestone venv deps lint format typecheck check \
	test test-unit test-integration test-issue ci clean security

help: ## Show this help (default target)
	@echo "Usage: make <target> [PARAM=value]"
	@echo
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---------------------------------------------------------------- Lifecycle

start-issue: ## Start an issue branch: ID=X NAME=short-name [TYPE=feature|fix]
	@$(call require,ID,make start-issue ID=X NAME=short-name [TYPE=feature|fix])
	$(call require,NAME,make start-issue ID=X NAME=short-name [TYPE=feature|fix])
	case "$(TYPE)" in feature|fix) ;; *) echo "ERROR: TYPE must be feature or fix" >&2; exit 1;; esac
	git checkout develop
	git pull --ff-only
	git checkout -b "$(TYPE)/issue-$(ID)-$(NAME)"

finish-issue: ## Finish an issue: ID=X MSG="type(scope): description"
	@$(call require,ID,make finish-issue ID=X MSG="type(scope): description")
	$(call require,MSG,make finish-issue ID=X MSG="type(scope): description")
	branch="$(BRANCH)"
	case "$$branch" in
		feature/issue-$(ID)-*|fix/issue-$(ID)-*) ;;
		*) echo "ERROR: current branch '$$branch' is not the branch of issue $(ID)" >&2; exit 1;;
	esac
	$(MAKE) check
	git add -A
	git commit -m "$(MSG)"
	git push -u origin "$$branch"
	if [ "$(ID)" = "0" ]; then body="$(MSG)"; else body="Closes #$(ID)"; fi
	gh pr create --base develop --head "$$branch" --title "$(MSG)" --body "$$body"
	gh pr merge "$$branch" --squash --delete-branch
	git checkout develop
	git pull --ff-only
	git branch -D "$$branch" 2>/dev/null || true
	if [ "$(ID)" != "0" ]; then gh issue close "$(ID)"; fi

finish-milestone: ## Release develop to main: MILESTONE=MX
	@$(call require,MILESTONE,make finish-milestone MILESTONE=MX)
	gh pr create --base main --head develop --title "release: $(MILESTONE)" --body "Release $(MILESTONE)"
	gh pr merge develop --merge
	git checkout main
	git pull --ff-only
	git tag "$(MILESTONE)"
	git push origin "$(MILESTONE)"
	number=$$(gh api "repos/{owner}/{repo}/milestones?state=open" \
		--jq '.[] | select(.title | startswith("$(MILESTONE) ")) | .number')
	test -n "$$number" || { echo "ERROR: milestone $(MILESTONE) not found" >&2; exit 1; }
	gh api -X PATCH "repos/{owner}/{repo}/milestones/$$number" -f state=closed
	git checkout develop
	git pull --ff-only

# ------------------------------------------------------ Environment & quality

venv: ## Create the .venv virtual environment
	python3 -m venv .venv

deps: ## Install all dependencies (needs network)
	$(PIP) install -e ".[all,dev]"

lint: ## Run ruff lint and format check
	$(RUFF) check .
	$(RUFF) format --check .

format: ## Auto-format and auto-fix with ruff
	$(RUFF) format .
	$(RUFF) check --fix .

typecheck: ## Run mypy in strict mode on src
	$(MYPY) src

check: lint typecheck ## Run lint and typecheck

security: ## Audit dependencies (pip-audit, needs network) and code (bandit)
	$(BIN)/pip-audit
	$(BIN)/bandit -r src -q

# ---------------------------------------------------------------------- Tests

test: ## Run the whole test suite
	$(PYTEST)

test-unit: ## Run unit tests
	$(PYTEST) tests/unit

test-integration: ## Run integration tests
	$(PYTEST) tests/integration

test-issue: ## Run tests of one issue (fails if none are marked): ID=X
	@$(call require,ID,make test-issue ID=X)
	$(PYTEST) -m "issue_$(ID)"

ci: check test ## Run what a CI pipeline would run (check + test)

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache build .coverage htmlcov
	find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
	find . -path ./.venv -prune -o -type d -name "*.egg-info" -exec rm -rf {} +

"""Unit tests for GitHub Actions CI workflow configuration."""

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _load_workflow() -> dict[str, Any]:
    assert WORKFLOW_PATH.is_file(), f"Workflow file not found at: {WORKFLOW_PATH}"
    data: dict[str, Any] = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return data


@pytest.mark.issue_21
def test_workflow_file_exists() -> None:
    assert WORKFLOW_PATH.is_file(), ".github/workflows/ci.yml must exist"


@pytest.mark.issue_21
def test_workflow_valid_yaml_and_structure() -> None:
    workflow = _load_workflow()
    assert isinstance(workflow, dict), "Workflow root must be a YAML mapping"
    assert "name" in workflow, "Workflow must declare a name"
    # PyYAML parses unquoted 'on:' as boolean True
    on_key = True if True in workflow else "on"
    assert on_key in workflow, "Workflow must specify trigger events"
    assert "jobs" in workflow, "Workflow must define jobs"


@pytest.mark.issue_21
def test_workflow_triggers_on_push_and_pr_for_key_branches() -> None:
    workflow = _load_workflow()
    triggers = workflow.get(True) or workflow.get("on")
    assert isinstance(triggers, dict), "Triggers must be a dictionary"

    assert "push" in triggers, "Workflow must trigger on push"
    assert "pull_request" in triggers, "Workflow must trigger on pull_request"

    push_branches = triggers["push"].get("branches", [])
    pr_branches = triggers["pull_request"].get("branches", [])

    for branch in ["main", "develop"]:
        assert branch in push_branches, f"push must trigger on branch '{branch}'"
        assert branch in pr_branches, f"pull_request must trigger on branch '{branch}'"


@pytest.mark.issue_21
def test_workflow_defines_all_required_jobs() -> None:
    workflow = _load_workflow()
    jobs = workflow.get("jobs", {})

    expected_jobs = ["lint-and-typecheck", "test", "security", "docker-build"]
    for job_name in expected_jobs:
        assert job_name in jobs, f"Job '{job_name}' must be defined in CI workflow"


@pytest.mark.issue_21
def test_workflow_lint_and_typecheck_job_configuration() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["lint-and-typecheck"]

    assert job.get("runs-on") == "ubuntu-latest"
    steps = job.get("steps", [])

    step_runs = " ".join(step.get("run", "") for step in steps)
    step_uses = " ".join(step.get("uses", "") for step in steps)

    assert "actions/checkout@v4" in step_uses
    assert "actions/setup-python@v5" in step_uses
    assert "ruff check ." in step_runs
    assert "ruff format --check ." in step_runs
    assert "mypy src" in step_runs


@pytest.mark.issue_21
def test_workflow_test_job_configuration() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["test"]

    assert job.get("runs-on") == "ubuntu-latest"
    matrix = job.get("strategy", {}).get("matrix", {})
    python_versions = matrix.get("python-version", [])

    assert "3.11" in python_versions, "Test matrix must include Python 3.11"
    assert "3.12" in python_versions, "Test matrix must include Python 3.12"

    steps = job.get("steps", [])
    step_runs = " ".join(step.get("run", "") for step in steps)
    assert "pytest" in step_runs, "Test job must execute pytest"


@pytest.mark.issue_21
def test_workflow_security_job_configuration() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["security"]

    assert job.get("runs-on") == "ubuntu-latest"
    steps = job.get("steps", [])
    step_runs = " ".join(step.get("run", "") for step in steps)

    assert "pip-audit" in step_runs, "Security job must run pip-audit"
    assert "bandit" in step_runs, "Security job must run bandit"


@pytest.mark.issue_21
def test_workflow_docker_build_job_configuration() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["docker-build"]

    assert job.get("runs-on") == "ubuntu-latest"
    steps = job.get("steps", [])
    step_uses = " ".join(step.get("uses", "") for step in steps)

    assert "docker/setup-buildx-action@v3" in step_uses
    assert "docker/build-push-action@v6" in step_uses

"""Unit tests for Dockerfile, .dockerignore, and docker-compose.yml configuration."""

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.issue_20
def test_dockerignore_exists_and_contains_standard_rules() -> None:
    dockerignore_path = REPO_ROOT / ".dockerignore"
    assert dockerignore_path.is_file(), ".dockerignore must exist at repository root"

    content = dockerignore_path.read_text(encoding="utf-8")
    lines = [
        line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")
    ]

    required_patterns = [
        ".git/",
        ".venv/",
        "__pycache__/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        ".env",
        "data/",
        "build/",
        "dist/",
    ]

    for pattern in required_patterns:
        assert pattern in lines or any(line == pattern for line in lines), (
            f"Expected pattern '{pattern}' in .dockerignore"
        )


@pytest.mark.issue_20
def test_dockerfile_exists_and_uses_python_311_base() -> None:
    dockerfile_path = REPO_ROOT / "Dockerfile"
    assert dockerfile_path.is_file(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")
    lines = [
        line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")
    ]

    from_line = next((line for line in lines if line.startswith("FROM ")), "")
    assert "python:3.11" in from_line, (
        f"Dockerfile base image must use Python 3.11, found: {from_line}"
    )


@pytest.mark.issue_20
def test_dockerfile_security_and_non_root_user() -> None:
    dockerfile_path = REPO_ROOT / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "appuser" in content, "Dockerfile must define dedicated non-root user appuser"
    assert "useradd" in content or "adduser" in content, "Dockerfile must create user"
    assert "USER appuser" in content, "Dockerfile must switch to USER appuser for execution"


@pytest.mark.issue_20
def test_dockerfile_workdir_and_dependencies_installation() -> None:
    dockerfile_path = REPO_ROOT / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "WORKDIR /app" in content, "Dockerfile WORKDIR must be /app"
    assert "COPY pyproject.toml" in content, "Dockerfile must copy pyproject.toml"
    assert "pip install" in content, "Dockerfile must run pip install"
    assert "/app/data" in content, "Dockerfile must configure data storage path /app/data"


@pytest.mark.issue_20
def test_dockerfile_port_and_healthcheck() -> None:
    dockerfile_path = REPO_ROOT / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "EXPOSE 8000" in content, "Dockerfile must expose port 8000"
    assert "HEALTHCHECK" in content, "Dockerfile must define a HEALTHCHECK"
    assert "/health" in content, "Dockerfile healthcheck must verify /health endpoint"
    assert "uvicorn" in content, "Dockerfile CMD must run uvicorn"
    assert "financial_research_agent.api.app:create_app" in content, (
        "Dockerfile CMD must target create_app factory"
    )


@pytest.mark.issue_20
def test_docker_compose_valid_structure() -> None:
    compose_path = REPO_ROOT / "docker-compose.yml"
    assert compose_path.is_file(), "docker-compose.yml must exist at repository root"

    compose_data: dict[str, Any] = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    assert isinstance(compose_data, dict), "docker-compose.yml root must be a mapping"
    assert "services" in compose_data, "docker-compose.yml must define 'services'"

    services = compose_data["services"]
    assert "api" in services, "docker-compose.yml must define 'api' service"
    assert "cli" in services, "docker-compose.yml must define 'cli' service"


@pytest.mark.issue_20
def test_docker_compose_api_service_configuration() -> None:
    compose_path = REPO_ROOT / "docker-compose.yml"
    compose_data: dict[str, Any] = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    api_service = compose_data["services"]["api"]
    assert api_service.get("build", {}).get("context") == ".", "api build context must be '.'"
    assert api_service.get("build", {}).get("dockerfile") == "Dockerfile", (
        "api dockerfile must be Dockerfile"
    )

    ports = [str(p) for p in api_service.get("ports", [])]
    assert any("8000:8000" in p for p in ports), (
        f"api service must expose port 8000:8000, got: {ports}"
    )

    volumes = [str(v) for v in api_service.get("volumes", [])]
    assert any("./data:/app/data" in v for v in volumes), (
        f"api service must mount ./data:/app/data, got: {volumes}"
    )

    healthcheck = api_service.get("healthcheck", {})
    assert "test" in healthcheck, "api service must specify healthcheck test"
    test_cmd = " ".join(str(part) for part in healthcheck["test"])
    assert "/health" in test_cmd, f"api healthcheck must test /health, got: {test_cmd}"


@pytest.mark.issue_20
def test_docker_compose_cli_service_configuration() -> None:
    compose_path = REPO_ROOT / "docker-compose.yml"
    compose_data: dict[str, Any] = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    cli_service = compose_data["services"]["cli"]
    assert cli_service.get("build", {}).get("context") == ".", "cli build context must be '.'"

    volumes = [str(v) for v in cli_service.get("volumes", [])]
    assert any("./data:/app/data" in v for v in volumes), (
        f"cli service must mount ./data:/app/data, got: {volumes}"
    )

    entrypoint = cli_service.get("entrypoint", [])
    entrypoint_str = " ".join(entrypoint) if isinstance(entrypoint, list) else str(entrypoint)
    assert "financial-research-agent" in entrypoint_str, (
        f"cli service entrypoint must invoke financial-research-agent, got: {entrypoint_str}"
    )

    profiles = cli_service.get("profiles", [])
    assert "cli" in profiles, "cli service must belong to the 'cli' profile"

"""Unit tests for demo script execution and comprehensive README documentation."""

from pathlib import Path

import pytest
from scripts.demo import main

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.issue_22
def test_demo_main_executes_successfully_in_mock_mode(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "--mock",
            "--ticker",
            "AAPL",
            "--query",
            "Summarize quarterly revenue, gross margins, and growth catalysts.",
        ]
    )

    assert exit_code == 0, f"Demo script failed with exit code {exit_code}"
    captured = capsys.readouterr()

    assert "FINANCIAL RESEARCH AGENT" in captured.out
    assert "Financial Research Report: AAPL" in captured.out
    assert "Executive Summary" in captured.out
    assert "Sources & Citations" in captured.out
    assert "citations captured" in captured.out


@pytest.mark.issue_22
def test_demo_main_writes_report_file(tmp_path: Path) -> None:
    output_file = tmp_path / "test_report.md"
    exit_code = main(
        [
            "--mock",
            "--ticker",
            "NVDA",
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0
    assert output_file.is_file(), "Report file was not created"

    content = output_file.read_text(encoding="utf-8")
    assert "# Financial Research Report: NVDA" in content
    assert "Executive Summary" in content
    assert "Sources & Citations" in content


@pytest.mark.issue_22
def test_readme_contains_all_core_documentation_sections() -> None:
    readme_path = REPO_ROOT / "README.md"
    assert readme_path.is_file(), "README.md must exist in repository root"

    content = readme_path.read_text(encoding="utf-8")

    required_sections = [
        "## Architecture",
        "## Tech Stack",
        "## Repository Layout",
        "## Quickstart",
        "## Running the End-to-End Demo",
        "## Command-Line Interface (CLI)",
        "## REST API (FastAPI)",
        "## Docker & Container Deployment",
        "## Apache Airflow DAGs",
        "## Development & Workflow",
    ]

    for section in required_sections:
        assert section in content, f"Missing required documentation section: '{section}'"

    # Key command & endpoint references
    assert "financial-research-agent research" in content
    assert "financial-research-agent ingest" in content
    assert "financial-research-agent transform" in content
    assert "GET /health" in content
    assert "POST /research" in content
    assert "docker compose up -d" in content
    assert "financial_ingestion_dag" in content
    assert "financial_transform_dag" in content

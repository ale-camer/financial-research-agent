"""Unit tests for the financial research CLI interface."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from financial_research_agent import __version__
from financial_research_agent.cli import build_parser, main
from financial_research_agent.orchestration.schemas import IngestionResult, TransformResult


@pytest.mark.issue_19
def test_cli_parser_structure() -> None:
    parser = build_parser()
    assert parser.prog == "financial-research-agent"


@pytest.mark.issue_19
def test_cli_no_args_shows_help(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "Available subcommands" in captured.err or "usage" in captured.err


@pytest.mark.issue_19
def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


@pytest.mark.issue_19
def test_cli_research_mock_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_file = tmp_path / "report.md"
    exit_code = main(
        [
            "research",
            "AAPL",
            "--mock",
            "-q",
            "Evaluate Apple risk profile",
            "-f",
            "markdown",
            "-o",
            str(out_file),
        ]
    )
    assert exit_code == 0
    assert out_file.is_file()
    content = out_file.read_text(encoding="utf-8")
    assert "Executive Summary" in content
    assert "AAPL" in content


@pytest.mark.issue_19
def test_cli_research_mock_json_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "research",
            "-t",
            "MSFT",
            "--mock",
            "-f",
            "json",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"ticker": "MSFT"' in captured.out
    assert "executive_summary" in captured.out


@pytest.mark.issue_19
def test_cli_research_missing_ticker(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["research"])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error: company ticker symbol is required" in captured.err


@pytest.mark.issue_19
def test_cli_ingest_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mock_pipeline = MagicMock()
    mock_result = MagicMock(spec=IngestionResult)
    mock_result.status = "success"
    mock_result.model_dump.return_value = {
        "status": "success",
        "total_documents_ingested": 2,
    }
    mock_pipeline.run.return_value = mock_result

    with patch(
        "financial_research_agent.cli.IngestionPipeline",
        return_value=mock_pipeline,
    ):
        exit_code = main(
            [
                "ingest",
                "-t",
                "AAPL",
                "MSFT",
                "--raw-dir",
                str(tmp_path / "raw"),
                "--period",
                "6mo",
            ]
        )
        assert exit_code == 0
        captured = capsys.readouterr()
        assert '"status": "success"' in captured.out
        assert mock_pipeline.run.called


@pytest.mark.issue_19
def test_cli_transform_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mock_pipeline = MagicMock()
    mock_result = MagicMock(spec=TransformResult)
    mock_result.status = "success"
    mock_result.model_dump.return_value = {
        "status": "success",
        "documents_parsed": 1,
    }
    mock_pipeline.run.return_value = mock_result

    with patch(
        "financial_research_agent.cli.TransformPipeline",
        return_value=mock_pipeline,
    ):
        exit_code = main(
            [
                "transform",
                "--raw-dir",
                str(tmp_path / "raw"),
                "--processed-dir",
                str(tmp_path / "processed"),
                "-t",
                "AAPL",
            ]
        )
        assert exit_code == 0
        captured = capsys.readouterr()
        assert '"status": "success"' in captured.out
        assert mock_pipeline.run.called

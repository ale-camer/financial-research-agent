"""Smoke test: the package is importable."""

import pytest

import financial_research_agent


@pytest.mark.issue_0
def test_package_exposes_version() -> None:
    assert financial_research_agent.__version__

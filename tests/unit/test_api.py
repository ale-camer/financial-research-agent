"""Unit tests for the delivery REST API endpoints and schemas."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import ValidationError

from financial_research_agent import __version__
from financial_research_agent.api import (
    HealthResponse,
    ResearchRequest,
    create_app,
)
from financial_research_agent.orchestration.ingestion import IngestionPipeline
from financial_research_agent.orchestration.schemas import IngestionResult, TransformResult
from financial_research_agent.orchestration.transform import TransformPipeline


@pytest.mark.issue_19
def test_api_schemas_validation() -> None:
    health = HealthResponse(version="0.1.0")
    assert health.status == "ok"
    assert health.version == "0.1.0"

    req = ResearchRequest(ticker="AAPL")
    assert req.ticker == "AAPL"
    assert req.max_iterations == 10
    assert req.mock is False

    with pytest.raises(ValidationError):
        ResearchRequest(ticker="")  # min_length=1

    with pytest.raises(ValidationError):
        ResearchRequest(ticker="AAPL", extra_invalid_key="error")  # extra forbidden


@pytest.mark.issue_19
def test_health_endpoint() -> None:
    app = create_app()
    client = app.test_client()

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__
    assert "timestamp" in data


@pytest.mark.issue_19
def test_research_endpoint_success() -> None:
    app = create_app()
    client = app.test_client()

    payload = {
        "ticker": "AAPL",
        "query": "Evaluate supply chain resilience",
        "mock": True,
    }
    response = client.post("/research", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert "Executive Summary" in data["markdown_report"]
    assert len(data["executive_summary"]) > 0


@pytest.mark.issue_19
def test_research_endpoint_validation_error() -> None:
    app = create_app()
    client = app.test_client()

    # Empty ticker symbol triggers 422
    response = client.post("/research", json={"ticker": ""})
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.issue_19
def test_ingest_endpoint() -> None:
    mock_pipeline = MagicMock(spec=IngestionPipeline)
    mock_result = IngestionResult(
        run_id="run_test_1",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=1.2,
        sec_filings_count=2,
        market_data_count=1,
        news_articles_count=0,
        total_documents_ingested=3,
        status="success",
    )
    mock_pipeline.run.return_value = mock_result

    app = create_app(ingestion_pipeline=mock_pipeline)
    client = app.test_client()

    payload = {"tickers": ["AAPL", "MSFT"]}
    response = client.post("/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_documents_ingested"] == 3


@pytest.mark.issue_19
def test_transform_endpoint() -> None:
    mock_pipeline = MagicMock(spec=TransformPipeline)
    mock_result = TransformResult(
        run_id="run_trans_1",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=0.8,
        documents_parsed=1,
        chunks_created=5,
        chunks_indexed=5,
        metrics_normalized=1,
        status="success",
    )
    mock_pipeline.run.return_value = mock_result

    app = create_app(transform_pipeline=mock_pipeline)
    client = app.test_client()

    payload = {"tickers": ["AAPL"]}
    response = client.post("/transform", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["documents_parsed"] == 1


@pytest.mark.issue_19
def test_not_found_endpoint() -> None:
    app = create_app()
    client = app.test_client()

    response = client.get("/non_existent_route")
    assert response.status_code == 404


@pytest.mark.anyio
@pytest.mark.issue_19
async def test_asgi_transport_protocol() -> None:
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

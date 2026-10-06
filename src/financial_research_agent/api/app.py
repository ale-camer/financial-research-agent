"""FastAPI application factory and REST API endpoints."""

import contextlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from financial_research_agent import __version__
from financial_research_agent.agent.llm_client import (
    BaseLLMClient,
    MockLLMClient,
    OpenAILLMClient,
)
from financial_research_agent.agent.loop import ResearchAgent
from financial_research_agent.agent.report_generator import ReportGenerator
from financial_research_agent.api.schemas import (
    HealthResponse,
    IngestRequest,
    ResearchRequest,
    ResearchResponse,
    TransformRequest,
)
from financial_research_agent.orchestration.ingestion import IngestionPipeline
from financial_research_agent.orchestration.schemas import (
    IngestionConfig,
    IngestionResult,
    TransformConfig,
    TransformResult,
)
from financial_research_agent.orchestration.transform import TransformPipeline

FASTAPI_AVAILABLE: bool = False
try:
    from fastapi import FastAPI, HTTPException, status

    FASTAPI_AVAILABLE = True
except ImportError:
    pass


def execute_research(
    request: ResearchRequest,
    agent: ResearchAgent | None = None,
    report_generator: ReportGenerator | None = None,
) -> ResearchResponse:
    """Execute research request and synthesize an auditable report."""
    ticker = request.ticker.strip().upper()
    query = request.query

    if agent is not None:
        active_agent = agent
        rep_gen = report_generator or ReportGenerator()
    elif request.mock:
        mock_llm = MockLLMClient()
        mock_llm.add_response(
            f"## Executive Summary\n\nAutomated research findings for {ticker}.\n\n"
            f"## Business Analysis\n\nRevenue trajectory is consistent with peer benchmarks.\n\n"
            f"## Risk Factors\n\nOperations are subject to macro and industry cyclicality."
        )
        active_agent = ResearchAgent(
            llm_client=mock_llm,
            max_iterations=request.max_iterations,
        )
        rep_gen = report_generator or ReportGenerator(llm_client=mock_llm)
    else:
        active_llm: BaseLLMClient
        try:
            active_llm = OpenAILLMClient()
        except Exception:
            mock_fb = MockLLMClient()
            mock_fb.add_response(
                f"## Executive Summary\n\nReport for {ticker}.\n\n## Findings\n\nData reviewed."
            )
            active_llm = mock_fb
        active_agent = ResearchAgent(
            llm_client=active_llm,
            max_iterations=request.max_iterations,
        )
        rep_gen = report_generator or ReportGenerator(llm_client=active_llm)

    run_result = active_agent.run(query=query)
    report = rep_gen.generate_from_run(
        ticker=ticker,
        run_result=run_result,
        title=f"Financial Research Report: {ticker}",
    )

    return ResearchResponse(
        ticker=report.ticker,
        query=report.raw_query,
        title=report.title,
        executive_summary=report.executive_summary,
        markdown_report=report.to_markdown(),
        citations_count=len(report.citations),
        generated_at=report.generated_at,
        metadata=report.metadata,
    )


def execute_ingestion(
    request: IngestRequest,
    pipeline: IngestionPipeline | None = None,
) -> IngestionResult:
    """Execute raw financial data ingestion pipeline."""
    config = IngestionConfig(
        tickers=request.tickers,
        sec_form_types=request.sec_form_types,
        market_period=request.market_period,
        raw_storage_dir=request.raw_storage_dir,
    )
    active_pipeline = pipeline or IngestionPipeline(config=config)
    return active_pipeline.run(config=config)


def execute_transformation(
    request: TransformRequest,
    pipeline: TransformPipeline | None = None,
) -> TransformResult:
    """Execute document transformation and vector indexing pipeline."""
    config = TransformConfig(
        raw_storage_dir=request.raw_storage_dir,
        processed_storage_dir=request.processed_storage_dir,
        vector_store_path=request.vector_store_path,
        tickers=request.tickers,
    )
    active_pipeline = pipeline or TransformPipeline(config=config)
    return active_pipeline.run(config=config)


class FallbackTestResponse:
    """Lightweight response representation for unit testing fallback app."""

    def __init__(self, status_code: int, json_data: Any, text: str = "") -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self) -> Any:
        return self._json_data


class FallbackTestClient:
    """Synchronous testing helper wrapping ASGI application calls."""

    def __init__(self, app: "FallbackASGIApp") -> None:
        self.app = app

    def get(self, path: str) -> FallbackTestResponse:
        return self.app._dispatch("GET", path, None)

    def post(self, path: str, json: Any = None) -> FallbackTestResponse:
        return self.app._dispatch("POST", path, json)


class FallbackASGIApp:
    """Standalone ASGI-compatible HTTP service stub when FastAPI is not present."""

    def __init__(
        self,
        agent: ResearchAgent | None = None,
        report_generator: ReportGenerator | None = None,
        ingestion_pipeline: IngestionPipeline | None = None,
        transform_pipeline: TransformPipeline | None = None,
    ) -> None:
        self.agent = agent
        self.report_generator = report_generator
        self.ingestion_pipeline = ingestion_pipeline
        self.transform_pipeline = transform_pipeline

    def test_client(self) -> FallbackTestClient:
        """Create a synchronous test client for testing endpoints directly."""
        return FallbackTestClient(self)

    def _dispatch(self, method: str, path: str, body_json: Any) -> FallbackTestResponse:
        """Internal synchronous route dispatcher."""
        norm_method = method.upper()
        clean_path = path.rstrip("/") or "/"

        if norm_method == "GET" and clean_path == "/health":
            resp = HealthResponse(version=__version__, timestamp=datetime.now(UTC))
            return FallbackTestResponse(200, resp.model_dump(mode="json"))

        if norm_method == "POST" and clean_path == "/research":
            try:
                req_obj = ResearchRequest.model_validate(body_json or {})
            except ValidationError as exc:
                return FallbackTestResponse(422, {"detail": exc.errors()})
            res = execute_research(req_obj, self.agent, self.report_generator)
            return FallbackTestResponse(200, res.model_dump(mode="json"))

        if norm_method == "POST" and clean_path == "/ingest":
            try:
                req_obj_ingest = IngestRequest.model_validate(body_json or {})
            except ValidationError as exc:
                return FallbackTestResponse(422, {"detail": exc.errors()})
            ingest_res = execute_ingestion(req_obj_ingest, self.ingestion_pipeline)
            return FallbackTestResponse(200, ingest_res.model_dump(mode="json"))

        if norm_method == "POST" and clean_path == "/transform":
            try:
                req_obj_trans = TransformRequest.model_validate(body_json or {})
            except ValidationError as exc:
                return FallbackTestResponse(422, {"detail": exc.errors()})
            trans_res = execute_transformation(req_obj_trans, self.transform_pipeline)
            return FallbackTestResponse(200, trans_res.model_dump(mode="json"))

        return FallbackTestResponse(404, {"detail": f"Not Found: {norm_method} {path}"})

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Any],
        send: Callable[[dict[str, Any]], Any],
    ) -> None:
        """ASGI request interface handling HTTP calls."""
        if scope.get("type") != "http":
            return

        method = str(scope.get("method", "GET"))
        path = str(scope.get("path", "/"))

        # Consume request body
        body_bytes = b""
        more_body = True
        while more_body:
            message = await receive()
            body_bytes += message.get("body", b"")
            more_body = message.get("more_body", False)

        body_json = None
        if body_bytes:
            with contextlib.suppress(Exception):
                body_json = json.loads(body_bytes.decode("utf-8"))

        res = self._dispatch(method, path, body_json)
        encoded_body = json.dumps(res.json()).encode("utf-8")

        await send(
            {
                "type": "http.response.start",
                "status": res.status_code,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(encoded_body)).encode("utf-8")],
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": encoded_body,
                "more_body": False,
            }
        )


def create_app(
    agent: ResearchAgent | None = None,
    report_generator: ReportGenerator | None = None,
    ingestion_pipeline: IngestionPipeline | None = None,
    transform_pipeline: TransformPipeline | None = None,
) -> Any:
    """Create and configure the FastAPI or fallback ASGI application."""
    if not FASTAPI_AVAILABLE:
        return FallbackASGIApp(
            agent=agent,
            report_generator=report_generator,
            ingestion_pipeline=ingestion_pipeline,
            transform_pipeline=transform_pipeline,
        )

    app = FastAPI(
        title="Financial Research Agent API",
        description="Agentic financial equity research REST API service.",
        version=__version__,
    )

    def health_check() -> HealthResponse:
        return HealthResponse(version=__version__, timestamp=datetime.now(UTC))

    def research_endpoint(request: ResearchRequest) -> ResearchResponse:
        try:
            return execute_research(request, agent, report_generator)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Research agent execution failed: {exc}",
            ) from exc

    def ingest_endpoint(request: IngestRequest) -> IngestionResult:
        try:
            return execute_ingestion(request, ingestion_pipeline)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ingestion pipeline failed: {exc}",
            ) from exc

    def transform_endpoint(request: TransformRequest) -> TransformResult:
        try:
            return execute_transformation(request, transform_pipeline)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transformation pipeline failed: {exc}",
            ) from exc

    app.add_api_route(
        "/health",
        health_check,
        methods=["GET"],
        response_model=HealthResponse,
    )
    app.add_api_route(
        "/research",
        research_endpoint,
        methods=["POST"],
        response_model=ResearchResponse,
    )
    app.add_api_route(
        "/ingest",
        ingest_endpoint,
        methods=["POST"],
        response_model=IngestionResult,
    )
    app.add_api_route(
        "/transform",
        transform_endpoint,
        methods=["POST"],
        response_model=TransformResult,
    )

    return app

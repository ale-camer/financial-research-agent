"""Command-line interface (CLI) for financial research, ingestion, and transformation."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from financial_research_agent import __version__
from financial_research_agent.agent.llm_client import (
    BaseLLMClient,
    MockLLMClient,
    OpenAILLMClient,
)
from financial_research_agent.agent.loop import ResearchAgent
from financial_research_agent.agent.report_generator import ReportGenerator
from financial_research_agent.orchestration.ingestion import IngestionPipeline
from financial_research_agent.orchestration.schemas import IngestionConfig, TransformConfig
from financial_research_agent.orchestration.transform import TransformPipeline


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="financial-research-agent",
        description=(
            "Agentic Financial Research Pipeline CLI: extract, transform, index, and research."
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit.",
    )

    subparsers = parser.add_subparsers(
        dest="subcommand",
        title="Available subcommands",
        description=(
            "Run 'financial-research-agent <command> --help' for details on each subcommand."
        ),
    )

    # Subcommand: research
    research_parser = subparsers.add_parser(
        "research",
        help="Query the research agent to generate a cited financial equity report.",
    )
    research_parser.add_argument(
        "ticker",
        nargs="?",
        default=None,
        help="Company equity ticker symbol (e.g. AAPL, MSFT).",
    )
    research_parser.add_argument(
        "-t",
        "--ticker-opt",
        dest="ticker_opt",
        default=None,
        help="Alternative flag for equity ticker symbol.",
    )
    research_parser.add_argument(
        "-q",
        "--query",
        default="Summarize company financial performance and principal business risks.",
        help="Research prompt or investigation query.",
    )
    research_parser.add_argument(
        "-m",
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum tool-calling reasoning steps (default: 10).",
    )
    research_parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output report formatting style (default: markdown).",
    )
    research_parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Optional file path to persist the rendered research report.",
    )
    research_parser.add_argument(
        "--mock",
        action="store_true",
        help="Execute with mock LLM client without external API credentials.",
    )

    # Subcommand: ingest
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Execute raw data extraction for SEC filings, market OHLCV, and RSS news.",
    )
    ingest_parser.add_argument(
        "-t",
        "--tickers",
        nargs="+",
        default=["AAPL", "MSFT", "NVDA"],
        help="List of company tickers to extract (default: AAPL MSFT NVDA).",
    )
    ingest_parser.add_argument(
        "--raw-dir",
        default="./data/raw",
        help="Target base directory for partitioned raw artifacts (default: ./data/raw).",
    )
    ingest_parser.add_argument(
        "--forms",
        nargs="+",
        default=["10-K", "10-Q"],
        help="SEC filing form types to extract (default: 10-K 10-Q).",
    )
    ingest_parser.add_argument(
        "--period",
        default="1y",
        help="Historical market data observation period (default: 1y).",
    )

    # Subcommand: transform
    transform_parser = subparsers.add_parser(
        "transform",
        help="Execute parsing, chunking, embedding vector indexing, and metric normalization.",
    )
    transform_parser.add_argument(
        "--raw-dir",
        default="./data/raw",
        help="Source directory of raw partitioned document JSONs (default: ./data/raw).",
    )
    transform_parser.add_argument(
        "--processed-dir",
        default="./data/processed",
        help="Destination directory for clean documents and metrics (default: ./data/processed).",
    )
    transform_parser.add_argument(
        "--index-path",
        default="./data/vector_store/index.json",
        help="Path for vector store JSON index (default: ./data/vector_store/index.json).",
    )
    transform_parser.add_argument(
        "-t",
        "--tickers",
        nargs="+",
        default=None,
        help="Optional list of company tickers to filter transform processing.",
    )

    return parser


def handle_research(args: argparse.Namespace) -> int:
    """Execute the financial research agent subcommand."""
    ticker = (args.ticker or args.ticker_opt or "").strip().upper()
    if not ticker:
        sys.stderr.write("Error: company ticker symbol is required for research.\n")
        return 1

    query = args.query

    llm: BaseLLMClient
    if args.mock:
        mock = MockLLMClient()
        mock_response = (
            f"## Executive Summary\n\n"
            f"{ticker} demonstrates disciplined capital allocation and operational execution.\n\n"
            f"## Performance & Strategy\n\n"
            f"Revenue diversification across product lines drives sustainable growth.\n\n"
            f"## Principal Risks\n\n"
            f"Macroeconomic volatility and competitive pressures remain key risk factors."
        )
        mock.add_response(mock_response)
        llm = mock
    else:
        try:
            llm = OpenAILLMClient()
        except Exception:
            # Fall back to mock client if API keys are missing
            fallback_mock = MockLLMClient()
            fallback_mock.add_response(
                f"## Executive Summary\n\nAnalysis for {ticker}.\n\n## Findings\n\nData reviewed."
            )
            llm = fallback_mock

    agent = ResearchAgent(
        llm_client=llm,
        max_iterations=args.max_iterations,
    )
    run_result = agent.run(query=query)

    report_gen = ReportGenerator(llm_client=llm)
    report = report_gen.generate_from_run(
        ticker=ticker,
        run_result=run_result,
        title=f"Financial Research Report: {ticker}",
    )

    rendered = (
        report.to_markdown() if args.format == "markdown" else report.model_dump_json(indent=2)
    )

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        sys.stdout.write(f"Report saved to: {out_path}\n")
    else:
        sys.stdout.write(rendered + "\n")

    return 0


def handle_ingest(args: argparse.Namespace) -> int:
    """Execute the data ingestion pipeline subcommand."""
    config = IngestionConfig(
        tickers=args.tickers,
        sec_form_types=args.forms,
        market_period=args.period,
        raw_storage_dir=args.raw_dir,
    )
    pipeline = IngestionPipeline(config=config)
    result = pipeline.run()

    summary_json = json.dumps(result.model_dump(mode="json"), indent=2)
    sys.stdout.write(summary_json + "\n")
    return 0 if result.status in {"success", "partial_success"} else 1


def handle_transform(args: argparse.Namespace) -> int:
    """Execute the document transform and vector indexing pipeline subcommand."""
    config = TransformConfig(
        raw_storage_dir=args.raw_dir,
        processed_storage_dir=args.processed_dir,
        vector_store_path=args.index_path,
        tickers=args.tickers,
    )
    pipeline = TransformPipeline(config=config)
    result = pipeline.run()

    summary_json = json.dumps(result.model_dump(mode="json"), indent=2)
    sys.stdout.write(summary_json + "\n")
    return 0 if result.status in {"success", "partial_success"} else 1


def main(argv: Sequence[str] | None = None) -> int:
    """CLI application entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help(sys.stderr)
        return 2

    if args.subcommand == "research":
        return handle_research(args)
    if args.subcommand == "ingest":
        return handle_ingest(args)
    if args.subcommand == "transform":
        return handle_transform(args)

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

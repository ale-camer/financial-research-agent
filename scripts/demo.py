#!/usr/bin/env python3
"""End-to-end interactive demonstration script for the Financial Research Agent."""

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from financial_research_agent.agent.llm_client import BaseLLMClient, MockLLMClient, OpenAILLMClient
from financial_research_agent.agent.loop import ResearchAgent
from financial_research_agent.agent.market_data_tool import MarketDataTool
from financial_research_agent.agent.report_generator import ReportGenerator
from financial_research_agent.agent.retrieval_tool import RetrievalTool
from financial_research_agent.transform.embeddings import EmbeddingGenerator
from financial_research_agent.transform.schemas import EmbeddedChunk
from financial_research_agent.transform.vector_store import VectorStore


def setup_demo_vector_store(ticker: str) -> tuple[VectorStore, EmbeddingGenerator]:
    """Populate an in-memory vector store with realistic mock chunks for demonstration."""
    store = VectorStore()
    dim = 3

    def mock_embed_fn(texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]

    embedding_gen = EmbeddingGenerator(dimensions=dim, embed_fn=mock_embed_fn)

    sample_chunks = [
        EmbeddedChunk(
            chunk_id=f"{ticker}_sec_10q_rev",
            document_id=f"{ticker}_10Q_2024Q3",
            ticker=ticker,
            form_type="10-Q",
            section_id="item_2",
            chunk_index=0,
            content=(
                f"{ticker} Corporation reported total quarterly revenue of $94.9 billion for Q3, "
                "representing an increase of 6.1% year-over-year. Services revenue reached an "
                "all-time record high of $24.97 billion, up 12% compared to the prior year period."
            ),
            embedding=[1.0, 0.0, 0.0],
            embedding_model="demo-embedding-model",
            dimensions=dim,
            metadata={
                "ticker": ticker,
                "source": "SEC_EDGAR",
                "form": "10-Q",
                "period": "2024-Q3",
            },
        ),
        EmbeddedChunk(
            chunk_id=f"{ticker}_sec_10q_margin",
            document_id=f"{ticker}_10Q_2024Q3",
            ticker=ticker,
            form_type="10-Q",
            section_id="item_2",
            chunk_index=1,
            content=(
                f"Gross margin for {ticker} stood at 46.2%, supported by strong services mix. "
                "Net income reached $14.74 billion, diluted earnings per share (EPS) was $0.97. "
                "Operating cash flow was robust at $26.8 billion."
            ),
            embedding=[0.8, 0.6, 0.0],
            embedding_model="demo-embedding-model",
            dimensions=dim,
            metadata={
                "ticker": ticker,
                "source": "SEC_EDGAR",
                "form": "10-Q",
                "period": "2024-Q3",
            },
        ),
        EmbeddedChunk(
            chunk_id=f"{ticker}_news_ai",
            document_id=f"{ticker}_NEWS_01",
            ticker=ticker,
            form_type="NEWS",
            section_id="bulletin",
            chunk_index=0,
            content=(
                f"Market Bulletin: Analysts praise {ticker}'s strategic expansion in generative AI "
                "features and enterprise subscription services, projecting double-digit growth."
            ),
            embedding=[0.7, 0.7, 0.1],
            embedding_model="demo-embedding-model",
            dimensions=dim,
            metadata={
                "ticker": ticker,
                "source": "NEWS_RSS",
                "publisher": "Financial Times",
            },
        ),
    ]

    store.add(sample_chunks)
    return store, embedding_gen


def run_demo(
    ticker: str,
    query: str,
    mock: bool = True,
    output_path: Path | None = None,
) -> int:
    """Run the end-to-end research agent pipeline and print the structured report."""
    print("=" * 70)
    print("       FINANCIAL RESEARCH AGENT — END-TO-END DEMO")
    print("=" * 70)
    print(f"Ticker:     {ticker}")
    print(f"Query:      {query}")
    print(f"Mode:       {'Deterministic Mock Mode' if mock else 'Live Provider Mode'}")
    print(f"Timestamp:  {datetime.now(UTC).isoformat()}")
    print("-" * 70)

    # 1. Knowledge Base Initialization
    print("► [1/4] Initializing vector knowledge base and document chunks...")
    vector_store, embedding_gen = setup_demo_vector_store(ticker)
    retrieval_tool = RetrievalTool(
        vector_store=vector_store,
        embedding_generator=embedding_gen,
    )
    market_tool = MarketDataTool()
    print("  ✔ Vector store indexed with SEC 10-Q filings and market bulletins.")

    # 2. Agent Initialization
    print("► [2/4] Initializing autonomous research agent with domain tools...")
    llm_client: BaseLLMClient
    if mock:
        mock_llm = MockLLMClient()
        mock_llm.add_tool_call_response(
            tool_name="retrieve_filing_chunks",
            arguments={"query": "quarterly revenue gross margin", "top_k": 3},
            call_id="call_retrieval_1",
        )
        mock_llm.add_response(
            "## Executive Summary\n\n"
            f"{ticker} demonstrates resilient operational performance with record Services "
            "revenues and robust gross margin expansion.\n\n"
            "## Financial Performance & Margins\n\n"
            f"According to SEC filings, {ticker} delivered quarterly revenue of $94.9B "
            "(+6.1% YoY) with Services reaching $24.97B. Gross margins were 46.2% and "
            "net income totaled $14.74 billion ($0.97 EPS).\n\n"
            "## Market Perspective & Catalysts\n\n"
            "Analyst reports highlight steady subscription growth and software tailwinds.\n\n"
            "## Principal Risks\n\n"
            "Supply chain dependencies and competitive cycles remain key monitorables."
        )
        llm_client = mock_llm
    else:
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(
                "  ✖ ERROR: Live mode requires LLM_API_KEY or OPENAI_API_KEY in environment.",
                file=sys.stderr,
            )
            return 1
        llm_client = OpenAILLMClient(api_key=api_key)

    agent = ResearchAgent(
        llm_client=llm_client,
        tools=[retrieval_tool, market_tool],
        max_iterations=4,
    )
    print("  ✔ Agent loop configured with retrieval and market analytical tools.")

    # 3. Agent Execution
    print(f"► [3/4] Running autonomous research loop for '{ticker}'...")
    run_result = agent.run(query=query)
    num_steps = len(run_result.steps)
    print(
        f"  ✔ Agent completed research loop in {run_result.iterations} iterations "
        f"({num_steps} steps)."
    )

    # 4. Report Generation
    print("► [4/4] Compiling structured research report with citations...")
    retrieval_output = retrieval_tool.run(query=query, ticker=ticker)
    generator = ReportGenerator(llm_client=llm_client)
    report = generator.generate_from_run(
        ticker=ticker,
        run_result=run_result,
        title=f"Financial Research Report: {ticker}",
        citations=retrieval_output.citations,
    )

    markdown_report = report.to_markdown()

    print("\n" + "=" * 70)
    print("                   FINAL RESEARCH REPORT")
    print("=" * 70)
    print(markdown_report)
    print("=" * 70)
    print(f"Summary Metrics: {len(report.citations)} citations captured.")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_report, encoding="utf-8")
        print(f"✔ Report successfully written to: {output_path.resolve()}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and run demo."""
    parser = argparse.ArgumentParser(
        description="Run an end-to-end interactive demo of the Financial Research Agent pipeline."
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default="AAPL",
        help="Stock ticker symbol to research (default: AAPL)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="Summarize recent quarterly revenue, margins, and market performance.",
        help="Financial query to investigate",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=True,
        help="Run in offline deterministic mock mode (default: True)",
    )
    parser.add_argument(
        "--live",
        dest="mock",
        action="store_false",
        help="Run against real external LLM API provider",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional file path to save the generated markdown report",
    )

    args = parser.parse_args(argv)
    output_path = Path(args.output) if args.output else None

    return run_demo(
        ticker=args.ticker.upper(),
        query=args.query,
        mock=args.mock,
        output_path=output_path,
    )


if __name__ == "__main__":
    sys.exit(main())

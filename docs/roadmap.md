# Roadmap

Source of truth for which issue belongs to which milestone. The LAST issue of each milestone is the one that requires `make finish-milestone MILESTONE=MX`.

Issue 0 (Day 0 scaffolding) lives in a local-only milestone M0 and is not created on GitHub.

| Milestone | Issue | Title | Closes milestone |
|---|---|---|---|
| M0 - Day 0 Scaffolding | 0 | Day 0 scaffolding (local only) | no |
| M1 - Extraction | 1 | Raw document Pydantic schemas | no |
| M1 - Extraction | 2 | SEC EDGAR filings extractor | no |
| M1 - Extraction | 3 | Market data extractor (yfinance) | no |
| M1 - Extraction | 4 | News RSS extractor | no |
| M1 - Extraction | 5 | Raw storage writer and extractor fixtures tests | yes |
| M2 - Transformation | 6 | Filing parser and text cleaner | no |
| M2 - Transformation | 7 | Document chunker | no |
| M2 - Transformation | 8 | Embedding generator | no |
| M2 - Transformation | 9 | Vector store loader | no |
| M2 - Transformation | 10 | Financial metrics normalizer | yes |
| M3 - Research Agent | 11 | Retrieval tool | no |
| M3 - Research Agent | 12 | Market data tool | no |
| M3 - Research Agent | 13 | LLM client abstraction | no |
| M3 - Research Agent | 14 | Agent loop with tool calling | no |
| M3 - Research Agent | 15 | Structured report generator with citations | no |
| M3 - Research Agent | 16 | Agent evaluation harness | yes |
| M4 - Orchestration & Delivery | 17 | Ingestion DAG | no |
| M4 - Orchestration & Delivery | 18 | Transform and indexing DAG | no |
| M4 - Orchestration & Delivery | 19 | CLI and FastAPI endpoint | no |
| M4 - Orchestration & Delivery | 20 | Dockerfile and docker-compose | no |
| M4 - Orchestration & Delivery | 21 | GitHub Actions CI workflow | no |
| M4 - Orchestration & Delivery | 22 | Final documentation and demo | yes |

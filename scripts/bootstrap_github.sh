#!/usr/bin/env bash
# Bootstrap the GitHub repository: public repo, branches, milestones and ALL roadmap issues.
# Run once, by the user, BEFORE the first PR so that GitHub issue numbers match docs/roadmap.md.
set -euo pipefail

REPO_NAME="financial-research-agent"

command -v gh >/dev/null || { echo "ERROR: gh CLI is required" >&2; exit 1; }
gh auth status >/dev/null || { echo "ERROR: run 'gh auth login' first" >&2; exit 1; }

# 1. Repository and permanent branches.
if ! git remote get-url origin >/dev/null 2>&1; then
    gh repo create "$REPO_NAME" --public --source=. --remote=origin
fi
git push -u origin main
git push -u origin develop

# 2. Milestones.
MILESTONES=(
    "M1 - Extraction"
    "M2 - Transformation"
    "M3 - Research Agent"
    "M4 - Orchestration & Delivery"
)
for title in "${MILESTONES[@]}"; do
    gh api "repos/{owner}/{repo}/milestones" -f title="$title" >/dev/null
    echo "Milestone created: $title"
done

# 3. Issues, created in roadmap order so that issue number == roadmap id.
# Format: "milestone index (1-4)|title"
ISSUES=(
    "1|Raw document Pydantic schemas"
    "1|SEC EDGAR filings extractor"
    "1|Market data extractor (yfinance)"
    "1|News RSS extractor"
    "1|Raw storage writer and extractor fixtures tests"
    "2|Filing parser and text cleaner"
    "2|Document chunker"
    "2|Embedding generator"
    "2|Vector store loader"
    "2|Financial metrics normalizer"
    "3|Retrieval tool"
    "3|Market data tool"
    "3|LLM client abstraction"
    "3|Agent loop with tool calling"
    "3|Structured report generator with citations"
    "3|Agent evaluation harness"
    "4|Ingestion DAG"
    "4|Transform and indexing DAG"
    "4|CLI and FastAPI endpoint"
    "4|Dockerfile and docker-compose"
    "4|GitHub Actions CI workflow"
    "4|Final documentation and demo"
)
for entry in "${ISSUES[@]}"; do
    index="${entry%%|*}"
    title="${entry#*|}"
    milestone="${MILESTONES[$((index - 1))]}"
    gh issue create --title "$title" --milestone "$milestone" \
        --body "See docs/roadmap.md. Detailed plan: docs/issue_<id>_<name>.md (created in Phase A)."
done

echo "Bootstrap done: ${#MILESTONES[@]} milestones, ${#ISSUES[@]} issues."

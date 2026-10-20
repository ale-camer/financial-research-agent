#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"

echo "==> Starting Financial Research Agent API on port ${PORT}..."
exec uvicorn financial_research_agent.api.app:create_app --factory --host 0.0.0.0 --port "${PORT}"

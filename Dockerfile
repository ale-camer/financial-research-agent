FROM python:3.11-slim AS runtime

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/app/data

WORKDIR /app

# Install system dependencies (curl for health check)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy dependency configuration and source files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY dags/ ./dags/

# Install the package with all optional extras
RUN pip install --no-cache-dir ".[all]"

# Prepare data storage directory and establish permissions
RUN mkdir -p /app/data && \
    chown -R appuser:appgroup /app

# Switch to non-privileged user
USER appuser

# Expose HTTP API port
EXPOSE 8000

# Container health probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default execution: launch FastAPI REST service via Uvicorn
CMD ["uvicorn", "financial_research_agent.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

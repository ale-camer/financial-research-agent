# Infrastructure and Deployment

This directory contains containerization and deployment configurations for the Financial Research Agent.

## Docker Setup

The system provides a production-ready containerized environment via `Dockerfile` and `docker-compose.yml`.

### Build Image
```bash
docker build -t financial-research-agent:latest .
```

### Run API Service via Docker Compose
To start the FastAPI REST API service in detached mode:
```bash
docker compose up -d
```
The service will be accessible at:
- Health probe: `http://localhost:8000/health`
- Interactive OpenAPI documentation: `http://localhost:8000/docs`

### Run CLI Research via Docker Compose
To execute an ad-hoc research task using the containerized CLI without running a local Python server:
```bash
docker compose run --rm cli research --ticker AAPL --query "What were Apple's Q3 revenues?" --mock
```

To stop all services:
```bash
docker compose down
```

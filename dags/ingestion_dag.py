"""Airflow DAG definition for raw financial data ingestion."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from financial_research_agent.orchestration.ingestion import IngestionPipeline

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator

    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False

    class DummyDAG:
        """Fallback DAG stub when Apache Airflow is not installed in the environment."""

        _current_dag: "DummyDAG | None" = None

        def __init__(
            self,
            dag_id: str,
            description: str = "",
            schedule: Any = None,
            schedule_interval: Any = None,
            default_args: dict[str, Any] | None = None,
            start_date: datetime | None = None,
            catchup: bool = False,
            tags: list[str] | None = None,
            **kwargs: Any,
        ) -> None:
            self.dag_id = dag_id
            self.description = description
            self.schedule_interval = schedule or schedule_interval
            self.default_args = default_args or {}
            self.start_date = start_date
            self.catchup = catchup
            self.tags = tags or []
            self.tasks: list[Any] = []

        def __enter__(self) -> "DummyDAG":
            DummyDAG._current_dag = self
            return self

        def __exit__(self, *args: Any) -> None:
            DummyDAG._current_dag = None

    class DummyOperator:
        """Fallback Operator stub when Apache Airflow is not installed."""

        def __init__(
            self,
            task_id: str,
            python_callable: Callable[..., Any],
            dag: Any = None,
            **kwargs: Any,
        ) -> None:
            self.task_id = task_id
            self.python_callable = python_callable
            self.dag = dag or DummyDAG._current_dag
            self.upstream_list: list[Any] = []
            self.downstream_list: list[Any] = []
            if self.dag and hasattr(self.dag, "tasks"):
                self.dag.tasks.append(self)

        def __rshift__(self, other: Any) -> Any:
            self.downstream_list.append(other)
            if hasattr(other, "upstream_list"):
                other.upstream_list.append(self)
            return other

    DAG = DummyDAG  # type: ignore[misc,assignment]
    PythonOperator = DummyOperator  # type: ignore[misc,assignment]


def run_sec_ingestion(**kwargs: Any) -> dict[str, Any]:
    """Execute raw SEC EDGAR filings extraction task."""
    pipeline = IngestionPipeline()
    summary = pipeline.ingest_sec_filings()
    return summary.model_dump(mode="json")


def run_market_data_ingestion(**kwargs: Any) -> dict[str, Any]:
    """Execute historical market data series extraction task."""
    pipeline = IngestionPipeline()
    summary = pipeline.ingest_market_data()
    return summary.model_dump(mode="json")


def run_news_ingestion(**kwargs: Any) -> dict[str, Any]:
    """Execute financial news RSS feed extraction task."""
    pipeline = IngestionPipeline()
    summary = pipeline.ingest_news_rss()
    return summary.model_dump(mode="json")


default_args = {
    "owner": "financial_agent",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="financial_ingestion_dag",
    description="Ingests raw SEC filings, market OHLCV data, and RSS financial news.",
    default_args=default_args,
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    catchup=False,
    tags=["finance", "ingestion", "raw"],
) as financial_ingestion_dag:
    task_ingest_sec_filings = PythonOperator(
        task_id="task_ingest_sec_filings",
        python_callable=run_sec_ingestion,
    )

    task_ingest_market_data = PythonOperator(
        task_id="task_ingest_market_data",
        python_callable=run_market_data_ingestion,
    )

    task_ingest_news_rss = PythonOperator(
        task_id="task_ingest_news_rss",
        python_callable=run_news_ingestion,
    )

    # All three extraction streams execute independently in parallel

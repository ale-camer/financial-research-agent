"""Airflow DAG definition for data transformation and vector indexing."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from financial_research_agent.orchestration.transform import TransformPipeline

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


def run_parse_filings(**kwargs: Any) -> dict[str, Any]:
    """Execute raw SEC filings parsing and HTML cleanup task."""
    pipeline = TransformPipeline()
    summary = pipeline.parse_filings()
    return summary.model_dump(mode="json")


def run_chunk_and_index(**kwargs: Any) -> dict[str, Any]:
    """Execute document chunking, embedding generation, and vector index persistence."""
    pipeline = TransformPipeline()
    summary = pipeline.chunk_and_index()
    return summary.model_dump(mode="json")


def run_normalize_metrics(**kwargs: Any) -> dict[str, Any]:
    """Execute historical market data quantitative metrics normalization task."""
    pipeline = TransformPipeline()
    summary = pipeline.normalize_metrics()
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
    dag_id="financial_transform_dag",
    description=(
        "Transforms raw documents into clean parsed filings, vector index, and normalized metrics."
    ),
    default_args=default_args,
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    catchup=False,
    tags=["finance", "transform", "vector_store", "metrics"],
) as financial_transform_dag:
    task_parse_filings = PythonOperator(
        task_id="task_parse_filings",
        python_callable=run_parse_filings,
    )

    task_chunk_and_index = PythonOperator(
        task_id="task_chunk_and_index",
        python_callable=run_chunk_and_index,
    )

    task_normalize_metrics = PythonOperator(
        task_id="task_normalize_metrics",
        python_callable=run_normalize_metrics,
    )

    # Chunker/Indexer requires parsed filings to complete first
    task_parse_filings >> task_chunk_and_index

"""Transformation and indexing pipeline orchestrator.

Coordinates parsing, chunking, embedding, and normalization.
"""

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from financial_research_agent.extract.schemas import (
    DocumentType,
    RawMarketData,
    RawSECFiling,
)
from financial_research_agent.extract.storage import (
    RawStorageWriter,
    StorageError,
)
from financial_research_agent.orchestration.schemas import (
    TransformConfig,
    TransformResult,
    TransformTaskSummary,
)
from financial_research_agent.transform.chunker import (
    ChunkerError,
    DocumentChunker,
)
from financial_research_agent.transform.embeddings import (
    EmbeddingError,
    EmbeddingGenerator,
)
from financial_research_agent.transform.normalizer import (
    MetricsNormalizer,
    NormalizerError,
)
from financial_research_agent.transform.parser import (
    FilingParser,
    ParserError,
)
from financial_research_agent.transform.schemas import (
    CleanDocument,
    EmbeddedChunk,
)
from financial_research_agent.transform.vector_store import (
    VectorStore,
    VectorStoreError,
)


class TransformError(Exception):
    """Base exception for transform and indexing pipeline failures."""


class TransformPipeline:
    """Coordinates parsing of raw filings, chunking/indexing, and financial metric normalization."""

    def __init__(
        self,
        config: TransformConfig | None = None,
        parser: FilingParser | None = None,
        chunker: DocumentChunker | None = None,
        embedding_generator: EmbeddingGenerator | None = None,
        vector_store: VectorStore | None = None,
        normalizer: MetricsNormalizer | None = None,
        storage_reader: RawStorageWriter | None = None,
    ) -> None:
        self.config = config or TransformConfig()
        self.parser = parser or FilingParser()
        self.chunker = chunker or DocumentChunker(
            max_tokens=self.config.chunk_max_tokens,
            overlap_tokens=self.config.chunk_overlap_tokens,
        )
        self.embedding_generator = embedding_generator or EmbeddingGenerator(
            dimensions=self.config.embedding_dimensions
        )
        self.vector_store = vector_store or VectorStore(storage_path=self.config.vector_store_path)
        self.normalizer = normalizer or MetricsNormalizer()
        self.storage_reader = storage_reader or RawStorageWriter(
            base_dir=self.config.raw_storage_dir
        )

    def parse_filings(
        self,
        raw_dir: Path | str | None = None,
        tickers: list[str] | None = None,
    ) -> TransformTaskSummary:
        """Parse and clean raw SEC filings found in storage into CleanDocument artifacts."""
        search_dir = Path(raw_dir or self.config.raw_storage_dir).resolve()
        active_tickers = tickers if tickers is not None else self.config.tickers
        target_tickers = {t.upper() for t in active_tickers} if active_tickers else None

        output_paths: list[str] = []
        errors: list[str] = []
        processed_count = 0
        produced_count = 0

        parsed_out_dir = Path(self.config.processed_storage_dir).resolve() / "parsed"
        try:
            parsed_out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            errors.append(f"Failed to create output directory '{parsed_out_dir}': {exc}")
            return TransformTaskSummary(
                task_name="parse_filings",
                items_processed=0,
                items_produced=0,
                output_paths=[],
                errors=errors,
            )

        # Look in sec_filing partition or recursively across raw dir
        candidate_paths = (
            list((search_dir / DocumentType.SEC_FILING.value).glob("**/*.json"))
            if (search_dir / DocumentType.SEC_FILING.value).is_dir()
            else list(search_dir.glob("**/*.json"))
        )

        for file_path in candidate_paths:
            try:
                raw_doc = self.storage_reader.read(file_path)
                if raw_doc.document_type != DocumentType.SEC_FILING:
                    continue
                if not isinstance(raw_doc.payload, RawSECFiling):
                    continue

                if target_tickers and raw_doc.payload.ticker.upper() not in target_tickers:
                    continue

                processed_count += 1
                clean_doc = self.parser.parse_filing(raw_doc.payload)

                target_file = parsed_out_dir / f"{clean_doc.document_id}.json"
                if target_file.exists() and not self.config.overwrite:
                    output_paths.append(str(target_file))
                    produced_count += 1
                    continue

                temp_path = target_file.with_suffix(f".tmp.{os.getpid()}")
                temp_path.write_text(clean_doc.model_dump_json(indent=2), encoding="utf-8")
                os.replace(temp_path, target_file)

                output_paths.append(str(target_file))
                produced_count += 1
            except (ParserError, StorageError, Exception) as exc:
                errors.append(f"Failed parsing filing '{file_path.name}': {exc}")

        return TransformTaskSummary(
            task_name="parse_filings",
            items_processed=processed_count,
            items_produced=produced_count,
            output_paths=output_paths,
            errors=errors,
        )

    def chunk_and_index(
        self,
        parsed_docs: list[CleanDocument] | None = None,
    ) -> TransformTaskSummary:
        """Chunk CleanDocuments, generate vector embeddings, and load into VectorStore."""
        output_paths: list[str] = []
        errors: list[str] = []
        processed_docs_count = 0
        produced_chunks_count = 0

        docs_to_index: list[CleanDocument] = []
        if parsed_docs is not None:
            docs_to_index = parsed_docs
        else:
            parsed_dir = Path(self.config.processed_storage_dir).resolve() / "parsed"
            if parsed_dir.is_dir():
                for doc_file in parsed_dir.glob("*.json"):
                    try:
                        content = doc_file.read_text(encoding="utf-8")
                        clean_doc = CleanDocument.model_validate_json(content)
                        docs_to_index.append(clean_doc)
                    except Exception as exc:
                        errors.append(f"Failed reading parsed document '{doc_file.name}': {exc}")

        all_embedded_chunks: list[EmbeddedChunk] = []
        for doc in docs_to_index:
            try:
                processed_docs_count += 1
                chunks = self.chunker.chunk_document(doc)
                if not chunks:
                    continue
                embedded = self.embedding_generator.embed_chunks(chunks)
                all_embedded_chunks.extend(embedded)
                produced_chunks_count += len(embedded)
            except (ChunkerError, EmbeddingError, Exception) as exc:
                errors.append(f"Failed chunking/embedding document '{doc.document_id}': {exc}")

        if all_embedded_chunks:
            try:
                self.vector_store.add(all_embedded_chunks)
                saved_index_path = self.vector_store.save()
                output_paths.append(str(saved_index_path))
            except (VectorStoreError, Exception) as exc:
                errors.append(f"Failed indexing chunks into vector store: {exc}")

        return TransformTaskSummary(
            task_name="chunk_and_index",
            items_processed=processed_docs_count,
            items_produced=produced_chunks_count,
            output_paths=output_paths,
            errors=errors,
        )

    def normalize_metrics(
        self,
        raw_dir: Path | str | None = None,
        tickers: list[str] | None = None,
    ) -> TransformTaskSummary:
        """Normalize raw market data records into quantitative financial return/risk metrics."""
        search_dir = Path(raw_dir or self.config.raw_storage_dir).resolve()
        active_tickers = tickers if tickers is not None else self.config.tickers
        target_tickers = {t.upper() for t in active_tickers} if active_tickers else None

        output_paths: list[str] = []
        errors: list[str] = []
        processed_count = 0
        produced_count = 0

        metrics_out_dir = Path(self.config.processed_storage_dir).resolve() / "metrics"
        try:
            metrics_out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            errors.append(f"Failed to create output directory '{metrics_out_dir}': {exc}")
            return TransformTaskSummary(
                task_name="normalize_metrics",
                items_processed=0,
                items_produced=0,
                output_paths=[],
                errors=errors,
            )

        candidate_paths = (
            list((search_dir / DocumentType.MARKET_DATA.value).glob("**/*.json"))
            if (search_dir / DocumentType.MARKET_DATA.value).is_dir()
            else list(search_dir.glob("**/*.json"))
        )

        for file_path in candidate_paths:
            try:
                raw_doc = self.storage_reader.read(file_path)
                if raw_doc.document_type != DocumentType.MARKET_DATA:
                    continue
                if not isinstance(raw_doc.payload, RawMarketData):
                    continue

                if target_tickers and raw_doc.payload.ticker.upper() not in target_tickers:
                    continue

                processed_count += 1
                metrics = self.normalizer.compute_market_metrics(raw_doc.payload)

                clean_ticker = metrics.ticker.upper()
                start_s = raw_doc.payload.start_date.strftime("%Y%m%d")
                end_s = raw_doc.payload.end_date.strftime("%Y%m%d")
                target_filename = (
                    f"metrics_{clean_ticker}_{raw_doc.payload.interval}_{start_s}_{end_s}.json"
                )
                target_file = metrics_out_dir / target_filename

                if target_file.exists() and not self.config.overwrite:
                    output_paths.append(str(target_file))
                    produced_count += 1
                    continue

                temp_path = target_file.with_suffix(f".tmp.{os.getpid()}")
                temp_path.write_text(metrics.model_dump_json(indent=2), encoding="utf-8")
                os.replace(temp_path, target_file)

                output_paths.append(str(target_file))
                produced_count += 1
            except (NormalizerError, StorageError, Exception) as exc:
                errors.append(f"Failed normalizing market data '{file_path.name}': {exc}")

        return TransformTaskSummary(
            task_name="normalize_metrics",
            items_processed=processed_count,
            items_produced=produced_count,
            output_paths=output_paths,
            errors=errors,
        )

    def run(self, config: TransformConfig | None = None) -> TransformResult:
        """Execute the full transformation and indexing pipeline in order."""
        if config is not None:
            self.config = config
            self.storage_reader = RawStorageWriter(base_dir=self.config.raw_storage_dir)
            self.chunker = DocumentChunker(
                max_tokens=self.config.chunk_max_tokens,
                overlap_tokens=self.config.chunk_overlap_tokens,
            )
            self.embedding_generator = EmbeddingGenerator(
                dimensions=self.config.embedding_dimensions
            )
            self.vector_store = VectorStore(storage_path=self.config.vector_store_path)

        run_id = f"transform_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(UTC)

        # 1. Parse SEC filings
        parse_summary = self.parse_filings()

        # 2. Chunk and index into vector store
        index_summary = self.chunk_and_index()

        # 3. Normalize market series metrics
        metrics_summary = self.normalize_metrics()

        completed_at = datetime.now(UTC)
        duration_seconds = max((completed_at - started_at).total_seconds(), 0.0)

        all_summaries = [parse_summary, index_summary, metrics_summary]
        all_errors = [err for s in all_summaries for err in s.errors]

        total_outputs = (
            parse_summary.items_produced
            + index_summary.items_produced
            + metrics_summary.items_produced
        )

        if not all_errors:
            status = "success"
        elif total_outputs > 0:
            status = "partial_success"
        else:
            status = "failed"

        return TransformResult(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            documents_parsed=parse_summary.items_produced,
            chunks_created=index_summary.items_produced,
            chunks_indexed=index_summary.items_produced,
            metrics_normalized=metrics_summary.items_produced,
            task_summaries=all_summaries,
            status=status,
        )

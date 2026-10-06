"""In-memory and file-backed vector store for document chunk search."""

import json
import math
import os
from pathlib import Path

from financial_research_agent.transform.schemas import EmbeddedChunk, SearchResult


class VectorStoreError(Exception):
    """Base exception for vector store operations."""


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute the cosine similarity between two float vectors."""
    if len(v1) != len(v2):
        raise VectorStoreError(
            f"Vector dimension mismatch: vector1 has {len(v1)}, vector2 has {len(v2)}"
        )

    dot = sum(a * b for a, b in zip(v1, v2, strict=True))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class VectorStore:
    """In-memory vector index supporting upsert, cosine search, and file persistence."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path).resolve() if storage_path else None
        self._chunks: dict[str, EmbeddedChunk] = {}

        if self.storage_path and self.storage_path.is_file():
            self.load(self.storage_path)

    def count(self) -> int:
        """Return the total number of indexed chunks."""
        return len(self._chunks)

    def clear(self) -> None:
        """Clear all stored vectors and chunks."""
        self._chunks.clear()

    def get(self, chunk_id: str) -> EmbeddedChunk | None:
        """Retrieve a single chunk by chunk_id."""
        return self._chunks.get(chunk_id)

    def add(self, chunks: list[EmbeddedChunk]) -> int:
        """Upsert a list of EmbeddedChunk records into the index."""
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
        return len(self._chunks)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        ticker: str | None = None,
        form_type: str | None = None,
        section_id: str | None = None,
    ) -> list[SearchResult]:
        """Search the store by cosine similarity with optional metadata filters."""
        if top_k <= 0:
            raise VectorStoreError(f"top_k must be positive, got {top_k}")

        if not self._chunks:
            return []

        results: list[SearchResult] = []
        for chunk in self._chunks.values():
            if ticker is not None and chunk.ticker.upper() != ticker.upper():
                continue
            if form_type is not None and chunk.form_type.upper() != form_type.upper():
                continue
            if section_id is not None and chunk.section_id != section_id:
                continue

            sim = cosine_similarity(query_vector, chunk.embedding)
            results.append(SearchResult(chunk=chunk, score=round(sim, 6)))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def save(self, path: str | Path | None = None) -> Path:
        """Persist the current vector index to a JSON file atomically."""
        target = Path(path).resolve() if path else self.storage_path
        if not target:
            raise VectorStoreError("No storage path provided to save vector store.")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp_file = target.with_suffix(f".tmp.{os.getpid()}")
            raw_data = [chunk.model_dump(mode="json") for chunk in self._chunks.values()]
            temp_file.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")
            os.replace(temp_file, target)
        except OSError as exc:
            raise VectorStoreError(f"Failed to save vector store to '{target}': {exc}") from exc

        return target

    def load(self, path: str | Path) -> int:
        """Load chunks from a JSON file into the store."""
        target = Path(path).resolve()
        if not target.is_file():
            raise VectorStoreError(f"Vector store file '{target}' does not exist.")

        try:
            content = target.read_text(encoding="utf-8")
            raw_data = json.loads(content)
            for item in raw_data:
                chunk = EmbeddedChunk.model_validate(item)
                self._chunks[chunk.chunk_id] = chunk
        except Exception as exc:
            raise VectorStoreError(f"Failed to load vector store from '{target}': {exc}") from exc

        return len(self._chunks)

"""Embedding generator client for document chunks."""

import os
from collections.abc import Callable
from typing import Any

from openai import OpenAI

from financial_research_agent.transform.schemas import DocumentChunk, EmbeddedChunk


class EmbeddingError(Exception):
    """Base exception for embedding generation failures."""


class EmbeddingGenerator:
    """Generates dense vector representations for text batches and DocumentChunks."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        client: Any | None = None,
        embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
        batch_size: int = 64,
    ) -> None:
        if batch_size <= 0:
            raise EmbeddingError(f"batch_size must be positive, got {batch_size}")
        if dimensions <= 0:
            raise EmbeddingError(f"dimensions must be positive, got {dimensions}")

        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self._embed_fn = embed_fn

        if embed_fn is None:
            if client is not None:
                self._client = client
            else:
                key = api_key or os.getenv("LLM_API_KEY", "mock-key")
                self._client = OpenAI(api_key=key)
        else:
            self._client = None

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for an arbitrary list of text strings in batches."""
        if not texts:
            return []

        all_vectors: list[list[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]

            if self._embed_fn is not None:
                try:
                    vectors = self._embed_fn(batch)
                except Exception as exc:
                    raise EmbeddingError(f"Custom embed_fn failed on batch: {exc}") from exc
            else:
                try:
                    response = self._client.embeddings.create(input=batch, model=self.model)
                    vectors = [item.embedding for item in response.data]
                except Exception as exc:
                    raise EmbeddingError(f"API call to embedding model failed: {exc}") from exc

            if len(vectors) != len(batch):
                raise EmbeddingError(
                    f"Vector count mismatch: sent {len(batch)} inputs, received {len(vectors)}"
                )

            for vec in vectors:
                if len(vec) != self.dimensions:
                    raise EmbeddingError(
                        f"Vector dimension mismatch: expected {self.dimensions}, got {len(vec)}"
                    )
                all_vectors.append(vec)

        return all_vectors

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[EmbeddedChunk]:
        """Convert DocumentChunk objects into vector-enriched EmbeddedChunk models."""
        if not chunks:
            return []

        texts = [c.content for c in chunks]
        vectors = self.generate_embeddings(texts)

        embedded_chunks: list[EmbeddedChunk] = []
        for chunk, vec in zip(chunks, vectors, strict=True):
            embedded = EmbeddedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                ticker=chunk.ticker,
                form_type=chunk.form_type,
                section_id=chunk.section_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=vec,
                embedding_model=self.model,
                dimensions=self.dimensions,
                metadata=dict(chunk.metadata),
            )
            embedded_chunks.append(embedded)

        return embedded_chunks

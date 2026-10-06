"""Token-aware recursive text chunker for financial research documents."""

from typing import Any

import tiktoken

from financial_research_agent.transform.schemas import CleanDocument, DocumentChunk


class ChunkerError(Exception):
    """Base exception for document chunking errors."""


def create_offline_byte_encoder(name: str = "offline_fallback") -> tiktoken.Encoding:
    """Create a self-contained offline tiktoken.Encoding requiring no remote downloads."""
    ranks = {bytes([i]): i for i in range(256)}
    return tiktoken.Encoding(
        name=name,
        pat_str=r".",
        mergeable_ranks=ranks,
        special_tokens={},
    )


class DocumentChunker:
    """Partitions CleanDocument instances into token-bounded overlapping chunks."""

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 64,
        encoding_name: str = "cl100k_base",
        tokenizer: Any | None = None,
    ) -> None:
        if max_tokens <= 0:
            raise ChunkerError(f"max_tokens must be positive, got {max_tokens}")
        if overlap_tokens < 0:
            raise ChunkerError(f"overlap_tokens cannot be negative, got {overlap_tokens}")
        if overlap_tokens >= max_tokens:
            raise ChunkerError(
                f"overlap_tokens ({overlap_tokens}) must be strictly less than "
                f"max_tokens ({max_tokens})"
            )

        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding_name = encoding_name

        if tokenizer is not None:
            self._encoder = tokenizer
        else:
            try:
                self._encoder = tiktoken.get_encoding(encoding_name)
            except Exception:
                # Fallback to local byte-level encoder for offline/sandboxed execution
                self._encoder = create_offline_byte_encoder(f"fallback_{encoding_name}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using the configured tokenizer."""
        return len(self._encoder.encode(text))

    def chunk_text(self, text: str) -> list[str]:
        """Split a text block into token-bounded chunks respecting the overlap window."""
        stripped = text.strip()
        if not stripped:
            return []

        tokens = self._encoder.encode(stripped)
        if len(tokens) <= self.max_tokens:
            return [stripped]

        stride = self.max_tokens - self.overlap_tokens
        chunks: list[str] = []
        start_idx = 0

        while start_idx < len(tokens):
            end_idx = min(start_idx + self.max_tokens, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            decoded = self._encoder.decode(chunk_tokens).strip()
            if decoded:
                chunks.append(decoded)

            if end_idx == len(tokens):
                break
            start_idx += stride

        return chunks

    def chunk_document(self, document: CleanDocument) -> list[DocumentChunk]:
        """Chunk a CleanDocument, preserving section hierarchy when sections are present."""
        if not document.clean_text.strip() and not document.sections:
            raise ChunkerError(f"Document '{document.document_id}' contains no text to chunk.")

        chunks: list[DocumentChunk] = []
        chunk_idx = 0

        if document.sections:
            for sec in document.sections:
                text_pieces = self.chunk_text(sec.content)
                for piece in text_pieces:
                    meta = {
                        "section_title": sec.title,
                        "section_id": sec.section_id,
                        **document.metadata,
                    }
                    chunk = DocumentChunk(
                        chunk_id=f"{document.document_id}_{chunk_idx:04d}",
                        document_id=document.document_id,
                        ticker=document.ticker,
                        form_type=document.form_type,
                        section_id=sec.section_id,
                        chunk_index=chunk_idx,
                        token_count=self.count_tokens(piece),
                        content=piece,
                        metadata=meta,
                    )
                    chunks.append(chunk)
                    chunk_idx += 1
            return chunks

        # Fallback when no structured sections exist
        text_pieces = self.chunk_text(document.clean_text)
        for piece in text_pieces:
            chunk = DocumentChunk(
                chunk_id=f"{document.document_id}_{chunk_idx:04d}",
                document_id=document.document_id,
                ticker=document.ticker,
                form_type=document.form_type,
                section_id=None,
                chunk_index=chunk_idx,
                token_count=self.count_tokens(piece),
                content=piece,
                metadata=dict(document.metadata),
            )
            chunks.append(chunk)
            chunk_idx += 1

        return chunks

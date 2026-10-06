"""Storage writer for persisting and loading raw document artifacts."""

import os
from pathlib import Path

from financial_research_agent.extract.schemas import RawDocument


class StorageError(Exception):
    """Base exception for raw storage operations."""


class RawStorageWriter:
    """Persists RawDocument artifacts to disk partitioned by type and extraction date."""

    def __init__(self, base_dir: str | Path = "./data/raw") -> None:
        self.base_dir = Path(base_dir).resolve()

    def resolve_path(self, document: RawDocument) -> Path:
        """Compute the partitioned storage path for a raw document."""
        dt = document.metadata.extracted_at
        year_str = f"{dt.year:04d}"
        month_str = f"{dt.month:02d}"
        clean_id = document.document_id.replace("/", "_").replace("\\", "_")
        filename = f"{clean_id}.json"

        return self.base_dir / document.document_type.value / year_str / month_str / filename

    def write(self, document: RawDocument, overwrite: bool = True) -> Path:
        """Write a RawDocument atomically to its partitioned location."""
        target_path = self.resolve_path(document)
        target_dir = target_path.parent

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(f"Failed to create storage directory '{target_dir}': {exc}") from exc

        if target_path.exists() and not overwrite:
            raise StorageError(
                f"File '{target_path}' already exists and overwrite is set to False."
            )

        temp_path = target_path.with_suffix(f".tmp.{os.getpid()}")
        try:
            json_data = document.model_dump_json(indent=2)
            temp_path.write_text(json_data, encoding="utf-8")
            os.replace(temp_path, target_path)
        except OSError as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise StorageError(f"Failed writing raw document to '{target_path}': {exc}") from exc

        return target_path

    def read(self, file_path: str | Path) -> RawDocument:
        """Load and validate a RawDocument from a JSON file path."""
        path = Path(file_path).resolve()
        if not path.is_file():
            raise StorageError(f"File '{path}' does not exist or is not a file.")

        try:
            content = path.read_text(encoding="utf-8")
            return RawDocument.model_validate_json(content)
        except Exception as exc:
            raise StorageError(
                f"Failed to read or validate raw document from '{path}': {exc}"
            ) from exc

    def exists(self, document: RawDocument) -> bool:
        """Check whether a document artifact already exists on disk."""
        return self.resolve_path(document).is_file()

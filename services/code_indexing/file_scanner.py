"""Repository file scanning utilities."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from loguru import logger

LANGUAGE_EXTENSIONS: Dict[str, set[str]] = {
    "python": {".py"},
    "typescript": {".ts", ".tsx"},
    "javascript": {".js", ".jsx"},
    "go": {".go"},
}


@dataclass
class ScannedFile:
    """Metadata describing a scanned file."""

    absolute_path: Path
    relative_path: Path
    language: str
    size_bytes: int


@dataclass
class FileScanResult:
    """Aggregated information about scanned files."""

    files: List[ScannedFile] = field(default_factory=list)
    skipped: int = 0
    errors: List[dict] = field(default_factory=list)
    language_breakdown: Dict[str, int] = field(default_factory=dict)


class FileScanner:
    """Scan repository files based on include/exclude rules."""

    def __init__(
        self,
        include_patterns: Optional[Iterable[str]] = None,
        exclude_patterns: Optional[Iterable[str]] = None,
        *,
        max_file_size_kb: int = 500,
    ) -> None:
        self.include_patterns = list(include_patterns or [])
        self.exclude_patterns = list(exclude_patterns or [])
        self.max_file_size_bytes = max_file_size_kb * 1024

    def scan(self, root: Path) -> FileScanResult:
        result = FileScanResult()
        root = Path(root)

        if not root.exists():
            raise FileNotFoundError(f"Repository path does not exist: {root}")

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            relative_path = path.relative_to(root)

            if self._should_skip(relative_path):
                result.skipped += 1
                continue

            try:
                size_bytes = path.stat().st_size
            except OSError as exc:  # pragma: no cover - filesystem edge case
                logger.warning("Failed to stat %s: %s", path, exc)
                result.errors.append({"file": str(relative_path), "error": str(exc)})
                continue

            if size_bytes > self.max_file_size_bytes:
                result.skipped += 1
                continue

            language = self._detect_language(path)
            if not language:
                result.skipped += 1
                continue

            scanned = ScannedFile(
                absolute_path=path,
                relative_path=relative_path,
                language=language,
                size_bytes=size_bytes,
            )
            result.files.append(scanned)
            result.language_breakdown[language] = result.language_breakdown.get(language, 0) + 1

        logger.info(
            "Scanned repository at %s: %s files included, %s skipped",
            root,
            len(result.files),
            result.skipped,
        )
        return result

    def _should_skip(self, relative_path: Path) -> bool:
        posix_path = relative_path.as_posix()

        # Skip hidden directories like .git by default
        if any(part.startswith(".") for part in relative_path.parts if part != "."):
            return True

        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(posix_path, pattern):
                return True

        if not self.include_patterns:
            return False

        return not any(fnmatch.fnmatch(posix_path, pattern) for pattern in self.include_patterns)

    @staticmethod
    def _detect_language(path: Path) -> Optional[str]:
        extension = path.suffix.lower()
        for language, extensions in LANGUAGE_EXTENSIONS.items():
            if extension in extensions:
                return language
        return None


__all__ = ["FileScanner", "FileScanResult", "ScannedFile", "LANGUAGE_EXTENSIONS"]

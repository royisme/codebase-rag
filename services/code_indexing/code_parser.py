"""Parsing helpers for extracting structural information from code files."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from loguru import logger

from .file_scanner import ScannedFile


@dataclass
class ParsedFunction:
    """A function or method extracted from source code."""

    name: str
    language: str
    file_path: Path
    start_line: int
    end_line: int


@dataclass
class ParsedImport:
    """An import statement extracted from source code."""

    module: str
    file_path: Path
    language: str


@dataclass
class ParsedFile:
    """Parsing result for a single file."""

    file: ScannedFile
    functions: List[ParsedFunction] = field(default_factory=list)
    imports: List[ParsedImport] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)


@dataclass
class ParseSummary:
    """Aggregate parsing statistics."""

    files_parsed: int = 0
    functions_extracted: int = 0
    imports_extracted: int = 0
    classes_extracted: int = 0


class CodeParser:
    """Parse scanned files and extract semantic signals."""

    def parse(self, files: Iterable[ScannedFile]) -> tuple[List[ParsedFile], List[dict], ParseSummary]:
        parsed_files: List[ParsedFile] = []
        errors: List[dict] = []
        summary = ParseSummary()

        for scanned in files:
            try:
                content = scanned.absolute_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                logger.warning("Failed to decode file as UTF-8: %s", scanned.relative_path)
                errors.append(
                    {
                        "file": scanned.relative_path.as_posix(),
                        "error": "Unicode decode error",
                    }
                )
                continue
            except OSError as exc:  # pragma: no cover - filesystem issues
                logger.warning("Failed to read file %s: %s", scanned.relative_path, exc)
                errors.append(
                    {
                        "file": scanned.relative_path.as_posix(),
                        "error": str(exc),
                    }
                )
                continue

            if scanned.language == "python":
                parsed = self._parse_python(scanned, content, errors)
            elif scanned.language in {"javascript", "typescript"}:
                parsed = self._parse_javascript(scanned, content)
            elif scanned.language == "go":
                parsed = self._parse_go(scanned, content)
            else:
                logger.debug("Skipping unsupported language for parsing: %s", scanned.language)
                continue

            parsed_files.append(parsed)
            summary.files_parsed += 1
            summary.functions_extracted += len(parsed.functions)
            summary.imports_extracted += len(parsed.imports)
            summary.classes_extracted += len(parsed.classes)

        return parsed_files, errors, summary

    def _parse_python(
        self,
        scanned: ScannedFile,
        content: str,
        errors: List[dict],
    ) -> ParsedFile:
        parsed_file = ParsedFile(file=scanned)

        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            logger.warning("Python syntax error in %s: %s", scanned.relative_path, exc)
            errors.append(
                {
                    "file": scanned.relative_path.as_posix(),
                    "error": f"Syntax error: {exc}",
                }
            )
            return parsed_file

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parsed_file.functions.append(
                    ParsedFunction(
                        name=node.name,
                        language="python",
                        file_path=scanned.relative_path,
                        start_line=getattr(node, "lineno", 0),
                        end_line=getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                    )
                )
            elif isinstance(node, ast.ClassDef):
                parsed_file.classes.append(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", None)
                if module:
                    parsed_file.imports.append(
                        ParsedImport(
                            module=module,
                            file_path=scanned.relative_path,
                            language="python",
                        )
                    )
                else:
                    names = [alias.name for alias in getattr(node, "names", [])]
                    for name in names:
                        parsed_file.imports.append(
                            ParsedImport(
                                module=name,
                                file_path=scanned.relative_path,
                                language="python",
                            )
                        )

        return parsed_file

    def _parse_javascript(self, scanned: ScannedFile, content: str) -> ParsedFile:
        parsed_file = ParsedFile(file=scanned)

        function_pattern = re.compile(r'function\s+(?P<name>[A-Za-z0-9_]+)\s*\(')
        arrow_pattern = re.compile(r'(?P<name>[A-Za-z0-9_]+)\s*=\s*\([^)]*\)\s*=>')
        class_pattern = re.compile(r'class\s+(?P<name>[A-Za-z0-9_]+)')
        import_pattern = re.compile(r"import\s+(?:.+?\s+from\s+)?['\"](?P<module>[^'\"]+)['\"]")

        for match in function_pattern.finditer(content):
            parsed_file.functions.append(
                ParsedFunction(
                    name=match.group("name"),
                    language=scanned.language,
                    file_path=scanned.relative_path,
                    start_line=_estimate_line(content, match.start()),
                    end_line=_estimate_line(content, match.end()),
                )
            )

        for match in arrow_pattern.finditer(content):
            parsed_file.functions.append(
                ParsedFunction(
                    name=match.group("name"),
                    language=scanned.language,
                    file_path=scanned.relative_path,
                    start_line=_estimate_line(content, match.start()),
                    end_line=_estimate_line(content, match.end()),
                )
            )

        for match in class_pattern.finditer(content):
            parsed_file.classes.append(match.group("name"))

        for match in import_pattern.finditer(content):
            parsed_file.imports.append(
                ParsedImport(
                    module=match.group("module"),
                    file_path=scanned.relative_path,
                    language=scanned.language,
                )
            )

        return parsed_file

    def _parse_go(self, scanned: ScannedFile, content: str) -> ParsedFile:
        parsed_file = ParsedFile(file=scanned)

        function_pattern = re.compile(r'func\s+(?:\([^)]*\)\s*)?(?P<name>[A-Za-z0-9_]+)\s*\(')
        import_block_pattern = re.compile(r'import\s+(?:\(\s*(?P<block>[^\)]+)\)|\s*"(?P<single>[^"]+)")')

        for match in function_pattern.finditer(content):
            parsed_file.functions.append(
                ParsedFunction(
                    name=match.group("name"),
                    language="go",
                    file_path=scanned.relative_path,
                    start_line=_estimate_line(content, match.start()),
                    end_line=_estimate_line(content, match.end()),
                )
            )

        for match in import_block_pattern.finditer(content):
            block = match.group("block")
            if block:
                modules = re.findall(r'"([^"]+)"', block)
            else:
                modules = [match.group("single")] if match.group("single") else []

            for module in modules:
                parsed_file.imports.append(
                    ParsedImport(
                        module=module,
                        file_path=scanned.relative_path,
                        language="go",
                    )
                )

        return parsed_file


def _estimate_line(content: str, position: int) -> int:
    """Estimate the line number for a position in ``content``."""

    return content.count("\n", 0, position) + 1


__all__ = [
    "CodeParser",
    "ParsedFile",
    "ParsedFunction",
    "ParsedImport",
    "ParseSummary",
]

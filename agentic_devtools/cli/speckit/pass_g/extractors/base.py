"""Abstract base class for language-specific symbol extractors (FR-002)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..models import ReferenceKind


@dataclass
class SymbolEntry:
    """A symbol discovered in the repository."""

    name: str
    qualified_name: str
    kind: ReferenceKind
    file_path: str
    line_number: int = 0


class SymbolExtractor(ABC):
    """Abstract base for pluggable language extractors."""

    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """Return file extensions handled by this extractor (e.g. {'.py'})."""

    @abstractmethod
    def extract_symbols(self, file_path: Path, content: str) -> list[SymbolEntry]:
        """Extract symbols from *content* of *file_path*."""

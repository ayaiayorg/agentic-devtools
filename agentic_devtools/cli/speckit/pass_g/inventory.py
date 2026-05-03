"""Repository symbol and file inventory builder (FR-002, FR-007, FR-011)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .constants import PROTECTED_FILE_PATTERNS
from .extractors.base import SymbolEntry
from .extractors.python_extractor import PythonExtractor


class SymbolInventory:
    """Indexed collection of repository files and symbols."""

    def __init__(
        self,
        file_paths: list[str],
        symbols: list[SymbolEntry],
    ) -> None:
        self._file_paths = sorted(file_paths)
        self._symbols = sorted(symbols, key=lambda s: (s.name, s.file_path, s.kind.value))
        self._file_set: set[str] = set(file_paths)
        self._symbol_by_name: dict[str, list[SymbolEntry]] = {}
        for sym in self._symbols:
            self._symbol_by_name.setdefault(sym.name, []).append(sym)
            if sym.qualified_name != sym.name:
                self._symbol_by_name.setdefault(sym.qualified_name, []).append(sym)

    def has_file(self, path: str) -> bool:
        """Check if *path* exists in the inventory."""
        normalized = path.lstrip("/")
        return normalized in self._file_set or path in self._file_set

    def find_files(self, pattern: str) -> list[str]:
        """Return file paths matching a glob-style *pattern*."""
        from fnmatch import fnmatch

        return [p for p in self._file_paths if fnmatch(p, pattern)]

    def get_symbols_by_name(self, name: str) -> list[SymbolEntry]:
        """Return symbols matching *name* (exact, case-sensitive).

        Both simple names (e.g., ``my_func``) and qualified names
        (e.g., ``module.MyClass.my_func``) are matched.
        """
        return list(self._symbol_by_name.get(name, []))

    def get_all_symbols(self) -> list[SymbolEntry]:
        """Return all symbols in deterministic order."""
        return list(self._symbols)

    def get_all_file_paths(self) -> list[str]:
        """Return all file paths in deterministic sorted order."""
        return list(self._file_paths)


def build_inventory(repo_root: Path) -> SymbolInventory:
    """Build a symbol inventory by scanning the repository (FR-002, FR-011).

    Uses ``git ls-files`` for file discovery and delegates to language
    extractors for symbol extraction.
    """
    file_paths = _discover_files(repo_root)
    file_paths = _apply_protected_filter(file_paths)

    extractor = PythonExtractor()
    symbols: list[SymbolEntry] = []

    # Extract Python symbols
    for fp in file_paths:
        full_path = repo_root / fp
        if full_path.suffix in extractor.supported_extensions():
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                symbols.extend(extractor.extract_symbols(Path(fp), content))
            except OSError:
                continue

    # Extract CLI entry points from pyproject.toml
    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.is_file():
        try:
            content = pyproject_path.read_text(encoding="utf-8", errors="replace")
            symbols.extend(extractor.extract_cli_entry_points(content))
        except (OSError, UnicodeDecodeError):
            pass

    return SymbolInventory(file_paths, symbols)


def _discover_files(repo_root: Path) -> list[str]:
    """Discover files using git ls-files."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return [line for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Fallback: walk the directory
    paths: list[str] = []
    for path in repo_root.rglob("*"):
        if path.is_file():
            try:
                paths.append(path.relative_to(repo_root).as_posix())
            except ValueError:
                continue
    return paths


# Patterns matched by exact basename (avoid false positives from substring).
_BASENAME_PATTERNS: frozenset[str] = frozenset({"_version.py"})


def _apply_protected_filter(file_paths: list[str]) -> list[str]:
    """Remove files matching PROTECTED_FILE_PATTERNS."""
    filtered: list[str] = []
    for fp in file_paths:
        basename = fp.rsplit("/", 1)[-1]
        if basename in _BASENAME_PATTERNS:
            continue
        if not any(pattern in fp for pattern in PROTECTED_FILE_PATTERNS if pattern not in _BASENAME_PATTERNS):
            filtered.append(fp)
    return filtered

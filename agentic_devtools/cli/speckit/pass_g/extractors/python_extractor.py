"""Python-specific symbol extraction using AST parsing (FR-002, FR-007)."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from ..models import ReferenceKind
from .base import SymbolEntry, SymbolExtractor


class PythonExtractor(SymbolExtractor):
    """Extract symbols from Python source files and pyproject.toml."""

    def supported_extensions(self) -> set[str]:
        return {".py"}

    def extract_symbols(self, file_path: Path, content: str) -> list[SymbolEntry]:
        """Extract class, function, and method names from a Python file."""
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return []

        symbols: list[SymbolEntry] = []
        module_path = _file_to_module_path(file_path)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                qualified = f"{module_path}.{node.name}" if module_path else node.name
                symbols.append(
                    SymbolEntry(
                        name=node.name,
                        qualified_name=qualified,
                        kind=ReferenceKind.CLASS_NAME,
                        file_path=file_path.as_posix(),
                        line_number=node.lineno,
                    )
                )
                # Extract methods within the class
                for item in ast.iter_child_nodes(node):
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_qualified = f"{qualified}.{item.name}"
                        symbols.append(
                            SymbolEntry(
                                name=item.name,
                                qualified_name=method_qualified,
                                kind=ReferenceKind.METHOD_NAME,
                                file_path=file_path.as_posix(),
                                line_number=item.lineno,
                            )
                        )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = f"{module_path}.{node.name}" if module_path else node.name
                symbols.append(
                    SymbolEntry(
                        name=node.name,
                        qualified_name=qualified,
                        kind=ReferenceKind.FUNCTION_NAME,
                        file_path=file_path.as_posix(),
                        line_number=node.lineno,
                    )
                )

        return symbols

    def extract_cli_entry_points(self, pyproject_content: str) -> list[SymbolEntry]:
        """Extract CLI entry points from pyproject.toml content."""
        scripts = _parse_project_scripts(pyproject_content)
        symbols: list[SymbolEntry] = []
        for name, target in scripts.items():
            symbols.append(
                SymbolEntry(
                    name=name,
                    qualified_name=target,
                    kind=ReferenceKind.CLI_COMMAND,
                    file_path="pyproject.toml",
                    line_number=0,
                )
            )
        return symbols


def _file_to_module_path(file_path: Path) -> str:
    """Convert a file path to a dotted module path."""
    parts = file_path.with_suffix("").parts
    # Remove __init__ from the end if present
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _parse_project_scripts(content: str) -> dict[str, str]:
    """Parse [project.scripts] from pyproject.toml content.

    Uses tomllib when available (Python 3.11+), falls back to regex parsing.
    """
    if sys.version_info >= (3, 11):
        try:
            import tomllib

            data = tomllib.loads(content)
            return dict(data.get("project", {}).get("scripts", {}))
        except Exception:
            pass

    # Fallback: simple regex-based parser for [project.scripts] section
    return _regex_parse_scripts_section(content)


def _regex_parse_scripts_section(content: str) -> dict[str, str]:
    """Parse [project.scripts] section using regex (Python 3.10 fallback)."""
    scripts: dict[str, str] = {}
    in_section = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[project.scripts]":
            in_section = True
            continue
        if in_section:
            if stripped.startswith("[") and stripped.endswith("]"):
                break
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*"([^"]+)"', stripped)
            if match:
                scripts[match.group(1)] = match.group(2)
    return scripts

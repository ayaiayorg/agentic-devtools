#!/usr/bin/env python3
"""Generate the tests/unit/ directory structure scaffolding from source files.

Usage:
    python scripts/scaffold_tests.py --dry-run   # Preview changes without writing
    python scripts/scaffold_tests.py --generate  # Create directory structure and test stubs

The script mirrors the 1:1:1 test policy (see tests/README.md):
    tests/unit/{module_path}/{source_file_name}/test_{function_name}.py

For each public function in each source module, one test stub file is created.
All intermediate directories receive an __init__.py file.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "agentic_devtools"
UNIT_TESTS_DIR = REPO_ROOT / "tests" / "unit"


class TestStub(NamedTuple):
    """Represents a single test stub to be created."""

    test_file: Path
    source_file: Path
    function_name: str


def _collect_public_functions(source_file: Path) -> list[str]:
    """Return a sorted list of public function names defined at module level.

    A function is considered public when its name does not start with an
    underscore.  Only ``def`` statements at the top level of the module are
    included (nested functions and class methods are excluded).
    """
    try:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    names: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
    return sorted(names)


def _source_files() -> list[Path]:
    """Return all .py source files under SOURCE_ROOT, excluding __init__.py and _version.py."""
    return sorted(
        p
        for p in SOURCE_ROOT.rglob("*.py")
        if p.name not in {"__init__.py", "_version.py"} and "__pycache__" not in p.parts
    )


def _test_stubs_for_file(source_file: Path) -> list[TestStub]:
    """Return the list of TestStub objects for a given source file."""
    functions = _collect_public_functions(source_file)
    if not functions:
        return []

    # Compute the relative module path inside agentic_devtools/, strip .py
    rel = source_file.relative_to(SOURCE_ROOT)
    # e.g. cli/git/core.py  ->  cli/git/core
    module_parts = rel.with_suffix("").parts  # ('cli', 'git', 'core')

    stubs: list[TestStub] = []
    for func in functions:
        test_file = UNIT_TESTS_DIR.joinpath(*module_parts) / f"test_{func}.py"
        stubs.append(TestStub(test_file=test_file, source_file=source_file, function_name=func))
    return stubs


def _build_import_path(source_file: Path) -> str:
    """Return the dotted import path for a source file.

    Example: agentic_devtools/cli/git/core.py -> agentic_devtools.cli.git.core
    """
    rel = source_file.relative_to(REPO_ROOT)
    return ".".join(rel.with_suffix("").parts)


def _stub_content(stub: TestStub) -> str:
    """Return the text content for a new test stub file."""
    import_path = _build_import_path(stub.source_file)
    return (
        f'"""Tests for {import_path}.{stub.function_name}."""\n'
        f"\n"
        f"from {import_path} import {stub.function_name}  # noqa: F401\n"
        f"\n"
        f"\n"
        f"def test_{stub.function_name}() -> None:\n"
        f"    # TODO: implement test\n"
        f"    raise NotImplementedError\n"
    )


def collect_all_stubs() -> list[TestStub]:
    """Collect all test stubs that should exist."""
    stubs: list[TestStub] = []
    for source_file in _source_files():
        stubs.extend(_test_stubs_for_file(source_file))
    return stubs


def _dirs_needing_init(stubs: list[TestStub]) -> list[Path]:
    """Return all directories (including parents up to UNIT_TESTS_DIR) that need __init__.py."""
    dirs: set[Path] = set()
    for stub in stubs:
        current = stub.test_file.parent
        while current != UNIT_TESTS_DIR.parent and current != UNIT_TESTS_DIR:
            dirs.add(current)
            current = current.parent
        dirs.add(UNIT_TESTS_DIR)
    return sorted(dirs)


def dry_run(stubs: list[TestStub]) -> None:
    """Print what would be created without writing any files."""
    if not stubs:
        print("No public functions found — nothing to scaffold.")
        return

    dirs = _dirs_needing_init(stubs)
    new_dirs = [d for d in dirs if not d.exists()]
    new_inits = [d / "__init__.py" for d in dirs if not (d / "__init__.py").exists()]
    new_stubs = [s for s in stubs if not s.test_file.exists()]

    print(f"Dry-run: {len(stubs)} test stub(s) for {len(_source_files())} source file(s)\n")

    if new_dirs:
        print(f"  Directories to create ({len(new_dirs)}):")
        for d in new_dirs:
            print(f"    {d.relative_to(REPO_ROOT)}/")

    if new_inits:
        print(f"\n  __init__.py files to create ({len(new_inits)}):")
        for f in new_inits:
            print(f"    {f.relative_to(REPO_ROOT)}")

    if new_stubs:
        print(f"\n  Test stub files to create ({len(new_stubs)}):")
        for s in new_stubs:
            print(f"    {s.test_file.relative_to(REPO_ROOT)}")
    else:
        print("\n  All test stubs already exist — nothing to create.")


def generate(stubs: list[TestStub]) -> None:
    """Create directories, __init__.py files, and test stubs."""
    if not stubs:
        print("No public functions found — nothing to scaffold.")
        return

    dirs = _dirs_needing_init(stubs)
    created_dirs = 0
    created_inits = 0
    created_stubs = 0
    skipped_stubs = 0

    # Create directories and __init__.py files
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created_dirs += 1
        init = d / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")
            created_inits += 1

    # Create test stub files (never overwrite existing ones)
    for stub in stubs:
        if stub.test_file.exists():
            skipped_stubs += 1
            continue
        stub.test_file.write_text(_stub_content(stub), encoding="utf-8")
        created_stubs += 1

    print(
        f"Generated: {created_dirs} dir(s), {created_inits} __init__.py file(s), "
        f"{created_stubs} test stub(s) | skipped {skipped_stubs} existing stub(s)."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold tests/unit/ structure from agentic_devtools/ source files."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without writing any files.",
    )
    mode.add_argument(
        "--generate",
        action="store_true",
        help="Create directory structure and test stub files.",
    )
    args = parser.parse_args(argv)

    stubs = collect_all_stubs()

    if args.dry_run:
        dry_run(stubs)
    else:
        generate(stubs)

    return 0


if __name__ == "__main__":
    sys.exit(main())

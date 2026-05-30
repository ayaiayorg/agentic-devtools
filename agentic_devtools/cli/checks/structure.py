"""Test structure validation (1:1:1 policy)."""

from __future__ import annotations

from pathlib import Path


def validate_test_structure(repo_root: str | Path | None = None) -> list[str]:
    """Validate the 1:1:1 test structure policy for tests/unit/.

    Returns a list of violation messages (empty = all pass).
    """
    if repo_root is None:
        repo_root = Path.cwd()
    repo_root = Path(repo_root)

    unit_tests_dir = repo_root / "tests" / "unit"
    source_root = repo_root / "agentic_devtools"
    violations: list[str] = []

    if not unit_tests_dir.exists():
        return violations

    for test_file in sorted(unit_tests_dir.rglob("test_*.py")):
        rel = test_file.relative_to(unit_tests_dir)
        parts = rel.parts

        if len(parts) < 2:
            violations.append(
                f"{rel}: test file is too shallow — expected "
                f"tests/unit/{{source_file}}/test_{{function}}.py "
                f"(minimum 2 path components, got {len(parts)})"
            )
            continue

        source_file_folder = parts[-2]
        module_path_parts = parts[:-2]

        expected_source = source_root.joinpath(*module_path_parts) / f"{source_file_folder}.py"
        if not expected_source.exists():
            source_path_display = "/".join((*module_path_parts, f"{source_file_folder}.py"))
            violations.append(f"{rel}: no matching source file found at agentic_devtools/{source_path_display}")

        current = unit_tests_dir
        for part in parts[:-1]:
            current = current / part
            init = current / "__init__.py"
            if not init.exists():
                violations.append(f"{rel}: missing __init__.py in {current.relative_to(repo_root)}")

    return violations

"""
FR validation for SpecKit pipeline.

Cross-references functional requirements (FR-###) in ``spec.md`` with task
content in ``tasks.md``.  Provides pure-function validation logic and an
``argparse``-based CLI entry point (``agdt-speckit-validate-frs``).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of FR-coverage validation."""

    covered: list[str] = field(default_factory=list)
    uncovered: list[str] = field(default_factory=list)
    total: int = 0
    warning: str | None = None

    @property
    def passed(self) -> bool:
        """Return ``True`` when every extracted FR is covered."""
        return len(self.uncovered) == 0

    def to_json(self) -> dict:
        """Return a JSON-serialisable dict matching the FR-011 schema."""
        return {
            "covered": list(self.covered),
            "uncovered": list(self.uncovered),
            "total": self.total,
        }


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

_FR_RE = re.compile(r"FR-\d+", re.IGNORECASE)


def extract_frs(spec_content: str) -> list[str]:
    """Extract unique FR identifiers from *spec_content* in document order.

    Case-insensitive dedup: ``FR-001`` and ``fr-001`` are considered the same
    identifier and the **first occurrence** is kept as canonical form.
    """
    seen: dict[str, str] = {}  # uppercased -> canonical
    result: list[str] = []
    for match in _FR_RE.finditer(spec_content):
        fr_id = match.group(0)
        key = fr_id.upper()
        if key not in seen:
            seen[key] = fr_id
            result.append(fr_id)
    return result


def check_coverage(fr_ids: list[str], tasks_content: str) -> dict[str, bool]:
    """Check which *fr_ids* appear in *tasks_content* (word-boundary, case-insensitive)."""
    coverage: dict[str, bool] = {}
    for fr_id in fr_ids:
        pattern = re.compile(r"\b" + re.escape(fr_id) + r"\b", re.IGNORECASE)
        coverage[fr_id] = bool(pattern.search(tasks_content))
    return coverage


def sort_fr_ids(fr_ids: list[str]) -> list[str]:
    """Sort FR identifiers by numeric suffix ascending, then length, then lex."""

    def _key(fr_id: str) -> tuple[int, int, str]:
        # Extract numeric suffix after "FR-"
        num_str = re.sub(r"(?i)^FR-", "", fr_id)
        return (int(num_str), len(fr_id), fr_id.upper())

    return sorted(fr_ids, key=_key)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def validate_frs(spec_content: str, tasks_content: str) -> ValidationResult:
    """Validate FR coverage: extract FRs from spec, check against tasks."""
    fr_ids = extract_frs(spec_content)

    if not fr_ids:
        return ValidationResult(
            covered=[],
            uncovered=[],
            total=0,
            warning="No FR identifiers found in spec content",
        )

    coverage = check_coverage(fr_ids, tasks_content)
    covered = sort_fr_ids([fid for fid, cov in coverage.items() if cov])
    uncovered = sort_fr_ids([fid for fid, cov in coverage.items() if not cov])

    return ValidationResult(
        covered=covered,
        uncovered=uncovered,
        total=len(fr_ids),
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _coerce_max_retries(value: int, default: int = 2) -> int:
    """Return a non-negative retry count, falling back to ``default``."""
    if value < 0:
        return default
    return value


def _resolve_max_retries(cli_value: int | None) -> int:
    """Resolve max-retries with precedence: CLI > env var > default (2)."""
    if cli_value is not None:
        return _coerce_max_retries(cli_value)
    env_val = os.environ.get("SPECKIT_VALIDATE_MAX_RETRIES")
    if env_val is not None:
        try:
            return _coerce_max_retries(int(env_val))
        except ValueError:
            pass
    return 2


def _print_human_output(result: ValidationResult, max_retries: int) -> None:
    """Print human-readable validation output."""
    print("=" * 60)
    print("SpecKit FR Coverage Validation")
    print("=" * 60)

    if result.warning:
        print(f"\n⚠ WARNING: {result.warning}")
        print("\nResult: PASS (no FRs to validate)")
        return

    print(f"\nTotal FRs: {result.total}")
    print(f"Covered:   {len(result.covered)}")
    print(f"Uncovered: {len(result.uncovered)}")
    print(f"Max retries: {max_retries}")
    print()

    all_frs = sort_fr_ids(result.covered + result.uncovered)
    covered_set = set(result.covered)
    for fr_id in all_frs:
        status = "✅" if fr_id in covered_set else "❌"
        print(f"  {status} {fr_id}")

    print()
    if result.passed:
        print("Result: PASS — all FRs covered")
    else:
        print("Result: FAIL — uncovered FRs detected")
        print(f"Uncovered: {', '.join(result.uncovered)}")


def validate_frs_command(argv: list[str] | None = None) -> None:
    """CLI entry point for ``agdt-speckit-validate-frs``."""
    parser = argparse.ArgumentParser(
        prog="agdt-speckit-validate-frs",
        description="Validate that all FRs in spec.md are referenced in tasks.md",
    )
    parser.add_argument(
        "--spec-file",
        required=True,
        help="Path to spec.md",
    )
    parser.add_argument(
        "--tasks-file",
        required=True,
        help="Path to tasks.md",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=False,
        help="Output results as JSON",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Max retry count (default: env SPECKIT_VALIDATE_MAX_RETRIES or 2)",
    )

    args = parser.parse_args(argv)

    max_retries = _resolve_max_retries(args.max_retries)

    # Read spec content
    spec_content = ""
    spec_path = args.spec_file
    if os.path.isfile(spec_path):
        try:
            with open(spec_path, encoding="utf-8") as f:
                spec_content = f.read()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"Error reading spec file '{spec_path}': {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
    else:
        print(
            f"Warning: spec file '{spec_path}' not found or is not a file; "
            "treating as empty spec content",
            file=sys.stderr,
        )

    # Read tasks content
    tasks_content = ""
    tasks_path = args.tasks_file
    if os.path.isfile(tasks_path):
        try:
            with open(tasks_path, encoding="utf-8") as f:
                tasks_content = f.read()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"Error reading tasks file '{tasks_path}': {exc}", file=sys.stderr)
            raise SystemExit(2) from exc

    try:
        result = validate_frs(spec_content, tasks_content)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.json_output:
        output = result.to_json()
        output["max_retries"] = max_retries
        if result.warning:
            output["warning"] = result.warning
        print(json.dumps(output))
    else:
        _print_human_output(result, max_retries)

    raise SystemExit(0 if result.passed else 1)

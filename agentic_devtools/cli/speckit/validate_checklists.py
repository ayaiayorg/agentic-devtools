"""
Checklist validation for SpecKit pipeline.

Validates that checklist markdown files contain actual checkbox items
(``- [ ]`` / ``- [x]`` / ``- [X]`` / ``* [ ]`` / ``* [x]`` / ``* [X]``)
rather than only descriptive prose. Provides pure-function helpers
(``count_checkboxes``, ``classify_file``), CLI-oriented validation functions,
and an ``argparse``-based CLI entry point
(``agdt-speckit-validate-checklists``).
"""

from __future__ import annotations

import argparse
import glob as glob_mod
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class FileClassification(Enum):
    """Classification of a checklist file based on checkbox count."""

    valid = "valid"
    deficient = "deficient"
    prose_only = "prose_only"


class Severity(Enum):
    """Severity level for checklist validation findings."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"


@dataclass
class FileResult:
    """Result of validating a single checklist file."""

    path: str
    checkbox_count: int
    classification: FileClassification
    severity: Severity
    explanation: str
    remediated: bool = False
    retries_used: int = 0

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict."""
        return {
            "path": self.path,
            "checkbox_count": self.checkbox_count,
            "classification": self.classification.value,
            "severity": self.severity.value,
            "explanation": self.explanation,
            "remediated": self.remediated,
            "retries_used": self.retries_used,
        }


@dataclass
class AggregateResult:
    """Aggregate result of validating multiple checklist files."""

    files: list[FileResult] = field(default_factory=list)
    passed: bool = True
    warning: str | None = None

    def to_json(self) -> dict:
        """Return a JSON-serialisable dict."""
        return {
            "files": [f.to_dict() for f in self.files],
            "passed": self.passed,
            "warning": self.warning,
        }


@dataclass
class RemediationResult:
    """Result of attempting LLM remediation on a deficient file."""

    remediated: bool
    retries_used: int
    file_result: FileResult


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

# Regex for checkbox lines: optional whitespace, then - or * followed by [ ], [x], or [X]
_CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]", re.MULTILINE)

# Regex for fenced code block openers/closers
_BACKTICK_FENCE_RE = re.compile(r"^(\s*)(`{3,})")
_TILDE_FENCE_RE = re.compile(r"^(\s*)(~{3,})")


def count_checkboxes(content: str) -> int:
    """Count markdown checkbox items, excluding those inside fenced code blocks.

    Implements CommonMark outermost-boundary rules for both backtick and tilde
    fenced code blocks. Handles fence length matching (closing fence must be at
    least as long as the opening fence).
    """
    count = 0
    in_fence = False
    fence_char: str | None = None
    fence_length = 0

    for line in content.split("\n"):
        # Check for fence boundaries
        backtick_match = _BACKTICK_FENCE_RE.match(line)
        tilde_match = _TILDE_FENCE_RE.match(line)

        if not in_fence:
            # Check if this line opens a fenced code block
            if backtick_match:
                fence_char = "`"
                fence_length = len(backtick_match.group(2))
                in_fence = True
                continue
            if tilde_match:
                fence_char = "~"
                fence_length = len(tilde_match.group(2))
                in_fence = True
                continue
        else:
            # Check if this line closes the current fenced code block
            if fence_char == "`" and backtick_match:
                closing_length = len(backtick_match.group(2))
                # Closing fence must be at least as long, and line must be
                # only the fence (plus optional whitespace)
                stripped = line.strip()
                if closing_length >= fence_length and stripped == "`" * closing_length:
                    in_fence = False
                    fence_char = None
                    fence_length = 0
                continue
            if fence_char == "~" and tilde_match:
                closing_length = len(tilde_match.group(2))
                stripped = line.strip()
                if closing_length >= fence_length and stripped == "~" * closing_length:
                    in_fence = False
                    fence_char = None
                    fence_length = 0
                continue
            # Inside a fence, skip all content
            continue

        # Outside of fenced code blocks, count checkbox items
        if _CHECKBOX_RE.match(line):
            count += 1

    return count


def classify_file(checkbox_count: int, min_items: int = 3) -> tuple[FileClassification, Severity]:
    """Classify a file based on its checkbox count.

    Returns:
        Tuple of (classification, severity):
        - 0 items → (prose_only, MEDIUM)
        - 1..min_items-1 → (deficient, LOW)
        - ≥min_items → (valid, NONE)
    """
    if checkbox_count == 0:
        return FileClassification.prose_only, Severity.MEDIUM
    if checkbox_count < min_items:
        return FileClassification.deficient, Severity.LOW
    return FileClassification.valid, Severity.NONE


def validate_file(path: str, min_items: int = 3) -> FileResult:
    """Validate a single checklist file.

    Reads the file, counts checkboxes, classifies, and returns a FileResult.

    Raises:
        SystemExit(2): If the file cannot be read (I/O error).
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: Cannot read file: {path} — {exc}", file=sys.stderr)
        sys.exit(2)

    checkbox_count = count_checkboxes(content)
    classification, severity = classify_file(checkbox_count, min_items)

    if classification == FileClassification.valid:
        explanation = f"File contains {checkbox_count} checkbox items (≥{min_items} required) — valid"
    elif classification == FileClassification.deficient:
        explanation = f"File contains {checkbox_count} checkbox items (minimum {min_items} required) — deficient"
    else:
        explanation = "File contains 0 checkbox items — prose-only, requires checklist formatting"

    return FileResult(
        path=path,
        checkbox_count=checkbox_count,
        classification=classification,
        severity=severity,
        explanation=explanation,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def validate_checklists(
    paths: list[str],
    min_items: int = 3,
    *,
    retry: bool = False,
    max_retries: int = 2,
) -> AggregateResult:
    """Validate multiple checklist files.

    Args:
        paths: List of resolved file paths to validate.
        min_items: Minimum checkbox items required for a file to be valid.
        retry: If True, attempt LLM remediation for invalid files.
        max_retries: Maximum remediation retries per file (default 2).

    Returns:
        AggregateResult with per-file results and aggregate pass/fail.
    """
    if not paths:
        return AggregateResult(
            files=[],
            passed=True,
            warning="No checklist files found to validate",
        )

    results: list[FileResult] = []
    for path in paths:
        file_result = validate_file(path, min_items)

        # Attempt remediation if enabled and file is invalid
        if retry and file_result.classification != FileClassification.valid:
            remediation = remediate_file(path, min_items, max_retries)
            file_result = remediation.file_result
            file_result.remediated = remediation.remediated
            file_result.retries_used = remediation.retries_used

        results.append(file_result)

    passed = all(r.classification == FileClassification.valid for r in results)
    return AggregateResult(files=results, passed=passed)


# ---------------------------------------------------------------------------
# Remediation (stub — requires LLM integration)
# ---------------------------------------------------------------------------


def remediate_file(path: str, min_items: int = 3, max_retries: int = 2) -> RemediationResult:
    """Attempt LLM remediation for a deficient checklist file.

    This is a stub that returns the current file state without modification.
    Full LLM integration requires the SpecKit pipeline's ``call_llm`` helper
    (extracted into a sourceable library) and ``COPILOT_GITHUB_TOKEN`` at runtime.

    When ``--retry`` is enabled, this function would:
    1. Load the sidecar generation prompt (``.generation-prompt-{stem}.md``)
    2. Re-prompt the LLM with validation failure details
    3. Re-validate after each retry
    4. Stop when valid or retries exhausted
    """
    # Return current state — no actual remediation without LLM integration
    file_result = validate_file(path, min_items)
    return RemediationResult(
        remediated=False,
        retries_used=0,
        file_result=file_result,
    )


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _resolve_paths(patterns: list[str], issue_number: int | None = None) -> list[str]:
    """Resolve file patterns to concrete paths.

    Handles:
    - Explicit paths (no glob metacharacters): must exist, else SystemExit(2)
    - Glob patterns: expanded, zero-match emits warning to stderr
    - Pipeline-mode default: ``{base_path}/<issue>-*/checklists/*.md``
    - Multi-directory collision detection: SystemExit(1)
    - 3-digit issue number safety check: SystemExit(1) if marker missing

    Returns deduplicated paths sorted by path (lexicographic order).
    """
    resolved: list[str] = []
    glob_metachar_re = re.compile(r"[*?\[]")

    for pattern in patterns:
        if not glob_metachar_re.search(pattern):
            # Explicit path — must exist
            if not os.path.isfile(pattern):
                print(
                    f"ERROR: File does not exist: {pattern}",
                    file=sys.stderr,
                )
                sys.exit(2)
            resolved.append(os.path.abspath(pattern))
        else:
            # Glob pattern
            matches = glob_mod.glob(pattern, recursive=True)
            if not matches:
                print(
                    f"WARNING: Glob pattern matched no files: {pattern}",
                    file=sys.stderr,
                )
            else:
                resolved.extend(os.path.abspath(m) for m in matches)

    # Deduplicate preserving insertion order, then sort for deterministic output
    seen: set[str] = set()
    deduped: list[str] = []
    for p in resolved:
        if p not in seen:
            seen.add(p)
            deduped.append(p)

    # Multi-directory collision detection for pipeline-mode
    if issue_number is not None:
        _check_collision(deduped, issue_number)

    return sorted(deduped)


def _check_collision(paths: list[str], issue_number: int) -> None:
    """Detect multi-directory collision and 3-digit safety check.

    When paths span multiple spec directories for the same issue number,
    abort with exit code 1. For issue numbers 100-999, verify the Source
    Issue marker is present.
    """
    # Extract unique spec directories (parent of 'checklists' directory)
    spec_dirs: set[str] = set()
    for p in paths:
        path_obj = Path(p)
        # Expected structure: .../specs/<issue>-<name>/checklists/<file>.md
        # The checklists dir is parent, spec dir is grandparent
        if path_obj.parent.name == "checklists":
            spec_dirs.add(str(path_obj.parent.parent))

    if len(spec_dirs) > 1:
        dirs_list = "\n  ".join(sorted(spec_dirs))
        print(
            f"ERROR: Multi-directory collision detected for issue #{issue_number}.\n"
            f"  Matched directories:\n  {dirs_list}\n"
            f"  Only one spec directory per issue number is allowed.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 3-digit safety check (100-999)
    if 100 <= issue_number <= 999 and spec_dirs:
        spec_dir = next(iter(spec_dirs))
        _verify_source_issue_marker(spec_dir, issue_number)


def _verify_source_issue_marker(spec_dir: str, issue_number: int) -> None:
    """Verify that a spec directory contains a Source Issue marker.

    For 3-digit issue numbers (100-999) which overlap the legacy numbering
    namespace, check that the spec directory actually belongs to the expected
    issue by looking for ``**Source Issue**`` referencing ``#<issue_number>``.
    """
    marker_pattern = re.compile(rf"\*\*Source Issue\*\*.*#\s*{issue_number}\b", re.IGNORECASE)

    # Check in checklists/requirements.md first, then spec.md
    candidates = [
        os.path.join(spec_dir, "checklists", "requirements.md"),
        os.path.join(spec_dir, "spec.md"),
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            try:
                content = Path(candidate).read_text(encoding="utf-8")
                if marker_pattern.search(content):
                    return  # Marker found — valid
            except (OSError, UnicodeDecodeError):
                continue

    print(
        f"ERROR: 3-digit issue number safety check failed for issue #{issue_number}.\n"
        f"  Directory: {spec_dir}\n"
        f"  No **Source Issue** marker referencing #{issue_number} found.\n"
        f"  This may be a legacy directory mismatch.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _print_human_output(result: AggregateResult) -> None:
    """Print human-readable validation output."""
    print("=" * 60)
    print("SpecKit Checklist Validation")
    print("=" * 60)

    if result.warning:
        print(f"\n⚠ WARNING: {result.warning}")
        print("\nResult: PASS (no files to validate)")
        return

    print(f"\nFiles validated: {len(result.files)}")
    print()

    for fr in result.files:
        severity_str = f" [{fr.severity.value}]" if fr.severity != Severity.NONE else ""
        status = "✅" if fr.classification == FileClassification.valid else "❌"
        remediation_note = " (remediated)" if fr.remediated else ""
        print(f"  {status} {fr.path}{severity_str}{remediation_note}")
        print(f"     {fr.explanation}")

    print()
    if result.passed:
        print("Result: PASS — all checklist files valid")
    else:
        failed = [f for f in result.files if f.classification != FileClassification.valid]
        print(f"Result: FAIL — {len(failed)} file(s) below minimum threshold")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _resolve_issue_number(cli_value: int | None) -> int | None:
    """Resolve issue number with precedence: CLI > env > state.

    Returns None if no numeric issue number can be determined.
    """
    if cli_value is not None:
        return cli_value

    env_val = os.environ.get("ISSUE_NUMBER")
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            pass

    # Try state key (only if purely numeric)
    try:
        from agentic_devtools.state import get_value

        issue_key = get_value("issue_key")
        if issue_key is not None:
            try:
                return int(str(issue_key))
            except ValueError:
                pass  # Non-numeric (e.g., Jira key) — skip
    except (ImportError, Exception):
        pass

    return None


def validate_checklists_command(argv: list[str] | None = None) -> None:
    """CLI entry point for ``agdt-speckit-validate-checklists``."""
    parser = argparse.ArgumentParser(
        prog="agdt-speckit-validate-checklists",
        description=(
            "Validate that checklist markdown files contain actual checkbox items. "
            "In pipeline mode (no paths specified), discovers checklists via glob."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[],
        help="File paths or glob patterns to validate (pipeline-mode if omitted)",
    )
    parser.add_argument(
        "--issue-number",
        type=int,
        default=None,
        help="Explicit numeric GitHub issue number for pipeline-mode discovery",
    )
    parser.add_argument(
        "--min-items",
        type=int,
        default=3,
        help="Minimum checkbox items required (default: 3, must be >= 1)",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=False,
        help="Output results as JSON",
    )
    parser.add_argument(
        "--retry",
        action="store_true",
        default=False,
        help="Enable bounded LLM re-prompting for invalid files (max 2 retries)",
    )

    args = parser.parse_args(argv)

    if args.min_items < 1:
        print(
            f"ERROR: --min-items must be >= 1, got {args.min_items}",
            file=sys.stderr,
        )
        sys.exit(2)

    # Resolve paths
    if args.paths:
        paths = _resolve_paths(args.paths)
    else:
        # Pipeline mode: discover via glob
        issue_number = _resolve_issue_number(args.issue_number)
        if issue_number is None:
            print(
                "ERROR: No issue number available for pipeline-mode discovery.\n"
                "  Provide explicit paths, --issue-number, or set ISSUE_NUMBER env var.",
                file=sys.stderr,
            )
            sys.exit(1)

        base_path = os.environ.get("SPEC_BASE_PATH", "specs")
        pattern = os.path.join(base_path, f"{issue_number}-*", "checklists", "*.md")
        paths = _resolve_paths([pattern], issue_number=issue_number)

    # Validate
    result = validate_checklists(
        paths,
        min_items=args.min_items,
        retry=args.retry,
    )

    # Output
    if args.json_output:
        print(json.dumps(result.to_json(), indent=2))
    else:
        _print_human_output(result)

    # Exit code
    sys.exit(0 if result.passed else 1)

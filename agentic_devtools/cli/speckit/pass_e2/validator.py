"""Orchestrator and CLI entry point for E.2 Test Coverage Validation.

Runs the full E.2 pipeline: spec parsing → task classification → coverage
mapping → finding generation → reporting.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from .coverage_mapper import evaluate_coverage, generate_task_scoped_findings, map_test_tasks_to_frs
from .models import TestCoverageFinding, TestCoverageResult, TestTask
from .reporter import render_test_coverage_summary
from .spec_parser import build_us_to_fr_mapping, extract_frs_with_priority, parse_user_story_sections
from .task_classifier import classify_test_types, detect_ambiguous_task, extract_task_fr_refs, is_test_task

# ---------------------------------------------------------------------------
# Task parsing
# ---------------------------------------------------------------------------

_TASK_LINE_RE = re.compile(
    r"^\s*-\s*\[[ xX]\]\s*(T\d+)\s+(.*)",
    re.MULTILINE,
)


def _parse_tasks_from_content(tasks_content: str) -> list[tuple[str, str]]:
    """Parse task lines from tasks.md content.

    Returns list of (task_id, description) tuples.
    """
    tasks: list[tuple[str, str]] = []
    for match in _TASK_LINE_RE.finditer(tasks_content):
        task_id = match.group(1)
        description = match.group(2).strip()
        tasks.append((task_id, description))
    return tasks


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def validate_test_coverage(
    spec_content: str,
    tasks_content: str | None,
) -> TestCoverageResult:
    """Run the full E.2 test coverage validation pipeline.

    Args:
        spec_content: Content of spec.md
        tasks_content: Content of tasks.md, or None if file doesn't exist

    Returns:
        TestCoverageResult with findings, coverage map, and summary.
    """
    # FR-009: Handle missing/empty tasks.md
    if tasks_content is None:
        return TestCoverageResult(
            findings=[
                TestCoverageFinding(
                    key="TASK:missing-tasks-file",
                    severity="CRITICAL",
                    description="tasks.md file does not exist.",
                    recommendation=("Run `/speckit.tasks` to generate the task breakdown before running analysis."),
                )
            ],
        )

    # Parse tasks
    raw_tasks = _parse_tasks_from_content(tasks_content)
    if not raw_tasks:
        return TestCoverageResult(
            findings=[
                TestCoverageFinding(
                    key="TASK:empty-tasks-file",
                    severity="CRITICAL",
                    description="tasks.md contains zero defined tasks.",
                    recommendation=("Run `/speckit.tasks` to generate the task breakdown before running analysis."),
                )
            ],
        )

    # Extract FRs with priority from spec
    fr_infos = extract_frs_with_priority(spec_content)
    if not fr_infos:
        return TestCoverageResult(
            findings=[],
            coverage={},
        )

    # Parse user story sections and build mapping
    us_sections = parse_user_story_sections(spec_content)
    us_to_fr = build_us_to_fr_mapping(us_sections)

    # Classify tasks
    test_tasks: list[TestTask] = []
    for task_id, description in raw_tasks:
        if is_test_task(description):
            fr_refs, us_labels = extract_task_fr_refs(description)
            test_types = classify_test_types(description)
            ambiguous = detect_ambiguous_task(description)
            test_tasks.append(
                TestTask(
                    task_id=task_id,
                    description=description,
                    fr_refs=fr_refs,
                    us_labels=us_labels,
                    test_types=test_types,
                    is_ambiguous=ambiguous,
                )
            )

    # Map test tasks to FRs
    fr_to_tasks, unmapped_tasks = map_test_tasks_to_frs(test_tasks, fr_infos, us_to_fr)

    # Evaluate coverage
    coverage_map, coverage_findings = evaluate_coverage(fr_infos, fr_to_tasks)

    # Generate task-scoped findings
    task_findings = generate_task_scoped_findings(test_tasks, unmapped_tasks, us_to_fr)

    # Generate priority-ambiguity findings (FR-001)
    ambiguity_findings: list[TestCoverageFinding] = []
    for fr_info in fr_infos:
        if fr_info.priority_ambiguous:
            ambiguity_findings.append(
                TestCoverageFinding(
                    key=f"{fr_info.fr_id}:priority-ambiguous",
                    severity="LOW",
                    fr_id=fr_info.fr_id,
                    description=(
                        f"{fr_info.fr_id} priority could not be determined — defaulting to HIGH severity (non-P1)."
                    ),
                    recommendation=(
                        f"Associate {fr_info.fr_id} with a user story that has "
                        f"an explicit priority (P1/P2/P3) in the spec."
                    ),
                )
            )

    # Combine all findings
    all_findings = coverage_findings + ambiguity_findings + task_findings

    # Render summary table
    summary_table = render_test_coverage_summary(coverage_map)

    return TestCoverageResult(
        findings=all_findings,
        coverage=coverage_map,
        summary_table=summary_table,
        test_tasks=test_tasks,
        unmapped_tasks=unmapped_tasks,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def test_coverage_command(argv: list[str] | None = None) -> None:
    """CLI entry point for ``agdt-speckit-test-coverage``."""
    parser = argparse.ArgumentParser(
        prog="agdt-speckit-test-coverage",
        description="Validate that all FRs have associated test tasks (E.2)",
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

    args = parser.parse_args(argv)

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
            f"Warning: spec file '{spec_path}' not found; treating as empty",
            file=sys.stderr,
        )

    # Read tasks content
    tasks_content: str | None = None
    tasks_path = args.tasks_file
    if os.path.isfile(tasks_path):
        try:
            with open(tasks_path, encoding="utf-8") as f:
                tasks_content = f.read()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"Error reading tasks file '{tasks_path}': {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
    # If file doesn't exist, tasks_content remains None (triggers FR-009)

    try:
        result = validate_test_coverage(spec_content, tasks_content)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_human_output(result)

    # Exit codes: 0 = no findings, 1 = findings present, 2 = fatal error
    raise SystemExit(1 if result.findings else 0)


def _print_human_output(result: TestCoverageResult) -> None:
    """Print human-readable validation output."""
    print("=" * 60)
    print("SpecKit E.2 Test Coverage Validation")
    print("=" * 60)

    if not result.coverage and not result.findings:
        print("\nNo FRs found or no findings generated.")
        return

    if result.findings:
        print(f"\n⚠ {len(result.findings)} finding(s) detected:\n")
        for finding in result.findings:
            print(f"  [{finding.severity}] {finding.key}: {finding.description}")
        print()

    if result.summary_table:
        print(result.summary_table)

    if not result.findings:
        print("\n✅ All FRs have associated test tasks.")

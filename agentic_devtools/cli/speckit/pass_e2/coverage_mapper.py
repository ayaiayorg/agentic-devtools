"""Coverage mapper for E.2 — maps test tasks to FRs and evaluates coverage.

Implements FR-003 (mapping), FR-004 (HIGH severity), FR-005 (CRITICAL severity),
and FR-009 (missing/empty tasks.md).
"""

from __future__ import annotations

from .models import FRCoverage, FRInfo, TestCoverageFinding, TestTask


def map_test_tasks_to_frs(
    test_tasks: list[TestTask],
    fr_infos: list[FRInfo],
    us_to_fr: dict[int, list[str]],
) -> tuple[dict[str, list[TestTask]], list[TestTask]]:
    """Map test tasks to FRs using explicit refs and US-label mapping (FR-003).

    Returns:
        Tuple of (fr_to_tasks, unmapped_tasks) where:
        - fr_to_tasks: dict mapping FR-ID → list of test tasks covering it
        - unmapped_tasks: test tasks that could not be mapped to any FR
    """
    fr_to_tasks: dict[str, list[TestTask]] = {info.fr_id.upper(): [] for info in fr_infos}
    unmapped_tasks: list[TestTask] = []

    # Build a lookup from US number to FR IDs (upper-cased)
    us_to_fr_upper: dict[int, list[str]] = {}
    for us_num, frs in us_to_fr.items():
        us_to_fr_upper[us_num] = [fr.upper() for fr in frs]

    max_us = max(us_to_fr.keys()) if us_to_fr else 0

    for task in test_tasks:
        mapped = False

        # Strategy (a): explicit FR references
        for fr_ref in task.fr_refs:
            key = fr_ref.upper()
            if key in fr_to_tasks:
                fr_to_tasks[key].append(task)
                mapped = True

        # Strategy (b): US-label mapping
        for us_num in task.us_labels:
            if us_num <= max_us and us_num in us_to_fr_upper:
                for fr_key in us_to_fr_upper[us_num]:
                    if fr_key in fr_to_tasks:
                        if task not in fr_to_tasks[fr_key]:
                            fr_to_tasks[fr_key].append(task)
                        mapped = True

        if not mapped:
            unmapped_tasks.append(task)

    return fr_to_tasks, unmapped_tasks


def evaluate_coverage(
    fr_infos: list[FRInfo],
    fr_to_tasks: dict[str, list[TestTask]],
) -> tuple[dict[str, FRCoverage], list[TestCoverageFinding]]:
    """Evaluate test coverage for each FR and generate findings (FR-004, FR-005).

    Returns:
        Tuple of (coverage_map, findings) where:
        - coverage_map: FR-ID → FRCoverage with test task details
        - findings: list of findings for uncovered FRs
    """
    coverage_map: dict[str, FRCoverage] = {}
    findings: list[TestCoverageFinding] = []

    for fr_info in fr_infos:
        key = fr_info.fr_id.upper()
        tasks = fr_to_tasks.get(key, [])

        # Determine test types from all mapped tasks
        all_types: list[str] = []
        for task in tasks:
            for t in task.test_types:
                if t not in all_types:
                    all_types.append(t)

        has_happy_path = "happy-path" in all_types

        cov = FRCoverage(
            fr_info=fr_info,
            test_tasks=tasks,
            test_types=all_types,
            has_happy_path=has_happy_path,
        )
        coverage_map[fr_info.fr_id] = cov

        # Generate findings
        if not cov.is_covered:
            # FR-005: P1 FR with no test task → CRITICAL (subsumes FR-004)
            if fr_info.priority == 1:
                findings.append(
                    TestCoverageFinding(
                        key=f"{fr_info.fr_id}:no-happy-path",
                        severity="CRITICAL",
                        fr_id=fr_info.fr_id,
                        description=(f"{fr_info.fr_id} (P1) has no test task — happy-path coverage is missing."),
                        recommendation=(
                            f"Add a test task for {fr_info.fr_id} covering the "
                            f"happy-path scenario, or re-run `/speckit.tasks` with "
                            f"an explicit request to include happy-path tests."
                        ),
                    )
                )
            else:
                # FR-004: Any FR with no test task → HIGH
                findings.append(
                    TestCoverageFinding(
                        key=f"{fr_info.fr_id}:no-test-task",
                        severity="HIGH",
                        fr_id=fr_info.fr_id,
                        description=(f"{fr_info.fr_id} has no associated test task."),
                        recommendation=(
                            f"Add a test task referencing {fr_info.fr_id} covering "
                            f"its acceptance scenarios, or re-run `/speckit.tasks`."
                        ),
                    )
                )
        elif fr_info.priority == 1 and not has_happy_path:
            # FR-005: P1 FR with test tasks but no happy-path → CRITICAL
            findings.append(
                TestCoverageFinding(
                    key=f"{fr_info.fr_id}:no-happy-path",
                    severity="CRITICAL",
                    fr_id=fr_info.fr_id,
                    description=(
                        f"{fr_info.fr_id} (P1) has test tasks but no happy-path "
                        f"test — only {', '.join(all_types)} detected."
                    ),
                    recommendation=(
                        f"Add a happy-path test task for {fr_info.fr_id}, or "
                        f"re-run `/speckit.tasks` with an explicit request to "
                        f"include happy-path tests for P1 requirements."
                    ),
                )
            )

    return coverage_map, findings


def generate_task_scoped_findings(
    test_tasks: list[TestTask],
    unmapped_tasks: list[TestTask],
    us_to_fr: dict[int, list[str]],
) -> list[TestCoverageFinding]:
    """Generate LOW-severity findings for task-scoped issues.

    - Invalid [USn] refs (referencing non-existent user stories)
    - Unmapped test tasks (no FR ref, no valid US label)
    - Ambiguous tasks (both implementation and test keywords)
    """
    findings: list[TestCoverageFinding] = []
    max_us = max(us_to_fr.keys()) if us_to_fr else 0

    # Check for invalid US references
    for task in test_tasks:
        for us_num in task.us_labels:
            if us_num > max_us or us_num not in us_to_fr:
                findings.append(
                    TestCoverageFinding(
                        key="TASK:invalid-us-ref",
                        severity="LOW",
                        description=(
                            f"Task {task.task_id} references [US{us_num}] but "
                            f"only {max_us} user stories exist in the spec."
                        ),
                        recommendation=(
                            f"Update task {task.task_id} to reference a valid "
                            f"user story or add an explicit FR-NNN reference."
                        ),
                    )
                )

    # Unmapped test tasks
    for task in unmapped_tasks:
        findings.append(
            TestCoverageFinding(
                key="TASK:unmapped-test-task",
                severity="LOW",
                description=(
                    f"Task {task.task_id} is a test task but lacks both an FR reference and a valid [USn] label."
                ),
                recommendation=(
                    f"Add an explicit FR-NNN reference or [USn] label to "
                    f"task {task.task_id} so it can be mapped to a requirement."
                ),
            )
        )

    # Ambiguous tasks
    for task in test_tasks:
        if task.is_ambiguous:
            findings.append(
                TestCoverageFinding(
                    key="TASK:ambiguous-task",
                    severity="LOW",
                    description=(
                        f"Task {task.task_id} contains both implementation and "
                        f"test keywords, making its intent ambiguous."
                    ),
                    recommendation=(
                        f"Split task {task.task_id} into separate implementation and test tasks for clarity."
                    ),
                )
            )

    return findings

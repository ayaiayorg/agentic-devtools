"""Pass E.2 — Test Coverage Validation.

Validates that every functional requirement (FR) in a spec has at least one
associated test task, with elevated severity for P1-associated FRs missing
happy-path coverage.
"""

from .constants import TEST_TASK_KEYWORDS, TEST_TYPE_KEYWORDS
from .coverage_mapper import evaluate_coverage, map_test_tasks_to_frs
from .models import (
    FRCoverage,
    FRInfo,
    TestCoverageFinding,
    TestCoverageResult,
    TestTask,
)
from .reporter import render_findings, render_test_coverage_summary
from .spec_parser import (
    build_us_to_fr_mapping,
    extract_frs_with_priority,
    parse_user_story_sections,
)
from .task_classifier import (
    classify_test_types,
    detect_ambiguous_task,
    extract_task_fr_refs,
    is_test_task,
)
from .validator import test_coverage_command, validate_test_coverage

__all__ = [
    "FRCoverage",
    "FRInfo",
    "TEST_TASK_KEYWORDS",
    "TEST_TYPE_KEYWORDS",
    "TestCoverageFinding",
    "TestCoverageResult",
    "TestTask",
    "build_us_to_fr_mapping",
    "classify_test_types",
    "detect_ambiguous_task",
    "evaluate_coverage",
    "extract_frs_with_priority",
    "extract_task_fr_refs",
    "is_test_task",
    "map_test_tasks_to_frs",
    "parse_user_story_sections",
    "render_findings",
    "render_test_coverage_summary",
    "test_coverage_command",
    "validate_test_coverage",
]

"""Constants for E.2 Test Coverage Validation (FR-002, FR-006, FR-011).

This module is the **single-edit location** for all keyword sets used in
test-task identification and test-type classification. Extending the keyword
sets requires only editing the lists below — no structural changes needed.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# FR-002 / FR-011: Test-task identification keywords
# ---------------------------------------------------------------------------
# A task is classified as a test task if its description matches any of these
# keywords using the matching semantics defined in FR-002:
#   - Single-word keywords: word-boundary matching (case-insensitive)
#   - Multi-word keywords: phrase matching with hyphen/space normalization
#     and optional trailing s/es on the last token

TEST_TASK_KEYWORDS: list[str] = [
    # Single-word keywords (word-boundary matched)
    "test",
    "verify",
    "validate",
    "assert",
    # Multi-word keywords (phrase matched with hyphen/space normalization)
    "spec test",
    "specification test",
    "e2e",
    "integration test",
    "unit test",
    "smoke test",
    "acceptance test",
]

# ---------------------------------------------------------------------------
# FR-006: Test-type classification keywords
# ---------------------------------------------------------------------------
# Each test type has a defined keyword set. A task may match multiple types.
# Multi-word keywords use hyphen/space normalization (same as FR-002).

TEST_TYPE_KEYWORDS: dict[str, list[str]] = {
    "happy-path": [
        "happy path",
        "happy-path",
        "success",
        "nominal",
        "primary flow",
        "basic flow",
        "main scenario",
    ],
    "edge-case": [
        "edge case",
        "edge-case",
        "boundary",
        "corner case",
        "corner-case",
        "limit",
        "overflow",
        "underflow",
    ],
    "negative": [
        "negative",
        "failure",
        "error case",
        "error-case",
        "invalid",
        "reject",
        "malformed",
        "unauthorized",
    ],
    "integration": [
        "integration test",
        "integration-test",
        "cross-module",
        "cross-component",
        "end-to-end integration",
    ],
    "e2e": [
        "e2e",
        "end to end",
        "end-to-end",
        "full flow",
        "full-flow",
        "system test",
        "system-test",
    ],
    "unit": [
        "unit test",
        "unit-test",
        "isolated test",
        "isolated-test",
        "function test",
        "function-test",
    ],
    "infrastructure": [
        "infrastructure",
        "setup test",
        "setup-test",
        "configuration test",
        "config test",
        "scaffold",
        "fixture",
    ],
}

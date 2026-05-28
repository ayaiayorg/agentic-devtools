#!/usr/bin/env bash
#
# test_spec_validation.sh - Unit tests for Phase 1 spec validation library
#
# Tests the validate_spec_quality, _check_mandatory_sections,
# _count_functional_requirements, _count_user_stories, _check_measurable_criteria,
# _check_bullet_ratio, and _build_structured_specify_feedback functions.
#
# Usage: bash test_spec_validation.sh
#
# Exit code: 0 if all tests pass, 1 if any test fails.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Mock dependencies that would normally be provided by generate-spec-from-issue.sh
# ---------------------------------------------------------------------------

# MANDATORY_SECTIONS array (same as in generate-spec-from-issue.sh)
MANDATORY_SECTIONS=(
    "## Problem Statement"
    "## User Scenarios & Testing"
    "## Requirements"
    "## Success Criteria"
)

# extract_section_headings mock — extracts ## headings and strips *(mandatory)*
extract_section_headings() {
    local filepath="$1"
    { grep -E '^## ' "$filepath" 2>/dev/null || true; } | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//'
}

# count_requirement_entries mock — production-equivalent section-scoped counting
count_requirement_entries() {
    local filepath="$1"
    if [[ ! -f "$filepath" ]]; then
        echo "0"
        return 0
    fi

    local scoped_lines count
    scoped_lines=$(
        awk '
            BEGIN { in_req = 0; saw_req = 0 }
            /^[[:space:]]*##[[:space:]]+Requirements([[:space:]]*$|[[:space:][:punct:]].*)/ {
                in_req = 1; saw_req = 1
            }
            saw_req && in_req && /^[[:space:]]*##[[:space:]]+/ && $0 !~ /^[[:space:]]*##[[:space:]]+Requirements([[:space:]]*$|[[:space:][:punct:]].*)/ {
                in_req = 0
            }
            { if (!saw_req || in_req) print }
        ' "$filepath" 2>/dev/null || printf ''
    )

    if [[ -z "$scoped_lines" ]]; then
        echo "0"
        return 0
    fi

    count=$(printf '%s\n' "$scoped_lines" | grep -oE '(^|[^[:alnum:]_])(FR|NFR)-[0-9]+' | grep -oE '(FR|NFR)-[0-9]+' | sort -u | wc -l) || true
    echo "${count:-0}"
}

# ---------------------------------------------------------------------------
# Source the spec-validation library
# ---------------------------------------------------------------------------
# shellcheck source=lib/spec-validation.sh
source "$SCRIPT_DIR/lib/spec-validation.sh"

PASS=0
FAIL=0
TOTAL=0

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
assert_eq() {
    local description="$1"
    local expected="$2"
    local actual="$3"
    TOTAL=$((TOTAL + 1))

    if [[ "$actual" == "$expected" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected='$expected', got='$actual')"
        FAIL=$((FAIL + 1))
    fi
}

assert_contains() {
    local description="$1"
    local needle="$2"
    local haystack="$3"
    TOTAL=$((TOTAL + 1))

    if printf '%s\n' "$haystack" | grep -qF -- "$needle"; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected to contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local description="$1"
    local needle="$2"
    local haystack="$3"
    TOTAL=$((TOTAL + 1))

    if ! printf '%s\n' "$haystack" | grep -qF -- "$needle"; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected NOT to contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Test fixture: create a valid spec file
# ---------------------------------------------------------------------------
create_valid_spec() {
    local filepath="$1"
    cat > "$filepath" << 'SPEC'
# Feature Specification: Test Feature

**Feature Branch**: `feature/test`
**Created**: 2024-01-01
**Status**: Draft
**Source Issue**: #42 (https://github.com/org/repo/issues/42)

## Problem Statement

This is a detailed problem statement describing the issue we are solving.
The current system lacks proper validation and this causes downstream failures.
Users experience frustration when their specifications are rejected after many
iterations. We need to implement a robust validation system that catches issues
early and provides actionable feedback.

## Scope

### In Scope
- Structural validation of spec files
- Retry mechanism with structured feedback

### Out of Scope
- Semantic analysis of spec content
- LLM prompt engineering changes

## User Scenarios & Testing *(mandatory)*

### User Story 1: Basic Validation

As a developer, I want my specs to be validated automatically, so that I catch
structural issues before they propagate downstream.

**Priority**: P1

**Acceptance Scenario**:
Given a spec file missing the Success Criteria section
When the validation runs
Then it reports MISSING_SECTIONS failure with the missing section name

### User Story 2: Retry Mechanism

As a pipeline maintainer, I want failed specs to be automatically retried with
structured feedback, so that transient LLM quality issues are self-correcting.

**Priority**: P1

**Acceptance Scenario**:
Given a spec that fails validation on first attempt
When the retry mechanism fires with structured feedback
Then the LLM produces a valid spec on the retry attempt

### User Story 3: Bullet Detection

As a SpecKit maintainer, I want bullet-only summaries to be detected and
rejected, so that specifications contain proper prose and detail.

**Priority**: P2

**Acceptance Scenario**:
Given a spec where more than 80% of content lines are bullet points
When validation runs
Then it reports BULLET_SUMMARY_DETECTED with the actual percentage

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST validate spec files against structural quality thresholds before writing to disk.
- **FR-002**: The system MUST check for all mandatory sections (Problem Statement, User Scenarios & Testing, Requirements, Success Criteria).
- **FR-003**: The system MUST verify that the spec contains at least 5 unique functional requirement entries (FR-### or NFR-### pattern).
- **FR-004**: The system MUST verify that the spec contains at least 3 user stories with Given/When/Then acceptance scenarios.
- **FR-005**: The system MUST check that at least 50% of success criteria entries contain measurable targets.
- **FR-006**: The system MUST reject specs below 2048 bytes after post-processing.
- **FR-007**: The system MUST detect and reject bullet-point-only outputs where >80% of content lines are bullets.

### Non-Functional Requirements

- **NFR-001**: Validation MUST complete in under 1 second for typical specs.
- **NFR-002**: All failure messages MUST be human-readable and actionable.

## Success Criteria *(mandatory)*

- **SC-001**: 100% of speckit-generated specs pass the new Phase 1 validation after retries.
- **SC-002**: 0% of bullet-summary or underspecified specs make it past Phase 1.
- **SC-003**: Recovery rate of 80% over the first 20 feature specs processed with retry.
- **SC-004**: Validation adds less than 2 seconds of latency to the specify phase in the pass case.
- **SC-005**: The existing test suite passes with zero regressions after integration.
- **SC-006**: The test file contains at least 10 distinct test cases covering all validation branches.

## Edge Cases

- Empty LLM response handled as operational failure (no retry budget consumed)
- Spec with exactly threshold values (boundary conditions)
SPEC
}

# ---------------------------------------------------------------------------
# Test fixture: create a minimal/bad spec
# ---------------------------------------------------------------------------
create_small_spec() {
    local filepath="$1"
    cat > "$filepath" << 'SPEC'
# Small Spec

## Problem Statement

This is too short.

## Requirements

- FR-001: Something
SPEC
}

# ---------------------------------------------------------------------------
# TC01: Valid spec passes all checks
# ---------------------------------------------------------------------------
echo ""
echo "=== TC01: Valid spec passes all checks ==="
TC01_FILE=$(mktemp "/tmp/tc01_spec.XXXXXX")
create_valid_spec "$TC01_FILE"

rc=0
output=$(validate_spec_quality "$TC01_FILE" 2>/dev/null) || rc=$?
assert_eq "Valid spec returns rc=0" "0" "$rc"
assert_eq "Valid spec produces no failure output" "" "$output"
rm -f "$TC01_FILE"

# ---------------------------------------------------------------------------
# TC02: Missing mandatory section fails with MISSING_SECTIONS
# ---------------------------------------------------------------------------
echo ""
echo "=== TC02: Missing mandatory section ==="
TC02_FILE=$(mktemp "/tmp/tc02_spec.XXXXXX")
# Create spec missing "## Success Criteria"
cat > "$TC02_FILE" << 'SPEC'
# Spec: Test

## Problem Statement

A detailed problem statement that describes the issue thoroughly with enough content
to pass the size threshold. We need multiple lines of prose here to ensure the file
is large enough. The validation system needs to check many things and we document them.

## User Scenarios & Testing

### User Story 1: First Story
As a developer, I want validation so that quality improves.
Given a spec file, When validation runs, Then issues are found.

### User Story 2: Second Story
As a user, I want feedback so that I can fix issues.
Given feedback, When I read it, Then I understand the problem.

### User Story 3: Third Story
As a maintainer, I want automation so that manual review decreases.
Given automation, When it runs, Then specs improve automatically.

## Requirements

- **FR-001**: Validate spec files
- **FR-002**: Check mandatory sections
- **FR-003**: Count functional requirements
- **FR-004**: Count user stories
- **FR-005**: Check measurable criteria
- **NFR-001**: Complete in under 1 second

This section contains enough additional prose content to make the file large enough
to pass the size threshold check. We need at least 2048 bytes total.
Adding more descriptive content about the requirements and their rationale.
Each requirement serves a specific purpose in the validation pipeline.
The system architecture supports extensibility and configurability.
Additional context and documentation helps future maintainers understand the design.
More prose to ensure we reach the byte threshold for this test case.
SPEC

rc=0
output=$(validate_spec_quality "$TC02_FILE" 2>/dev/null) || rc=$?
assert_eq "Missing section returns rc=1" "1" "$rc"
assert_contains "Reports MISSING_SECTIONS" "MISSING_SECTIONS" "$output"
assert_contains "Reports Success Criteria as missing" "Success Criteria" "$output"
rm -f "$TC02_FILE"

# ---------------------------------------------------------------------------
# TC03: Spec below 2048 bytes fails with BELOW_SIZE_THRESHOLD
# ---------------------------------------------------------------------------
echo ""
echo "=== TC03: Below size threshold ==="
TC03_FILE=$(mktemp "/tmp/tc03_spec.XXXXXX")
create_small_spec "$TC03_FILE"

rc=0
output=$(validate_spec_quality "$TC03_FILE" 2>/dev/null) || rc=$?
assert_eq "Small spec returns rc=1" "1" "$rc"
assert_contains "Reports BELOW_SIZE_THRESHOLD" "BELOW_SIZE_THRESHOLD" "$output"
rm -f "$TC03_FILE"

# ---------------------------------------------------------------------------
# TC04: Fewer than 5 FRs fails with INSUFFICIENT_REQUIREMENTS
# ---------------------------------------------------------------------------
echo ""
echo "=== TC04: Insufficient requirements ==="
TC04_FILE=$(mktemp "/tmp/tc04_spec.XXXXXX")
# Create spec with only 3 FRs but passing other checks
cat > "$TC04_FILE" << 'SPEC'
# Spec: Test Feature

## Problem Statement

Detailed problem statement with enough prose to pass size checks and provide
sufficient context about the problem being solved. This needs multiple lines.

## User Scenarios & Testing

### User Story 1: First Story
As a developer, I want validation.
Given a spec, When validated, Then it passes.

### User Story 2: Second Story
As a user, I want clear feedback.
Given failures, When reported, Then I understand.

### User Story 3: Third Story
As a maintainer, I want automation.
Given automation, When running, Then quality improves.

## Requirements

- **FR-001**: First requirement description
- **FR-002**: Second requirement description
- **FR-003**: Third requirement description

Additional prose content to reach the byte threshold. This section documents
the rationale behind each requirement and how they interconnect.
More content to ensure file size. The validation framework is designed to be
extensible and configurable for different project needs.
Even more content added here to satisfy the 2048 byte minimum.
Padding content for test purposes to ensure we cross the threshold.
Additional lines of descriptive text about the architecture.

## Success Criteria

- **SC-001**: 100% of specs pass validation
- **SC-002**: 0% of bad specs get through
- **SC-003**: Recovery rate of 80%
SPEC

rc=0
output=$(validate_spec_quality "$TC04_FILE" 2>/dev/null) || rc=$?
assert_eq "Few FRs returns rc=1" "1" "$rc"
assert_contains "Reports INSUFFICIENT_REQUIREMENTS" "INSUFFICIENT_REQUIREMENTS" "$output"
assert_contains "Found count in output" "found=3" "$output"
rm -f "$TC04_FILE"

# ---------------------------------------------------------------------------
# TC05: Fewer than 3 user stories fails with INSUFFICIENT_USER_STORIES
# ---------------------------------------------------------------------------
echo ""
echo "=== TC05: Insufficient user stories ==="
TC05_FILE=$(mktemp "/tmp/tc05_spec.XXXXXX")
cat > "$TC05_FILE" << 'SPEC'
# Spec: Test Feature

## Problem Statement

Detailed problem statement with enough content for size validation.
Multiple lines of prose describing the problem context in detail.

## User Scenarios & Testing

### User Story 1: Only Story
As a developer, I want one thing.
Given something, When it happens, Then result occurs.

## Requirements

- **FR-001**: First
- **FR-002**: Second
- **FR-003**: Third
- **FR-004**: Fourth
- **FR-005**: Fifth

More prose content to pass the size threshold. Documentation about the
requirements and how they relate to the overall system architecture.
Additional descriptive text ensuring sufficient file size for validation.
Extra content padding for the test scenario byte minimum.
More lines to reach the 2048 byte threshold requirement.
Additional context about system design and validation approach.
Enough content now to pass the size check comfortably.

## Success Criteria

- **SC-001**: 100% pass rate
- **SC-002**: 0% failure leakage
- **SC-003**: 80% recovery rate over first 20 specs
SPEC

rc=0
output=$(validate_spec_quality "$TC05_FILE" 2>/dev/null) || rc=$?
assert_eq "Few user stories returns rc=1" "1" "$rc"
assert_contains "Reports INSUFFICIENT_USER_STORIES" "INSUFFICIENT_USER_STORIES" "$output"
rm -f "$TC05_FILE"

# ---------------------------------------------------------------------------
# TC06: Non-measurable success criteria fails
# ---------------------------------------------------------------------------
echo ""
echo "=== TC06: Non-measurable success criteria ==="
TC06_FILE=$(mktemp "/tmp/tc06_spec.XXXXXX")
cat > "$TC06_FILE" << 'SPEC'
# Spec: Test Feature

## Problem Statement

Detailed problem description with sufficient prose for size validation.
The problem is complex and requires thorough documentation.

## User Scenarios & Testing

### User Story 1: First
As a developer, I want validation.
Given a spec, When validated, Then passes.

### User Story 2: Second
As a user, I want feedback.
Given failures, When reported, Then understood.

### User Story 3: Third
As a maintainer, I want quality.
Given quality gates, When running, Then specs improve.

## Requirements

- **FR-001**: First requirement
- **FR-002**: Second requirement
- **FR-003**: Third requirement
- **FR-004**: Fourth requirement
- **FR-005**: Fifth requirement

Prose content about requirements rationale and interconnections.
More detailed text to satisfy size requirements for the test.
Additional documentation about the validation system design.
Extra padding content for test byte threshold compliance.

## Success Criteria

- **SC-001**: The system should work well
- **SC-002**: Users should be happy
- **SC-003**: Quality should improve
- **SC-004**: Things should be better
SPEC

rc=0
output=$(validate_spec_quality "$TC06_FILE" 2>/dev/null) || rc=$?
assert_eq "Non-measurable criteria returns rc=1" "1" "$rc"
assert_contains "Reports NON_MEASURABLE_CRITERIA" "NON_MEASURABLE_CRITERIA" "$output"
rm -f "$TC06_FILE"

# ---------------------------------------------------------------------------
# TC07: Bullet-only spec fails with BULLET_SUMMARY_DETECTED
# ---------------------------------------------------------------------------
echo ""
echo "=== TC07: Bullet-heavy spec detected ==="
TC07_FILE=$(mktemp "/tmp/tc07_spec.XXXXXX")
cat > "$TC07_FILE" << 'SPEC'
# Spec: Bullet Test

## Problem Statement

- Problem point one
- Problem point two
- Problem point three
- Problem point four
- Problem point five
- Problem point six

## User Scenarios & Testing

### User Story 1: Story
- As a developer
- I want validation
- Given a spec
- When validated
- Then passes

### User Story 2: Story Two
- As a user
- I want feedback
- Given failures
- When reported
- Then understood

### User Story 3: Story Three
- As a maintainer
- I want quality
- Given quality gates
- When running
- Then specs improve

## Requirements

- **FR-001**: First requirement bullet
- **FR-002**: Second requirement bullet
- **FR-003**: Third requirement bullet
- **FR-004**: Fourth requirement bullet
- **FR-005**: Fifth requirement bullet
- **FR-006**: Sixth requirement bullet
- **NFR-001**: Non-functional one

## Success Criteria

- **SC-001**: 100% pass rate
- **SC-002**: 0% failure rate
- **SC-003**: 80% recovery
- **SC-004**: Under 2 seconds latency
- Extra bullet one
- Extra bullet two
- Extra bullet three
- Extra bullet four
- Extra bullet five
- Extra bullet six
- Extra bullet seven
- Extra bullet eight
- Extra bullet nine
- Extra bullet ten
- Extra bullet eleven
- Extra bullet twelve
- Extra bullet thirteen
- Extra bullet fourteen
- Extra bullet fifteen
- Extra bullet sixteen
- Extra bullet seventeen
- Extra bullet eighteen
- Extra bullet nineteen
- Extra bullet twenty
- Extra bullet twenty-one
- Extra bullet twenty-two
- Extra bullet twenty-three
- Extra bullet twenty-four
- Extra bullet twenty-five
- Extra bullet twenty-six
- Extra bullet twenty-seven
- Extra bullet twenty-eight
- Extra bullet twenty-nine
- Extra bullet thirty
- Extra bullet thirty-one
- Extra bullet thirty-two
- Extra bullet thirty-three
- Extra bullet thirty-four
- Extra bullet thirty-five
SPEC

rc=0
output=$(validate_spec_quality "$TC07_FILE" 2>/dev/null) || rc=$?
assert_eq "Bullet-heavy spec returns rc=1" "1" "$rc"
assert_contains "Reports BULLET_SUMMARY_DETECTED" "BULLET_SUMMARY_DETECTED" "$output"
rm -f "$TC07_FILE"

# ---------------------------------------------------------------------------
# TC08: Exactly 5 FR/NFR entries passes the FR check (boundary)
# ---------------------------------------------------------------------------
echo ""
echo "=== TC08: Boundary - exactly 5 FRs passes ==="
TC08_FILE=$(mktemp "/tmp/tc08_spec.XXXXXX")
cat > "$TC08_FILE" << 'SPEC'
# Spec: FR Boundary Test

## Problem Statement

Detailed problem statement with enough content to satisfy size checks.
This includes additional prose and context to exceed minimum bytes.
More details about why requirement boundaries matter for validation.
Extra descriptive text to keep this fixture realistic and substantial.

## User Scenarios & Testing

### User Story 1: First
As a developer, I want predictable validation outcomes.
Given a spec, When validation runs, Then boundary cases pass correctly.

### User Story 2: Second
As a maintainer, I want stable threshold checks.
Given requirement counts, When evaluating boundaries, Then outcomes are deterministic.

### User Story 3: Third
As a user, I want clear behavior at minimum values.
Given exactly five requirement entries, When validated, Then the spec passes this gate.

## Requirements

- **FR-001**: First requirement
- **FR-002**: Second requirement
- **FR-003**: Third requirement
- **NFR-001**: Fourth requirement
- **NFR-002**: Fifth requirement

Additional prose to ensure this fixture is comfortably above the size threshold.
Further explanation about boundary semantics and expected behavior in validation.
More context for realistic quality-gate testing and regression prevention.
Additional implementation-neutral narrative to increase size for boundary coverage.
This fixture intentionally targets only the requirement-count lower bound and should
avoid tripping unrelated gates such as file-size or structural completeness checks.
The specification includes all mandatory sections, multiple user stories with full
acceptance scenarios, and measurable success criteria.
More prose lines are added here to exceed MIN_SPEC_BYTES reliably in all environments.
Boundary-focused fixtures can become brittle when content shrinks during maintenance.
This extra explanatory block keeps the fixture comfortably above the size threshold
while preserving the intended semantic target: exactly five requirement identifiers.
The quality gate should pass this file when all other structural expectations are met.
Maintainers can edit surrounding text without accidentally dropping below the minimum.

## Success Criteria

- **SC-001**: 100% pass rate
- **SC-002**: 0% failure leakage
- **SC-003**: 80% recovery over 20 runs
SPEC

rc=0
output=$(validate_spec_quality "$TC08_FILE" 2>/dev/null) || rc=$?
assert_eq "Spec with sufficient FRs returns rc=0" "0" "$rc"
assert_not_contains "Does not report INSUFFICIENT_REQUIREMENTS" "INSUFFICIENT_REQUIREMENTS" "$output"
rm -f "$TC08_FILE"

# ---------------------------------------------------------------------------
# TC09: Multiple failures reported together (compound failure)
# ---------------------------------------------------------------------------
echo ""
echo "=== TC09: Compound failures ==="
TC09_FILE=$(mktemp "/tmp/tc09_spec.XXXXXX")
create_small_spec "$TC09_FILE"  # Small spec fails multiple checks

rc=0
output=$(validate_spec_quality "$TC09_FILE" 2>/dev/null) || rc=$?
assert_eq "Compound failure returns rc=1" "1" "$rc"
assert_contains "Reports size failure" "BELOW_SIZE_THRESHOLD" "$output"
assert_contains "Reports missing sections" "MISSING_SECTIONS" "$output"
assert_contains "Reports insufficient requirements" "INSUFFICIENT_REQUIREMENTS" "$output"
assert_contains "Reports insufficient user stories" "INSUFFICIENT_USER_STORIES" "$output"
rm -f "$TC09_FILE"

# ---------------------------------------------------------------------------
# TC10: User story heading variants accepted (case-insensitive)
# ---------------------------------------------------------------------------
echo ""
echo "=== TC10: User story heading variants ==="
TC10_FILE=$(mktemp "/tmp/tc10_spec.XXXXXX")
cat > "$TC10_FILE" << 'SPEC'
# Spec: Heading Variant Test

## Problem Statement

Detailed problem statement for heading variant testing.

## User Scenarios & Testing

### User Story 1: First Format
As a developer, I want consistent heading parsing.
Given different heading formats, When parsed, Then all are counted.

### USER STORY 2: Uppercase Format
As a user, I want flexibility in heading format.
Given an uppercase heading, When counted, Then it is included.

### user story 3: lowercase
As a maintainer, I want case-insensitive matching.
Given a lowercase heading, When the counter runs, Then it finds this story.

### User Story: Direct Colon Title
As a user, I want headings with a colon immediately after "Story" to be counted.
Given a heading with no number before the colon, When parsed, Then it is included.
SPEC

# Test user story counting directly
us_count=$(_count_user_stories "$TC10_FILE")
assert_eq "Counts 4 user stories with variant headings" "4" "$us_count"
rm -f "$TC10_FILE"

# ---------------------------------------------------------------------------
# TC11: User stories without Given/When/Then are NOT counted
# ---------------------------------------------------------------------------
echo ""
echo "=== TC11: User stories without GWT not counted ==="
TC11_FILE=$(mktemp "/tmp/tc11_spec.XXXXXX")
cat > "$TC11_FILE" << 'SPEC'
# Spec: GWT Test

### User Story 1: Has GWT
As a developer, I want validation.
Given a spec, When validated, Then it passes.

### User Story 2: No GWT
As a user, I want something but there are no acceptance scenarios here.
Given this is only a partial scenario marker.
This story includes only one scenario marker and is intentionally incomplete.

### User Story 3: Has GWT
As a maintainer, I want quality.
Given quality gates, When running, Then specs improve.

### User Story 4: Also No GWT
Some description without acceptance criteria format.
Given only one scenario keyword appears here as well.
SPEC

us_count=$(_count_user_stories "$TC11_FILE")
assert_eq "Only counts stories with GWT scenarios" "2" "$us_count"
rm -f "$TC11_FILE"

# ---------------------------------------------------------------------------
# TC12: Missing SC-### entries fails
# ---------------------------------------------------------------------------
echo ""
echo "=== TC12: Missing success criteria entries ==="
TC12_FILE=$(mktemp "/tmp/tc12_spec.XXXXXX")
cat > "$TC12_FILE" << 'SPEC'
# Spec: Missing SC Entries

## Problem Statement

Detailed problem statement with enough prose content to satisfy file-size checks.
This fixture intentionally keeps the success criteria section present but empty of SC IDs.
Additional content ensures other validations are satisfied for isolation.
More descriptive text to exceed minimum byte thresholds.

## User Scenarios & Testing

### User Story 1: First
As a developer, I want robust quality checks.
Given a specification, When validated, Then missing SC entries are detected.

### User Story 2: Second
As a maintainer, I want explicit failure categories.
Given missing SC IDs, When criteria checks run, Then failures are reported.

### User Story 3: Third
As a user, I want actionable retry guidance.
Given a failed attempt, When feedback is generated, Then I can fix the output.

## Requirements

- **FR-001**: First requirement
- **FR-002**: Second requirement
- **FR-003**: Third requirement
- **FR-004**: Fourth requirement
- **FR-005**: Fifth requirement

## Success Criteria

- This section has prose only.
- No SC identifiers are included here.
SPEC

rc=0
output=$(validate_spec_quality "$TC12_FILE" 2>/dev/null) || rc=$?
assert_eq "Missing SC entries returns rc=1" "1" "$rc"
assert_contains "Reports MISSING_SUCCESS_CRITERIA" "MISSING_SUCCESS_CRITERIA" "$output"
rm -f "$TC12_FILE"

# ---------------------------------------------------------------------------
# TC13: Override threshold constants changes validation behavior
# ---------------------------------------------------------------------------
echo ""
echo "=== TC13: Configurable thresholds ==="
TC13_FILE=$(mktemp "/tmp/tc13_spec.XXXXXX")
create_valid_spec "$TC13_FILE"

# Override MIN_FUNCTIONAL_REQUIREMENTS to require more
OLD_MIN_FR="$MIN_FUNCTIONAL_REQUIREMENTS"
MIN_FUNCTIONAL_REQUIREMENTS=20

rc=0
output=$(validate_spec_quality "$TC13_FILE" 2>/dev/null) || rc=$?
assert_eq "Overridden threshold causes failure" "1" "$rc"
assert_contains "Reports insufficient with overridden min" "minimum=20" "$output"

# Restore
MIN_FUNCTIONAL_REQUIREMENTS="$OLD_MIN_FR"
rm -f "$TC13_FILE"

# ---------------------------------------------------------------------------
# TC14: Sourcing guard prevents double-load
# ---------------------------------------------------------------------------
echo ""
echo "=== TC14: Sourcing guard ==="
# Source again — should be a no-op due to guard
source "$SCRIPT_DIR/lib/spec-validation.sh"
assert_eq "Library loads without error on re-source" "0" "$?"

# ---------------------------------------------------------------------------
# TC15: _build_structured_specify_feedback produces actionable output
# ---------------------------------------------------------------------------
echo ""
echo "=== TC15: Structured feedback format ==="
FAILURES="MISSING_SECTIONS: ## Success Criteria
INSUFFICIENT_REQUIREMENTS: found=2, minimum=5"

feedback=$(_build_structured_specify_feedback "/dev/null" "$FAILURES")
assert_contains "Feedback contains missing sections guidance" "Missing Mandatory Sections" "$feedback"
for mandatory_section in "${MANDATORY_SECTIONS[@]}"; do
    assert_contains "Feedback includes mandatory heading: ${mandatory_section}" "$mandatory_section" "$feedback"
done
expected_mandatory_csv="${MANDATORY_SECTIONS[0]}, ${MANDATORY_SECTIONS[1]}, ${MANDATORY_SECTIONS[2]}, ${MANDATORY_SECTIONS[3]}"
assert_contains "Feedback preserves full multi-word section headings in remediation list" "$expected_mandatory_csv" "$feedback"
assert_contains "Feedback lists headings as a comma-separated sequence" ", ##" "$feedback"
assert_contains "Feedback contains requirements guidance" "Insufficient Functional Requirements" "$feedback"
assert_contains "Feedback mentions minimum FR count" "${MIN_FUNCTIONAL_REQUIREMENTS}" "$feedback"

# ---------------------------------------------------------------------------
# TC16: Scenario keyword substrings do not count as Given/When/Then markers
# ---------------------------------------------------------------------------
echo ""
echo "=== TC16: Reject partial-word scenario keyword matches ==="
TC16_FILE=$(mktemp "/tmp/tc16_spec.XXXXXX")
cat > "$TC16_FILE" << 'SPEC'
# Spec: Keyword Boundary Test

### User Story 1: Valid GWT
As a developer, I want proper keyword detection.
Given a spec, When validation runs, Then valid stories are counted.

### User Story 2: Partial Words
As a maintainer, I want to avoid false positives.
This line includes regiven, whenever, and then2 but not real scenario markers.

### User Story 3: More Partial Words
As a user, I want strict matching.
Only pseudogiven and whenthen appear in this story.
SPEC

us_count=$(_count_user_stories "$TC16_FILE")
assert_eq "Counts only stories with full Given/When/Then markers" "1" "$us_count"
rm -f "$TC16_FILE"

# ---------------------------------------------------------------------------
# TC17: Non-bold SC entries with wrapped measurable targets
# ---------------------------------------------------------------------------
echo ""
echo "=== TC17: Non-bold SC entries with wrapped measurable targets ==="
TC17_FILE=$(mktemp "/tmp/tc17_spec.XXXXXX")
cat > "$TC17_FILE" << 'SPEC'
# Spec: Wrapped SC Test

## Success Criteria

- SC-001: Improve operational reliability across deployments.
  At least 95% of rollout alerts are acknowledged within 5 minutes.
- SC-002: Stakeholders understand reporting outcomes.
SPEC

rc=0
output=$(_check_measurable_criteria "$TC17_FILE" 2>/dev/null) || rc=$?
assert_eq "Non-bold SC entries with wrapped measurable line pass threshold" "0" "$rc"
assert_eq "No measurable-criteria failure output on pass" "" "$output"
rm -f "$TC17_FILE"

# ---------------------------------------------------------------------------
# TC18: Wrapped SC entries without measurable targets fail
# ---------------------------------------------------------------------------
echo ""
echo "=== TC18: Wrapped SC entries without measurable targets ==="
TC18_FILE=$(mktemp "/tmp/tc18_spec.XXXXXX")
cat > "$TC18_FILE" << 'SPEC'
# Spec: Wrapped SC Non-Measurable Test

## Success Criteria

- SC-001: Improve operational reliability across deployments.
  Alert handling should feel faster for on-call engineers.
- SC-002: Stakeholders understand reporting outcomes.
  Report narratives should be easier to follow.
SPEC

rc=0
output=$(_check_measurable_criteria "$TC18_FILE" 2>/dev/null) || rc=$?
assert_eq "Wrapped SC entries without numeric targets fail" "1" "$rc"
assert_eq "Non-measurable wrapped SC failure includes ratio details" "0/50" "$output"
rm -f "$TC18_FILE"

# ---------------------------------------------------------------------------
# TC19: Success Criteria validation is scoped to ## Success Criteria section
# ---------------------------------------------------------------------------
echo ""
echo "=== TC19: Success Criteria section scoping ==="
TC19_FILE=$(mktemp "/tmp/tc19_spec.XXXXXX")
OLD_MIN_SPEC_BYTES_TC19="$MIN_SPEC_BYTES"
MIN_SPEC_BYTES=400
cat > "$TC19_FILE" << 'SPEC'
# Spec: Success Criteria Scope Test

## Problem Statement

Detailed problem statement that provides enough context for this focused test.
The important behavior under test is section scoping for SC identifiers.

## User Scenarios & Testing

### User Story 1: First
As a developer, I want section-scoped SC validation.
Given SC IDs appear outside the Success Criteria section, When validation runs, Then they are ignored.

### User Story 2: Second
As a maintainer, I want predictable structural enforcement.
Given an empty Success Criteria section, When validation executes, Then missing SC entries are reported.

### User Story 3: Third
As a reviewer, I want failures to match section intent.
Given measurable SC IDs in another section, When checks run, Then they do not satisfy the SC gate.

## Requirements

- **FR-001**: First requirement
- **FR-002**: Second requirement
- **FR-003**: Third requirement
- **FR-004**: Fourth requirement
- **FR-005**: Fifth requirement
- **SC-901**: 95% of requests complete under 2 seconds (intentionally outside Success Criteria)

## Success Criteria

- This section intentionally has no SC identifiers.
- It contains prose only to verify section scoping behavior.
SPEC

rc=0
output=$(validate_spec_quality "$TC19_FILE" 2>/dev/null) || rc=$?
assert_eq "SC IDs outside Success Criteria do not satisfy SC gate" "1" "$rc"
assert_contains "Reports MISSING_SUCCESS_CRITERIA when SC section has no SC IDs" "MISSING_SUCCESS_CRITERIA" "$output"
assert_not_contains "Does not report NON_MEASURABLE_CRITERIA when SC section has zero SC IDs" "NON_MEASURABLE_CRITERIA" "$output"
MIN_SPEC_BYTES="$OLD_MIN_SPEC_BYTES_TC19"
rm -f "$TC19_FILE"

# ---------------------------------------------------------------------------
# TC20: Missing file category is preserved in feedback formatting
# ---------------------------------------------------------------------------
echo ""
echo "=== TC20: Missing file handling and feedback ==="
MISSING_FILE_PATH="/tmp/this-file-does-not-exist-${RANDOM}"
rc=0
output=$(validate_spec_quality "$MISSING_FILE_PATH" 2>/dev/null) || rc=$?
assert_eq "Missing file returns rc=1" "1" "$rc"
assert_contains "Reports MISSING_FILE category" "MISSING_FILE" "$output"

feedback=$(_build_structured_specify_feedback "/dev/null" "$output")
assert_contains "Feedback includes missing file section" "Missing Specification File" "$feedback"
assert_contains "Feedback includes missing file path detail" "$MISSING_FILE_PATH" "$feedback"

# ---------------------------------------------------------------------------
# TC21: Invalid numeric overrides fall back to defaults with warning
# ---------------------------------------------------------------------------
echo ""
echo "=== TC21: Invalid threshold overrides fallback ==="
TC21_OUTPUT=$(MIN_SPEC_BYTES="oops" SPECIFY_MAX_RETRIES="0" SPECIFY_MAX_OPERATIONAL_FAILURES="invalid" MAX_BULLET_LINE_PCT="0008" bash -c '
    set -euo pipefail
    MANDATORY_SECTIONS=("## Problem Statement" "## User Scenarios & Testing" "## Requirements" "## Success Criteria")
    extract_section_headings() { :; }
    count_requirement_entries() { echo "0"; }
    # shellcheck source=lib/spec-validation.sh
    source "'"$SCRIPT_DIR"'/lib/spec-validation.sh"
    tmp_file=$(mktemp)
    printf "tiny\n" > "$tmp_file"
    validation_rc=0
    validation_output=$(validate_spec_quality "$tmp_file" 2>/dev/null) || validation_rc=$?
    rm -f "$tmp_file"
    echo "MIN_SPEC_BYTES=$MIN_SPEC_BYTES"
    echo "SPECIFY_MAX_RETRIES=$SPECIFY_MAX_RETRIES"
    echo "SPECIFY_MAX_OPERATIONAL_FAILURES=$SPECIFY_MAX_OPERATIONAL_FAILURES"
    echo "MAX_BULLET_LINE_PCT=$MAX_BULLET_LINE_PCT"
    echo "VALIDATION_RC=$validation_rc"
    echo "VALIDATION_OUTPUT=$validation_output"
' 2>&1)
assert_contains "Warns on invalid MIN_SPEC_BYTES override" "Warning: MIN_SPEC_BYTES='oops' is not a valid non-negative integer. Using default (2048)." "$TC21_OUTPUT"
assert_contains "Warns on non-positive SPECIFY_MAX_RETRIES override" "Warning: SPECIFY_MAX_RETRIES='0' is not a valid positive integer. Using default (3)." "$TC21_OUTPUT"
assert_contains "Warns on invalid SPECIFY_MAX_OPERATIONAL_FAILURES override" "Warning: SPECIFY_MAX_OPERATIONAL_FAILURES='invalid' is not a valid positive integer. Using default (10)." "$TC21_OUTPUT"
assert_contains "Falls back MIN_SPEC_BYTES to default" "MIN_SPEC_BYTES=2048" "$TC21_OUTPUT"
assert_contains "Falls back SPECIFY_MAX_RETRIES to default" "SPECIFY_MAX_RETRIES=3" "$TC21_OUTPUT"
assert_contains "Falls back SPECIFY_MAX_OPERATIONAL_FAILURES to default" "SPECIFY_MAX_OPERATIONAL_FAILURES=10" "$TC21_OUTPUT"
assert_contains "Normalizes leading-zero numeric overrides" "MAX_BULLET_LINE_PCT=8" "$TC21_OUTPUT"
assert_contains "Validation still uses validated MIN_SPEC_BYTES default" "VALIDATION_RC=1" "$TC21_OUTPUT"
assert_contains "Size failure reports validated minimum threshold" "minimum=2048" "$TC21_OUTPUT"

# ---------------------------------------------------------------------------
# TC22: '+' bullets are included in bullet ratio detection
# ---------------------------------------------------------------------------
echo ""
echo "=== TC22: Plus-sign bullets count toward bullet ratio ==="
TC22_FILE=$(mktemp "/tmp/tc22_spec.XXXXXX")
cat > "$TC22_FILE" << 'SPEC'
+ bullet one
+ bullet two
+ bullet three
+ bullet four
+ bullet five
single prose line
SPEC
rc=0
output=$(_check_bullet_ratio "$TC22_FILE" 2>/dev/null) || rc=$?
assert_eq "Plus-sign bullets can trigger bullet ratio failure" "1" "$rc"
assert_contains "Bullet ratio output includes configured max threshold" "/80" "$output"
rm -f "$TC22_FILE"

# ---------------------------------------------------------------------------
# TC23: Bullet ratio ignores fenced code blocks and tab-only blank lines
# ---------------------------------------------------------------------------
echo ""
echo '=== TC23: Bullet ratio ignores fenced blocks (``` and ~~~) and tab-only blank lines ==='
TC23_FILE=$(mktemp "/tmp/tc23_spec.XXXXXX")
# The first line in the heredoc below is intentionally a tab-only blank line.
cat > "$TC23_FILE" << 'SPEC'
	
```bash
+ code bullet one
+ code bullet two
+ code bullet three
+ code bullet four
+ code bullet five
```

~~~python
+ tilde code bullet one
+ tilde code bullet two
+ tilde code bullet three
~~~

+ actual bullet one
+ actual bullet two
+ actual bullet three
single prose line
SPEC
rc=0
output=$(_check_bullet_ratio "$TC23_FILE" 2>/dev/null) || rc=$?
assert_eq "Fenced-block bullets do not count toward bullet ratio" "0" "$rc"
assert_eq "Passing bullet ratio produces no output" "" "$output"
rm -f "$TC23_FILE"

# ---------------------------------------------------------------------------
# TC24: Mandatory section check does not leak loop variable state
# ---------------------------------------------------------------------------
echo ""
echo "=== TC24: Mandatory section check keeps caller variables unchanged ==="
TC24_FILE=$(mktemp "/tmp/tc24_spec.XXXXXX")
create_valid_spec "$TC24_FILE"
section="caller-sentinel"
output=$(_check_mandatory_sections "$TC24_FILE")
assert_eq "Mandatory section check returns no missing sections for valid spec" "" "$output"
assert_eq "Mandatory section check does not overwrite caller section variable" "caller-sentinel" "$section"
rm -f "$TC24_FILE"

# ---------------------------------------------------------------------------
# TC25: Closing fence can be longer than opening fence (CommonMark)
# ---------------------------------------------------------------------------
echo ""
echo "=== TC25: Longer closing fence terminates fenced code block ==="
TC25_FILE=$(mktemp "/tmp/tc25_spec.XXXXXX")
cat > "$TC25_FILE" << 'SPEC'
```bash
+ fenced code bullet one
+ fenced code bullet two
````

+ actual bullet one
+ actual bullet two
+ actual bullet three
+ actual bullet four
+ actual bullet five
single prose line
SPEC
rc=0
output=$(_check_bullet_ratio "$TC25_FILE" 2>/dev/null) || rc=$?
assert_eq "Longer closing fence allows post-fence bullets to be counted" "1" "$rc"
assert_contains "Bullet ratio failure still reports configured threshold" "/80" "$output"
rm -f "$TC25_FILE"

# ---------------------------------------------------------------------------
# TC26: Fallback skeleton normalizes bullet-marked issue body lines
# ---------------------------------------------------------------------------
echo ""
echo "=== TC26: Fallback skeleton strips markdown bullet markers from issue body ==="
TC26_ISSUE_BODY=$'- unique-bullet-alpha\n- unique-bullet-beta\n- unique-bullet-gamma\n- unique-bullet-delta\n- unique-bullet-epsilon\n- unique-bullet-zeta\n- unique-bullet-eta\n- unique-bullet-theta\n- unique-bullet-iota\n- unique-bullet-kappa\n- unique-bullet-lambda\n- unique-bullet-mu'
rc=0
output=$(_generate_fallback_skeleton "Fallback Bullet Normalization" "$TC26_ISSUE_BODY" "1640" "https://github.com/ayaiayorg/agentic-devtools/pull/1640" 2>/dev/null) || rc=$?
assert_eq "Fallback skeleton generation succeeds for bullet-heavy issue body" "0" "$rc"
assert_contains "Fallback keeps issue body content text" "unique-bullet-alpha" "$output"
assert_not_contains "Fallback removes markdown bullet marker from issue body line" "- unique-bullet-alpha" "$output"

# ---------------------------------------------------------------------------
# TC27: Dynamic thresholds handle short/long/empty/200-char boundaries
# ---------------------------------------------------------------------------
echo ""
echo "=== TC27: _compute_dynamic_thresholds boundary behavior ==="
OLD_MIN_SPEC_BYTES_TC27="$MIN_SPEC_BYTES"
OLD_MIN_SPEC_BYTES_BASELINE_TC27="${MIN_SPEC_BYTES_BASELINE:-$MIN_SPEC_BYTES}"
OLD_REDUCTION_FACTOR_TC27="$AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR"
MIN_SPEC_BYTES=2048
MIN_SPEC_BYTES_BASELINE=2048
AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR="0.6"

_compute_dynamic_thresholds "short body"
assert_eq "Short body (<200 chars) reduces MIN_SPEC_BYTES" "1228" "$MIN_SPEC_BYTES"

body_200=$(printf 'a%.0s' {1..200})
_compute_dynamic_thresholds "$body_200"
assert_eq "Exactly 200 chars keeps baseline MIN_SPEC_BYTES" "2048" "$MIN_SPEC_BYTES"

body_long=$(printf 'a%.0s' {1..2001})
MIN_SPEC_BYTES=1228
_compute_dynamic_thresholds "$body_long"
assert_eq "Long body (>200 chars) resets MIN_SPEC_BYTES to baseline" "2048" "$MIN_SPEC_BYTES"

_compute_dynamic_thresholds ""
assert_eq "Empty body reduces MIN_SPEC_BYTES" "1228" "$MIN_SPEC_BYTES"

MIN_SPEC_BYTES="$OLD_MIN_SPEC_BYTES_TC27"
MIN_SPEC_BYTES_BASELINE="$OLD_MIN_SPEC_BYTES_BASELINE_TC27"
AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR="$OLD_REDUCTION_FACTOR_TC27"

# ---------------------------------------------------------------------------
# TC28: Reduction-factor validation falls back to default for invalid values
# ---------------------------------------------------------------------------
echo ""
echo "=== TC28: AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR invalid handling ==="
TC28_INVALID_OUTPUT=$(AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR="not-a-number" bash -c '
set -euo pipefail
SCRIPT_DIR="$1"
source "$SCRIPT_DIR/lib/spec-validation.sh"
printf "AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR=%s\n" "$AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR"
MIN_SPEC_BYTES=2048
MIN_SPEC_BYTES_BASELINE=2048
_compute_dynamic_thresholds "short body"
printf "MIN_SPEC_BYTES=%s\n" "$MIN_SPEC_BYTES"
' -- "$SCRIPT_DIR" 2>&1)
assert_contains "Warns on non-decimal reduction factor" "not a valid decimal. Using default (0.6)." "$TC28_INVALID_OUTPUT"
assert_contains "Invalid reduction factor falls back to 0.6" "AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR=0.6" "$TC28_INVALID_OUTPUT"
assert_contains "Fallback factor is applied to short-body reduction" "MIN_SPEC_BYTES=1228" "$TC28_INVALID_OUTPUT"

TC28_RANGE_OUTPUT=$(AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR="1.5" bash -c '
set -euo pipefail
SCRIPT_DIR="$1"
source "$SCRIPT_DIR/lib/spec-validation.sh"
printf "AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR=%s\n" "$AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR"
' -- "$SCRIPT_DIR" 2>&1)
assert_contains "Warns on out-of-range reduction factor" "outside valid range (0.0–1.0). Using default (0.6)." "$TC28_RANGE_OUTPUT"
assert_contains "Out-of-range reduction factor falls back to 0.6" "AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR=0.6" "$TC28_RANGE_OUTPUT"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==========================================="
echo "Results: ${PASS}/${TOTAL} passed, ${FAIL} failed"
echo "==========================================="

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0

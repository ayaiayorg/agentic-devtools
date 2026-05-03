# Feature Specification: SpecKit Pipeline — FR Test Coverage Validation

**Feature Branch**: `1202-speckit-pipeline-validate-each`
**Created**: 2026-04-15
**Status**: Draft
**Input**: GitHub Issue #1202 — Validate each FR has at least one test task
**Source Issue**: #1202 (<https://github.com/ayaiayorg/agentic-devtools/issues/1202>)

## Clarifications

### Session 2026-05-03

- Q: Where exactly should the test-coverage sub-pass be inserted within the existing detection passes (A–G) in `speckit.analyze.agent.md`, and should it be a new lettered category or a sub-pass within
  Category E (Coverage Gaps)? → A: It should be integrated as a sub-pass within Category E (Coverage Gaps), directly after the existing FR-to-task coverage check. This aligns with FR-010's requirement
  to integrate within the existing coverage-gaps analysis and avoids disrupting the established A–G category lettering. The sub-pass should be labeled "E.2 Test Coverage Validation" (with the existing
  coverage check becoming "E.1 Task Coverage").
- Q: FR-003 defines heuristic matching via shared user-story labels (e.g., `[US1]`), but what is the precise mapping rule from `[USn]` to FRs — is it positional (User Story 1 in document order),
  explicit heading text, or some other mechanism? → A: The mapping is positional by document order in `spec.md`: `[US1]` maps to FRs associated with the first user story section, `[US2]` maps to FRs
  associated with the second, and so on. The set of FRs associated with a user story section is derived by collecting all `FR-NNN` identifiers explicitly referenced anywhere within that section's
  text boundary (from the user story heading to the next same-level heading or the end of the User Stories block). References in acceptance-scenario prose, description text, and independent-test
  notes are all included. The user story number corresponds to the 1-based index of user story sections as they appear in the spec. If a task references `[USn]` and the spec has fewer than n user
  stories, it is treated as an unmapped reference and reported as a LOW finding.
- Q: When a task contains test-related keywords but no explicit FR reference and no `[USn]` label, should it be treated as unmapped (covering no FRs) or should there be a fallback heuristic (e.g.,
  keyword similarity to FR descriptions)? → A: The task should be treated as unmapped — it covers zero FRs for test-coverage purposes. No keyword-similarity fallback should be applied, as this would
  introduce non-deterministic behavior. The task should appear in the existing "Unmapped Tasks" section of the report, and a LOW finding should note that the test task lacks an FR or user-story
  mapping.
- Q: FR-006 defines happy-path keywords including "direct reference to P1 acceptance criteria with positive outcomes" — how should this semantic matching be implemented given that acceptance criteria
  are free-form text? → A: This clause should be interpreted narrowly: a task qualifies via "direct reference to P1 acceptance criteria" only if it explicitly cites an acceptance scenario identifier
  (e.g., "Acceptance Scenario 1 from US1") or quotes near-verbatim phrasing from a P1 acceptance scenario with a positive outcome. General semantic similarity is not sufficient. In practice, the
  keyword-based detection (happy path, success, nominal, etc.) will be the primary classification mechanism; the acceptance-criteria reference is a supplementary signal, not a fuzzy-match requirement.
- Q: NFR-003 requires zero false positives on existing `specs/` directory examples — should the implementation include an automated regression test that runs analysis against all existing spec
  directories, or is manual verification during development sufficient? → A: An automated regression test MUST be included. It should be a parameterized test that discovers all `specs/*/` directories
  containing both `spec.md` and `tasks.md`, runs the test-coverage validation logic against each, and asserts zero test-coverage findings are produced — unless the spec directory contains an explicit
  allowlist file (`expected-findings.txt`) enumerating the expected findings as stable keys (one per line). Two key formats are supported:
  (1) `FR-NNN:<kind>` for FR-scoped coverage-gap findings (e.g., `FR-002:no-test-task`, `FR-001:no-happy-path`), and
  (2) `TASK:<kind>` for task-scoped LOW findings not tied to a specific FR (e.g., `TASK:invalid-us-ref`, `TASK:unmapped-test-task`, `TASK:ambiguous-task`).
  When an allowlist is present the test asserts exact match (no new findings, no stale entries); when absent it asserts zero findings.
  This ensures NFR-003 is continuously enforced in CI, not just verified once.

## Problem Statement

The SpecKit analysis step (`speckit.analyze`) currently validates that each functional requirement (FR) maps to at least one task (the existing coverage-gaps validation),
but it does not distinguish between implementation tasks and **test** tasks. This gap means a spec can pass analysis with full task coverage yet have zero
test coverage for its most important requirements — exactly what happened in PR #1178, where FR-001 (the core feature) had infrastructure tests but no
happy-path test task.

This specification defines the rules for a dedicated **test coverage sub-pass** within the existing Category E (Coverage Gaps) analysis that ensures every FR has at least
one associated test task, with elevated severity for P1-associated FRs missing happy-path coverage. The sub-pass is designated **E.2 Test Coverage Validation** (with the existing task-coverage check
becoming **E.1 Task Coverage**), preserving the established A–G category structure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Detect FRs with no test task (Priority: P1)

As a developer running `/speckit.analyze`, I want the analysis report to flag any functional requirement that has zero associated test tasks,
so that I catch missing test coverage before implementation begins.

**Why this priority**: This is the core value proposition. Without it, SpecKit can produce implementation plans that appear complete but lack
test coverage for critical requirements — the exact problem that motivated this issue.

**Independent Test**: Can be fully tested by running `/speckit.analyze` against a `spec.md` with 3 FRs and a `tasks.md` where one FR has no
test-related task. The report must include a HIGH-severity finding for the uncovered FR and the Test Coverage Summary table must show the gap.

**Acceptance Scenarios**:

1. **Given** a `spec.md` containing FR-001, FR-002, and FR-003, and a `tasks.md` where FR-002 has no test task (only implementation tasks),
**When** the analysis runs, **Then** the findings table includes a HIGH-severity entry identifying FR-002 as lacking test coverage.
2. **Given** a `spec.md` with FR-001 through FR-005, and a `tasks.md` where every FR has at least one test task,
**When** the analysis runs, **Then** no test-coverage-gap findings are generated and the Test Coverage Summary confirms full test coverage.
3. **Given** a `spec.md` with FR-001 and a `tasks.md` containing a task
`T005 [US1] Write unit tests for feature validation in tests/test_feature.py` that references FR-001 by user-story mapping,
**When** the analysis runs, **Then** FR-001 is considered covered by test task T005.

---

### User Story 2 — Flag missing happy-path tests for P1 FRs as CRITICAL (Priority: P1)

As a developer running `/speckit.analyze`, I want the analysis to escalate to CRITICAL severity when any FR associated with a P1 user story has no
happy-path test task, so that the most important user-facing behavior is never left untested.

**Why this priority**: Equal to US1 because this was the exact failure mode in PR #1178 — the core feature (FR-001, P1 story) had no
happy-path test. Detecting the gap generically (US1) is necessary but insufficient;
the severity escalation ensures the finding cannot be dismissed as low-priority.

**Independent Test**: Can be tested by providing a `spec.md` with a P1 user story linked to FR-001 and a `tasks.md` that has
infrastructure/setup test tasks but no happy-path test for FR-001.
The report must contain a CRITICAL finding explicitly mentioning the absence of happy-path test coverage.

**Acceptance Scenarios**:

1. **Given** a `spec.md` where FR-001 is linked to the P1 user story, and a `tasks.md` with no test task for FR-001,
**When** the analysis runs, **Then** the finding is CRITICAL (not HIGH) and the summary text explicitly mentions "happy-path" and the P1 story.
2. **Given** a `spec.md` where FR-004 is linked to a P3 user story, and a `tasks.md` with no test task for FR-004,
**When** the analysis runs, **Then** the finding is HIGH (not CRITICAL) because FR-004 is not associated with a P1 story.
3. **Given** a `spec.md` where FR-001 is linked to P1, and a `tasks.md` with only negative/edge-case tests for FR-001 but no happy-path test,
**When** the analysis runs, **Then** the finding is CRITICAL because happy-path coverage is still missing despite other test types being present.

---

### User Story 3 — Test coverage summary in the analysis report (Priority: P2)

As a developer reviewing the analysis report, I want a dedicated test-coverage summary section that shows each FR, its associated test task IDs
(if any), and the test types detected (happy-path, edge-case, integration, e2e), so that I can quickly assess test completeness.

**Why this priority**: This provides visibility and actionability for the findings from US1 and US2. Without a clear summary,
developers must manually cross-reference the findings table with tasks.md.

**Independent Test**: Can be tested by running analysis against any spec+tasks pair and verifying the report contains a
"Test Coverage Summary" table with one row per FR.

**Acceptance Scenarios**:

1. **Given** a `spec.md` with FR-001 through FR-003 and a `tasks.md` with various test tasks,
**When** the analysis completes, **Then** the report includes a "Test Coverage Summary" table listing each FR,
its mapped test task IDs, detected test types, and a coverage status indicator.
2. **Given** a `tasks.md` with a task description `Write e2e tests validating the full user creation flow (FR-001, FR-003)`,
**When** the analysis runs, **Then** the test coverage summary maps that task to both FR-001 and FR-003, with test type "e2e".

---

### User Story 4 — Actionable remediation for test-coverage gaps (Priority: P3)

As a developer who sees a test-coverage finding, I want the analysis report to suggest a concrete next action
(e.g., "Run `/speckit.tasks` with an explicit request to include test tasks or happy-path tests" or "Add a test task for FR-002 covering happy-path scenario X"),
so that I can fix the gap without guessing.

**Why this priority**: Enhances developer experience but is not strictly required for gap detection.
The core detection (US1/US2) and visibility (US3) deliver value without remediation guidance.

**Independent Test**: Can be tested by confirming that every test-coverage finding in the report includes a non-empty
Recommendation column with an actionable suggestion.

**Acceptance Scenarios**:

1. **Given** a CRITICAL finding for FR-001 missing happy-path tests, **When** the report is generated,
**Then** the Recommendation column suggests re-running `/speckit.tasks` with explicit test generation
or manually adding a test task referencing FR-001.
2. **Given** a HIGH finding for FR-004 missing any test task, **When** the report is generated,
**Then** the Recommendation references the specific acceptance scenarios from the spec that should be tested.

---

### Edge Cases

- What happens when a `tasks.md` does not exist or is empty?
The analysis should report a CRITICAL finding that no tasks file exists or that the tasks file contains zero defined tasks,
superseding per-FR test coverage checks.
- What happens when an FR has no acceptance scenarios in `spec.md`?
The analysis should still flag missing test tasks (the FR exists and needs coverage)
but note in the finding that the FR also lacks testable acceptance criteria.
- What happens when a test task references an FR that does not exist in `spec.md`?
This is already covered by the existing unmapped-tasks validation and should remain as-is — no change needed.
- How are test tasks identified when they use synonyms (e.g., "check", "ensure", "smoke test")?
The keyword set must be extensible and include common synonyms beyond the initial set.
- What happens when a task is ambiguously both implementation and test (e.g., "Implement and verify user login flow")?
The task should be counted as a test task if it contains any test-related keyword,
but the analysis should note the ambiguity as a LOW finding.
- What happens when a test task contains a `[USn]` label but the spec has fewer than n user stories?
The task is treated as unmapped (covers zero FRs for test-coverage purposes), appears in the "Unmapped Tasks" section,
and a LOW finding notes the invalid user-story reference.
- What happens when a test task has test-related keywords but no explicit FR reference and no `[USn]` label?
The task is treated as unmapped — it covers zero FRs for test-coverage purposes. No keyword-similarity fallback
is applied. The task appears in the "Unmapped Tasks" section with a LOW finding noting the missing FR or user-story mapping.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The analysis MUST extract all FR identifiers (pattern: `FR-NNN`) from `spec.md` along with their associated
user story priority (P1, P2, P3) when determinable from the spec structure.
When an FR's priority cannot be determined (e.g., the FR is not nested under a clearly prioritized user story),
the analysis MUST default to HIGH severity for that FR (i.e., treat it as non-P1 for the purposes of FR-005's CRITICAL escalation)
and emit a LOW-severity informational finding noting the ambiguity.
This priority-ambiguity finding is a **standalone informational finding** with its own finding ID (e.g., `F-NN`)
and does NOT conflict with FR-005's de-duplication rule — FR-005 de-duplicates overlapping findings for the
**same FR and same validation concern** (i.e., test-coverage gaps), whereas the priority-ambiguity finding
addresses a distinct concern (metadata completeness). Both findings may coexist for the same FR without
violating de-duplication because they target different validation aspects.

- **FR-002**: The analysis MUST identify test-related tasks in `tasks.md` using a canonical set of keywords that at minimum includes:
`test`, `verify`, `validate`, `assert`, `spec test`, `specification test`, `e2e`, `integration test`, `unit test`, `smoke test`, `acceptance test`.
Additional keywords may be added by editing this canonical list (see FR-011 for extensibility).
Matching semantics use **case-insensitive matching** with two distinct strategies based on keyword length:
  - **Multi-word keywords** (e.g., `integration test`) are matched as literal phrases via substring search,
  with an **optional trailing `s` or `es` on the last token** —
  for example, the keyword `integration test` also matches `integration tests`.
  - **Single-word keywords** (e.g., `test`, `verify`) are matched with **word-boundary awareness** — they must appear as whole words
  (i.e., bounded by whitespace, punctuation, or start/end of string) to avoid false positives from substrings like "contest" or "unverified".

  **Word-boundary definition**: A word boundary is any position adjacent to a character that is NOT a letter,
  digit, or hyphen (`-`). Specifically: whitespace, underscores (`_`), slashes (`/`), periods (`.`),
  parentheses, brackets, commas, colons, semicolons, quotation marks, and start/end of string are all boundary positions.
  Hyphens are NOT boundaries (they connect compound words like `happy-path`).
  Consequently, single-word keywords do **not** match inside hyphenated compounds —
  e.g., the keyword `test` does NOT match within `unit-test` because the hyphen is not a boundary,
  and `path` does NOT match within `happy-path`.

  **Punctuation normalization (multi-word keywords only)**: When matching **multi-word keywords**,
  both the keyword and the target text MUST undergo hyphen/space normalization —
  hyphens (`-`) and spaces between word tokens are treated as equivalent.
  For example, the keyword `integration test` matches `integration-test`, `integration test`, and `integration-tests`
  in the task description. This normalization ensures consistent identification regardless of whether authors
  use hyphenated or space-separated compound terms.
  This normalization does **not** apply to single-word keyword matching — single-word keywords
  use the raw word-boundary definition above (where hyphens are not boundaries) and therefore
  cannot match individual tokens within hyphenated compounds.

Pluralization handling applies uniformly: single-word keywords allow a trailing `s`/`es` variant (e.g., `test` matches `tests`),
and multi-word keywords allow a trailing `s`/`es` on the last token only (e.g., `unit test` matches `unit tests`).

- **FR-003**: The analysis MUST map each identified test task to one or more FRs using two strategies:
(a) explicit FR identifier references in the task description (e.g., `FR-001`),
and (b) heuristic matching via shared user-story labels (e.g., `[US1]` in the task maps to FRs associated with User Story 1 in the spec).
The user-story label mapping is positional by document order: `[US1]` maps to FRs associated with the first user story section,
`[US2]` to FRs associated with the second, and so on.
The set of FRs associated with a user story section is derived by collecting all `FR-NNN` identifiers
explicitly referenced anywhere within that section's text boundary (from the user story heading
to the next same-level heading or the end of the User Stories block); references in acceptance-scenario
prose, description text, and independent-test notes are all included.
If a task references `[USn]` and the spec has fewer than n user stories,
the reference is treated as unmapped and reported as a LOW finding.
Test tasks that contain test-related keywords but lack both an explicit FR reference and a `[USn]` label
are treated as unmapped — they cover zero FRs for test-coverage purposes and appear in the "Unmapped Tasks" section.

- **FR-004**: The analysis MUST report any FR with zero associated test tasks as a finding with severity HIGH in the findings table.

- **FR-005**: The analysis MUST escalate to CRITICAL severity when any FR associated with a P1 user story has no happy-path test task.
When an FR triggers both FR-004 (zero test tasks) and FR-005 (P1 FR missing happy-path), the analysis MUST produce
a single finding using the highest applicable severity (CRITICAL), not duplicate findings for the same FR.

- **FR-006**: Happy-path test tasks MUST be distinguished from edge-case, negative, and infrastructure test tasks.
A task qualifies as happy-path if its description indicates testing of the primary success scenario
(keywords: `happy path`, `happy-path`, `success`, `nominal`, `primary flow`, `basic flow`, `main scenario`,
or direct reference to P1 acceptance criteria with positive outcomes — where "direct reference" means the task
explicitly cites an acceptance scenario identifier such as "Acceptance Scenario 1 from US1" or quotes near-verbatim
phrasing from a P1 acceptance scenario; general semantic similarity is not sufficient).

  **Explicit test-type keyword sets**: Each supported test type has a defined keyword set for classification:

  | Test Type | Keywords |
  |-----------|----------|
  | happy-path | `happy path`, `happy-path`, `success`, `nominal`, `primary flow`, `basic flow`, `main scenario` |
  | edge-case | `edge case`, `edge-case`, `boundary`, `corner case`, `corner-case`, `limit`, `overflow`, `underflow` |
  | negative | `negative`, `failure`, `error case`, `error-case`, `invalid`, `reject`, `malformed`, `unauthorized` |
  | integration | `integration test`, `integration-test`, `cross-module`, `cross-component`, `end-to-end integration` |
  | e2e | `e2e`, `end to end`, `end-to-end`, `full flow`, `full-flow`, `system test`, `system-test` |
  | unit | `unit test`, `unit-test`, `isolated test`, `isolated-test`, `function test`, `function-test` |
  | infrastructure | `infrastructure`, `setup test`, `setup-test`, `configuration test`, `config test`, `scaffold`, `fixture` |

  **Multiple type assignment**: A single task MAY match multiple test types simultaneously.
  When a task matches more than one category, ALL matched types are recorded in the Test Coverage Summary
  (e.g., a task matching both "integration" and "e2e" keywords is reported with types `integration, e2e`).
  There is no precedence between types — they are additive, not exclusive.

  Test-type classification matching semantics: keyword matching for test-type classification (happy-path, edge-case,
negative, etc.) follows the same punctuation normalization and case-insensitive rules as FR-002's test-task
identification — specifically, hyphens and spaces between keyword tokens are treated as equivalent
(e.g., `happy path`, `happy-path`, and `HAPPY-PATH` all classify a task as happy-path).

- **FR-007**: The analysis report MUST include a "Test Coverage Summary" table with columns:
FR identifier, associated user story, test task IDs (or "None"), detected test types, and coverage status.
When an FR's associated user story cannot be determined (see FR-001), the "associated user story" column MUST display "N/A".

- **FR-008**: Each test-coverage finding MUST include an actionable recommendation in the Recommendation column
referencing the specific FR and its acceptance scenarios (or "N/A" when none exist).
When an FR has no acceptance scenarios defined in `spec.md`, the scenario reference MUST display "N/A" and the
recommendation MUST explicitly note that the FR lacks testable acceptance criteria and suggest adding acceptance
scenarios to the spec before writing test tasks. This reconciles with the Edge Cases constraint that FRs without
acceptance scenarios are still flagged for missing test coverage.

- **FR-009**: The analysis MUST treat the absence of a `tasks.md` file, or a `tasks.md` file that is empty (zero tasks defined), as a CRITICAL finding
that supersedes individual FR test-coverage checks.

- **FR-010**: The test-coverage validation MUST be integrated within the existing Category E (Coverage Gaps) analysis
of `speckit.analyze` as sub-pass **E.2 Test Coverage Validation** (with the existing task-coverage check designated **E.1 Task Coverage**),
preserving backward compatibility with all other analysis passes (A, B, C, D, F, G) and the established category lettering.

- **FR-011**: The keyword set used for test-task identification MUST be defined as a discoverable, enumerated list
in a clearly marked, single-edit location (e.g., a dedicated configuration section) so that it can be extended without structural changes.

### Non-Functional Requirements

- **NFR-001**: The test-coverage validation MUST NOT add more than negligible overhead to total analysis execution time
(i.e., it does not introduce additional external calls and operates only on already-loaded artifacts).

- **NFR-002**: Findings from the test-coverage sub-pass MUST use the same sequential ID format (`F-NN`), severity scale,
and table structure as existing analysis findings, maintaining report consistency.

- **NFR-003**: The validation MUST produce zero false positives on the existing `specs/` directory examples —
any existing spec+tasks pair that already has adequate test coverage must not generate spurious findings.
This MUST be enforced via an automated parameterized regression test that discovers all `specs/*/` directories
containing both `spec.md` and `tasks.md`, runs the test-coverage validation logic against each, and asserts
zero test-coverage findings are produced — unless the spec directory contains an explicit allowlist file
(`expected-findings.txt`) enumerating expected findings as stable keys (one per line) that are known and accepted.
Two key formats are supported:
(1) `FR-NNN:<kind>` for FR-scoped coverage-gap findings (e.g., `FR-002:no-test-task`, `FR-001:no-happy-path`), and
(2) `TASK:<kind>` for task-scoped LOW findings not tied to a specific FR (e.g., `TASK:invalid-us-ref`,
`TASK:unmapped-test-task`, `TASK:ambiguous-task`).
Task-scoped keys use **set semantics** (deduplicated by kind): if multiple tasks produce the same kind
(e.g., two distinct unmapped test tasks both emit `TASK:unmapped-test-task`), the key appears only once
in both the generated set and the allowlist. This is intentional — the allowlist captures which *kinds*
of findings are accepted, not their multiplicity.
The `<kind>` suffix corresponds to the finding type emitted by E.2 (e.g., `no-test-task`, `no-happy-path`,
`invalid-us-ref`, `unmapped-test-task`, `ambiguous-task`),
making entries resilient to sequential `F-NN` ID renumbering caused by other passes.
When an allowlist file is present, the test asserts that the set of generated finding keys exactly matches
the allowlist (no new findings, no stale entries). When no allowlist file is present, the test asserts
zero findings. This test MUST run in CI to continuously enforce NFR-003.

- **NFR-004**: The analysis output MUST remain parseable by downstream consumers (e.g., `speckit.implement`, human reviewers)
without format changes beyond the additive "Test Coverage Summary" table.

### Key Entities

- **FR Identifier**: A functional requirement tag in `spec.md` following the `FR-NNN` pattern,
associated with a user story priority level.
- **Test Task**: A task in `tasks.md` whose description contains test-related keywords,
associated with one or more FRs via explicit reference or heuristic matching.
- **Test Type Classification**: A categorization of a test task as one of: happy-path, edge-case, negative, integration, e2e, unit,
or infrastructure — derived from keywords in the task description.
- **Test Coverage Mapping**: The relationship between an FR and its associated test tasks,
including coverage status (covered, uncovered) and test types present.
- **User-Story Label**: A tag in the format `[USn]` in `tasks.md` that maps a task to FRs under the nth user story
(1-based, positional by document order) in `spec.md`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running `/speckit.analyze` on a minimal synthetic fixture that reproduces the PR #1178 failure mode produces a CRITICAL finding
for FR-001 missing happy-path test coverage — the exact gap that motivated this issue.
The fixture MUST be checked in at `specs/1202-speckit-pipeline-validate-each/fixtures/sc-001/` containing a `spec.md` (with a P1 FR)
and a `tasks.md` (with implementation tasks but no happy-path test task for that FR), ensuring SC-001 remains verifiable in CI
independently of external PR artifacts.

- **SC-002**: Running `/speckit.analyze` on all existing `specs/` directory examples produces no new false-positive test-coverage findings —
backward compatibility is maintained. This is verified by the automated regression test described in NFR-003,
which asserts that each spec directory's test-coverage (E.2) findings exactly match its allowlist (or zero findings when no allowlist exists).

- **SC-003**: The analysis report for any spec with 3+ FRs includes a "Test Coverage Summary" table
with one row per FR and accurate test task mapping.

- **SC-004**: 100% of test-coverage findings include a non-empty, actionable Recommendation that references the specific FR
and suggests a concrete remediation step.

- **SC-005**: The distinction between CRITICAL (P1 FR missing happy-path) and HIGH (any FR missing test task) severity
is consistently applied across all analysis runs.

- **SC-006**: The test-task keyword list is explicitly enumerated in a discoverable, single-edit location
and can be extended by editing that clearly marked section.

---
*Generated by Copilot SDK (claude-opus-4.6)*

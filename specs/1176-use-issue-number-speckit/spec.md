# Specification: Use Issue Number in SpecKit Directories

## Status

**Normative** — this document is the source of truth for implementation and verification of issue **#1176**.
It supersedes any prior clarification-only summary.

## Problem Statement

The SpecKit workflow currently creates feature/spec directories using the next available three-digit sequence
(for example `001-my-feature`, `002-another-feature`). For GitHub-driven work, the directory identity must
instead be anchored to the GitHub issue number when one is available so that:

- the spec directory is stable and reproducible for the same issue,
- artifacts across scripts and reruns resolve to the same location,
- generated work is easier to trace back to the originating issue,
- issue-numbered directories do not interfere with legacy sequence-based creation.

This change applies to the issue-driven generation flow and must preserve backward compatibility for the
legacy "create new feature" flow that still uses three-digit autoincrement prefixes.

## Goals

1. Use the GitHub issue number as the leading directory identifier for issue-driven spec generation.
2. Keep legacy autoincrement behavior for non-issue-driven feature creation.
3. Ensure Bash and PowerShell implementations behave consistently where both exist.
4. Ensure rerunning generation for the same issue reuses the same directory path, even if the issue title changes.
5. Make the generated spec directory path deterministic, validated, and safe.

## Non-Goals

- Renaming pre-existing spec directories created under old rules.
- Migrating legacy three-digit directories to issue-number-based names.
- Changing the semantics of non-issue-driven feature creation beyond required filtering of candidate directories.
- Supporting arbitrary identifier formats beyond the rules defined below.

## Definitions

- **Issue-driven generation**: The flow initiated from a GitHub issue, implemented by `generate-spec-from-issue.sh`.
- **Legacy feature creation**: The non-issue-driven flow implemented by the existing create-new-feature scripts.
- **Spec directory**: The feature directory under the SpecKit/specs area whose name begins with an identifier and is
  followed by a slug, for example `1176-use-issue-number-speckit`.
- **Issue number**: The numeric GitHub issue identifier, e.g. `1176`.
- **Three-digit sequence directory**: A directory whose name begins with exactly three digits followed by `-`,
  matching `^[0-9]{3}-`.
- **Issue-number directory**: A directory whose name begins with the raw (unpadded) GitHub issue number
  followed by `-`, e.g. `1176-use-issue-number-speckit` or `42-my-feature`. Issue numbers are **never
  zero-padded** in directory names, so issue #42 produces `42-my-feature` (not `042-my-feature`). For
  issue numbers with fewer than 3 digits (1–99) or more than 3 digits (1000+), the unpadded prefix is
  naturally excluded from the legacy `^[0-9]{3}-` autoincrement pattern. However, **three-digit issue
  numbers (100–999)** produce prefixes like `157-` that *do* match `^[0-9]{3}-`, creating an overlap
  with the legacy namespace. This overlap is an accepted trade-off documented in edge case #8 and FR-009.
- **Slug**: The sanitized, lowercase, hyphenated title-derived suffix appended after the numeric identifier.

## Key Entities

### 1. Spec Directory Name

A directory name with the format:

- issue-driven flow: `<ISSUE_NUMBER>-<slug>` where `ISSUE_NUMBER` is the raw unpadded GitHub issue number
  (e.g., `42-my-feature`, `1176-use-issue-number-speckit`)
- legacy flow: `<NNN>-<slug>` where `NNN` is a zero-padded three-digit autoincremented sequence
  (e.g., `001-my-feature`, `042-my-feature`)

### 2. Issue Metadata

The source data used by issue-driven generation, including:

- issue number,
- issue title,
- issue body or description where applicable.

### 3. Full Pipeline Artifacts

All generated outputs whose paths depend on the chosen spec directory, including:

- the spec directory itself,
- generated `spec.md`,
- plan/tasks/prompts or equivalent downstream artifacts,
- any rerun outputs that must resolve to the same issue directory.

## Functional Requirements

### FR-001 Issue-driven directory naming

The issue-driven generation flow **must** create or resolve the target spec directory using the GitHub issue number
as the leading identifier instead of a three-digit autoincrement sequence.

Example:

- Issue `#1176` titled `Use Issue Number in SpecKit Directories`
- Target directory: `1176-use-issue-number-speckit`

### FR-002 Directory slug generation

The slug portion of the directory name **must** be derived from the issue title using the existing title
sanitization rules already used by the feature/spec generation workflow, unless those rules would produce an empty
slug, in which case a safe non-empty fallback slug must be used.

The implementation of this issue does not redefine the sanitization algorithm; it requires that the issue number
prefix be combined with the sanitized slug deterministically.

### FR-003 Stable issue identity

For issue-driven generation, the issue number **must** be treated as the canonical identity of the spec directory.
Different titles for the same issue **must not** cause creation of different spec directories.

### FR-004 Collision check behavior for issue-driven flow

`generate-spec-from-issue.sh` **must** check whether the target issue-numbered directory already exists before
attempting to create a new directory.

If the target directory already exists, the script **must** reuse that directory rather than failing due to the
existing path or allocating a different numeric prefix.

### FR-005 Legacy create-new-feature behavior remains sequence-based

The non-issue-driven creation flow **must** continue to use a three-digit autoincrement sequence and **must not**
switch to issue numbers.

This requirement preserves existing behavior for workflows that do not originate from a GitHub issue.

### FR-006 Backward compatibility with existing directories

Existing sequence-based directories and existing issue-numbered directories **must** remain valid on disk.
The implementation **must not** require migration or renaming of previously created directories.

### FR-007 Bash autoincrement candidate filtering

Any Bash logic that determines the highest existing numeric sequence for legacy directory creation **must** only
consider directories that match `^[0-9]{3}-`.

Directories using issue-number prefixes such as `1176-...` **must not** be treated as sequence candidates.

### FR-008 PowerShell autoincrement candidate filtering

Any PowerShell logic that determines the highest existing numeric sequence for legacy directory creation, including
logic used by `create-new-feature.ps1` and its helper functions such as `Get-HighestNumberFrom*`, **must** only
consider directories that match `^\d{3}-`.

Directories using issue-number prefixes such as `1176-...` **must not** be treated as sequence candidates.

### FR-009 No sequence gaps caused by issue-number directories

The presence of issue-numbered directories **must not** affect the next sequence number chosen for legacy
three-digit directory creation, **except** for three-digit issue numbers (100–999) whose unpadded prefixes
coincidentally match the legacy `^[0-9]{3}-` pattern. In that case the autoincrement scanner may count
the issue directory as a sequence candidate, potentially skipping one number. This is an accepted trade-off
(see edge case #8) because: (a) such collisions are rare in practice, (b) the resulting gap is harmless
and limited to a single skipped number, and (c) the alternative — changing the naming scheme or adding
a marker prefix — introduces unnecessary complexity.

Example (no overlap):

- Existing directories: `001-foo`, `002-bar`, `1176-use-issue-number-speckit`
- Next legacy directory created by autoincrement: `003-baz`

Example (3-digit issue overlap — accepted):

- Existing directories: `001-foo`, `002-bar`, `117-some-issue`
- Next legacy directory created by autoincrement: `118-…` (skips to 118; accepted trade-off)

### FR-010 Downstream artifact path consistency

All downstream outputs produced by the issue-driven flow **must** use the reused or created issue-numbered spec
directory as their base path so that the full pipeline artifacts remain colocated and deterministic across reruns.

### FR-011 ISSUE_NUMBER validation at script entry

`generate-spec-from-issue.sh` **must** validate `ISSUE_NUMBER` at script entry before using it to derive paths.

Validation rules:

- `ISSUE_NUMBER` is required for issue-driven generation.
- `ISSUE_NUMBER` must contain only decimal digits.
- `ISSUE_NUMBER` must represent a positive integer greater than zero.
- If validation fails, the script must stop with a clear error and must not create or modify directories.

### FR-012 Rerun behavior when the issue title changes

When issue-driven generation is rerun for the same issue number and the newly computed slug differs from the slug
of an already existing directory for that issue, the flow **must** reuse the existing issue-numbered directory path
rather than creating a second directory for the same issue.

This preserves a stable artifact location keyed by issue number.

### FR-013 Workflow rerun idempotency

The `speckit-issue-trigger.yml` workflow **must** handle reruns for the same issue idempotently. When a remote
branch and/or PR already exists for the issue, the workflow must not fail due to:

- `git checkout -b` on an already existing branch, or
- `git push -u origin` being rejected as a non-fast-forward push.

The workflow must detect existing remote branches and update them (e.g., checkout and reset, or force-push
with lease) rather than attempting to create them afresh.

### FR-014 `.specify` helper compatibility with issue-number branches

Shared `.specify` helpers in `common.sh` that enforce branch-name conventions — specifically
`check_feature_branch` and `find_feature_dir_by_prefix` — **must** accept both legacy 3-digit prefixed
branches (`^[0-9]{3}-`) and longer numeric issue-number branches (e.g., `1176-...`), so that issue-number
branches remain usable with `.specify` tooling.

## User Stories

### US1 — Generate a spec from a GitHub issue

As a developer using the issue-driven SpecKit workflow,
I want the generated spec directory to use the GitHub issue number,
so that the spec is directly traceable to the originating issue.

#### Scenarios

1. **Happy path**
   - Given issue `#1176` with title `Use Issue Number in SpecKit Directories`
   - When I run the issue-driven generation flow
   - Then the target directory is `1176-use-issue-number-speckit`
   - And generated artifacts are written under that directory

2. **Existing issue directory**
   - Given directory `1176-use-issue-number-speckit` already exists
   - When I rerun the issue-driven generation flow for issue `#1176`
   - Then the existing directory is reused
   - And the run does not fail due to the directory already existing

3. **No impact on downstream artifact placement**
   - Given issue-driven generation succeeds
   - When additional pipeline artifacts are produced
   - Then they are written relative to the same issue-numbered spec directory

4. **Changed issue title on rerun**
   - Given issue `#1176` previously generated `1176-use-issue-number-speckit`
   - And the issue title later changes such that the new slug would differ
   - When I rerun the issue-driven generation flow for issue `#1176`
   - Then the existing `1176-use-issue-number-speckit` directory is reused
   - And no second `1176-...` directory is created for that same issue

5. **Invalid issue number**
   - Given `ISSUE_NUMBER` is missing, non-numeric, zero, or negative
   - When I invoke `generate-spec-from-issue.sh`
   - Then the script exits with a clear validation error
   - And no spec directory is created or modified

### US2 — Preserve stable paths across reruns

As a developer rerunning generation for an existing GitHub issue,
I want the workflow to resolve to the same directory every time,
so that edits and generated artifacts stay in one place.

#### Scenarios

1. **Same title, same issue**
   - Given an issue-numbered directory already exists for the issue
   - When generation is rerun with the same title
   - Then the same directory is reused

2. **Existing artifacts present**
   - Given plan/spec/tasks or other generated files already exist in the issue directory
   - When generation is rerun for the same issue
   - Then the workflow continues to target that directory
   - And existing artifacts are not displaced into a new issue directory

3. **Fresh generation**
   - Given no directory exists yet for the issue
   - When generation is run
   - Then a new issue-numbered directory is created

4. **Changed title**
   - Given an existing issue-numbered directory for the issue uses a slug based on an older title
   - When generation is rerun after the title changes
   - Then the existing path is reused as the canonical path for that issue

### US3 — Preserve legacy autoincrement for non-issue flows

As a developer using the legacy create-new-feature workflow,
I want three-digit numbering to continue working correctly,
so that issue-numbered directories do not disturb the sequence.

#### Scenarios

1. **Ignore issue-numbered directories in Bash**
   - Given existing directories `001-alpha`, `002-beta`, and `1176-use-issue-number-speckit`
   - When the Bash legacy creation flow computes the next sequence
   - Then it ignores `1176-use-issue-number-speckit`
   - And selects `003`

2. **Ignore issue-numbered directories in PowerShell**
   - Given existing directories `001-alpha`, `002-beta`, and `1176-use-issue-number-speckit`
   - When the PowerShell legacy creation flow computes the next sequence
   - Then it ignores `1176-use-issue-number-speckit`
   - And selects `003`

3. **Mixed directory population**
   - Given the specs directory contains both legacy three-digit directories and issue-numbered directories
   - When the next legacy feature directory is created
   - Then only names matching the exact three-digit pattern influence the sequence

## Scenario Catalog

### SC-001 Create issue-numbered directory

Verify that issue-driven generation creates `<ISSUE_NUMBER>-<slug>` instead of `<NNN>-<slug>`.

### SC-002 Reuse existing issue directory

Verify that rerunning issue-driven generation for the same issue reuses the existing directory instead of creating
a new one.

### SC-003 Validate issue number early

Verify that invalid `ISSUE_NUMBER` values are rejected at the start of `generate-spec-from-issue.sh` and that no
filesystem changes occur.

### SC-004 Changed title does not create a second issue directory

Verify that rerunning generation for the same issue after a title change still resolves to the original
issue-numbered directory.

### SC-005 Legacy Bash numbering ignores issue-numbered directories

Verify that Bash autoincrement logic only considers directories matching `^[0-9]{3}-`.

### SC-006 Legacy PowerShell numbering ignores issue-numbered directories

Verify that PowerShell autoincrement logic only considers directories matching `^\d{3}-`, including the logic used
by `create-new-feature.ps1` helper functions.

## Edge Cases and Required Outcomes

1. **Existing mixed directories**
   - If both `003-something` and `1176-something-else` exist, only `003-something` is a sequence candidate.

2. **Issue title sanitizes differently on rerun**
   - The existing directory for the issue remains authoritative and must be reused.

3. **Issue number is malformed**
   - The issue-driven script must fail before path computation or directory creation.

4. **Issue number has leading zeros in input**
   - Validation **must reject** leading zeros (e.g., `042` is invalid input). The `^[1-9][0-9]*$` validation
     rule enforces this. Zero-padding is exclusively a legacy autoincrement convention and must not be applied
     to issue-driven directory naming. This prevents padded issue inputs such as `042-` from masquerading as
     legacy `^[0-9]{3}-` directories and avoids collisions for unpadded one- and two-digit issue numbers; the
     accepted overlap for natural three-digit issue numbers is covered separately in edge case #8 / FR-009.

5. **Slug sanitization yields an empty result**
   - The flow must still produce a safe non-empty directory name suffix using the implementation's fallback behavior.

6. **Directory already exists with content**
   - Reruns must reuse the path rather than creating a sibling directory for the same issue.

7. **Presence of large issue numbers**
   - Issue-number prefixes with more than three digits are valid for issue-driven generation and must not be
     interpreted as legacy sequence numbers.

8. **Issue numbers below 1000 (1–999)**
   - Issue-driven directories for these issue numbers use the raw unpadded number (e.g., issue #42 → `42-`,
     issue #7 → `7-`). Because the legacy pattern requires exactly three digits (`^[0-9]{3}-`), unpadded
     one- or two-digit prefixes (`7-`, `42-`) do not match it and are safely excluded from autoincrement
     scanning. **Three-digit issue numbers (100–999)**, however, produce prefixes like `157-` that *do*
     match `^[0-9]{3}-`, creating an overlap with the legacy autoincrement namespace. The autoincrement
     scanner may therefore count such a directory as a sequence candidate and skip one number. This is
     explicitly allowed by FR-009's exception clause for three-digit issue numbers and is an accepted
     trade-off because: (a) in practice, the autoincrement counter is typically well below 100, making
     actual collisions unlikely; (b) even when a collision occurs, the impact is limited to skipping a
     single sequence number; and (c) avoiding the overlap entirely would require a more complex naming
     scheme that adds unnecessary friction for a marginal edge case.

## Implementation Constraints

1. `generate-spec-from-issue.sh` is the only script required to perform issue-number validation at script entry.
2. Collision detection and reuse for the issue-driven flow must occur in `generate-spec-from-issue.sh`.
3. Legacy autoincrement behavior remains owned by the create-new-feature scripts and helpers.
4. Bash and PowerShell legacy flows must remain behaviorally aligned with respect to filtering autoincrement
   candidates to exact three-digit prefixes.
5. `speckit-issue-trigger.yml` must be updated for rerun idempotency (FR-013) as part of this feature.
6. `common.sh` branch validation and prefix-matching helpers must be updated for issue-number branch
   compatibility (FR-014) as part of this feature.

## Acceptance Criteria

The implementation is complete only when all of the following are true:

1. Running the issue-driven generation flow for issue `#1176` creates or resolves `1176-use-issue-number-speckit`.
2. Rerunning the issue-driven flow for the same issue reuses the same directory.
3. Rerunning after changing the issue title still reuses the original issue-numbered directory.
4. Invalid `ISSUE_NUMBER` values are rejected immediately by `generate-spec-from-issue.sh`.
5. Legacy Bash autoincrement ignores issue-numbered directories and only matches `^[0-9]{3}-`.
6. Legacy PowerShell autoincrement ignores issue-numbered directories and only matches `^\d{3}-`.
7. The presence of issue-numbered directories does not create sequence gaps for legacy three-digit numbering,
   except that issue-numbered directories with exact three-digit prefixes (`100`-`999`) may be counted by
   legacy matching and therefore may cause a skipped number.
8. Downstream generated artifacts remain under the resolved issue-numbered directory.
9. Rerunning the `speckit-issue-trigger.yml` workflow for an issue that already has a remote branch/PR
   does not fail; the workflow updates the existing branch idempotently.
10. `check_feature_branch` in `common.sh` accepts issue-number branches (e.g., `1176-...`) without error.
11. `find_feature_dir_by_prefix` in `common.sh` correctly resolves issue-numbered spec directories from
    issue-number branches.

## Verification Guidance

Verification should include:

- unit or script-level coverage for issue-number validation,
- tests for issue-driven directory creation and reuse,
- tests for changed-title reruns,
- tests for Bash three-digit filtering,
- tests for PowerShell three-digit filtering,
- tests confirming mixed directory populations do not affect legacy numbering,
- tests for workflow rerun idempotency (existing branch/PR scenario),
- tests for `check_feature_branch` and `find_feature_dir_by_prefix` accepting issue-number branches.

## Resolved Clarifications Incorporated Into This Spec

1. **FR-008 autoincrement isolation** — only exact three-digit prefixes are sequence candidates.
2. **PowerShell parity** — `create-new-feature.ps1` helpers must apply the same filtering behavior.
3. **Re-run with changed title** — the existing issue-numbered path is reused.
4. **Collision check location** — issue-driven collision handling belongs in `generate-spec-from-issue.sh`.
5. **ISSUE_NUMBER validation location** — validation occurs at entry in `generate-spec-from-issue.sh`.

---
*Generated by Copilot SDK (claude-opus-4.6)*

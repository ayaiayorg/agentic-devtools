# Implementation Plan: Use Issue Number in SpecKit Directories

**Feature**: 1176-use-issue-number-speckit
**Source Issue**: #1176

## 1. Technical Context

### Technology Stack

- **Shell**: Bash (`.github/scripts/speckit-trigger/`, `.specify/scripts/bash/`)
- **PowerShell**: `.specify/scripts/powershell/`
- **CI/CD**: GitHub Actions (`speckit-issue-trigger.yml`)
- **Python**: Copilot SDK wrapper (`copilot_generate.py`) — not modified

### Key Files (Modification Targets)

| File | Role |
|------|------|
| `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` | CI pipeline: generates spec from labeled issue |
| `.specify/scripts/bash/create-new-feature.sh` | Local dev: creates feature branch + spec dir |
| `.specify/scripts/powershell/create-new-feature.ps1` | Local dev (Windows): creates feature branch + spec dir |
| `.github/scripts/speckit-trigger/check-idempotency.sh` | CI pipeline: detects existing specs for an issue |

### Architecture Decision: Issue-Number Mode vs. Autoincrement Mode

The `generate-spec-from-issue.sh` script uses the GitHub issue number as the directory
prefix **without zero-padding** (e.g., issue #42 → `42-short-name`, issue #1176 →
`1176-short-name`). The local `create-new-feature.sh` and
`create-new-feature.ps1` scripts continue to use legacy autoincrement with a
zero-padded 3-digit prefix (e.g., `001-short-name`, `042-short-name`). Both modes must
coexist: the autoincrement counter must **ignore** issue-numbered directories wherever
they do not overlap the legacy `^[0-9]{3}-` namespace, so their presence does not
create sequence gaps except for the accepted 3-digit issue-number exception described
in FR-009 / edge case #8.

### Filtering Rule (Central Design Decision)

**Autoincrement directories**: Match `^[0-9]{3}-` (exactly 3 digits followed by hyphen).
These are the legacy locally generated directories only.

**Issue-numbered directories**: Use the raw GitHub issue number prefix, with no
zero-padding added for compatibility with autoincrement scanning. Examples: `42-`,
`1176-`. For issue numbers with fewer than 3 digits (1–99), the prefix remains unpadded (`42-`, not
`042-`), so it does not match the legacy `^[0-9]{3}-` autoincrement pattern. For
issue numbers with 4+ digits (1000+), the prefix naturally exceeds the 3-digit
pattern. **Three-digit issue numbers (100–999)** produce prefixes like `157-` that
*do* match `^[0-9]{3}-`, creating an overlap with the legacy namespace. This is an
accepted trade-off (see spec edge case #8 and FR-009): in practice, the autoincrement
counter is typically well below 100, and even if a collision occurs the impact is
limited to skipping a single sequence number.

The **autoincrement scanner** (`get_highest_from_specs`, `get_highest_from_branches`,
`get_next_feature_number`) must filter to `^[0-9]{3}-` only. For issue numbers
outside the 100–999 range, this filter cleanly excludes issue-numbered directories
from the autoincrement counter. For issue numbers 100–999, the overlap is accepted
per FR-009.

## 2. Research Summary

The research findings are summarized below.

Key decisions:

1. **3-digit filter regex** — `^[0-9]{3}-` in Bash, `^\d{3}-` in PowerShell. Applied
   uniformly to spec dirs AND branch scanning.
2. **Collision handling** — in `generate-spec-from-issue.sh` only; detect existing dir
   with same issue number prefix and reuse it.
3. **Re-run with changed title** — reuse existing directory path (do not create a new one).
4. **ISSUE_NUMBER validation** — at script entry in `generate-spec-from-issue.sh`;
   must be a positive integer.
5. **PowerShell parity** — both `Get-HighestNumberFromSpecs` and
   `Get-HighestNumberFromBranches` updated to filter `^\d{3}-`.

## 3. Design Overview

### Current State (Bugs)

| Script | Function | Current Regex | Bug |
|--------|----------|---------------|-----|
| `create-new-feature.sh` | `get_highest_from_specs` | `grep -o '^[0-9]\+'` | Matches ANY leading digits (e.g., `42-foo` → 42) |
| `create-new-feature.ps1` | `Get-HighestNumberFromSpecs` | `'^(\d+)'` | Matches ANY leading digits |
| `create-new-feature.ps1` | `Get-HighestNumberFromBranches` | `'^(\d+)-'` | Matches ANY leading digits followed by hyphen |
| `generate-spec-from-issue.sh` | `get_next_feature_number` (spec scan) | `grep -o '^[0-9]\+'` | Matches ANY leading digits |
| `generate-spec-from-issue.sh` | No ISSUE_NUMBER validation | — | Script proceeds with invalid input |
| `generate-spec-from-issue.sh` | No collision detection | — | Lacks deterministic issue-based dir reuse; reruns may create a new dir and concurrent runs may collide/fail loudly |

### Target State

```text
┌──────────────────────────────────────────────────────────────┐
│ generate-spec-from-issue.sh (CI pipeline)                    │
│                                                              │
│  1. Validate ISSUE_NUMBER (positive integer)         FR-011  │
│  2. Scan for existing dir with issue-number prefix   FR-004  │
│     → If found: reuse directory path                 FR-012  │
│     → If not found: create <ISSUE_NUMBER>-<slug>     FR-004  │
│  3. Autoincrement filter: ^[0-9]{3}- only            FR-007  │
│  4. Proceed with spec generation pipeline                    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ create-new-feature.sh (local dev)                            │
│                                                              │
│  get_highest_from_specs: filter ^[0-9]{3}- only      FR-007  │
│  get_highest_from_branches: already correct           ✓      │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ create-new-feature.ps1 (local dev, Windows)                  │
│                                                              │
│  Get-HighestNumberFromSpecs: filter ^\d{3}- only     FR-008  │
│  Get-HighestNumberFromBranches: filter ^\d{3}- only  FR-008  │
└──────────────────────────────────────────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Validation & Collision Detection in `generate-spec-from-issue.sh`

**Deliverables**: FR-011, FR-004, FR-012

#### 1a. ISSUE_NUMBER validation (FR-011)

At the very top of `generate-spec-from-issue.sh`, immediately after the existing
`${ISSUE_NUMBER:?}` check, add:

```bash
# Validate ISSUE_NUMBER is a positive integer
if ! [[ "$ISSUE_NUMBER" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: ISSUE_NUMBER must be a positive integer, got: '$ISSUE_NUMBER'" >&2
    exit 1
fi
```

This rejects `0`, negative numbers, non-numeric strings, and empty values.

#### 1b. Collision detection and directory reuse (FR-004, FR-012, FR-015)

In `generate-spec-from-issue.sh`, immediately after `BRANCH_NAME` is computed
and before the script creates or assigns the new spec directory, add a scan for
an existing spec directory with the same issue number prefix:

```bash
# Check for existing spec directory with this issue number
EXISTING_DIR=""
if [[ -d "$REPO_ROOT/$SPEC_BASE_PATH" ]]; then
    for dir in "$REPO_ROOT/$SPEC_BASE_PATH"/"$ISSUE_NUMBER"-*; do
        if [[ -d "$dir" ]]; then
            EXISTING_DIR="$dir"
            break
        fi
    done
fi

if [[ -n "$EXISTING_DIR" ]]; then
    # FR-015: For 3-digit issue numbers (100–999), verify the candidate directory
    # belongs to this issue by checking its spec.md Source Issue header. This prevents
    # accidentally reusing an unrelated legacy NNN-* directory.
    if [[ ${#ISSUE_NUMBER} -eq 3 ]]; then
        SPEC_FILE_PATH="$EXISTING_DIR/spec.md"
        if [[ -f "$SPEC_FILE_PATH" ]] && grep -q "^\*\*Source Issue\*\*: #${ISSUE_NUMBER}$" "$SPEC_FILE_PATH"; then
            echo "Verified Source Issue match for 3-digit issue number"
        else
            echo "Error: Existing directory '$(basename "$EXISTING_DIR")' matches issue number prefix" >&2
            echo "but does not contain a spec.md with '**Source Issue**: #${ISSUE_NUMBER}'." >&2
            echo "This may be a legacy autoincrement directory. Refusing to reuse." >&2
            exit 1
        fi
    fi
    echo "Reusing existing spec directory: $(basename "$EXISTING_DIR")"
    SPEC_DIR="$EXISTING_DIR"
    BRANCH_NAME="$(basename "$EXISTING_DIR")"
else
    # Create new directory using raw issue number (no zero-padding)
    BRANCH_NAME="${ISSUE_NUMBER}-${SHORT_NAME}"
    SPEC_DIR="$REPO_ROOT/$SPEC_BASE_PATH/$BRANCH_NAME"
fi
```

This means if the issue title changed between runs, the existing directory is
reused (FR-012). For 3-digit issue numbers (100–999), the reuse path additionally
verifies that the candidate directory's `spec.md` contains a matching `**Source Issue**: #N`
header (FR-015), preventing accidental reuse of unrelated legacy directories in the
overlapping namespace. The `check-idempotency.sh` script handles the "already fully
processed" case upstream; this collision check handles the "directory exists but
re-run is allowed" case.

#### 1c. Autoincrement filter in `get_next_feature_number` (FR-007)

In `generate-spec-from-issue.sh`, change the spec directory scan regex from:

```bash
number=$(echo "$dirname" | grep -o '^[0-9]\+' || echo "0")
```

to:

```bash
# Only count 3-digit prefixed directories for autoincrement
echo "$dirname" | grep -q '^[0-9]\{3\}-' || continue
number=$(echo "$dirname" | grep -o '^[0-9]\{3\}')
number=$((10#$number))
```

The branch scan already correctly filters to `^[0-9]{3}-`.

### Phase 2: Autoincrement Filter in `create-new-feature.sh`

**Deliverables**: FR-007

#### 2a. Fix `get_highest_from_specs`

Change:

```bash
number=$(echo "$dirname" | grep -o '^[0-9]\+' || echo "0")
```

to:

```bash
# Only count 3-digit prefixed directories for autoincrement
echo "$dirname" | grep -q '^[0-9]\{3\}-' || continue
number=$(echo "$dirname" | grep -o '^[0-9]\{3\}')
```

The `get_highest_from_branches` function already correctly filters branch
names using `grep -q '^[0-9]\{3\}-'`, so no change is needed there.

### Phase 3: PowerShell Parity in `create-new-feature.ps1`

**Deliverables**: SC-006

#### 3a. Fix `Get-HighestNumberFromSpecs`

Change:

```powershell
if ($_.Name -match '^(\d+)') {
```

to:

```powershell
if ($_.Name -match '^\d{3}-') {
    if ($_.Name -match '^(\d{3})') {
```

Or equivalently, use a single combined regex:

```powershell
if ($_.Name -match '^(\d{3})-') {
```

#### 3b. Fix `Get-HighestNumberFromBranches`

Change:

```powershell
if ($cleanBranch -match '^(\d+)-') {
```

to:

```powershell
if ($cleanBranch -match '^(\d{3})-') {
```

### Phase 4: Testing

**Deliverables**: Verification of all FRs

#### 4a. Manual test matrix

| # | Test Case | Script | Expected |
|---|-----------|--------|----------|
| 1 | Specs dir has `001-foo`, `42-bar` → autoincrement | `create-new-feature.sh` | Next = 002 (ignores `42-bar`) |
| 2 | Specs dir has `001-foo`, `42-bar` → autoincrement | `create-new-feature.ps1` | Next = 002 (ignores `42-bar`) |
| 3 | Branches include `001-foo`, `99-bar` → autoincrement | Both scripts | Next = 002 (ignores `99-bar`) |
| 4 | ISSUE_NUMBER=abc → validation | `generate-spec-from-issue.sh` | Exit 1 with error |
| 5 | ISSUE_NUMBER=0 → validation | `generate-spec-from-issue.sh` | Exit 1 with error |
| 6 | ISSUE_NUMBER=42, no existing dir → create | `generate-spec-from-issue.sh` | Creates `42-short-name` |
| 7 | ISSUE_NUMBER=42, `42-old-name` exists → reuse | `generate-spec-from-issue.sh` | Reuses `42-old-name` |
| 8 | Specs dir has `001-foo`, `002-bar`, `42-issue` → autoincrement | `generate-spec-from-issue.sh` | Next = 003 (ignores `42-issue`) |

#### 4b. Automated tests

Create a test script `.github/scripts/speckit-trigger/test-autoincrement-filter.sh`
that sets up a temporary specs directory with mixed-prefix directories and verifies
the autoincrement logic. This should be runnable locally and in CI.

### Phase 5: Documentation Update

Update `specs/README.md` and `SPEC_DRIVEN_DEVELOPMENT.md` to document:

- The new directory naming convention (issue-numbered vs. autoincrement)
- That autoincrement ignores issue-numbered directories
- The ISSUE_NUMBER validation rules

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Regex change breaks existing autoincrement for 3-digit dirs | Low | High | All existing dirs already use 3-digit prefix; test with real `specs/` contents |
| Issue-numbered dir collides with legacy autoincrement dir for 3-digit issue numbers (e.g., issue #117 → `117-...`) | Medium | Medium | `check-idempotency.sh` detects existing issue-linked specs upstream; legacy autoincrement scanner may count the 3-digit issue dir and skip one number, which is an accepted trade-off per FR-009 |
| PowerShell regex behaves differently than Bash | Low | Medium | Test both scripts with identical directory fixtures |
| Re-run with changed title creates orphan directory | Low | Low | FR-012 ensures reuse; old dir is reused, not abandoned |

## 6. Dependencies

### Internal Dependencies

- `check-idempotency.sh` — already handles "spec exists, skip" logic; no changes needed
- `speckit-issue-trigger.yml` — **needs changes for rerun idempotency**: with deterministic
  issue-number branch naming, the workflow's `git checkout -b "$BRANCH_NAME"` +
  `git push -u origin "$BRANCH_NAME"` will fail on reruns when a remote branch/PR for that
  issue already exists (non-fast-forward push / branch already exists). The workflow must be
  updated to handle existing branches idempotently — e.g., detect an existing remote branch
  and either check it out and reset, or force-push with lease — so issue-triggered reruns
  do not break
- `sanitize-branch-name.sh` — no changes needed (produces SHORT_NAME)

### External Dependencies

- None. All changes are to shell/PowerShell scripts with no library dependencies.

### Backward Compatibility

- Existing `specs/` directories with 3-digit prefixes (`001-*`, `002-*`, etc.) continue to
  work identically.
- Existing directories with non-3-digit prefixes (none currently exist in the repo) would
  now be ignored by autoincrement — this is the desired behavior.
- Shared `.specify` helpers in `common.sh` that currently assume a `^[0-9]{3}-` prefix
  (for example `check_feature_branch` and `find_feature_dir_by_prefix`) must be updated
  to accept both legacy 3-digit prefixes and longer numeric issue-number prefixes such as
  `1176-*`, so issue-number branches/directories remain usable with `.specify` tooling.

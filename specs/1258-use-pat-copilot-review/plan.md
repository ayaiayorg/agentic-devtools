# Implementation Plan: Use PAT for Copilot Review Request in SpecKit Workflows

**Issue**: [#1258](https://github.com/ayaiayorg/agentic-devtools/issues/1258)
**Branch**: `speckit/1258/phase-3-plan`

## Technical Context

- **Stack**: GitHub Actions workflows (YAML + embedded JavaScript via `actions/github-script@v7`)
- **Affected files**: 3 workflow YAML files under `.github/workflows/`
- **Key dependency**: `actions/github-script@v7` — accepts an optional `github-token` input to override the default `GITHUB_TOKEN` for all Octokit calls within its `script` block
- **Existing infrastructure**: `COPILOT_GITHUB_TOKEN` is already part of the existing workflow design: it is validated in the `Validate Copilot Token` step
  and used later by artifact-generation-related steps in `speckit-phase-progression.yml` and `speckit-issue-trigger.yml`

## Research Summary

Detailed decision rationale is captured in this section. Key decisions:

1. **Reuse `COPILOT_GITHUB_TOKEN`** rather than creating a dedicated secret — simpler, single rotation point, already validated in 2 of 3 workflows
2. **Add token validation step to `speckit-copilot-review-request.yml`** — consistent with the other two workflows; fail fast if the PAT is missing
3. **Update existing "Validate Copilot Token" error messages** — replace outdated `Copilot Requests: Read` guidance with accurate minimum permissions

## Design Overview

The fix is a **configuration-only change** with **one small workflow-structure addition**: add the existing `Validate Copilot Token` step to
`speckit-copilot-review-request.yml`. That validation step is **required**, not optional in behavior — it should fail fast when `COPILOT_GITHUB_TOKEN`
is missing, matching the other two workflows. Beyond that single validation step, there are no new scripts, no new actions, and no other new workflow
steps. Each "Request Copilot Review" step already contains complete, working JavaScript logic (idempotency checks, 422 handling, error logging). The
only defect is that the Octokit client behind `github.*` is authenticated with `GITHUB_TOKEN` instead of `COPILOT_GITHUB_TOKEN`.

**The fix**: Add `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` to each `actions/github-script@v7` step that calls `github.rest.pulls.requestReviewers()`.

```yaml
# Before (broken)
- uses: actions/github-script@v7
  with:
    script: |
      await github.rest.pulls.requestReviewers(...)

# After (fixed)
- uses: actions/github-script@v7
  with:
    github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}
    script: |
      await github.rest.pulls.requestReviewers(...)
```

### Scope of `github-token` override

The `github-token` input on `actions/github-script@v7` replaces the token used to construct the `github` Octokit instance for **that step only**. It does not affect other steps in the job. This is
safe because each "Request Copilot Review" step only calls PR reviewer APIs — no other API calls are made within these steps that would need the default `GITHUB_TOKEN`.

**Important**: In `speckit-copilot-review-request.yml`, the "Check existing reviewers" idempotency step (`id: idempotency`) calls `listRequestedReviewers`
and `listReviews`. These are **read** operations that work fine with `GITHUB_TOKEN` (the job already has `pull-requests: write` permission). However, for
consistency and to ensure the same token is used for both reading and writing reviewer state, the idempotency check step should **also** receive the
PAT override.

## Implementation Phases

### Phase 1: Fix `speckit-phase-progression.yml` (P1)

**File**: `.github/workflows/speckit-phase-progression.yml`
**Steps**: `Request Copilot Review` (`actions/github-script@v7`), `Validate Copilot Token`

1. Add `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` to the `actions/github-script@v7` step named "Request Copilot Review"
2. Update the "Validate Copilot Token" step's error message to include accurate minimum permissions: `Pull requests: Write` (fine-grained) or `repo` (classic), plus Copilot access

**Deliverable**: The phase-progression "Request Copilot Review" step authenticates with the PAT.

### Phase 2: Fix `speckit-issue-trigger.yml` (P1)

**File**: `.github/workflows/speckit-issue-trigger.yml`
**Steps**: `Request Copilot Review` (`actions/github-script@v7`), `Validate Copilot Token`

1. Add `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` to the `actions/github-script@v7` step named "Request Copilot Review"
2. Update the "Validate Copilot Token" step's error message to include accurate minimum permissions

**Deliverable**: The issue-trigger "Request Copilot Review" step authenticates with the PAT.

### Phase 3: Fix `speckit-copilot-review-request.yml` (P1)

**File**: `.github/workflows/speckit-copilot-review-request.yml`
**Steps**: `Request Copilot Review` (`actions/github-script@v7`), `Check existing reviewers` (`id: idempotency`)

1. Add `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` to the "Request Copilot Review" step
2. Add `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` to the "Check existing reviewers" step (for consistency — ensures the same authenticated identity for both read and write
   operations)
3. Add a new "Validate Copilot Token" step **before** the "Check existing reviewers" step, matching the pattern from the other two workflows:

```yaml
- name: Validate Copilot Token
  env:
    COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
  run: |
    if [[ -z "$COPILOT_GITHUB_TOKEN" ]]; then
      echo "::error::COPILOT_GITHUB_TOKEN secret is not configured. Add a fine-grained PAT with 'Pull requests: Write' permission, or a classic PAT with 'repo' scope. The token owner must be a repository collaborator with Copilot access."
      exit 1
    fi
    echo "✓ COPILOT_GITHUB_TOKEN is configured"
```

**Decision on FR-007**: Fail the job when the PAT is missing. This workflow's sole purpose is requesting Copilot review — if it can't authenticate, there's nothing useful it can do. Failing fast gives
clear signal. The other steps (linked-issue comment) are informational and don't justify running without the core capability.

**Deliverable**: The copilot-review-request workflow validates the PAT upfront and uses it for both idempotency check and review request.

### Phase 4: Update Error Messages (P2)

Across all three "Validate Copilot Token" steps, ensure the error messages describe the **actual** minimum permissions needed:

| Workflow | Current message | Updated message |
|---|---|---|
| `speckit-issue-trigger.yml` (`Validate Copilot Token` step) | `"Add a fine-grained PAT with 'Copilot Requests: Read' permission."` | `"Add a fine-grained PAT with 'Pull requests: Write' and 'Copilot Requests: Read' permissions, or a classic PAT with 'repo' scope. The token owner must be a repository collaborator with Copilot access."` |
| `speckit-phase-progression.yml` (`Validate Copilot Token` step) | `(no permission guidance)` | Same as above |
| `speckit-copilot-review-request.yml` | *(new step — message defined in Phase 3)* | `"Add a fine-grained PAT with 'Pull requests: Write' permission, or a classic PAT with 'repo' scope. The token owner must be a repository collaborator with Copilot access."` |

> **Note:** `speckit-copilot-review-request.yml` does not use Copilot APIs (it only calls PR reviewer APIs via `requestReviewers`),
> so it does not require the `Copilot Requests: Read` permission.
> The other two workflows need `Copilot Requests: Read` because they generate artifacts via Copilot APIs.

### Phase 5: Verification (P1)

1. Validate YAML syntax (no broken indentation) — `yamllint` or manual review
2. Verify no other steps in any of the three workflows reference `github-token` in a conflicting way
3. Verify the "Post Completed Comment" / "Post Review Request Status" steps in each workflow still use the default `GITHUB_TOKEN` (they should — they write issue comments, not PR reviewers)
4. Audit: confirm every `actions/github-script@v7` step that accesses PR reviewer state or calls `requestReviewers` has
   `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` — explicitly including the `id: idempotency` step in
   `speckit-copilot-review-request.yml`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `COPILOT_GITHUB_TOKEN` lacks `Pull requests: Write` permission | Medium | High — same failure as today | Document required permissions in error messages; verify PAT permissions before merging |
| PAT token override breaks other API calls in the same step | Low | Medium | Each "Request Copilot Review" step only calls reviewer APIs; no cross-contamination risk |
| Idempotency check returns different results with PAT vs. `GITHUB_TOKEN` | Very Low | Low | Both tokens have `pull-requests: read` capability; `listRequestedReviewers` and `listReviews` are read operations |
| YAML indentation error breaks workflow | Low | High — workflow fails to parse | Validate YAML after editing |
| PAT rate limit hit when used for both artifact generation and review request | Very Low | Low | Both operations are once-per-run, well within rate limits |
| Broadened `COPILOT_GITHUB_TOKEN` blast radius | Low | Medium — a leaked token now grants `Pull requests: Write` in addition to Copilot artifact permissions | Acceptable tradeoff: single rotation point, already validated in 2 of 3 workflows, and the alternative (a dedicated secret) doubles secret-management overhead for minimal security gain. Mitigated by fine-grained PAT scoping to this repository only |

## Dependencies

- **External**: `COPILOT_GITHUB_TOKEN` secret must have `Pull requests: Write` (fine-grained) or `repo` (classic) permission, and the owning user must be a repository collaborator with Copilot access
- **Internal**: No code dependencies — purely workflow YAML changes
- **Testing**: Requires a live workflow run to verify (e.g., trigger `workflow_dispatch` on phase-progression, or apply `speckit:spec-needed` label on an issue)

---
*Generated by Copilot SDK (claude-opus-4.6)*

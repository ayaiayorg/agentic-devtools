# Implementation Plan: Auto-Request Copilot Review After PR Creation

## Technical Context

- **Stack**: GitHub Actions workflows (YAML + `actions/github-script@v7`), Bash scripts
- **Key workflows**:
  - `speckit-issue-trigger.yml` — Phase 1 spec PR creation
  - `speckit-phase-progression.yml` — Phase 2–5 spec PR creation
  - `speckit-implement-trigger.yml` — Implementation agent assignment (PRs created by Copilot agent, not this workflow)
- **Review gate**: `copilot-review-gate.yml` — required check that verifies Copilot has reviewed the PR
- **Copilot reviewer login**: `copilot-pull-request-reviewer[bot]`
- **PR creation**: All spec PRs use `create-spec-pr.sh` (out of scope for changes per FR-005)
- **Implementation PRs**: Created asynchronously by `copilot-swe-agent[bot]` after agent assignment — the workflow only assigns, it does not create the PR itself

## Research Summary

The key research decisions for this plan are:

- **Spec PRs**: Request Copilot review as an inline step immediately after PR creation in the existing spec workflows, rather than adding a separate workflow for those PRs.
- **Implementation PRs**: Handle Copilot review requests in a dedicated `pull_request`-triggered workflow because those PRs are created asynchronously after agent assignment.
- **Idempotency**: Make the implementation workflow safe for duplicate `labeled` events by checking whether Copilot is already
  requested/reviewing before requesting again, and treating "already requested" as a non-fatal outcome.
- **Permissions**: Scope the new workflow to the minimum required permissions, primarily the ability to read PR metadata, request reviewers, and comment on the linked issue.

## Design Overview

The feature has **two independent integration points**:

### 1. Spec PRs (Phase 1–5)

Add a new `github-script` step **after** the "Create Pull Request" step in both `speckit-issue-trigger.yml` (Phase 1) and `speckit-phase-progression.yml` (Phases 2–5). This step:

1. Extracts the PR number from the `create-pr` step output
2. Calls `github.rest.pulls.requestReviewers()` with `reviewers: ['copilot-pull-request-reviewer[bot]']`
3. Sets an output (`copilot_review_requested: 'true'` or `'false'`) consumed by the downstream comment step
4. Uses `continue-on-error: true` and `core.warning()` on failure (FR-009)

The existing "Post Completed Comment" / "Post Phase Progress Comment" steps are updated to append the status line (`🤖 Copilot review requested` or `⚠️ Copilot review request failed`) based on the new
step's outcome.

### 2. Implementation PRs

Create a new `speckit-copilot-review-request.yml` workflow triggered on `pull_request` events (`opened`, `labeled`) that:

1. Filters for PRs authored by `copilot-swe-agent[bot]` or labeled `speckit:implementation`
2. Requests Copilot as a reviewer via `github.rest.pulls.requestReviewers()`
3. Extracts the linked issue number from the PR title/body
4. Posts a status comment on the linked issue (success or failure)
5. Uses `continue-on-error: true` with `core.warning()` on failure

### Architecture Diagram

```text
speckit-issue-trigger.yml          speckit-phase-progression.yml
  ├─ Create Pull Request              ├─ Create Pull Request
  ├─ Request Copilot Review  ← NEW    ├─ Request Copilot Review  ← NEW
  └─ Post Completed Comment            └─ Post Phase Progress Comment
     (appends review status)               (appends review status)

pull_request [opened, labeled]
  └─ speckit-copilot-review-request.yml  ← NEW WORKFLOW
       ├─ Filter: copilot-swe-agent[bot] or speckit:implementation label
       ├─ Request Copilot Review
       └─ Post status comment on linked issue
```

## Implementation Phases

### Phase 1: New Dedicated Workflow for Implementation PRs

**Deliverable**: `.github/workflows/speckit-copilot-review-request.yml`

**Tasks**:

1. Create `speckit-copilot-review-request.yml` triggered on `pull_request` events of type `opened` and `labeled`, targeting `main` branch
2. Add event/job gating so the workflow runs for `opened` when the PR author is `copilot-swe-agent[bot]`, and for `labeled` only when the newly
   added label is `speckit:implementation` (avoid reruns for unrelated labels)
3. Declare minimal permissions: `pull-requests: write`, `issues: write`, `contents: read`
4. Add `github-script` step to request Copilot reviewer using `github.rest.pulls.requestReviewers()` with `continue-on-error: true`
5. Add `github-script` step to extract issue number from PR title/body (regex: `#(\d+)`)
6. Add `github-script` step to post status comment on the linked issue with appropriate emoji status line
7. Handle idempotency for both side effects: if Copilot is already a requested reviewer, log info and skip; before posting the
   linked-issue status comment, detect an existing workflow status comment for the same PR and update or skip it so repeated runs do not add
   duplicate/misleading comments

### Phase 2: Spec PR Review Request — Phase 1 (speckit-issue-trigger.yml)

**Deliverable**: New step in `speckit-issue-trigger.yml` after "Create Pull Request"

**Tasks**:

1. Add a "Request Copilot Review" step after the `create-pr` step, gated on `steps.create-pr.outputs.pr_number != ''`
2. Use `actions/github-script@v7` with `continue-on-error: true` to call `github.rest.pulls.requestReviewers()`
3. Set step output `copilot_review_requested` to `'true'` or `'false'`
4. Update the "Post Completed Comment" step to read the new output and append the status line (`🤖 Copilot review requested` or `⚠️ Copilot review request failed`)

### Phase 3: Spec PR Review Request — Phases 2–5 (speckit-phase-progression.yml)

**Deliverable**: New step in `speckit-phase-progression.yml` after "Create Pull Request"

**Tasks**:

1. Add a "Request Copilot Review" step after the `create-pr` step, gated on the same conditions as the existing post-PR steps plus `steps.create-pr.outputs.pr_number != ''`
2. Use `actions/github-script@v7` with `continue-on-error: true`
3. Set step output `copilot_review_requested`
4. Update the "Post Phase Progress Comment" step to append the status line

### Phase 4: Validation and Testing

**Deliverable**: Verified workflows pass linting and match conventions

**Tasks**:

1. Validate YAML syntax for all modified/new workflow files
2. Verify permissions are minimal and scoped correctly (AC-008)
3. Verify `create-spec-pr.sh` is NOT modified (AC-007)
4. Review all `if` conditions for correctness and edge-case safety
5. Verify idempotency: `labeled` event after `opened` should not produce duplicate comments or errors
6. Verify the `continue-on-error: true` + `core.warning()` pattern matches the existing pattern in `copilot-review-gate.yml`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Copilot reviewer bot name changes | Low | High | Use constant `copilot-pull-request-reviewer[bot]` matching existing `copilot-review-gate.yml` |
| `requestReviewers` API rejects bot accounts | Low | Medium | `continue-on-error: true` ensures workflow doesn't fail; warning is logged |
| `labeled` event triggers duplicate review requests | Medium | Low | GitHub API is idempotent for re-requesting an already-requested reviewer; comment step checks outcome |
| Implementation PR has no linked issue number | Low | Medium | Graceful skip of issue comment when no issue number is extractable |
| Permissions insufficient for new workflow | Low | Medium | Explicitly declare `pull-requests: write` at job level; test in a draft PR |

## Dependencies

- **Internal**: `create-spec-pr.sh` outputs `pr_number` — already present and used by auto-merge
- **External**: `actions/github-script@v7` — already pinned across all SpecKit workflows
- **API**: `github.rest.pulls.requestReviewers()` — standard GitHub REST API
- **Bot account**: `copilot-pull-request-reviewer[bot]` — same as `copilot-review-gate.yml`

---
*Generated by Copilot SDK (claude-opus-4.6)*

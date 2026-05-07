# Feature Specification: AI PR Loop Automated Agentic Repair

**Feature Branch**: `speckit/1359/phase-2-clarify`  
**Created**: 2026-05-07  
**Status**: Draft  
**Input**: User description: "Enable the AI PR Loop to programmatically trigger an agentic fix workflow via a Copilot CLI session on a GitHub-hosted runner when PRs are blocked by Copilot review
comments or failing required checks"  
**Source Issue**: #1359 (<https://github.com/ayaiayorg/agentic-devtools/issues/1359>)

---

## Overview

The current AI PR Loop workflow (`ai-pr-loop.yml`) detects when a PR is blocked by Copilot review comments or CI failures but stops without taking automated corrective action. A human must manually
start a local `/agdt.pr-merge-manager` or `/agdt.address-copilot-review` session. This feature closes that gap by dispatching an agentic repair job on a GitHub-hosted runner that addresses review
comments, fixes lint/test/coverage failures, pushes changes, and re-requests Copilot review — enabling fully automated PR convergence to a mergeable state.

---

## Clarifications

### Session 2026-05-07

- Q: What is the appropriate job timeout for the repair job — 15 minutes or 20 minutes (FR-012)? → A: 15 minutes. The repair job is scoped to a single focused task (address review comments or fix
  lint/formatting issues) and should not require the full 20-minute budget of the outer AI PR Loop job. A 15-minute timeout provides ample time for typical repairs while preserving GitHub Actions
  minutes. If the agent cannot fix the issue within 15 minutes, it is unlikely to succeed with 5 more minutes — the issue likely requires human intervention.
- Q: How does the repair job obtain CI failure logs for diagnosis when dispatched for CI failures (FR-002, User Story 2)? → A: The repair job uses `gh run view` and `gh api` to fetch workflow run logs
  and check-suite annotations for the failing checks on the PR's head SHA. It parses the log output to identify specific failure messages (e.g., ruff violations, pytest assertion errors) and uses
  those as context for the Copilot agent session. Only the most recent failing run per required check is consulted.
- Q: What happens if the repair agent partially succeeds — e.g., addresses 3 of 5 review comments but cannot resolve the remaining 2? → A: The agent pushes whatever fixes it has made, replies to the
  threads it addressed (resolving those), and posts explanatory replies on the threads it could not address. It then re-requests Copilot review. The subsequent AI PR Loop cycle will re-evaluate: if
  the remaining comments are still blocking, another repair dispatch (up to the 3-per-SHA limit) may be triggered. Partial progress is preferable to all-or-nothing behavior.
- Q: Should the deduplication guard's hidden marker comment format (`<!-- repair-dispatch:SHA:N -->`) be a single comment that is updated or one comment per dispatch? → A: A single hidden marker
  comment per PR that is updated in place (via `gh api PATCH`) with incrementing count. This keeps the PR timeline clean. Format: `<!-- repair-dispatch:FULL_SHA:COUNT -->`. The marker is searched via
  `gh api` listing PR comments and filtering for the HTML comment pattern matching the current head SHA.
- Q: What specific Copilot CLI invocation is used on the GitHub-hosted runner to start the agentic session? → A: The repair job uses the existing session launcher
  (`agentic_devtools/cli/copilot/session.py`), which prefers the standalone `copilot` binary (`copilot -p`) and falls back to `gh copilot suggest` with a prompt file written to disk for reliability
  and to avoid command-line length limits. The rendered `/agdt.address-copilot-review` prompt is passed via the session launcher. The `gh copilot` extension must be pre-installed in the job's setup
  step via `gh extension install github/gh-copilot`. The job sets `GH_TOKEN` (the environment variable read by `gh` for authentication) from the `COPILOT_GITHUB_TOKEN` repository secret — this is
  distinct from the default `secrets.GITHUB_TOKEN`, which lacks the permissions needed for pushing code and requesting reviewers. If `gh copilot` installation or invocation fails, the job posts a
  failure comment and exits with a non-zero code.

---

## Problem Statement

The AI PR Loop (`ai-pr-loop.yml`) currently halts when it detects a blocking condition — either
Copilot review comments requiring changes or failing required CI checks. At this point, a human
developer must manually trigger a local Copilot session (`/agdt.address-copilot-review` or
`/agdt.pr-merge-manager`) to address the feedback and push fixes. This creates two problems:

1. **Latency**: PRs sit idle until a human notices and intervenes, often for hours or overnight.
2. **Toil**: The majority of Copilot comments and CI failures (lint, formatting, import ordering,
   minor test fixes) are mechanically addressable — a human is performing work that an agent could
   handle autonomously.

The desired end state is a fully autonomous PR convergence loop: when the AI PR Loop detects a
fixable blocker, it dispatches an agentic repair job on a GitHub-hosted runner that addresses the
issue, pushes a fix, and re-requests review — all without human intervention. The human remains
the fallback for genuinely complex issues that exceed the agent's capability or the configured
retry budget.

---

## User Scenarios & Testing

### User Story 1 — Automated Copilot Review Comment Resolution (Priority: P1)

As a developer whose PR has received Copilot review comments, I want the AI PR Loop to automatically address those comments without my manual intervention, so that my PR converges to a clean state and
merges without me monitoring it.

**Why this priority**: This is the primary use case described in the issue. Today, every PR with Copilot feedback requires manual `/agdt.address-copilot-review` invocation. Automating this eliminates
the most common human-in-the-loop bottleneck.

**Independent Test**: Can be fully tested by creating a PR that triggers a Copilot review with actionable comments, then observing that the AI PR Loop dispatches a repair job, addresses comments,
replies, resolves threads, re-requests review, and the PR eventually merges.

**Acceptance Scenarios**:

1. **Given** a PR with a `CHANGES_REQUESTED` Copilot review containing inline comments, **When** the AI PR Loop workflow runs (triggered by `pull_request_review` event), **Then** a repair job is
   dispatched that runs `/agdt.address-copilot-review` with the review URL.
2. **Given** the repair job has addressed comments and pushed a new commit, **When** the push completes, **Then** Copilot review is re-requested and the push naturally re-triggers the AI PR Loop via
   the lint workflow.
3. **Given** a Copilot review with only non-addressable comments (false positives), **When** the repair job runs, **Then** it replies with explanations, resolves threads, and re-requests review
   without making code changes.
4. **Given** the repair job fails (e.g., agent exits with non-zero code or timeout), **When** the failure is detected, **Then** a comment is posted on the PR indicating the repair failed and human
   intervention is needed.

---

### User Story 2 — Automated CI Failure Repair (Priority: P2)

As a developer whose PR has failing required checks (lint, tests, coverage), I want the AI PR Loop to attempt automated fixes for those failures, so that trivially-fixable CI issues don't require my
manual attention.

**Why this priority**: CI failures are the second most common blocker. Many failures (lint violations, import ordering, minor test fixes) are mechanically addressable by an agent. This extends the
loop's self-healing capability beyond just review comments.

**Independent Test**: Can be tested by creating a PR with intentional lint violations or a failing unit test, then observing that the repair job identifies the failures, applies fixes, pushes, and CI
subsequently passes.

**CI Failure Log Retrieval**: The repair job obtains CI failure context by using `gh run view` and `gh api` to fetch workflow run logs and check-suite annotations for the failing checks on the PR's
head SHA. It parses the log output to identify specific failure messages (e.g., ruff violations, pytest assertion errors) and uses those as context for the Copilot agent session. Only the most recent
failing run per required check is consulted.

**Acceptance Scenarios**:

1. **Given** a PR where required CI checks have failed (and no Copilot review comments exist), **When** the AI PR Loop detects failed checks, **Then** a repair job is dispatched that checks out the
   branch, identifies failures from CI logs, and attempts to fix them.
2. **Given** the repair job has fixed lint/test/coverage issues and pushed, **When** CI re-runs on the new commit, **Then** the checks pass and the PR proceeds toward merge.
3. **Given** a CI failure that cannot be automatically fixed (e.g., fundamental logic error), **When** the repair job cannot resolve the issue after attempting, **Then** it posts a comment describing
   what it tried and what failed, and stops without creating an infinite loop.

---

### User Story 3 — Combined Review + CI Failure Handling (Priority: P2)

As a developer whose PR has both Copilot review comments AND failing CI checks, I want the repair job to handle both in a single pass, so that the PR doesn't bounce between multiple repair cycles
unnecessarily.

**Why this priority**: In practice, Copilot comments and CI failures often co-occur (e.g., Copilot suggests a change that would also fix a lint error). Handling both together reduces cycle count and
time-to-merge.

**Independent Test**: Can be tested by creating a PR with both review comments and a failing test, then observing that the repair job addresses comments AND fixes the test in one commit.

**Acceptance Scenarios**:

1. **Given** a PR with both actionable Copilot comments and a failing lint check, **When** the repair job runs, **Then** it addresses the review comments first, applies `ruff` fixes for lint issues
   (using only pinned trusted tooling per SEC-003), and pushes once. Verification that all issues are resolved is delegated to the subsequent CI run triggered by the push.
2. **Given** all issues are resolved in a single repair pass, **When** CI re-runs and Copilot re-reviews, **Then** the PR merges without additional repair dispatches.

---

### User Story 4 — Separation of Responsibilities (Priority: P1)

As a repository maintainer, I want the repair job to handle only code changes and comment resolution (push, comment, re-request review), while the existing AI PR Loop job retains exclusive
responsibility for approve and merge, so that the security model is preserved.

**Why this priority**: Security architecture is non-negotiable. The repair agent runs in a privileged context (secrets present, write access via PAT) but its scope of action is strictly limited to
pushing fixes and interacting with reviews. It must NEVER approve or merge PRs. This separation of responsibilities prevents a compromised or malfunctioning agent from merging bad code.

**Independent Test**: Can be verified by inspecting the workflow definition to confirm the repair job has no merge/approve permissions, and by observing that after repair the normal AI PR Loop cycle
performs the approval and merge.

**Acceptance Scenarios**:

1. **Given** the repair job has successfully addressed all issues, **When** it completes, **Then** it does NOT approve or merge the PR — it only pushes code changes, replies to comments, and
   re-requests review.
2. **Given** the repair job pushes a new commit, **When** the lint workflow triggers and Copilot re-reviews with APPROVED state, **Then** the existing privileged AI PR Loop job handles approval and
   merge.

---

### User Story 5 — Cycle Limit and Infinite Loop Prevention (Priority: P1)

As a repository maintainer, I want the agentic repair to have bounded retry behavior, so that a pathological PR doesn't consume unlimited CI resources.

**Why this priority**: Without bounds, a PR that an agent cannot fix would loop indefinitely, consuming compute and potentially generating noise. The existing 50-cycle limit applies to the outer loop,
but the repair dispatch itself needs its own safeguards.

**Independent Test**: Can be tested by creating a scenario where the agent cannot fix the issue (e.g., a test failure caused by missing external dependency), then observing that it stops after the
configured retry limit.

**Acceptance Scenarios**:

1. **Given** the repair job has already been dispatched 3 times for this PR on the current
   head SHA (the bounded retry limit), **When** the AI PR Loop re-evaluates and finds the
   same issues persist, **Then** it does NOT dispatch further repairs for that SHA and posts
   a "human intervention required" comment (bounded retry guard per SC-004).
2. **Given** the overall AI PR Loop cycle count reaches the configured maximum (50), **When** the next trigger fires, **Then** the loop posts a "human intervention required" comment and stops.
3. **Given** the repair job's internal timeout is reached (15 minutes), **When** the agent has not completed, **Then** the job is terminated and a failure comment is posted on the PR.

---

### User Story 6 — Observability and Auditability (Priority: P3)

As a repository maintainer, I want visibility into what the repair agent did, so that I can audit its actions and diagnose issues.

**Why this priority**: Important for trust and debugging but not blocking for the core functionality.

**Independent Test**: Can be tested by triggering a repair dispatch and then verifying that the workflow run logs, PR comments, and commit messages provide a complete audit trail.

**Acceptance Scenarios**:

1. **Given** a repair job is dispatched, **When** it begins executing, **Then** a PR comment is posted indicating the repair has started (with a link to the workflow run).
2. **Given** the repair job completes (success or failure), **When** it finishes, **Then** the PR comment is updated with the outcome summary (comments addressed, threads resolved, commit SHA, or
   failure reason).
3. **Given** a repair job runs, **When** its workflow run is inspected, **Then** the logs show each phase of the `/agdt.address-copilot-review` agent execution.

---

### Edge Cases

- What happens when the PR branch has merge conflicts with `main`? The repair job should detect this and report it as unresolvable (not attempt conflict resolution).
- How does the system handle concurrent triggers (e.g., Copilot review submitted while a previous repair job is still running)? The concurrency group should prevent duplicate dispatches.
- What happens when the `COPILOT_GITHUB_TOKEN` secret is missing or expired? The repair job should fail fast with a clear error message.
- What happens when the PR is closed or merged between dispatch and execution? The repair job should detect the terminal state and exit cleanly without posting comments.
- What happens when the repair agent's push is rejected (e.g., branch protection requires signed commits)? The failure should be reported clearly.
- What happens when the PR modifies privileged paths (`.github/workflows/`)? The repair job should NOT be dispatched — these PRs require human review per existing policy.
- What happens when the repair agent partially succeeds (addresses some but not all review comments)? The agent pushes whatever fixes it has made, replies to addressed threads (resolving those), posts
  explanatory replies on unresolved threads, and re-requests Copilot review. Partial progress is committed; the subsequent AI PR Loop cycle re-evaluates remaining blockers and may dispatch another
  repair (up to the 3-per-SHA limit).

---

## Requirements

### Functional Requirements

- **FR-001**: The AI PR Loop workflow MUST detect when a PR is blocked by actionable Copilot review comments (CHANGES_REQUESTED state with inline comments) and dispatch a repair job.
- **FR-002**: The AI PR Loop workflow MUST detect when a PR is blocked by failing required CI
  checks and dispatch a repair job. The detection strategy for CI failures is:
  1. **`pull_request_review` trigger path** (primary): The AI PR Loop already polls/waits for
     all required checks to complete before making dispatch decisions. CI failures observed at
     this point are definitive.
  2. **`workflow_run` trigger path** (lint completion): This path fires when a specific
     workflow completes. Before dispatching a repair, the loop MUST poll all required check
     suites (via `gh api` check-suites endpoint) to confirm they have reached a terminal
     state (`completed`). If any required check is still `in_progress` or `queued`, the loop
     MUST wait (with bounded timeout) or defer dispatch until a subsequent trigger provides
     a definitive failure signal. This prevents premature dispatch based on incomplete check
     status.
  3. **Deterministic decision**: A repair dispatch for CI failures is only triggered when
     ALL required checks have completed AND at least one has `conclusion: failure`.
  4. **CI log retrieval**: The repair job uses `gh run view` and `gh api` to fetch workflow
     run logs and check-suite annotations for the failing checks. Only the most recent
     failing run per required check is consulted.
- **FR-003**: The repair job MUST run on a standard GitHub-hosted runner (ubuntu-latest), NOT a self-hosted runner or the GitHub Copilot Cloud Coding Agent sandbox.
- **FR-004**: The repair job MUST authenticate using a repository secret PAT (`COPILOT_GITHUB_TOKEN`) that has permission to push code, post comments, resolve threads, and request reviewers.
- **FR-005**: The repair job MUST install `agentic-devtools` from a trusted source — either a
  pinned PyPI release version or a checkout of the repository's default branch (`main`) — and
  invoke the `/agdt.address-copilot-review` agent prompt via a Copilot CLI session. The
  installation MUST NOT use `pip install .` from the PR branch, as that would execute
  PR-sourced build/install logic (e.g., `setup.py`, `pyproject.toml` build hooks) while
  the PAT is in the environment. Additionally, the agent definition and prompt files
  (`.github/agents/`, `.github/prompts/`) MUST be sourced from the default branch checkout
  (or a pinned artifact), NOT from the PR branch — otherwise a malicious PR could alter
  agent instructions while the PAT is present. Code edits are applied to the PR worktree,
  but the agent's own instructions remain trusted. The Copilot CLI is installed via
  `gh extension install github/gh-copilot` in the job's setup step. The session is started
  using the existing session launcher (`agentic_devtools/cli/copilot/session.py`), which
  prefers the standalone `copilot` binary (`copilot -p <prompt>`) and falls back to
  `gh copilot suggest` with a prompt file written to disk for reliability and to avoid
  command-line length limits.
- **FR-006**: The repair job MUST NOT approve or merge PRs — these actions remain the exclusive responsibility of the existing privileged AI PR Loop steps.
- **FR-007**: The system MUST limit repair dispatches to at most 3 per PR head SHA
  (bounded retry with deduplication guard). Each dispatch is counted via a single hidden
  marker comment per PR that is updated in place (via `gh api PATCH`) with incrementing
  count. Format: `<!-- repair-dispatch:FULL_SHA:COUNT -->`. The marker is searched via
  `gh api` listing PR comments and filtering for the HTML comment pattern matching the
  current head SHA. Once 3 dispatches have been issued for a given SHA, no further repairs
  are dispatched for that SHA and a "human intervention required" comment is posted.
- **FR-008**: The repair job MUST post a PR comment when it starts and update it when it completes (success or failure).
- **FR-009**: The repair job MUST re-request Copilot review after pushing fixes, so the loop can naturally re-trigger.
- **FR-010**: The repair job MUST NOT be dispatched for PRs that modify privileged paths (`.github/workflows/`, `.github/actions/`, `.github/scripts/` — excluding `.md` files).
- **FR-011**: The repair job MUST respect the existing 50-cycle outer loop limit.
- **FR-012**: The repair job MUST have an internal timeout of 15 minutes (maximum job duration) after which it is terminated. This is shorter than the outer AI PR Loop's 20-minute timeout because the
  repair job is scoped to a single focused task. If the agent cannot complete within 15 minutes, the issue likely requires human intervention.
- **FR-013**: The system MUST skip repair dispatch for fork PRs (cannot push to forks).
- **FR-014**: The system MUST skip repair dispatch for PRs with the `ai-pr-loop-ignore` label.
- **FR-015**: When the repair agent partially succeeds (addresses some but not all review comments or CI failures), it MUST push the partial fixes, reply to addressed threads, post explanatory replies
  on unresolved threads, and re-request Copilot review. The subsequent AI PR Loop cycle re-evaluates remaining blockers.

### Non-Functional Requirements

- **NFR-001**: The repair job MUST complete within 15 minutes for typical PRs (enforced by the job-level `timeout-minutes: 15` setting per FR-012).
- **NFR-002**: The dispatch decision (whether to trigger repair) MUST be deterministic and auditable from the workflow run logs.
- **NFR-003**: The repair job MUST NOT leak secrets (PAT) in logs, PR comments, or commit messages.
- **NFR-004**: The system MUST be resilient to transient GitHub API failures (retry with backoff where appropriate).
- **NFR-005**: The concurrency model MUST prevent multiple repair jobs from running simultaneously for the same PR (use existing `concurrency` group or a dedicated one for the repair job).
- **NFR-006**: The system MUST degrade gracefully when `gh copilot` is unavailable or the PAT lacks required permissions — posting a clear failure comment rather than silently failing.

### Security Requirements

The repair job executes in an environment that has access to a PAT (`COPILOT_GITHUB_TOKEN`) while
operating on code from a PR branch. This creates a potential attack surface if a malicious PR
could manipulate the agent into exfiltrating the token. The following requirements constrain this
risk:

- **SEC-001**: The repair job MUST NOT be dispatched for PRs originating from forks (already
  covered by FR-013). Fork PRs cannot be trusted with repository secrets.
- **SEC-002**: The `COPILOT_GITHUB_TOKEN` PAT MUST be a fine-grained personal access token
  (or GitHub App token) scoped to the minimum required permissions using the actual
  fine-grained PAT permission labels:
  - **Contents: Read and write** (push commits to the PR branch)
  - **Pull requests: Read and write** (post comments, request reviewers, resolve threads)
  - **Actions: Read** (check workflow/CI status)

  It MUST NOT have Administration, Security events, or Organization scopes. The token
  owner must be a repository collaborator with Copilot access enabled.
- **SEC-003**: The repair job MUST NOT execute any code sourced from the PR branch while
  secrets are present in the execution environment. This includes test suites (`pytest`),
  CI scripts (`scripts/run-pr-checks.sh`), `Makefile` targets, `package.json` scripts, or
  any other executable content that an attacker could modify in a malicious PR to exfiltrate
  `COPILOT_GITHUB_TOKEN`. The trusted-code execution model is:
  1. **Analysis phase** (secrets present): The agent reads diffs, review comments, and CI
     logs. It generates code fixes using only the Copilot LLM and built-in `ruff`/
     `markdownlint-cli2` (installed from pinned versions, not from the PR branch). It
     pushes the fix commit using `gh` and the PAT.
  2. **Verification phase** (no secrets): Test execution and CI validation occur in the
     *subsequent* CI run triggered by the push — a separate workflow job where the standard
     CI pipeline runs with its own security model.
  The repair job itself MUST NOT invoke `pytest`, `bash scripts/*.sh`, or any other
  PR-sourced executable. Verification is delegated to the normal CI pipeline that runs
  after the repair commit is pushed.

  > **Implementation note**: The existing `/agdt.address-copilot-review` prompt (used
  > interactively in VS Code) includes `agdt-test`/`agdt-task-wait` steps. When the same
  > agent prompt is invoked by the CI-dispatched repair job, a **CI-safe mode** MUST be
  > enforced that skips all test execution steps. This can be achieved via an environment
  > variable (e.g., `AGDT_CI_REPAIR_MODE=1`) that the prompt respects, or by using a
  > dedicated CI-specific prompt variant that omits test steps entirely. The repair job
  > relies on the subsequent CI run for verification rather than running tests in-process.
- **SEC-004**: The PAT MUST be passed exclusively via GitHub Actions secrets
  (`${{ secrets.COPILOT_GITHUB_TOKEN }}`), never hardcoded in workflow files, logs, commit
  messages, or PR comments. The workflow MUST use `add-mask` to ensure the token value is
  redacted from logs.
- **SEC-005**: The repair job runs on an ephemeral GitHub-hosted runner (`ubuntu-latest`) that
  is destroyed after the job completes. No secrets persist beyond the job's lifetime.
- **SEC-006**: The repair job MUST NOT be dispatched for PRs that modify privileged paths
  (already covered by FR-010). This prevents a malicious PR from altering workflow definitions
  to capture secrets on a subsequent run.
- **SEC-007**: The agent MUST NOT commit or push files that contain secret-like patterns
  (tokens, keys, passwords). A pre-push validation step SHOULD scan staged changes for
  accidental secret inclusion.
- **SEC-008**: If the repair job detects that the PR introduces changes to `Dockerfile`,
  `docker-compose.yml`, or any file that could alter the execution environment of subsequent
  CI runs, it MUST flag this for human review rather than auto-fixing.

### Key Entities

- **Repair Dispatch**: A decision point in the AI PR Loop where it determines a repair is needed and triggers the repair job. Contains: PR number, head SHA, review ID (if review-triggered), failure
  type (review/CI/both).
- **Repair Job**: A GitHub Actions job that runs the agentic fix workflow. Contains: PAT authentication, `agentic-devtools` installation (from trusted source), `gh copilot` extension installation,
  Copilot CLI session execution in non-interactive mode, 15-minute timeout bound.
- **Deduplication Guard**: A single hidden marker comment per PR, updated in place via `gh api PATCH`, with format `<!-- repair-dispatch:FULL_SHA:COUNT -->`. Searched by listing PR comments and
  filtering for the HTML comment pattern matching the current head SHA.
- **Cycle Tracker**: The existing `<!-- ai-pr-loop-cycle-tracker -->` comment that counts total loop iterations across all trigger types.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: PRs blocked solely by addressable Copilot review comments converge to merged state without human intervention in ≥80% of cases.
- **SC-002**: PRs blocked by lint/formatting CI failures converge to passing CI without human intervention in ≥90% of cases.
- **SC-003**: The median time from Copilot review submission to PR merge (for auto-fixable issues) is under 10 minutes.
- **SC-004**: No PR enters an infinite repair loop — the system halts after at most 3 repair
  dispatches per PR head SHA (inner bound, see FR-007 and the deduplication guard) and 50 total
  cycles (outer bound, see FR-011). The inner limit of 3 is a firm design decision, not subject
  to further clarification.
- **SC-005**: Zero instances of the repair job approving or merging a PR (security invariant).
- **SC-006**: Every repair dispatch is visible in the PR comment history with start/end timestamps and outcome.
- **SC-007**: The repair job succeeds end-to-end (dispatch → fix → push → re-review request) on a standard `ubuntu-latest` runner without requiring self-hosted infrastructure.

---

## Open Questions

- ~~[RESOLVED]: Maximum repair dispatch attempts per PR — pinned at 3 attempts per unique head SHA (SC-004), within the overall 50-cycle limit (FR-011).~~
- ~~[RESOLVED]: Runner type — the parent issue title mentions "self-hosted runner" but this is outdated terminology from early
  exploration. FR-003 confirms the repair job runs on standard GitHub-hosted runners (`ubuntu-latest`). Self-hosted runners are
  explicitly excluded to avoid persistent secrets and to leverage ephemeral runner isolation (SEC-005).~~
- ~~[RESOLVED]: Should the repair job attempt CI failure fixes when the failure is in a workflow file itself? — No.
  FR-010/SEC-006 prohibit dispatch for any PR that modifies `.github/workflows/` (non-`.md`). If the PR's diff touches
  workflow files, repair is skipped entirely regardless of the failure source. This eliminates the attack surface of
  workflow-file manipulation.~~
- ~~[RESOLVED]: What is the appropriate job timeout for the repair job — 15 minutes. The repair job is scoped to a single focused task and should complete well within this bound. See FR-012.~~
- No remaining open questions. All ambiguities have been resolved.

---
*Generated by Copilot SDK (claude-opus-4.6)*

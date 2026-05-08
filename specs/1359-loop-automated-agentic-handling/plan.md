# Implementation Plan: AI PR Loop Automated Agentic Repair

**Issue**: [#1359](https://github.com/ayaiayorg/agentic-devtools/issues/1359)
**Spec**: `specs/1359-loop-automated-agentic-handling/spec.md`

---

## 1. Technical Context

### Technology Stack

- **GitHub Actions** (YAML workflows) — primary orchestration layer
- **JavaScript** (`actions/github-script@v7`) — in-workflow logic for dispatch decisions, comment management, guard checks
- **Python 3.12** — `agentic-devtools` CLI tooling (`agdt-*` commands), Copilot session launcher
- **GitHub CLI** (`gh`) — PR interactions, CI check queries, Copilot review management
- **Copilot CLI** (`copilot -p` / `gh copilot suggest`) — agentic code repair sessions

### Key Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `actions/github-script@v7` | v7 | Inline JavaScript in workflow steps |
| `actions/checkout@v4` | v4 | Repository checkout: trusted `main` branch for prompts/instructions, plus untrusted PR SHA checkout (`persist-credentials: false`, data-only) for code edits |
| `actions/setup-python@v5` | v5 | Python runtime for `agentic-devtools` |
| `ruff` | pinned (0.11.12) | Trusted lint/format fixer |
| `markdownlint-cli2` | pinned (0.17.2) | Trusted markdown fixer |
| `gh copilot` extension | latest | Copilot CLI agent session |

### Architecture Decisions

1. **Single workflow file**: The repair job is added as a new job within the existing
   `ai-pr-loop.yml` workflow (not a separate workflow). This preserves the existing
   concurrency group, trigger logic, and permissions model. The repair job is gated
   by a dispatch-decision step in the existing `ai-pr-loop` job.
2. **Two-phase trust model**: The repair job checks out PR code **only as
   editable source** — it never executes PR-sourced scripts, tests, or
   `pip install .` from the PR branch. All executable code comes from
   trusted sources: `agentic-devtools` is installed from PyPI (pinned
   version), agent prompts are read from the `main` branch checkout
   (`__trusted_main/`), and only pinned trusted tooling (`ruff`,
   `markdownlint-cli2`) is executed. The `persist-credentials: false`
   option on the PR checkout prevents the PR code from inheriting push
   tokens. Verification (tests, CI) runs in the subsequent CI pipeline
   triggered by the push (no secrets from this job). This is consistent
   with the workflow header's policy of never executing untrusted PR
   code in the privileged workflow — the PR branch is treated as
   untrusted data (read/edit), not as executable code.

   > **Note (Phase 4 action):** The current `ai-pr-loop.yml` header
   > states that the PR branch is fetched only to apply a patch artifact
   > (no direct PR checkout). Phase 4 must update the workflow's header
   > and security rationale to document the new behavior: a direct PR
   > checkout as data-only (`persist-credentials: false`), ensuring the
   > workflow documentation remains accurate and auditable.
3. **Copilot session via existing launcher**: Reuse `agentic_devtools/cli/copilot/session.py`
   `start_copilot_session()` in non-interactive mode.
4. **CI-safe prompt variant**: A dedicated prompt file
   (`.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`) omits test
   execution phases while retaining the full triage/fix/reply/resolve/re-request flow.

---

## 2. Research Summary

Key decisions:

| Decision | Choice | Rationale |
|---|---|---|
| Workflow architecture | New job in existing `ai-pr-loop.yml` | Shares concurrency group, avoids `workflow_dispatch` complexity, reuses trigger/guard logic |
| Repair dispatch mechanism | Job dependency (`needs: ai-pr-loop`) with output passing | Simpler than `repository_dispatch`; keeps everything in one workflow run for auditability |
| Agent installation source | `pip install agentic-devtools` from PyPI (pinned) | SEC-003 compliance — never install from PR branch |
| Agent prompt source | Checkout `main` branch in a separate path | SEC-003 — agent instructions must be trusted, not PR-sourced |
| Deduplication marker | Single PR comment, updated via PATCH | Keeps PR timeline clean per clarification |
| CI-safe mode | Dedicated prompt variant (not env-var gating) | More explicit, easier to audit, no runtime conditionals in prompt |
| `add-mask` for PAT | `echo "::add-mask::${COPILOT_GITHUB_TOKEN}"` | NFR-003 compliance — redact token from logs |

---

## 3. Design Overview

### High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                    ai-pr-loop.yml (PRIVILEGED)                       │
│                                                                      │
│  ┌─────────────────────┐     ┌──────────────────────────────────┐   │
│  │ Job: ai-pr-loop      │────→│ Job: agentic-repair              │   │
│  │ (existing)           │     │ (NEW)                            │   │
│  │                      │     │                                  │   │
│  │ • Resolve PR meta    │     │ • Checkout main (trusted)        │   │
│  │ • Guards + cycles    │     │ • Install agdt from PyPI         │   │
│  │ • Apply lint patch   │     │ • Install gh copilot             │   │
│  │ • Check review       │     │ • Build CI-safe prompt           │   │
│  │ • Approve & merge    │     │ • Run copilot session (15m)      │   │
│  │ • Record cycle       │     │ • Post start/end PR comment      │   │
│  │                      │     │ • Re-request Copilot review      │   │
│  │ NEW STEPS:           │     │                                  │   │
│  │ • Dispatch decision  │     │ DOES NOT:                        │   │
│  │   - Dedup guard      │     │ • Approve PR                     │   │
│  │   - Privileged paths │     │ • Merge PR                       │   │
│  │   - Fork check       │     │ • Run PR-sourced scripts/tests   │   │
│  └─────────────────────┘     └──────────────────────────────────┘   │
│                                                                      │
│  Concurrency: ai-pr-loop-${{ PR# }}                                  │
│  Triggers: workflow_run (lint), pull_request_review                   │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```text
ai-pr-loop job                          agentic-repair job
────────────                            ──────────────────
1. Resolve PR #, SHA, branch
2. Run guards (cycle limit, labels)
3. Check review comments ──→ has_comments?
4. Check CI status ──→ has_failed_checks?
5. Dispatch decision:                   6. Checkout trusted main
   - repair_needed? ──────────────────→ 7. Install agdt (PyPI, pinned)
   - repair_type (review/ci/both)       8. Install gh copilot
   - review_url                         9. Build prompt (CI-safe variant)
   - pr_number, head_sha              10. Start copilot session (-p)
                                       11. Agent: triage → fix → push
                                       12. Agent: reply, resolve threads
                                       13. Agent: re-request review
                                       14. Post completion comment
                                       ────────────────────────────────
                                       Push triggers new lint workflow
                                       → new AI PR Loop cycle
```

---

## 4. Implementation Phases

### Phase 1: Deduplication Guard & Dispatch Decision (P1)

**Deliverables**: New workflow step in the `ai-pr-loop` job that decides whether to dispatch a repair, and the deduplication marker comment system.

**Tasks**:

1. **Add dispatch-decision step** to `ai-pr-loop.yml` after the `check-review` step and before the `merge-check` step. This step:
   - Runs when `has_comments == 'true'` OR `has_failed_checks == 'true'`
   - AND merge is not possible (review not clean or checks failing)
   - AND the lint patch step did NOT push (no conflicting concurrent fix)
   - Checks privileged paths (FR-010) — reuse existing `PRIVILEGED_PATH_PREFIXES` check
   - Checks fork status (FR-013) — reuse existing fork guard
   - Checks `ai-pr-loop-ignore` label (FR-014)

2. **Implement deduplication guard** within the dispatch-decision step.
   Uses a **single idempotent PR comment** that carries both the dispatch
   counter and the repair job status (consolidating dedup tracking and
   status reporting into one comment, per the research summary goal of
   keeping the PR timeline clean):
   - Search PR comments for the prefix `<!-- repair-dispatch:FULL_SHA:` matching
     current `head_sha` (per spec FR-007's required format). Use prefix matching
     (not the full marker including the count suffix) because `N` varies across
     dispatches
   - If found and dispatch count ≥ 3: skip dispatch, PATCH the same comment
     to update status to "human intervention required" (the plan intentionally
     consolidates all status updates — including the exhaustion notice — into
     a single PATCH-able comment rather than posting a separate comment as
     FR-007 literally states, to keep the PR timeline clean; see the research
     summary's "single idempotent PR comment" rationale)
   - If found and dispatch count < 3: increment count via
     `github.rest.issues.updateComment` PATCH on the same comment
   - If not found: create new marker comment with COUNT=1 and status
     "pending"
   - The comment body format:

     ```text
     <!-- repair-dispatch:FULL_SHA:N -->
     🔧 **AI PR Loop Repair** (SHA: `SHORT_SHA`, dispatch N/3)
     **Status**: pending | started | completed | failed
     **Type**: review / ci / both
     **Run**: [link] (added when repair starts)
     ```

3. **Determine repair type** and set outputs:
   - `repair_needed`: `'true'` or `'false'`
   - `repair_type`: `'review'`, `'ci'`, or `'both'`
   - `review_url`: GitHub review URL (if review-triggered)
   - `pr_number`, `head_sha`, `head_branch`: forwarded from pr-meta

4. **Add Docker/privileged-file detection** (SEC-008):
   - Check if PR modifies `Dockerfile`, `docker-compose.yml`, or `docker-compose.yaml`
   - If so, skip repair dispatch and post comment flagging for human review

**Files modified**:

- `.github/workflows/ai-pr-loop.yml` — add dispatch-decision step (~120 lines JS)

---

### Phase 2: CI-Safe Prompt Variant (P1)

**Deliverables**: A CI-specific version of the address-copilot-review prompt that omits test execution.

**Tasks**:

1. **Create CI-safe prompt file** at `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`:
   - Copy from `agdt.address-copilot-review.prompt.md`
   - Remove Phase 4 test execution (`agdt-test`, `agdt-task-wait` blocks)
   - Add explicit note: "Verification is delegated to the subsequent CI run"
   - Add constraint: "Do NOT run `pytest`, `agdt-test`, `bash scripts/*.sh`, or any PR-sourced executable"
   - Add constraint: "Do NOT install packages from the PR branch (`pip install .`)"
   - Retain: triage, code edits (using `ruff check --fix`, `ruff format`), commit, push,
     reply, resolve threads, re-request review

2. **Create CI-safe agent definition** at `.github/agents/agdt.address-copilot-review.ci-repair.agent.md`:
   - Points to the CI-safe prompt
   - Same structure as existing agent but with CI-repair scope documented

3. **Add `AGDT_CI_REPAIR_MODE` environment variable support** in the existing prompt:
   - As a defense-in-depth measure, add a note at the top of the original prompt:
     "If `AGDT_CI_REPAIR_MODE=1` is set, skip all test execution steps"
   - This is secondary to the dedicated prompt — the repair job uses the CI-safe variant directly

**Files created**:

- `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`
- `.github/agents/agdt.address-copilot-review.ci-repair.agent.md`

**Files modified**:

- `.github/prompts/agdt.address-copilot-review.prompt.md` — add env-var guard note (defense-in-depth)

---

### Phase 3: Repair Job Definition (P1)

**Deliverables**: The `agentic-repair` job in `ai-pr-loop.yml` that performs the actual fix.

**Tasks**:

1. **Define the `agentic-repair` job** with:
   - `needs: ai-pr-loop`
   - `if: needs.ai-pr-loop.outputs.repair_needed == 'true'`
   - `runs-on: ubuntu-latest`
   - `timeout-minutes: 15` (FR-012)
   - Same concurrency group as the main job (inherited from workflow-level)
   - `permissions`: same as workflow-level (inherited)

2. **Add outputs** to the `ai-pr-loop` job for the repair job to consume:
   - `repair_needed`, `repair_type`, `review_url`, `pr_number`, `head_sha`, `head_branch`

3. **Implement setup steps**:
   - Mask the PAT: `echo "::add-mask::${COPILOT_GITHUB_TOKEN}"` (SEC-004)
   - Validate PAT presence: fail fast if `COPILOT_GITHUB_TOKEN` is empty (NFR-006)
   - Checkout trusted `main` branch:

     ```yaml
     uses: actions/checkout@v4
     with:
       ref: main
       path: __trusted_main
     ```

   - Checkout PR branch (for code edits only):

     ```yaml
     uses: actions/checkout@v4
     with:
       ref: ${{ needs.ai-pr-loop.outputs.head_sha }}
       path: pr-worktree
       persist-credentials: false
     ```

   - Configure git credentials and restore branch (avoids detached HEAD):

     Since `persist-credentials: false` disables the checkout action's
     credential helper and SHA-based checkout leaves a detached HEAD,
     explicitly configure credentials and switch to a real branch so
     that `agdt-git-save-work` (and other `agdt-git-*` commands that
     resolve the current branch) can push successfully:

     ```bash
     cd pr-worktree
     # Configure push credentials via the GitHub token
     git remote set-url origin "https://x-access-token:${COPILOT_GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
     # Switch from detached HEAD to the actual PR branch
     git checkout -B "${{ needs.ai-pr-loop.outputs.head_branch }}" HEAD
     ```

     This mirrors the credential setup used in the existing `ai-pr-loop`
     job's lint-patch push step.

   - Set up Python 3.12
   - **Add `AGDT_VERSION` workflow-level env variable** to the top of
     `ai-pr-loop.yml` (e.g., `AGDT_VERSION: '0.42.0'`). This variable
     does not exist yet and must be introduced as a new `env:` entry,
     providing a single source of truth for the pinned version used by
     the repair job:

     ```yaml
     # Top of ai-pr-loop.yml
     env:
       AGDT_VERSION: '0.42.0'  # NEW — source of truth for repair job
     ```

   - Install `agentic-devtools` from PyPI at that pinned version:

     ```bash
     pip install agentic-devtools==${{ env.AGDT_VERSION }}
     ```

   - Install `ruff` and `markdownlint-cli2` at pinned versions
   - Install the standalone `copilot` binary (required for non-interactive
     agentic sessions with `--allow-all`). The `gh copilot` extension is
     **not sufficient** — it only supports `gh copilot suggest` which
     lacks `--allow-all` and `--autopilot` flags needed for autonomous
     execution. Install the standalone binary to `~/.agdt/bin/copilot`
     (the managed install path checked by `_get_copilot_binary()`):

     ```bash
     # Install standalone copilot binary (required for --allow-all support)
     agdt-setup-copilot-cli  # installs standalone binary to ~/.agdt/bin/copilot
     gh extension install github/gh-copilot  # fallback only if standalone unavailable
     ```

     If the standalone binary is unavailable at runtime,
     `start_copilot_session()` falls back to `gh copilot suggest` (without
     `--allow-all`), which will fail to execute `agdt-*` tool invocations.
     The repair job should validate binary availability before starting
     the session.

4. **Implement PR state validation step**:
   - Check if PR is still open (not merged/closed) — exit cleanly if terminal
   - Check if head SHA still matches (another push may have occurred)
   - Check for merge conflicts — report and exit if present

5. **Implement prompt rendering step**:
   - Read the CI-safe prompt from `__trusted_main/.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`
   - For review-triggered repairs: inject the review URL
   - For CI-failure repairs: fetch failure logs via `gh run view` and `gh api`, inject as context
   - For combined: inject both review URL and CI failure context
   - Write rendered prompt to a temporary file

6. **Update the existing repair comment to "started" status**:
   - PATCH the marker comment created by the dispatch-decision step
     (Phase 1, Task 2) to update its status and add the workflow run
     link. This reuses the same comment rather than posting a new one,
     keeping the PR timeline clean:

     ```text
     <!-- repair-dispatch:FULL_SHA:N -->
     🔧 **AI PR Loop Repair** (SHA: `SHORT_SHA`, dispatch N/3)
     **Status**: started
     **Type**: review / ci / both
     **Run**: [workflow run link]
     ```

7. **Implement Copilot session execution step**:
   - Set `GH_TOKEN` from `secrets.COPILOT_GITHUB_TOKEN`
   - Set `AGDT_CI_REPAIR_MODE=1`
   - Run the session via a wrapper script that captures and propagates
     the Copilot subprocess exit code. The current `start_copilot_session()`
     implementation records `SESSION_ERROR` in logs but returns normally
     on non-zero subprocess exit, so the workflow step would not fail.
     The wrapper explicitly checks the return value and exits non-zero
     on failure:

     <!-- markdownlint-disable MD007 MD022 MD025 MD029 MD031 MD032 MD046 -->

     ```bash
cd pr-worktree
python - <<'PY'
import pathlib, sys
from agentic_devtools.cli.copilot.session import start_copilot_session
result = start_copilot_session(
    prompt=pathlib.Path('/tmp/repair-prompt.md').read_text(),
    working_directory='.',
    interactive=False
)
# result is a CopilotSessionResult with a .process attribute (Popen handle)
# For non-interactive sessions, process=None means the fallback path was
# taken (Copilot binary unavailable or prompt too large for argv), so the
# session did not actually run — treat this as a failure
if result.process is None:
    print('ERROR: Copilot session did not start (fallback path)', file=sys.stderr)
    sys.exit(1)
result.process.wait()
if result.process.returncode != 0:
    sys.exit(result.process.returncode)
PY
     ```

     `start_copilot_session()` returns a `CopilotSessionResult` dataclass
     (not an `int`). For non-interactive sessions the `.process` attribute
     holds the `subprocess.Popen` handle; when `.process` is `None` it
     means the session fell back to printing the prompt (Copilot binary
     missing or prompt too large for argv), so the wrapper exits non-zero.
     Otherwise it waits for the subprocess to finish and propagates a
     non-zero return code, ensuring the workflow step correctly detects
     Copilot session failures instead of silently marking repairs as
     "completed".

   - Fallback: if the Python session launcher is unavailable, use the
     standalone Copilot CLI directly with `-p` (matching the invocation
     pattern in `_build_copilot_args()`). For large prompts, pass a
     short file-reference instruction via `-p` instead of the full
     prompt text (matching how `start_copilot_session()` handles
     argv-length limits):

     ```bash
     cd pr-worktree
     copilot --allow-all -p "Read the prompt from /tmp/repair-prompt.md and follow the instructions."
     ```

8. **Implement completion/failure handling step**:
   - On success: PATCH the same repair comment to set status to
     "completed" with outcome summary (comments addressed, threads
     resolved, commit SHA)
   - On failure/timeout: PATCH the same repair comment to set status to
     "failed" with failure details and "human intervention required"
   - Capture exit code from Copilot session

9. **Implement secret scanning pre-push guard** (SEC-007):
   - Add a step that scans staged changes for secret-like patterns before the Copilot session's push:
     - This is challenging since the Copilot agent does its own `agdt-git-save-work`
     - Solution: Add a `pre-push` check in the prompt instructions that the agent must run
     - The prompt includes: "Before pushing, run the following
       secret-scanning guard (written as an explicit conditional so that
       a no-match result does not abort the shell under `set -e`):

       ```bash
       if git diff HEAD --staged | grep -iqE '(token|password|secret|api_key|private_key)'; then
         echo 'ABORT: potential secret detected'
         exit 1
       fi
       ```

       "
     - Defense in depth: the PAT is already masked via `add-mask`

<!-- markdownlint-enable MD007 MD022 MD025 MD029 MD031 MD032 MD046 -->

**Files modified**:

- `.github/workflows/ai-pr-loop.yml` — add `agentic-repair` job (~200 lines), add outputs to `ai-pr-loop` job

---

<!-- markdownlint-disable MD001 -->

### Phase 4: CI Failure Log Retrieval (P2)

**Deliverables**: Logic to fetch and parse CI failure logs for the repair agent's context.

**Tasks**:

1. **Implement CI log retrieval step** in the repair job:
   - Use `gh api` to list check runs for the head SHA
   - Filter to failed checks (excluding `AI PR Loop` and `Generate lint fix patch`)
   - For each failed check, get the workflow run ID
   - Use `gh run view <run_id> --log-failed` to get failure logs
   - Truncate logs to a reasonable size (e.g., last 200 lines per check)
   - Format as structured context for the prompt

2. **Implement CI failure context injection** into the prompt:
   - Append a `## CI Failure Context` section to the rendered prompt
   - Include: check name, conclusion, log excerpt
   - Focus on actionable information (ruff violations, pytest assertion errors)

3. **Create CI failure repair prompt section**:
   - Add instructions for the agent to:
     - Parse failure messages
     - Apply `ruff check --fix .` and `ruff format .` for lint failures
     - For test failures: read the test, understand the assertion, fix the code
     - Use only pinned trusted tooling (ruff, markdownlint-cli2)

4. **Update `ai-pr-loop.yml` header and security rationale**:
   - The current workflow header states the PR branch is fetched only to apply
     a patch artifact (no direct PR checkout). Update the header to document
     the new behavior: a direct PR checkout (`persist-credentials: false`,
     data-only) for code edits alongside the trusted `main` checkout for
     prompts/instructions. This keeps the workflow documentation accurate
     and auditable.

**Files modified**:

- `.github/workflows/ai-pr-loop.yml` — add log retrieval step in repair job, update workflow header security rationale
- `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md` — add CI failure handling instructions

---

### Phase 5: Observability & Auditability (P3)

**Deliverables**: Enhanced logging, PR comments, and audit trail for repair actions.

**Tasks**:

1. **Enhance the single repair comment** with structured metadata:
   - Repair type, trigger event, cycle count, dispatch count for this SHA
   - Link to workflow run with step-level deep link
   - Outcome summary on completion: comments addressed (count), threads
     resolved (count), commit SHA (if pushed), CI failures fixed (if CI
     repair), duration, Copilot session log link (if accessible)
   - All updates are PATCH operations on the same comment created by
     the dispatch-decision step (Phase 1, Task 2)

2. **Add workflow run annotations**:
   - Use `core.notice()` / `core.warning()` for key decision points
   - Log dispatch decision rationale
   - Log dedup guard state (current count, limit)

3. **Ensure commit messages include repair context**:
   - The CI-safe prompt should instruct the agent to include `[ai-repair]` in the commit body
   - This makes repair commits identifiable in git log

**Files modified**:

- `.github/workflows/ai-pr-loop.yml` — enhance comment steps
- `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md` — commit message instructions

---

### Phase 6: Integration Testing & Validation (P1)

**Deliverables**: Verified end-to-end repair flow.

**Tasks**:

1. **Manual test: review comment repair**:
   - Create a test PR with intentional issues
   - Trigger Copilot review (or use synthetic review)
   - Observe dispatch → repair → push → re-review cycle
   - Verify: repair comment posted, threads resolved, Copilot re-requested

2. **Manual test: CI failure repair**:
   - Create a test PR with ruff violations
   - Observe dispatch → repair → push → CI passes
   - Verify: lint fixes applied correctly

3. **Manual test: dedup guard**:
   - Trigger repair 3 times on same SHA
   - Verify 4th dispatch is blocked with "human intervention required"

4. **Manual test: privileged path guard**:
   - Create a PR modifying `.github/workflows/test.yml`
   - Verify repair is NOT dispatched

5. **Manual test: fork PR guard**:
   - Verify repair is NOT dispatched for fork PRs

6. **Manual test: timeout handling**:
   - Verify the 15-minute timeout produces a clear failure comment

7. **Manual test: partial success**:
   - Create a PR where some comments are addressable and some are not
   - Verify partial fixes are pushed and appropriate replies posted

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Copilot agent makes incorrect fixes | Medium | Medium | Subsequent CI run catches errors; dedup guard limits retries to 3 |
| PAT leaked in logs | Low | Critical | `add-mask`, never echo token, SEC-004 compliance |
| Infinite loop despite guards | Low | High | 3-per-SHA inner limit + 50-cycle outer limit + 15m timeout |
| `gh copilot` unavailable on runner | Medium | Medium | Graceful degradation: post failure comment, exit non-zero |
| Race condition: PR merged during repair | Low | Low | Pre-flight PR state check; push failure is non-fatal |
| Malicious PR manipulates agent | Low | Critical | Agent/prompt sourced from `main`; `agentic-devtools` from PyPI; no PR-sourced execution |
| `COPILOT_GITHUB_TOKEN` secret missing | Low | Medium | Fail-fast validation at job start with clear error message |
| Agent pushes secrets into code | Very Low | Critical | Prompt includes secret-scanning guard; PR goes through normal CI |
| Concurrent repair + lint patch | Low | Medium | Concurrency group prevents parallel runs; `cancel-in-progress: false` |

---

## 6. Dependencies

### External Dependencies

| Dependency | Required For | Risk |
|---|---|---|
| `gh copilot` CLI extension | Running agent sessions on runner | May require specific `gh` version; install step handles this |
| `COPILOT_GITHUB_TOKEN` secret | PAT for push/comment/review actions | Must be configured by repo admin before feature works |
| PyPI `agentic-devtools` package | Trusted agent tooling installation | Must have a published release; pin to specific version |
| GitHub Actions `ubuntu-latest` | Ephemeral runner environment | Standard; no special requirements |

### Internal Dependencies

| Dependency | Required For | Status |
|---|---|---|
| `agentic_devtools/cli/copilot/session.py` | Copilot session launcher | Exists; may need minor adaptation for CI context |
| `.github/prompts/agdt.address-copilot-review.prompt.md` | Base for CI-safe variant | Exists; used as template |
| `ai-pr-loop.yml` existing guard logic | Fork, label, privileged path checks | Exists; reused in dispatch decision |
| `agdt-gh-request-copilot-review` | Re-request review after fix | Exists; used by agent prompt |
| `agdt-gh-reply-to-review-comments` | Reply to review comments | Exists; used by agent prompt |
| `agdt-gh-resolve-review-threads` | Resolve review threads | Exists; used by agent prompt |
| `agdt-git-save-work` | Commit and push fixes | Exists; used by agent prompt |

---
*Generated by Copilot SDK (claude-opus-4.6)*

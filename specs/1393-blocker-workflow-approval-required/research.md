# Research: Workflow Approval Required Blocks Autonomous AI PR Loop

**Issue**: [#1393](https://github.com/ayaiayorg/agentic-devtools/issues/1393)

---

## Decision 1: Collaborator vs. Programmatic Approval

### Context

GitHub requires manual workflow approval for runs triggered by first-time contributors
or bot accounts. Two primary strategies exist to bypass this gate for trusted automation.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **A: Repository Collaborator** | Zero code; immediate effect; leverages GitHub's built-in trust model | GitHub App bots (`[bot]` suffix) cannot be added as traditional collaborators; requires admin access |
| **B: Programmatic Approval via REST API** | Works regardless of collaborator status; automatable | Requires token with Actions write permission (fine-grained PAT: Actions → Read and write; classic PAT: `workflow` scope); adds code complexity; polling delay |

### Decision

**Both** — use collaborator approach (FR-001/FR-002) as the primary zero-code path, with
programmatic approval (FR-003/FR-004) as an automatic fallback. This dual-path design ensures
the system works even if org-level policies block the collaborator approach at runtime.

### Rationale

- The collaborator approach eliminates the problem entirely with zero runtime overhead.
- The programmatic fallback activates automatically when the primary path is insufficient
  (detected via the monitoring mechanism polling for stuck runs).
- Defense-in-depth: two independent mechanisms reduce the chance of permanent blockage.

---

## Decision 2: Scheduled Workflow vs. `workflow_run` for Approval Monitor

### Context

The approval monitor needs a trigger mechanism to detect and approve stuck runs.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **A: `workflow_run` event** | Event-driven; immediate response | Circular dependency — `ai-pr-loop.yml` fires on `workflow_run` of lint; cannot approve its own trigger |
| **B: Scheduled workflow (cron)** | Independent; no circular deps; simple polling model | Delay up to schedule interval; consumes CI minutes |
| **C: Repository dispatch** | On-demand; no polling waste | Requires external trigger; adds complexity |

### Decision

**B: Scheduled workflow** — new `workflow-approval-monitor.yml` with `*/2 * * * *` cron.

### Rationale

- Avoids circular dependency: the lint workflow triggers `ai-pr-loop.yml` via `workflow_run`;
  if the monitor were also a `workflow_run` consumer, it could not approve the lint run
  that hasn't completed yet.
- Simple polling model with configurable frequency.
- `workflow_dispatch` added for manual testing without waiting for schedule.
- 2-minute interval aligns with FR-004 detection threshold.

---

## Decision 3: Config File Format and Location

### Context

The trusted bot allow-list (FR-007) needs a storage location that is:

- Version-controlled and auditable
- Easy to modify via PR
- Discoverable by the approval monitor workflow

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **A: `.github/ai-pr-loop-config.json`** | Standard location; JSON schema support; no comments needed | JSON lacks comments (mitigated by descriptive field names) |
| **B: Environment variable** | Simple; no file needed | Not version-controlled; hard to audit changes |
| **C: YAML config in workflow file** | Co-located with workflow | Mixes config with logic; harder to share across workflows |
| **D: `.github/CODEOWNERS`-style flat file** | Familiar pattern | No schema support; parsing complexity |

### Decision

**A: `.github/ai-pr-loop-config.json`** — simple JSON with descriptive field names.

### Rationale

- JSON is universally parseable in `actions/github-script` without additional dependencies.
- Descriptive field names (`trusted_bot_accounts`) make the config self-documenting without comments.
- Location under `.github/` is the standard for repository configuration.
- Changes are auditable via git history and PR review.

---

## Decision 4: Graceful Degradation Strategy

### Context

When both the collaborator approach and programmatic approval fail, the system needs a
fallback to avoid permanent blockage of the PR loop.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **A: Synthetic `pull_request_review` event** | Leverages existing trigger in `ai-pr-loop.yml`; proven pattern from `synthetic-copilot-review.yml` | Bypasses lint results; may proceed without lint data |
| **B: Manual notification only** | Simple; no bypasses | Defeats automation goal; adds toil |
| **C: Direct workflow dispatch** | Immediate; targeted | Requires PAT; bypasses trigger guards |

### Decision

**A: Synthetic `pull_request_review` event** — reuse the existing pattern from
`synthetic-copilot-review.yml`.

### Rationale

- `ai-pr-loop.yml` already triggers on `pull_request_review` (lines 30-31) — no new
  trigger mechanism needed.
- The `synthetic-copilot-review.yml` workflow provides a proven template for posting
  synthetic review events.
- The fallback path is clearly logged (FR-006) so operators know which path was taken.
- This path only activates after the approval monitor exhausts its retry limit, so it
  serves as a last resort, not a primary bypass.

---

*Generated by Copilot SDK (claude-opus-4.6)*

# Data Model: LangChain Work-on-Issue Workflow

## Core State (`WorkOnIssueState`)

This design extends the existing `agentic_devtools.orchestration.state_schema.WorkOnIssueState` fields rather than
renaming them, so the real-node graph remains compatible with the current stub graph and tests.

### Existing persisted fields

- `issue_key: str` — canonical issue identifier used to derive the deterministic LangGraph `thread_id`.
- `step: str` — current workflow step marker already used by the existing schema; values stay aligned with graph node
  names and gate states.
- `status: str` — high-level execution status such as `active`, `in-progress`, `paused`, `failed`, or `completed`
  (hyphenated values follow repository workflow conventions).
- `plan: str` — existing plan-content field reused for the generated Jira plan comment body.
- `error: str | None` — latest resumable or terminal error message.
- `retry_count: int` — verification retry counter, bounded by the existing workflow retry policy.
- `events: list[WorkOnIssueEvent]` — append-only audit trail.
- `human_approved: bool` — existing boolean used for planning-gate approval.
- `agent_context: dict[str, Any]` — non-secret execution context only.
- `affected_paths: list[str]` — file paths identified during planning/implementation.

### Added typed fields for LangGraph resume/parity

- `commit_message: str` — derived commit message required before `commit_node` can mutate git state.
- `source_branch: str` — current branch captured for PR creation and commit-parity checks.
- `pr_title: str` — derived PR title for the Azure DevOps adapter.
- `pr_description: str` — derived PR body/description.
- `failed_node: str | None` — node name recorded when execution fails but remains resumable.
- `resume_target_node: str | None` — node/gate the runner expects to resume next.
- `idempotency_keys: dict[str, str]` — per-side-effect reconciliation keys (for example Jira comment fingerprints,
  commit fingerprints, or PR creation keys).
- `artifact_references: dict[str, str]` — external artifact identifiers already created (comment IDs, commit SHAs,
  PR IDs, checklist refs).
- `implementation_result: ImplementationResumeData | None` — validated resume payload captured from `--resume-data`
  when the implementation gate hands control back to the graph.

## Relationships and Derived Rules

- `issue_key` maps to `thread_id = f"work-on-issue-{issue_key}"`; this relationship must remain stable across fresh
  runs and resumes.
- `step`, `status`, `failed_node`, and `resume_target_node` are coordinated runner/graph fields:
  - `step` identifies the last completed or currently paused node.
  - `status="paused"` requires `resume_target_node` to identify a gate or failed resumable node.
  - `status="failed"` requires `failed_node` and `error` to be populated together.
- `plan` is produced by `planning_node` and consumed by `planning_gate_node`; it must remain the single persisted plan
  body field used across both stub and real graphs.
- `implementation_result` is only populated when `resume_target_node == "implementation_gate"` and the payload passes
  the `ImplementationResumeData` schema.
- `artifact_references` entries are keyed by side-effect type and are validated against corresponding
  `idempotency_keys` during retry/resume reconciliation.

## Validation Rules

- `step` must use the existing workflow field name and may only contain known workflow node/gate identifiers.
- `plan` may be empty before `planning_node` runs, but `planning_gate_node` must reject approval if `plan` is missing.
- `agent_context` may contain flags such as `dry_run`, `interactive`, `model`, `jira_config_id`, and
  `azure_devops_config_id`; it must never store PATs, auth headers, or other secrets.
- `resume_target_node` may only be `planning_gate`, `implementation_gate`, or a node explicitly marked resumable by the
  runner.
- `implementation_result` must satisfy `ImplementationResumeData` when present; passing a boolean resume payload is
  valid only for `planning_gate`.
- Selective checkpoint reset must operate on the `thread_id` derived from `issue_key`; unrelated thread IDs in the same
  database remain valid.

## Event Entity (`WorkOnIssueEvent`)

- `event: str` — event name such as `planning_started`, `planning_completed`, or `dry_run_skipped`.
- `timestamp: str` — UTC ISO-8601 timestamp.
- `node: str | None` — optional node name associated with the event.
- `details: dict[str, Any] | None` — structured metadata for retries, interrupts, or reconciled side effects.

## Implementation Resume Payload (`ImplementationResumeData`)

- `completed: bool` — required and must be `true` to release `implementation_gate`.
- `summary: str` — required non-empty implementation summary.
- `affected_paths: list[str]` — optional list of non-empty repository-relative paths.
- Unknown keys are rejected during CLI/runner validation to keep resume semantics deterministic.

## State Transitions

`step` transitions (node/gate identifiers):

1. `initiate` → `setup`
2. `setup` → `planning`
3. `planning` → `planning_gate` (interrupt/pause)
4. `planning_gate` (resume approved) → `checklist_creation`
5. `checklist_creation` → `implementation`
6. `implementation` → `implementation_gate` (interrupt/pause)
7. `implementation_gate` (resume with valid `ImplementationResumeData`) → `implementation_review`
8. `implementation_review` → `verification`
9. `verification` (success) → `commit`
10. `commit` → `pull_request`
11. `pull_request` → `completion`
12. `completion` → terminal `status="completed"`

Terminal/branching rules:

- `verification` may loop back to `implementation` while `retry_count < MAX_RETRIES`.
- `verification` failures with `retry_count >= MAX_RETRIES` must transition to a failure/paused-for-resume state and
  must not transition to `commit`.
- Any side-effecting node may transition to `failed_resumable` when the runner records enough idempotency metadata to
  reconcile on resume.
- Any non-resumable failure transitions to `failed_terminal`, which requires a fresh run instead of `--resume`.

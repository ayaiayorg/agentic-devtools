# Implementation Plan: CI-Provider Abstraction & Workflow Extraction

## 1. Technical Context

**Stack**: Python 3.10+, pip-installable package (`agentic-devtools`), CLI entry points via `pyproject.toml`, GitHub Actions YAML workflows, `gh` CLI for GitHub API interactions.

**Key Dependencies**:

- `requests` — HTTP client for provider API calls
- `Jinja2` — template rendering (existing `substitute_variables()`)
- `PyYAML` — potential workflow config parsing
- Existing `agentic_devtools/adapters/base.py` — `IssueAdapter` ABC (issue CRUD only)
- Existing `agentic_devtools/cli/github/` — PR state, checks, merge, approve commands
- Existing `agentic_devtools/background_tasks.py` — background task infrastructure

**Architecture Decisions**:

- New `CIPlatformProvider` ABC is **separate** from the existing `IssueAdapter` — it covers CI-specific operations (event parsing, check status, comment posting, merge gating) not issue CRUD
- The orchestrator is **stateless** — all state flows through provider method calls and function parameters
- Feature flag (`AGDT_USE_PYTHON_ORCHESTRATOR=1`) enables parallel operation during migration
- CLI entry point follows existing `agdt-*` pattern via `pyproject.toml` scripts

## 2. Research Summary

Key design decisions:

- Provider interface design (separate from `IssueAdapter`)
- Retry/backoff strategy
- Event payload normalization approach
- Template rendering reuse
- Test fixture strategy

## 3. Design Overview

```text
┌─────────────────────────────────────────────────────────┐
│  ai-pr-loop.yml (≤50 lines)                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ triggers + permissions + agdt-ai-pr-loop          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  agentic_devtools/cli/ci/                              │
│  ├── __init__.py                                       │
│  ├── provider.py        (CIPlatformProvider ABC)       │
│  ├── exceptions.py      (MalformedEventError, etc.)    │
│  ├── models.py          (EventPayload, PRMetadata,    │
│  │                       CheckRunStatus, ReviewInfo)    │
│  ├── retry.py           (exponential backoff utility)  │
│  ├── github_provider.py (GitHubActionsProvider)        │
│  ├── orchestrator.py    (AI PR loop state machine)     │
│  ├── guards.py          (privileged-path, docker, etc.)│
│  ├── speckit_trigger.py (SpecKit label/phase logic)    │
│  └── commands.py        (CLI entry points)             │
└─────────────────────────────────────────────────────────┘
```

**Data Flow**:

1. YAML triggers `agdt-ai-pr-loop` with env vars (`GITHUB_EVENT_PATH`, `GITHUB_EVENT_NAME`)
2. CLI entry point reads the raw event JSON from `$GITHUB_EVENT_PATH`
3. Provider's `parse_event()` normalizes it into an `EventPayload` dataclass
4. Orchestrator evaluates guards, checks, reviews, and dispatches actions via provider methods
5. Provider methods call GitHub API (via `gh` CLI or `requests`)

## 4. Implementation Phases

### Phase 1: Foundation (Provider Interface + Models)

**Deliverables**:

- `agentic_devtools/cli/ci/__init__.py` — package init
- `agentic_devtools/cli/ci/exceptions.py` — `MalformedEventError`, `ProviderRateLimitError`
- `agentic_devtools/cli/ci/models.py` — `EventPayload`, `PRMetadata`, `CheckRunStatus`, `ReviewInfo` dataclasses
- `agentic_devtools/cli/ci/retry.py` — exponential backoff with jitter utility
  (1s initial delay, 60s cap, max 5 retries per call, honors `Retry-After` header
  on HTTP 429/403 responses, raises `ProviderRateLimitError` after exhaustion)
- `agentic_devtools/cli/ci/provider.py` — `CIPlatformProvider` ABC with all abstract methods
- Tests: unit tests for models, exceptions, retry logic (TDD)
  - All tests must follow the 1:1:1 test layout enforced by `scripts/validate_test_structure.py` (see `tests/README.md`)
  - Test files live under `tests/unit/cli/ci/` mirroring `agentic_devtools/cli/ci/`, one test file per symbol
  - Every directory must contain `__init__.py`

**ABC Methods** (minimum):

```python
class CIPlatformProvider(ABC):
    @abstractmethod
    def parse_event(self, raw_payload: dict, event_name: str) -> EventPayload: ...
    @abstractmethod
    def get_pr_metadata(self, pr_number: int) -> PRMetadata: ...
    @abstractmethod
    def list_check_runs(self, head_sha: str) -> list[CheckRunStatus]: ...
    @abstractmethod
    def list_reviews(self, pr_number: int) -> list[ReviewInfo]: ...
    @abstractmethod
    def post_comment(self, pr_number: int, body: str) -> int: ...
    @abstractmethod
    def update_comment(self, comment_id: int, body: str) -> None: ...
    @abstractmethod
    def find_comment(self, pr_number: int, marker: str) -> tuple[int, str] | None: ...
    # Returns (comment_id, comment_body) so callers can parse marker content
    # (e.g., extracting dispatch counts from repair-dispatch markers)
    @abstractmethod
    def approve_pr(self, pr_number: int, head_sha: str, body: str) -> None: ...
    @abstractmethod
    def merge_pr(self, pr_number: int, head_sha: str, method: str) -> None: ...
    @abstractmethod
    def request_reviewer(self, pr_number: int, reviewer: str) -> None: ...
    @abstractmethod
    def list_pr_files(self, pr_number: int) -> list[str]: ...
    @abstractmethod
    def get_check_annotations(self, check_run_id: int, limit: int) -> list[str]: ...
```

### Phase 2: GitHub Actions Provider

**Deliverables**:

- `agentic_devtools/cli/ci/github_provider.py` — full implementation of `CIPlatformProvider`
- Test fixtures: `tests/fixtures/ci_events/` with recorded payloads
- Integration tests verifying behavioral equivalence with inline JS (1:1:1 layout under `tests/unit/cli/ci/github_provider/`)

**Key Implementation Details**:

- Uses `gh` CLI (via `run_safe`) for API calls, consistent with existing codebase patterns
- All `run_safe` invocations that include user-controlled text (PR titles, comment bodies, branch names)
  **must** pass `shell=False` to prevent Windows `%VAR%` expansion — consistent with the existing
  security pattern in `agentic_devtools/cli/github/issue_commands.py`
- Handles pagination via `--paginate` flag
- Implements retry logic from `retry.py`
- Parses both `pull_request_review` and `workflow_run` event formats

### Phase 3: Guards Module

**Deliverables**:

- `agentic_devtools/cli/ci/guards.py` — all safety/security guards extracted:
  - `check_privileged_paths(files: list[str]) -> bool`
  - `check_docker_files(files: list[str]) -> bool`
  - `check_deduplication(provider, pr_number, head_sha, max_dispatches) -> tuple[bool, int]`
  - `check_exclusion_labels(labels: list[str]) -> tuple[bool, str | None]`
  - `check_fork_pr(head_repo: str, base_repo: str) -> bool`
  - `check_cycle_limit(cycle_count: int, max_cycles: int) -> bool`
**Concrete Guard Semantics** (MUST-preserve from existing YAML):

- **Privileged paths**: `.github/workflows/`, `.github/actions/`, `.github/scripts/` — any PR
  touching files under these directories (excluding `*.md` files) triggers the privileged-path
  guard and skips automated processing
- **Docker files**: `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml` — triggers
  the docker-files guard (matching the current `ai-pr-loop.yml` guard). **Note**: Phase 3
  intentionally expands the guard scope to also cover `.dockerignore` and `Dockerfile.*`
  patterns; this is a behavior change that will require review
- **Exclusion labels**: `ai-pr-loop-ignore` — skips the PR entirely (workflow exits
  early); `do-not-auto-merge` — allows processing but prevents automated merge (sets
  `do_not_merge` flag). These are the two labels currently enforced in `ai-pr-loop.yml`
- **Fork PRs**: head repository `full_name` differs from base repository `full_name`
  (i.e., `pr.head.repo.full_name !== pr.base.repo.full_name`), which catches both
  cross-owner and same-owner cross-repo PRs
- **Deduplication**: reads/upserts a marker PR comment (`<!-- repair-dispatch:<sha>:<count> -->`)
  and increments a dispatch count per SHA to prevent redundant re-triggers
  (max dispatches configurable, default 3 per SHA, matching `MAX_DISPATCHES_PER_SHA`
  in `ai-pr-loop.yml`). The marker-comment approach matches the current `ai-pr-loop.yml`
  implementation — it does **not** scan existing workflow-dispatch runs
- **Cycle limit**: maximum number of AI loop iterations per PR (tracked via
  `<!-- ai-pr-loop-cycle-tracker -->` comment, default 50 matching `ai-pr-loop.yml`)

- Tests: full coverage of each guard with edge cases (1:1:1 layout under `tests/unit/cli/ci/guards/`)

### Phase 4: Orchestrator Extraction

**Deliverables**:

- `agentic_devtools/cli/ci/orchestrator.py` — main AI PR loop state machine:
  - `run_ai_pr_loop(provider: CIPlatformProvider, event_payload: EventPayload) -> int`
  - Implements: metadata resolution → guards → lint patch handling → review evaluation → dispatch decision → merge gate → approval → merge → cycle recording
- `agentic_devtools/cli/ci/patch_handler.py` — lint patch download, validation, apply logic
- Tests: state machine tests with mocked provider, golden-file comparisons (1:1:1 layout under `tests/unit/cli/ci/orchestrator/`)

### Phase 5: SpecKit Trigger Extraction

**Deliverables**:

- `agentic_devtools/cli/ci/speckit_trigger.py`:
  - `process_speckit_label_event(provider, event_payload) -> int`
  - Label validation, idempotency check, phase transition logic
  - Deduplication guard for repeated triggers
- Tests: synthetic label events covering all phase transitions (1:1:1 layout under `tests/unit/cli/ci/speckit_trigger/`)

### Phase 6: CLI Entry Points & Comment Templates

**Deliverables**:

- `agentic_devtools/cli/ci/commands.py`:
  - `ai_pr_loop_command()` — CLI entry point for `agdt-ai-pr-loop`
  - `speckit_trigger_command()` — CLI entry point for `agdt-speckit-trigger`
- `agentic_devtools/prompts/ci/timeout-comment.md` — template for timeout comment
- `agentic_devtools/prompts/ci/exhausted-comment.md` — template for exhausted comment
- `agentic_devtools/prompts/ci/merge-failed-comment.md` — template for merge failure
- `agentic_devtools/prompts/ci/ready-no-merge-comment.md` — template for do-not-merge case
- Entry points in `pyproject.toml`
- Uses `substitute_variables()` for all comment rendering (FR-007)

**CI Template Loading**: These templates are **non-workflow templates** and do not follow the
`<workflow>/default-<step>-prompt.md` naming convention used by `load_prompt_template()`. A
dedicated `load_ci_template(template_name: str) -> str` helper will be added to the
`prompts/loader.py` module to resolve templates from the `prompts/ci/` subdirectory. This
helper **only loads raw template content** (reads the file from disk and returns the string);
it does **not** perform variable substitution. Callers are responsible for invoking
`substitute_variables(template, variables)` separately with the appropriate variables dict,
reusing the same rendering pipeline without requiring workflow state.

### Phase 7: YAML Minimization & Feature Flag

**Deliverables**:

- Minimized `ai-pr-loop.yml` (≤50 lines): triggers, permissions, env, single `agdt-ai-pr-loop` call.
  **Execution mode**: `agdt-ai-pr-loop` runs **synchronously** (not as a background task)
  so the GitHub Actions workflow step blocks until orchestration completes. This avoids
  the broken migration path where a background task exits the step before the loop finishes
- Feature flag: `AGDT_USE_PYTHON_ORCHESTRATOR` env var selects execution path
- Minimized speckit workflows (≤30 lines each)
- End-to-end smoke tests comparing old vs new path outputs

### Phase 8: Latency Benchmark & ADO Provider Stub

**Deliverables**:

- `scripts/measure-orchestrator-latency.py` — benchmark script (NFR-002)
- `agentic_devtools/cli/ci/ado_provider.py` — Azure DevOps stub (P3, validates abstraction)
- Documentation updates to `.github/copilot-instructions.md`

## 5. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Behavioral drift during extraction | High | Medium | Golden-file fixtures; parallel operation with feature flag |
| Rate limiting in CI | Medium | Low | Built-in retry with jitter; `Retry-After` header honoring |
| `gh` CLI version differences | Low | Low | Pin minimum `gh` version; test in CI matrix |
| Latency regression from Python overhead | Medium | Low | Benchmark script; early measurement in Phase 2 |
| Security guard regression | High | Low | Guards extracted first with 100% coverage; reviewed independently |
| YAML minimization breaks concurrency | Medium | Medium | Preserve concurrency group logic in CLI; integration test |

## 6. Dependencies

**External**:

- `gh` CLI (already available in CI runners and local dev)
- GitHub Actions runner environment variables (`GITHUB_EVENT_PATH`, `GITHUB_EVENT_NAME`, etc.)
- `COPILOT_GITHUB_TOKEN` secret (existing)

**Internal**:

- `agentic_devtools/cli/subprocess_utils.py` — `run_safe()` for shell commands
- `agentic_devtools/prompts/loader.py` — `substitute_variables()` for templates
- `agentic_devtools/background_tasks.py` — background task pattern (for long-running orchestration)
- `agentic_devtools/state.py` — state management (minimal usage; orchestrator is stateless)

**Ordering Constraints**:

- Phase 1 → Phase 2 (provider interface before implementation)
- Phase 2 → Phase 4 (provider needed for orchestrator tests)
- Phase 3 can parallel with Phase 2
- Phase 5 can parallel with Phase 4
- Phase 6 depends on Phase 4 + Phase 5
- Phase 7 depends on Phase 6
- Phase 8 can start after Phase 4

---
*Generated by Copilot SDK (claude-opus-4.6)*

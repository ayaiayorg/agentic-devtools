# Implementation Plan: Standardize Copilot Review PR Response Process

## 1. Technical Context

### Technology Stack

- **Language**: Python 3.10+ (per `requires-python = ">=3.10"` in `pyproject.toml`)
- **Package**: `agentic-devtools` (pip-installable, CLI entry points via `pyproject.toml`)
- **CI Platform**: GitHub Actions (`gh` CLI for API interactions)
- **APIs**: GitHub REST API, GitHub GraphQL API (via `gh api`)
- **Template Engine**: Jinja2 (existing `agentic_devtools.prompts.loader` module)
- **Testing**: pytest with 1:1:1 structure, 100% coverage requirement
- **Existing Infrastructure**: `agentic_devtools/cli/ci/` package with provider abstraction, orchestrator, guards, retry utilities

### Architecture Decisions

- All business logic in Python (`agentic_devtools/cli/ci/`), workflow YAML is orchestration-only
- Reuse existing `CIPlatformProvider` abstraction and `GitHubActionsProvider`
- Reuse existing `agdt-gh-resolve-review-threads` and `agdt-gh-reply-to-review-comments` Python functions directly (not subprocess)
- Templates in `agentic_devtools/prompts/ci/` loaded via `load_ci_template()` + `substitute_variables()`
- New modules extend the existing `cli/ci/` package; no new top-level packages

## 2. Research Summary

Key technical decisions informing this plan:

- **Copilot SDK integration**: Use Copilot SDK for commit message generation with a 5-minute timeout; local fallback generates a conventional-commit message from PR title + commit history
- **Result comment detection**: Polling-based approach (30s intervals, 15min max) preferred over webhooks for simplicity and reliability in GitHub Actions
- **Force-push safety**: `--force-with-lease` combined with pre-push SHA verification (FR-017) prevents overwriting concurrent changes
- **Template selection**: Automatic selection based on review state — suppressed-comments template vs CI-only template

## 3. Design Overview

### High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│  GitHub Actions Workflow (ai-pr-loop.yml)                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Orchestration only: triggers, env vars, secrets, steps     │  │
│  └────────────────────────────────────────────────────────────┘  │
│         │                                                        │
│         ▼                                                        │
│  agdt-ai-pr-loop (Python CLI entry point)                        │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│  agentic_devtools/cli/ci/ (Python business logic)                │
│                                                                  │
│  orchestrator.py ─── Extended state machine:                     │
│    ├── Guards (existing)                                         │
│    ├── CI status check (existing)                                │
│    ├── Review evaluation (existing)                              │
│    ├── NEW: Trigger comment posting                              │
│    ├── NEW: Result comment polling                               │
│    ├── NEW: Thread resolution                                    │
│    ├── NEW: Commit squash + message generation                   │
│    └── NEW: Force-push with SHA verification                     │
│                                                                  │
│  NEW modules:                                                    │
│  ├── trigger.py       (trigger comment logic + dedup)            │
│  ├── result_poller.py (agent result detection + timeout)         │
│  ├── thread_resolver.py (reply + resolve orchestration)          │
│  ├── squash.py        (commit squash + message generation)       │
│  └── templates.py     (template selection + rendering)           │
│                                                                  │
│  Reused (direct Python calls, external to cli/ci/):              │
│  ├── agentic_devtools/cli/github/resolve_review_threads.py       │
│  └── agentic_devtools/cli/github/review_reply.py                 │
└──────────────────────────────────────────────────────────────────┘
```

### Module Interaction Flow

```text
Event (pull_request_review / workflow_run)
  → orchestrator.run_ai_pr_loop()
    → guards (existing)
    → CI status check (existing)
    → copilot_review_ready? (new check)
    → trigger.post_trigger_comment()
      → templates.select_template()
      → templates.render_trigger_comment()
      → dedup check (find_comment with marker)
      → provider.post_comment() [PAT-authenticated]
    → result_poller.poll_for_result_comment()
      → filter by sentinel marker (<!-- copilot-agent-result -->)
      → secondary confirmation: comment author == github-actions[bot]
      → 30s interval, 15min max
      → timeout → post failure comment (via GITHUB_TOKEN) + exit non-zero
    → thread_resolver.resolve_copilot_review_threads()
      → calls review_reply functions directly
      → calls resolve_review_threads functions directly
    → squash.squash_and_force_push()
      → generate commit message (Copilot SDK or fallback)
      → SHA verification before force-push
      → git push --force-with-lease [PAT-authenticated]
```

## 4. Implementation Phases

### Phase 1: Template System & Comment Rendering (FR-003, FR-004, FR-005, FR-006)

**Constraints:**

- **FR-006 compliance**: All rendered trigger comments MUST begin with `@copilot` at the very start of the comment body.
  Templates MUST place `@copilot` as the first content, with any metadata (e.g., dedup markers) appended after
  the `@copilot` prefix line.

**Deliverables:**

- `agentic_devtools/prompts/ci/pr_review_process.md` template (must start with `@copilot`)
- `agentic_devtools/prompts/ci/ci_review_process.md` template (must start with `@copilot`)
- `agentic_devtools/cli/ci/templates.py` — template selection and rendering module
- Unit tests following 1:1:1 structure (include assertion that rendered output starts with `@copilot`)

**New files:**

| File | Purpose |
|------|---------|
| `agentic_devtools/prompts/ci/pr_review_process.md` | Template for suppressed-comments trigger |
| `agentic_devtools/prompts/ci/ci_review_process.md` | Template for CI-only trigger |
| `agentic_devtools/cli/ci/templates.py` | `select_template()`, `render_trigger_comment()` |
| `tests/unit/cli/ci/templates/test_select_template.py` | Template selection tests |
| `tests/unit/cli/ci/templates/test_render_trigger_comment.py` | Rendering tests |

### Phase 2: Trigger Comment & Deduplication (FR-001, FR-002, FR-006, FR-012)

**Constraints:**

- The dedup marker (`<!-- copilot-trigger:REVIEW_ID -->`) MUST be appended after the initial `@copilot` prefix line (not before it) to preserve FR-006 compliance.
- `post_trigger_comment()` MUST validate that the final comment body starts with `@copilot` before posting.

**Deliverables:**

- `agentic_devtools/cli/ci/trigger.py` — trigger comment posting with deduplication
- Integration with `CIPlatformProvider.post_comment()` and `find_comment()`
- Hidden HTML marker for deduplication (`<!-- copilot-trigger:REVIEW_ID -->`)
- Unit tests

**New files:**

| File | Purpose |
|------|---------|
| `agentic_devtools/cli/ci/trigger.py` | `post_trigger_comment()`, `is_duplicate_trigger()` |
| `tests/unit/cli/ci/trigger/test_post_trigger_comment.py` | Trigger posting tests |
| `tests/unit/cli/ci/trigger/test_is_duplicate_trigger.py` | Dedup detection tests |

### Phase 3: Result Comment Polling (FR-014, FR-016)

**Constraints:**

- **FR-014 compliance**: Polling MUST filter primarily by the sentinel marker (`<!-- copilot-agent-result -->`) in the comment body, with the `github-actions[bot]` author login as secondary
  confirmation.
- The result comment MUST be posted by the workflow step using the workflow's `GITHUB_TOKEN` (not the PAT) to ensure the author is deterministically `github-actions[bot]`.
- Timeout failure comments (FR-016) MUST also be posted via `GITHUB_TOKEN` (author: `github-actions[bot]`).

**Deliverables:**

- `agentic_devtools/cli/ci/result_poller.py` — polling logic with timeout + failure comment
- Sentinel marker detection (`<!-- copilot-agent-result -->`) + author login verification (`github-actions[bot]`)
- Timeout failure comment with workflow run link (posted via `GITHUB_TOKEN`)
- Unit tests

**New files:**

| File | Purpose |
|------|---------|
| `agentic_devtools/cli/ci/result_poller.py` | `poll_for_result_comment()`, `post_timeout_failure()` |
| `tests/unit/cli/ci/result_poller/test_poll_for_result_comment.py` | Polling logic tests |
| `tests/unit/cli/ci/result_poller/test_post_timeout_failure.py` | Timeout failure tests |

### Phase 4: Thread Resolution Orchestration (FR-007, FR-008)

**Deliverables:**

- `agentic_devtools/cli/ci/thread_resolver.py` — orchestrates reply + resolve
- Direct Python calls to existing `resolve_review_threads` and `review_reply` functions
- Retry logic (3 retries per NFR-002)
- Unit tests

**New files:**

| File | Purpose |
|------|---------|
| `agentic_devtools/cli/ci/thread_resolver.py` | `resolve_copilot_review_threads()` |
| `tests/unit/cli/ci/thread_resolver/test_resolve_copilot_review_threads.py` | Resolution tests |

### Phase 5: Commit Squash & Force-Push (FR-009, FR-010, FR-011, FR-017)

**Deliverables:**

- `agentic_devtools/cli/ci/squash.py` — squash commits, generate message, force-push
- Copilot SDK integration with 5-minute timeout + local fallback
- SHA verification before force-push (FR-017)
- Unit tests

**New files:**

| File | Purpose |
|------|---------|
| `agentic_devtools/cli/ci/squash.py` | `squash_and_force_push()`, `generate_commit_message()`, `_local_fallback_message()` |
| `tests/unit/cli/ci/squash/test_squash_and_force_push.py` | Squash + push tests |
| `tests/unit/cli/ci/squash/test_generate_commit_message.py` | Message generation tests |
| `tests/unit/cli/ci/squash/test_local_fallback_message.py` | Fallback message tests |

### Phase 6: Orchestrator Integration (FR-013, NFR-005, NFR-006)

**Deliverables:**

- Extend `run_ai_pr_loop()` with new Copilot review response path
- Structured audit logging for each step
- Update workflow YAML to pass required secrets/env vars
- Integration tests

**Modified files:**

| File | Change |
|------|--------|
| `agentic_devtools/cli/ci/orchestrator.py` | Add copilot response path after review evaluation |
| `agentic_devtools/cli/ci/models.py` | Add `CopilotReviewContext` dataclass |
| `agentic_devtools/cli/ci/__init__.py` | Export new modules |
| `.github/workflows/ai-pr-loop.yml` | Verify existing `COPILOT_GITHUB_TOKEN` secret mapping; add `GITHUB_TOKEN` env var to result-posting and timeout-failure steps for `github-actions[bot]` authorship |
| `pyproject.toml` | No new entry points needed (extends existing `agdt-ai-pr-loop`) |

### Phase 7: End-to-End Testing & Documentation

**Deliverables:**

- Workflow integration tests (`tests/workflows/`)
- Documentation updates
- PR check validation

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Copilot SDK unavailable/undocumented | Medium | Medium | Local fallback generates message from PR title + commit history |
| Race condition during force-push | Low | High | SHA verification (FR-017) + `--force-with-lease` |
| Polling timeout false positives | Low | Medium | 15min window is generous; failure comment provides debugging link |
| Duplicate triggers from concurrent workflow runs | Medium | Low | Dedup marker + concurrency group in YAML |
| PAT permission issues | Low | High | Clear error messages (NFR-007); document required scopes |
| Existing `agdt-gh-*` function API changes | Low | Medium | Pin to internal function signatures; add integration tests |

## 6. Dependencies

### External Dependencies

- GitHub REST API v3 (PR comments, reviews, check runs)
- GitHub GraphQL API (thread resolution — already used)
- Copilot SDK (commit message generation — with fallback)
- `gh` CLI (already required; pinned in CI)

### Internal Dependencies

- `agentic_devtools.cli.ci.provider.CIPlatformProvider` — post_comment, find_comment
- `agentic_devtools.cli.ci.github_provider.GitHubActionsProvider` — concrete implementation
- `agentic_devtools.cli.ci.retry.retry_with_backoff` — retry decorator
- `agentic_devtools.cli.github.resolve_review_threads` — thread resolution internals
- `agentic_devtools.cli.github.review_reply` — reply posting internals
- `agentic_devtools.prompts.loader.load_ci_template` — template loading
- `agentic_devtools.prompts.loader.substitute_variables` — Jinja2 rendering

### Sequencing Constraints

- Phase 1 (templates) can start immediately — no dependencies
- Phase 2 (trigger) depends on Phase 1 templates
- Phase 3 (polling) depends on Phase 2 (needs trigger comment to define polling start)
- Phase 4 (thread resolution) depends on Phase 3 (needs result comment reference)
- Phase 5 (squash) depends on Phase 4 (runs after threads resolved)
- Phase 6 (orchestrator) depends on all prior phases
- Phase 7 (E2E) depends on Phase 6

---
*Generated by Copilot SDK (claude-opus-4.6)*

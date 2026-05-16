# Implementation Plan: LangChain-Based PR Review Workflow (Parallel Path)

**Issue**: [#1428](https://github.com/ayaiayorg/agentic-devtools/issues/1428)  
**Branch**: `1428-implement-langchain-based-pull`

## 1. Technical Context

| Aspect | Detail |
|--------|--------|
| Language | Python 3.10+ |
| Package manager | pip / hatchling + hatch-vcs |
| LangGraph (existing) | `langgraph>=0.2.0` already a core dependency |
| LangGraph checkpoint | `langgraph-checkpoint-sqlite>=3.0.1` (core dep) |
| Existing orchestration | `agentic_devtools/orchestration/` — work-on-issue graph |
| Review state | `agentic_devtools/cli/azure_devops/review_state.py` (dataclasses + JSON CRUD) |
| Review workflow entry | `agentic_devtools/cli/workflows/commands.py` → `initiate_pull_request_review_workflow` |
| Config system | `.agdt/config/review-models.json` + override file |
| Test policy | 1:1:1 under `tests/unit/`, TDD required, `pytest.importorskip` for optional deps |

### Key Dependencies

- `langgraph>=0.2.0` — already a **core** dependency (not optional)
- `langchain-core>=0.3,<1.0` — needs to be added as optional extra `[langchain]`
- Existing `review-state.json` schema must remain unchanged

### Architecture Decisions

- Engine routing at the workflow initiation layer (not deep inside Azure DevOps commands)
- LangGraph review graph in `agentic_devtools/orchestration/review/` (new subpackage)
- Shared checkpointing from parent `orchestration/` package
- Existing lifecycle commands (`agdt-approve-file`, etc.) remain engine-agnostic

## 2. Research Summary

See [research.md](research.md) for detailed analysis of:

- Engine resolution priority mechanism
- LangGraph graph topology for PR review
- Optional dependency packaging strategy
- Session/failure state recording

Key decisions:

1. **Routing layer**: Inject at `initiate_pull_request_review_workflow` before calling `review_pull_request`
2. **State compatibility**: LangChain path writes identical `review-state.json`; adds `engine` field to session entries
3. **Dependency model**: `langchain-core` as optional extra; `langgraph` already core
4. **Graph design**: Linear pipeline with conditional retry edges (scaffold → review-files → summarize)

## 3. Design Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│               agdt-initiate-pull-request-review-workflow         │
│                          (CLI entry point)                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  resolve_engine()   │
                    │  CLI > state > env  │
                    └──────┬─────────┬────┘
                           │         │
              engine="default"   engine="langchain"
                           │         │
              ┌────────────▼──┐  ┌───▼─────────────────────┐
              │ Existing path │  │ Preflight validation     │
              │ (unchanged)   │  │ → import langchain-core  │
              └───────────────┘  │ → validate config        │
                                 └───────────┬─────────────┘
                                             │
                                 ┌───────────▼─────────────┐
                                 │ LangGraph Review Graph   │
                                 │ (orchestration/review/)  │
                                 │                          │
                                 │ scaffold → file_review   │
                                 │ → summarize → complete   │
                                 └───────────┬─────────────┘
                                             │
                                 ┌───────────▼─────────────┐
                                 │ review-state.json        │
                                 │ (same schema, +engine    │
                                 │  field on session entry) │
                                 └─────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Engine Resolution & Routing Infrastructure

**Deliverables**: Engine resolution function, `--engine` CLI flag, state/env reading, routing dispatch

| Task | File | Description |
|------|------|-------------|
| 1.1 | `agentic_devtools/cli/workflows/engine_resolution.py` (new) | `resolve_review_engine(cli_flag, state_key, env_var) → str` with priority logic |
| 1.2 | `agentic_devtools/cli/workflows/commands.py` | Add `--engine` argparse argument to `initiate_pull_request_review_workflow` |
| 1.3 | `agentic_devtools/cli/workflows/commands.py` | Write `review.engine` to state when CLI flag provided; call `resolve_review_engine` for routing |
| 1.4 | `agentic_devtools/cli/workflows/commands.py` | Branch: if engine == "langchain" → call LangChain path; else → existing path |
| 1.5 | Tests | `tests/unit/cli/workflows/engine_resolution/test_resolve_review_engine.py` — all priority combos |

### Phase 2: Dependency Preflight & Error Handling

**Deliverables**: Import validation, config validation, actionable error messages

| Task | File | Description |
|------|------|-------------|
| 2.1 | `agentic_devtools/orchestration/review/__init__.py` (new) | Package init with `validate_langchain_dependencies()` |
| 2.2 | `agentic_devtools/orchestration/review/preflight.py` (new) | Check `langchain-core` importable, check config present |
| 2.3 | `pyproject.toml` | Add `[langchain]` optional extra with `langchain-core>=0.3,<1.0` |
| 2.4 | `agentic_devtools/cli/workflows/commands.py` | Call preflight before LangChain dispatch; exit(1) with actionable message on failure |
| 2.5 | Tests | `tests/unit/orchestration/review/preflight/test_validate_langchain_dependencies.py` |

### Phase 3: LangGraph Review Graph Implementation

**Deliverables**: State schema, graph nodes, graph builder for PR review

| Task | File | Description |
|------|------|-------------|
| 3.1 | `agentic_devtools/orchestration/review/state_schema.py` (new) | `PRReviewState` TypedDict for LangGraph |
| 3.2 | `agentic_devtools/orchestration/review/nodes.py` (new) | Node functions: `scaffold_node`, `review_file_node`, `summarize_node`, `complete_node` |
| 3.3 | `agentic_devtools/orchestration/review/graph_builder.py` (new) | `build_pr_review_graph(checkpointer=None) → CompiledStateGraph` |
| 3.4 | `agentic_devtools/orchestration/review/runner.py` (new) | `run_langchain_review(pr_id, config, state_dir)` — orchestrates graph invocation |
| 3.5 | Tests | Unit tests for each node + graph compilation test (using `pytest.importorskip`) |

### Phase 4: Review-State Integration

**Deliverables**: LangChain path reads/writes compatible `review-state.json`

| Task | File | Description |
|------|------|-------------|
| 4.1 | `agentic_devtools/orchestration/review/state_bridge.py` (new) | Adapter: load existing `ReviewState`, update from graph output, save back |
| 4.2 | `agentic_devtools/cli/azure_devops/review_state.py` | Add optional `engine` field to `ReviewSession` dataclass |
| 4.3 | `agentic_devtools/orchestration/review/nodes.py` | Wire scaffold/review nodes to call existing `review_scaffold.py` and `file_review_commands.py` |
| 4.4 | Tests | Schema compatibility: write via LangChain path, read via existing commands |

### Phase 5: Observability & Failure Recording

**Deliverables**: `[langchain]`-prefixed logging, failed session recording

| Task | File | Description |
|------|------|-------------|
| 5.1 | `agentic_devtools/orchestration/review/logging_config.py` (new) | Logger setup with `[langchain]` prefix filter |
| 5.2 | `agentic_devtools/orchestration/review/runner.py` | Wrap graph invocation in try/except; record `"failed"` session on exception |
| 5.3 | `agentic_devtools/orchestration/review/runner.py` | Emit progress markers: `[langchain] scaffolding...`, `[langchain] reviewing file N/M...` |
| 5.4 | Tests | Verify failed session status written; verify no credential leakage in logs |

### Phase 6: Integration Testing & Documentation

**Deliverables**: End-to-end routing tests, updated docs

| Task | File | Description |
|------|------|-------------|
| 6.1 | `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py` | Extend with engine routing scenarios |
| 6.2 | Integration test | Side-by-side artifact comparison (mock LLM) |
| 6.3 | `.github/copilot-instructions.md` | Document `--engine langchain` flag and `review.engine` state key |
| 6.4 | `README.md` / `CHANGELOG.md` | Feature documentation |

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LangGraph version incompatibility between existing core dep and new `langchain-core` extra | Medium | High | Pin compatible ranges; test in CI with both installed |
| Startup overhead exceeds 5s budget (NFR-003) | Low | Medium | Lazy imports; measure in Phase 3 tests |
| LangChain callback leaks credentials | Low | High | Custom callback handler that filters sensitive patterns; test coverage |
| Existing review lifecycle commands break with new session `engine` field | Low | Medium | Field is optional with default `None`; backward-compatible deserialization |
| Partial write corruption on mid-run failure | Medium | Medium | Use atomic write pattern (write to temp, rename); mark session `"failed"` |

## 6. Dependencies

### External

| Package | Version | Type |
|---------|---------|------|
| `langchain-core` | `>=0.3,<1.0` | Optional extra `[langchain]` |
| `langgraph` | `>=0.2.0` | Already core dependency |
| `langgraph-checkpoint-sqlite` | `>=3.0.1` | Already core dependency |

### Internal

| Module | Dependency Reason |
|--------|-------------------|
| `orchestration/checkpointing.py` | Shared SQLite checkpointer |
| `cli/azure_devops/review_state.py` | Read/write `review-state.json` |
| `cli/azure_devops/review_scaffold.py` | Thread scaffolding |
| `cli/azure_devops/review_models_config.py` | Model configuration loading |
| `cli/workflows/commands.py` | Routing injection point |
| `state.py` | Read `review.engine` state key |

---
*Generated by Copilot SDK (claude-opus-4.6)*

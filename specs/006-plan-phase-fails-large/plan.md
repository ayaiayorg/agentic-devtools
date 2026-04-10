# Implementation Plan: Plan Phase Context Budget Management (Spec 006)

**Branch**: `006-plan-phase-fails-large` | **Spec**: [spec.md](spec.md) | **Issue**: #1175

## 1. Technical Context

- **Language**: Python 3.10+ (target version from `pyproject.toml`) / Bash (trigger scripts)
- **SpecKit trigger scripts**: `.github/scripts/speckit-trigger/` — shell + Python generation pipeline
- **State layer**: `agentic_devtools/state.py` — JSON-based, dot-notation keys
- **Key source files**:
  - `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — `run_plan_phase()` (plan orchestration), `call_llm()` (LLM invocation with prompt payload)
  - `.github/scripts/speckit-trigger/copilot_generate.py` — Python generation path invoked by shell trigger
  - `agentic_devtools/context_budget.py` — NEW reusable budget module (pure functions, no I/O)
- **Key test dirs**:
  - `tests/unit/context_budget/` — NEW budget module unit tests
- **Existing truncation patterns**: `_inline_prompt()` in `session.py` (argv-limit fallback chain), `_format_jira_issue_comments()` (200-char truncation per comment)
- **Coverage requirement**: 100% line coverage enforced by CI (branch coverage disabled)

## 2. Research Summary

Key research decisions and rationale:

| Decision | Choice |
|---|---|
| Module location | New module `agentic_devtools/context_budget.py` — standalone, no circular deps |
| Integration point | Between issue context assembly and `call_llm()` invocation in `run_plan_phase()` within `generate-spec-from-issue.sh` |
| Configuration source | `AGDT_PLAN_CONTEXT_BUDGET` env var → `os.environ.get()`, consistent with `AGDT_USE_EMOJI` pattern |
| Reduction strategy | Deterministic pipeline: strip markdown → remove images → collapse whitespace → hard truncate |
| Budget scope | Assembled plan-phase prompt content (spec.md content + plan instructions passed to `call_llm()`) |
| Fallback chain | Full → Reduced → Truncated → Summary-only → `ContextBudgetError` (permanent failure) |
| No LLM summarization | Explicit exclusion — all reduction is deterministic, reproducible, zero-cost |
| Backward compatibility | Below-budget content returned byte-identical — zero-allocation passthrough |

## 3. Design Overview

```text
generate-spec-from-issue.sh            ← existing trigger script
  │
  ├─ spec.md content: str               ← assembled from issue context
  └─ plan instructions: str             ← prompt template
        │
        ▼
run_plan_phase()                        ← existing plan orchestration
        │
  assembled prompt payload: str
        │
        ▼
  ┌─────────────────────────────────────────┐
  │  enforce_context_budget()               │  ← NEW (context_budget.py)
  │                                         │
  │  1. Measure prompt payload char count   │
  │  2. If ≤ budget → return unchanged      │
  │  3. Stage 1: apply_reductions()         │
  │     • strip_markdown_formatting()       │
  │     • remove_image_references()         │
  │     • collapse_whitespace()             │
  │  4. If ≤ budget → return reduced        │
  │  5. Stage 2: hard_truncate()            │
  │     • Truncate to budget with marker    │
  │  6. If ≤ budget → return truncated      │
  │  7. Stage 3: summary_only()             │
  │     • First N chars of content only     │
  │  8. If still over → ContextBudgetError  │
  └─────────────────────────────────────────┘
        │
        ▼
call_llm() → copilot_generate.py       ← existing LLM invocation with budget-compliant prompt
```

### Key Design Principles

1. **Single responsibility**: `context_budget.py` is a pure-function module — no state reading, no I/O, no side effects. Configuration (budget value) is passed as a parameter.
2. **Caller controls integration**: `run_plan_phase()` in `generate-spec-from-issue.sh` reads the env var,
   invokes `enforce_context_budget()` (via a Python helper script or inline call), and passes results to `call_llm()`.
   This keeps the budget module testable in isolation.
3. **Byte-identical passthrough**: When combined content is ≤ budget, the original strings are returned without any transformation — identity check, not deep-copy.
4. **Diagnostic metadata**: Every call returns a `BudgetResult` dataclass containing the stage reached, original/final sizes, and whether reduction occurred — enabling logging and future telemetry.

## 4. Implementation Phases

### Phase 1 — Core Budget Module (TDD: RED → GREEN)

**Goal**: Create `agentic_devtools/context_budget.py` with the reduction pipeline and all supporting types.

**Deliverables**:

- `ContextBudgetError` exception class
- `ReductionStage` enum: `PASSTHROUGH`, `REDUCED`, `TRUNCATED`, `SUMMARY_ONLY`
- `BudgetResult` dataclass: `description`, `comments`, `stage`, `original_chars`, `final_chars`, `budget`
- Pure reduction functions: `strip_markdown_formatting()`, `remove_image_references()`, `collapse_whitespace()`, `hard_truncate()`
- `validate_content_shape()` — non-empty + substantive text check
- `enforce_context_budget()` — orchestrator function implementing the fallback chain

**Step 1 — Create test scaffolding** (RED):

```text
tests/unit/context_budget/__init__.py
tests/unit/context_budget/test_enforce_context_budget.py
tests/unit/context_budget/test_strip_markdown_formatting.py
tests/unit/context_budget/test_remove_image_references.py
tests/unit/context_budget/test_collapse_whitespace.py
tests/unit/context_budget/test_hard_truncate.py
tests/unit/context_budget/test_validate_content_shape.py
tests/unit/context_budget/test_budgetresult.py
tests/unit/context_budget/test_reductionstage.py
tests/unit/context_budget/test_contextbudgeterror.py
```

Test cases to cover:

- Below-budget content → passthrough (byte-identical)
- Exactly-at-budget content → passthrough
- Over-budget with markdown → reduced via strip
- Over-budget with images → reduced via image removal
- Over-budget requiring truncation → hard truncate with `[…truncated]` marker
- Over-budget requiring summary-only → description-only, truncated
- Empty input → `validate_content_shape()` raises or returns sentinel
- Input that is only images/whitespace → summary-only stage
- Budget of 0 → immediate `ContextBudgetError`
- Negative budget → treated as 0, immediate error
- Non-numeric `AGDT_PLAN_CONTEXT_BUDGET` → handled at call site, not in pure module
- Already-minimal content that cannot be reduced → `ContextBudgetError`
- Determinism: identical input → identical output (assert byte equality)

**Step 2 — Implement module** (GREEN):

File: `agentic_devtools/context_budget.py`

```python
"""Plan-phase context budget management.

Enforces a character budget on content passed to the planning workflow step.
All reduction techniques are deterministic — no LLM summarization.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass

DEFAULT_CONTEXT_BUDGET = 32_000


class ContextBudgetError(Exception):
    """Raised when content cannot be reduced to fit the budget."""


class ReductionStage(enum.Enum):
    PASSTHROUGH = "passthrough"
    REDUCED = "reduced"
    TRUNCATED = "truncated"
    SUMMARY_ONLY = "summary_only"


@dataclass(frozen=True)
class BudgetResult:
    description: str
    comments: str
    stage: ReductionStage
    original_chars: int
    final_chars: int
    budget: int
```

**Step 3 — Validate** (REFACTOR):

```bash
agdt-test-pattern tests/unit/context_budget/ -v
python scripts/validate_test_structure.py
```

---

### Phase 2 — Integration Into SpecKit Trigger Pipeline

**Goal**: Wire `enforce_context_budget()` into `run_plan_phase()` in `generate-spec-from-issue.sh` so the plan-generation LLM call receives budget-compliant content.

**Step 1 — Write integration tests** (RED):

Create tests for the SpecKit trigger integration:

- Plan phase with small issue → passthrough (no change)
- Plan phase with oversized issue body → reduced content reaches `call_llm()`
- `AGDT_PLAN_CONTEXT_BUDGET` env var overrides default
- Invalid env var value → falls back to default with warning
- `ContextBudgetError` → prints error, plan phase fails gracefully with actionable message

**Step 2 — Modify `run_plan_phase()` in `generate-spec-from-issue.sh`** (GREEN):

Insert budget enforcement before the `call_llm "$prompt"` invocation in `run_plan_phase()`. The shell script
should call the Python budget module (via a helper invocation) to enforce the context budget on the assembled
prompt payload, then use the reduced content for the LLM call.

**Step 3 — Update `copilot_generate.py`**:

Ensure the Python generation path surfaces oversized-input detection and fallback-compatible failure signaling
back to `generate-spec-from-issue.sh` when the budget cannot be met.

---

### Phase 3 — Reduction Functions Implementation

**Goal**: Implement the four deterministic reduction functions.

| Function | Removes | Preserves |
|---|---|---|
| `strip_markdown_formatting()` | `#`, `**`, `__`, `*`, `_`, `[text](url)` → `text`, `---` | Plain text content, code block content |
| `remove_image_references()` | `![alt](url)`, `<img>`, `!image!`, base64 data URIs | All non-image content |
| `collapse_whitespace()` | Multiple blank lines, trailing spaces, multiple spaces | Single blank lines, leading indent |
| `hard_truncate(text, limit)` | Content beyond limit | Word boundary before limit, `[…truncated]` marker |

---

### Phase 4 — Validation & Edge Cases

**Goal**: `validate_content_shape()` and all 8 documented edge cases.

---

### Phase 5 — Full Suite Verification

```bash
agdt-test && agdt-task-wait
bash scripts/run-pr-checks.sh
python scripts/validate_test_structure.py
```

## 5. Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Markdown stripping removes meaningful content | Medium | Preserve code block content; extensive test fixtures |
| Budget too aggressive — planning prompt loses critical context | Low | Summary-only is last resort; budget configurable via env var |
| Secondary call sites have different variable shapes | Medium | Audit all `issue_description` usages; shared helper |
| Existing test mocks break with new budget logic | Medium | Budget is transparent for small content (passthrough) |
| Performance regression on >1MB content | Low | All operations O(n) string/regex; no LLM calls |

## 6. Dependencies

### External

- No new third-party packages (uses `re`, `dataclasses`, `enum` from stdlib)

### Internal

- `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — primary integration point (`run_plan_phase()`, `call_llm()`)
- `.github/scripts/speckit-trigger/copilot_generate.py` — Python generation path
- `agentic_devtools/context_budget.py` — NEW reusable budget module

### Sequencing

1. Phase 1 (core module) → no deps
2. Phase 3 (reducers) → parallel with Phase 1
3. Phase 2 (integration) → depends on 1 + 3
4. Phase 4 (edge cases) → depends on 1 + 3
5. Phase 5 (verification) → depends on all

---
*Generated by Copilot SDK (claude-opus-4.6)*

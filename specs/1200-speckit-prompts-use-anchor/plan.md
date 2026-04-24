# Implementation Plan: Semantic Anchors in SpecKit Task Prompts

## Technical Context

- **Stack**: Markdown prompt templates consumed by LLM-based planning agents (GPT-4/4o family)
- **Architecture**: SpecKit pipeline — `speckit.tasks` agent reads spec/plan artifacts and generates `tasks.md` using the tasks template as structural reference
- **Key files (in scope)**:
  - `.github/agents/speckit.tasks.agent.md` — agent prompt driving task generation (measured: **1,508 tokens**, cl100k_base)
  - `.specify/templates/tasks-template.md` — structural template referenced by the agent (measured: **2,380 tokens**, cl100k_base)
- **Validation-only file** (read, not edited): `.github/agents/speckit.implement.agent.md` — the implement agent that consumes generated tasks
- **Tokenizer**: OpenAI `cl100k_base` (tiktoken) for NFR-001 measurement
- **Token budget**: NFR-001 specifies baseline ~1,601 tokens, ceiling ~1,841 tokens. The spec likely targets the agent file (1,508 baseline); a ~240-token growth allowance means the agent file must
  stay ≤ ~1,750 tokens. The template has a separate, larger budget; total additions across both files should remain modest.

## Research Summary

Key design decisions:

- **Where to place semantic-anchor guidance** — in the agent file's Task Generation Rules section
- **How to update the template** — update the Notes section and add an HTML comment block with anchor guidance
- **Terminology normalization** — unified term "semantic anchor", no legacy alternatives

## Design Overview

The change is a **prompt-wording-only update** to two files. No runtime code, no execution engine changes, no new files.

### Change Strategy

1. **Agent file** (`speckit.tasks.agent.md`): Add a compact "Location References" subsection under Task Generation Rules that:
   - Mandates semantic anchors instead of hardcoded line numbers
   - Defines acceptable anchor types for code and non-code files
   - Covers insertion-point and cross-task reference patterns
   - Uses the unified term "semantic anchor"

2. **Template file** (`tasks-template.md`): Add a brief guidance block in the Notes section that:
   - Reinforces the semantic-anchor requirement for generated output
   - Provides compact before/after examples showing the transformation
   - Covers edge cases (ambiguous anchors, newly created symbols)

### Design Constraints

- Additions to the agent file must stay within ~240 tokens of the 1,508 baseline
- Template additions should be proportionally modest
- No legacy terminology ("content-based anchor", "structural reference") introduced
- The implement agent prompt is NOT modified — only validated for compatibility

## Implementation Phases

### Phase 1: Baseline Measurement and Audit

**Deliverables**: Documented token baselines, audit of existing line-number patterns in generated output

- [ ] T001 Measure and record cl100k_base token counts for both in-scope files (pre-change baseline)
- [ ] T002 Audit 3+ existing `tasks.md` files in `specs/` to catalogue line-number reference patterns and confirm the problem scope
- [ ] T003 Read the implement agent prompt (`speckit.implement.agent.md`) and confirm it uses search-based navigation (grep/glob/view) — no line-number dependency

### Phase 2: Agent Prompt Update

**Deliverables**: Updated `.github/agents/speckit.tasks.agent.md` with semantic-anchor guidance

- [ ] T004 [US1] [US3] Add a "Location References" subsection inside the existing "Task Generation Rules" section of `speckit.tasks.agent.md` containing:
  - A rule stating tasks MUST use **semantic anchors** (not hardcoded line numbers) when describing where to edit a file
  - Acceptable anchor types for code files: function/method/class names, constants, decorators, import blocks, test names, comment markers
  - Acceptable anchor types for non-code files: headings, YAML/JSON key paths, table sections, bullet groups, recognizable text blocks
  - Insertion-point guidance: "before/after/inside/under" a named landmark
  - Cross-task reference guidance: "the helper introduced in Task N" or "the `build_anchor` function created in the previous step"
  - Disambiguation rule: when an anchor is ambiguous, include enough surrounding context (e.g., "the `validate` method in `RequestHandler`", not just "the `validate` method")
  - A compact negative example: ❌ `(line 73)`, `(~lines 42-57)` — and a compact positive example: ✅ `in the _execute_merge() function`, `under the ## Dependencies heading`
- [ ] T005 [US3] [FR-007] Ensure the term "semantic anchor" is used consistently — no occurrences of "content-based anchor", "structural reference", or other legacy terms

### Phase 3: Template Update

**Deliverables**: Updated `.specify/templates/tasks-template.md` with anchor guidance and examples

- [ ] T006 [US1] [US2] Add a "Location References" guidance block to the Notes section of `tasks-template.md` containing:
  - A concise restatement: "Describe edit locations using semantic anchors, not line numbers"
  - 2–3 before/after example transformations (one code, one non-code, one cross-task)
  - Edge-case guidance for ambiguous or missing anchors
- [ ] T007 [US2] Update sample task descriptions in the template to demonstrate semantic-anchor style where applicable (e.g., `src/[location]/[file].py` patterns could include anchor hints)

### Phase 4: Token Measurement and Validation

**Deliverables**: Post-change token counts, compatibility confirmation, sample output review

- [ ] T008 Measure cl100k_base token counts for both files post-change and confirm they stay within NFR-001 ceiling
- [ ] T009 [US4] Validate implement-agent compatibility: confirm `speckit.implement.agent.md` contains no line-number-dependent logic and can process semantic-anchor-based tasks without modification
- [ ] T010 Review 3 representative `tasks.md` generation scenarios (existing-symbol edit, insertion relative to anchor, non-code file edit, cross-task reference) to confirm the updated prompts produce
  anchor-based output

### Phase 5: Polish

**Deliverables**: Final cleanup, documentation consistency

- [ ] T011 Verify no legacy terminology ("content-based anchor", "structural reference") exists in either file
- [ ] T012 Run markdownlint on both changed files to ensure no formatting regressions

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Token budget exceeded | Low | Medium | Compact wording; measure after each edit; trim examples if over budget |
| Planners still emit line numbers despite guidance | Medium | Low | Explicit negative examples + "MUST NOT" language in the rule |
| Guidance too verbose, reducing prompt effectiveness | Low | Medium | Keep to ~15-20 lines of added content per file; use bullet lists not prose |
| Ambiguous anchors in edge cases | Medium | Low | Include disambiguation guidance and fallback to surrounding-context snippets |
| Template HTML comment ignored by some LLMs | Low | Low | Place key rules in visible Markdown (Notes section), not only in comments |

## Dependencies

### Internal

- **Existing prompt structure**: Both files must retain their current section organization (Task Generation Rules in agent, Notes in template)
- **tiktoken / cl100k_base**: Required for NFR-001 token measurement (available via `pip install tiktoken`)

### External

- **No external dependencies** — this is a prompt-only change with no runtime code, API, or package changes

---
*Generated by Copilot SDK (claude-opus-4.6)*

# Implementation Plan: SpecKit Pipeline Task Deduplication in Analysis Step

**Source Issue**: [#1201](https://github.com/ayaiayorg/agentic-devtools/issues/1201)

## 1. Technical Context

### Technology Stack

- **Agent prompt system**: Markdown prompt templates in `.github/agents/speckit.analyze.agent.md` and `.github/prompts/speckit.analyze.prompt.md`
- **Analysis categories**: Currently A–F, defined in the pipeline's inline prompt (`run_analyze_phase` in `generate-spec-from-issue.sh`)
  as inline detection pass sections; the agent prompt file mirrors these for interactive use
- **Report format**: Markdown table with `| ID | Category | Severity | Location(s) | Summary | Recommendation |` columns
- **Finding IDs**: Sequential `F-NN` format (e.g., `F-01`, `F-02`) shared across all categories in the pipeline/report output; the category is identified in the Category column, not the ID prefix.
  Category G findings follow this same convention.
  Note: `.github/agents/speckit.analyze.agent.md` currently documents category-initial IDs (e.g., `A1`). A task in Phase 1 aligns the agent prompt's ID guidance to the `F-NN` convention.
- **Severity levels**: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` (existing heuristic in §5 of the agent)
- **Downstream consumers**: `check-analysis-gate.sh` (spec #1197) parses the findings table for CRITICAL findings; human reviewers consume the analysis report for planning decisions
- **Pipeline execution path**: `speckit-phase-progression.yml` → `generate-spec-from-issue.sh` (`run_analyze_phase`) → `call_llm`/`copilot_generate.py` → `analysis-report.md`.
  The pipeline does **not** invoke the `.github/agents/speckit.analyze.agent.md` agent directly; `run_analyze_phase` constructs its own inline analysis prompt with detection passes A–F.
- **Agent/template files**: `.github/agents/speckit.analyze.agent.md` and `.github/prompts/speckit.analyze.prompt.md` are interactive-Copilot artifacts (for VS Code agent use),
  maintained in sync with the pipeline's inline prompt but not executed by the GitHub Action.
- **No new Python code required**: The analyze step is an LLM prompt (inline in the pipeline script and mirrored in the agent file), not a Python module — though
  the pipeline execution path does invoke Python (`call_llm`/`copilot_generate.py`) to send the prompt. Category G is added by extending both the pipeline script's
  inline prompt and the agent prompt file with a new detection pass section; no new Python modules, CLI commands, or dependencies are introduced.

### Key Dependencies

- `.github/agents/speckit.analyze.agent.md` — interactive-Copilot agent definition (kept in sync with the pipeline's inline prompt; not executed by the GitHub Action)
- `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — pipeline script containing `run_analyze_phase()` with an inline analysis prompt that independently
  defines detection passes A–F and must be updated alongside the agent prompt
- `.github/prompts/speckit.analyze.prompt.md` — prompt template (thin wrapper referencing the agent)
- `.specify/templates/commands/analyze.md` — SDK template variant (mirrors agent)
- `specs/*/analysis-report.md` — existing reports show output format conventions
- Spec #1197 (gate creation) — the gate script parses findings tables; Category G findings must be compatible
- Spec #1199 (validate-all) — FR coverage validation runs before analyze; Category G consumes tasks.md data that has already been
  validated

### Architecture Decisions

1. **Prompt-only implementation** — Category G is a new section in the analyze agent prompt and the pipeline script's inline prompt
   (`run_analyze_phase` in `generate-spec-from-issue.sh`), not a Python module. The LLM executes the detection logic at analysis time,
   consistent with categories A–F. No new Python code, CLI commands, or dependencies are introduced.

2. **Structured finding contract** — While the LLM produces markdown output, the spec requires each finding to be representable as a
   JSON-serializable object (FR-006). The prompt instructs the agent to emit findings in the standard table format. As an optional
   implementation choice — to simplify programmatic consumption by downstream tools — the prompt also requests a structured JSON block
   in the report, though this is not a spec requirement.

3. **Fixed thresholds at prompt level** — Numeric thresholds or explicit heuristics for each comparison dimension are defined in the prompt
   text (e.g., description similarity uses the qualitative criterion "substantially same intent"). No configuration mechanism is needed
   for Phase 1.

4. **Cluster-first grouping** — The prompt instructs the agent to identify overlap clusters before emitting findings, ensuring one finding per cluster (FR-004) rather than pairwise enumeration.

## 2. Research Summary

Key research decisions (conducted during planning, not committed as a separate artifact):

1. **Detection approach**: LLM-driven semantic analysis within the agent prompt, not algorithmic code. The LLM already performs semantic comparison for categories A and F; Category G extends this with
   explicit dimension criteria and grouping rules.

2. **Threshold definition**: Fixed qualitative-to-numeric mappings for each dimension, documented in the prompt. Description similarity uses "substantially same intent" (qualitative); file path
   overlap uses "majority of same files" (≥50%); code section overlap uses "same function/class/method name."

3. **Grouping algorithm**: Transitive closure — if task A overlaps task B, and task B overlaps task C, all three form one cluster. The prompt instructs the agent to identify connected components
   rather than independent pairs.

4. **Output integration**: Category G findings go in the same findings table as A–F. A separate "Category G Metrics" subsection is added to the Metrics block.
   Optionally, a `category-g-findings.json` structured block is included to simplify programmatic consumption (not a spec requirement;
   see AD-2).

5. **Backward compatibility**: Categories A–F are untouched. Category G is appended after F. The existing severity heuristic in §5 is extended, not replaced.

## 3. Design Overview

### Prompt Architecture

Both the interactive-Copilot agent file and the pipeline script's inline prompt share the
same logical structure. Changes are applied to both in parallel.

```text
speckit.analyze.agent.md / run_analyze_phase() inline prompt
├── §4. Detection Passes
│   ├── A. Duplication Detection        (unchanged)
│   ├── B. Ambiguity Detection          (unchanged)
│   ├── C. Underspecification           (unchanged)
│   ├── D. Constitution Alignment       (unchanged)
│   ├── E. Coverage Gaps                (unchanged)
│   ├── F. Inconsistency               (unchanged)
│   └── G. Task Deduplication  ← NEW
│       ├── Comparison dimensions (3)
│       ├── Classification rules
│       ├── Severity mapping
│       ├── Grouping rules
│       └── Structured output contract
├── §5. Severity Assignment             (extended with G rules)
├── §6. Produce Compact Analysis Report (extended with G metrics)
└── (rest unchanged)
```

### Finding Data Model

Each Category G finding contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | `F-NN` (sequential, following last existing ID) |
| `overlap_type` | enum | `duplicate` \| `overlapping` \| `conflicting` |
| `severity` | enum | `CRITICAL` \| `HIGH` |
| `task_ids` | array[string] | Task identifiers in the cluster |
| `dimensions` | array[string] | Which of `description`, `file_path`, `code_section` triggered |
| `rationale` | string | ≤500 characters explaining the basis |

### Severity Decision Tree

```text
Is the cluster a duplicate (same work, same scope)?
  → YES: CRITICAL
Is the cluster conflicting (contradictory outcomes)?
  → YES: CRITICAL
Is the cluster overlapping?
  → How many dimensions match strongly?
    → ≥2 dimensions: CRITICAL
    → exactly 1 dimension: HIGH
```

### Grouped Finding Severity

When a cluster contains tasks with mixed severity (e.g., some pairs are CRITICAL duplicate, others are HIGH overlapping), the grouped finding uses the highest severity present: CRITICAL.

## 4. Implementation Phases

### Phase 1: Prompt Extension — Category G Detection Pass

**Deliverables**: Updated analyze agent prompt and pipeline inline prompt (`run_analyze_phase` in `generate-spec-from-issue.sh`) with Category G section

**Tasks**:

1. Add `#### G. Task Deduplication` section after `#### F. Inconsistency` in the agent prompt
2. Define the three comparison dimensions with qualitative criteria and numeric thresholds or explicit heuristics (per AD-3)
3. Define classification rules (duplicate/overlapping/conflicting) with severity mapping
4. Define grouping rules (transitive closure, one finding per cluster)
5. Define the 500-character rationale constraint
6. Add edge case handling instructions (missing dimensions, broad-vs-narrow scope, contradictory verbs)
7. Add Category G detection pass to the inline prompt in `generate-spec-from-issue.sh` (`run_analyze_phase`) to match the agent prompt
8. Align finding ID examples in the agent prompt from category-initial format (e.g., `A1`) to the sequential `F-NN` format used in pipeline/report output

### Phase 2: Severity and Metrics Integration

**Deliverables**: Updated severity heuristic and metrics sections

**Tasks**:

1. Extend §5 Severity Assignment with Category G entries:
   - `CRITICAL`: Task deduplication finding — duplicate tasks, conflicting tasks, or multi-dimension overlap (≥2 dimensions)
   - `HIGH`: Task deduplication finding — single-dimension overlap
2. Extend §6 Metrics block with Category G metrics:
   - Deduplication Finding Count
   - Counts by overlap type (duplicate/overlapping/conflicting)
   - Multi-task group count (findings involving >2 tasks)
3. Add Category G summary subsection template to the report structure

### Phase 3: Structured Output Contract (Optional)

**Deliverables**: JSON-serializable finding format for programmatic consumers

> **Note:** This phase is optional per AD-2. The structured JSON block simplifies programmatic consumption but is not a spec requirement.
> The standard findings table (produced in Phase 1) is sufficient for all required downstream consumers.
> Skip this phase if the implementation team decides the table format alone meets project needs.

**Tasks** (if elected):

1. Add instruction for the agent to emit a `### Category G Structured Findings` block containing a JSON array of finding objects
2. Define the JSON schema in the prompt (fields: `id`, `overlap_type`, `severity`, `task_ids`, `dimensions`, `rationale`)
3. Ensure the structured block is emitted after the findings table but before the Metrics section
4. Document the contract for downstream consumers (gate script, human reviewers)

### Phase 4: SDK Template Sync

**Deliverables**: Consistent templates across all three analyze prompt locations

**Tasks**:

1. Mirror Category G changes to `.specify/templates/commands/analyze.md`
2. Verify `.github/prompts/speckit.analyze.prompt.md` correctly delegates to the agent (no content changes needed if it's a thin wrapper)
3. Update any prompt variable references if new variables are introduced

### Phase 5: Validation and Testing

**Deliverables**: Verified backward compatibility and correct detection behavior

**Tasks**:

1. Run `speckit.analyze` on an existing spec with known non-overlapping tasks → verify Category G reports no findings, categories A–F unchanged
2. Run `speckit.analyze` on a synthetic spec with duplicate tasks → verify Category G detects them as `duplicate` / `CRITICAL`
3. Run `speckit.analyze` on a synthetic spec with overlapping tasks (single dimension) → verify `overlapping` / `HIGH`
4. Run `speckit.analyze` on a synthetic spec with conflicting tasks → verify `conflicting` / `CRITICAL`
5. Run `speckit.analyze` on a synthetic spec with a 3+ task cluster → verify single grouped finding
6. Verify the gate script (#1197) can parse Category G findings from the table without modification
7. If the optional structured JSON block is included (Phase 3), verify it is valid and parseable

### Phase 6: Documentation

**Deliverables**: Updated documentation reflecting Category G

**Tasks**:

1. Update `SPEC_DRIVEN_DEVELOPMENT.md` if it references analysis categories
2. Update `docs/copilot-commands.md` if it describes analyze output
3. Add a note in the spec directory's `README.md` about the new category

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM produces false positives (over-detects overlap) | Medium | Medium | Fixed thresholds with conservative criteria; qualitative "substantially same intent" avoids keyword-only matching |
| LLM produces inconsistent results across runs | Medium | Low | NFR-002 recommends determinism (SHOULD, not MUST); prompt includes explicit decision tree; accept minor variance in rationale wording |
| Category G findings overwhelm the 50-finding limit | Low | Medium | FR-004 grouping ensures one finding per cluster; typical task sets have few true overlaps |
| Gate script (#1197) fails to parse Category G findings | Low | High | Category G uses identical table format as A–F; severity values are a subset of existing (`CRITICAL`, `HIGH`) |
| Prompt becomes too long for context window | Low | Medium | Category G adds ~100 lines to a ~200-line prompt; well within limits |
| Category A (existing duplication) conflicts with Category G | Medium | Medium | Scope distinction: A detects duplicate *requirements*, G detects duplicate *tasks*. Add explicit note in prompt. |

## 6. Dependencies

### External Dependencies

- None. No new packages, APIs, or services required.

### Internal Dependencies

- Spec #1197 (gate creation) — Category G findings must be parseable by `check-analysis-gate.sh`. The gate uses the standard findings table format, so no gate changes are needed.
- Spec #1199 (validate-all) — FR coverage validation produces `fr-coverage.json` before analyze runs. Category G consumes tasks.md directly, not the coverage file, so no ordering dependency.
- `.github/agents/speckit.analyze.agent.md` — interactive-Copilot agent file to modify. Must be coordinated if other PRs are in flight.
- `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — pipeline script with inline prompt to modify in sync with the agent prompt.

### Prerequisite Knowledge

- Understanding of the existing A–F detection passes and their scoping (requirements vs. tasks vs. constitution)
- Understanding of the findings table format and severity assignment heuristic
- Understanding of the gate script's parsing expectations (spec #1197)

---
*Generated by Copilot SDK (claude-opus-4.6)*

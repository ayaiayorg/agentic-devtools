# Cross-Artifact Consistency & Quality Analysis Report

**Feature**: Migrate to native spec-kit core (#1408)
**Date**: 2026-05-13

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | Duplication | LOW | FR-006 / FR-012; T024 / T026 | FR-006 ("Add installation instructions to developer documentation") and FR-012 ("Document the upgrade strategy") both target `SPEC_DRIVEN_DEVELOPMENT.md` with overlapping documentation scope. T024 and T026 both write to the same file. | Clarify boundary: FR-006 covers initial setup, FR-012 covers ongoing upgrades. Add explicit scope note to each requirement. |
| F-02 | Duplication | LOW | Plan 1.8 / T033 | Plan task 1.8 ("Write comprehensive README") and T033 ("Write comprehensive README for speckit-ext-agdt") are identical work items appearing in both Phase 1 and Phase 8. | T033 is the authoritative task; Plan 1.8 deliverable is satisfied by T033. Note this mapping in the plan. |
| F-03 | Ambiguity | MEDIUM | NFR-001 | "standard connection" is undefined — no bandwidth or latency baseline specified. | Define "standard connection" (e.g., ≥10 Mbps download, ≤100ms latency) or replace with a concrete network profile. |
| F-04 | Ambiguity | MEDIUM | AC-4.1 | "≥80% of a custom script's functionality" — no measurement method defined. Line coverage? Feature count? Behavioral equivalence? | Specify measurement method: e.g., "covers ≥80% of the script's documented use cases as enumerated in the inventory." |
| F-05 | Ambiguity | LOW | Risk table | "active maintenance (>1 release in 6 months)" — unclear whether this means ≥1 tagged release or any commit activity. | Clarify: "at least one tagged semver release on the default branch within the prior 6 months." |
| F-06 | Underspecification | MEDIUM | EC-003 / T007 | Command namespacing as `agdt:*` is stated but no example of how existing `.github/agents/` references (e.g., `speckit.specify`) map to `agdt:specify` is provided. T023 says "update if changed" but lacks criteria for detection. | Add a mapping table showing old command name → new namespaced name. T023 should include a concrete grep pattern to find stale references. |
| F-07 | Underspecification | MEDIUM | NFR-003 | "must pass `specify doctor` at CI time" — no task creates the CI step that runs `specify doctor`. T008 covers lint/manifest validation but not `specify doctor`. | Add `specify doctor` to T008's CI workflow or create a dedicated task. |
| F-08 | Underspecification | MEDIUM | FR-005 | "Publish both packages to public repositories" — no criteria for what constitutes "published" (GitHub release? Tag? Package registry?). T016/T017 say "Tag and publish" but the publish target is only "public GitHub repository." | Clarify whether publishing means a GitHub Release with assets, or just a tagged commit on a public repo. |
| F-09 | Underspecification | LOW | T042 | "Global search-and-replace for stale `.specify/scripts/` path references" — no list of file patterns to search or expected scope. | Specify glob patterns (e.g., `**/*.yml`, `**/*.md`, `.github/**`) and expected match count range for verification. |
| F-10 | Constitution | LOW | Spec | No explicit "Out of Scope" section — "Non-Goals" serves this purpose but does not use the canonical heading from typical spec-kit templates. | Rename "Non-Goals" to "Out of Scope / Non-Goals" or add a brief "Out of Scope" section referencing non-goals. |
| F-11 | Coverage | MEDIUM | NFR-001 | NFR-001 (installation under 30 seconds) has no dedicated verification task. T045 is the closest (E2E smoke test) but does not measure installation time. | Add a timing assertion to T045 or create a new task that benchmarks `specify install` duration. |
| F-12 | Coverage | MEDIUM | NFR-003 | NFR-003 (`specify doctor` CI verification) is not covered by any task. T008 covers lint and manifest validation only. | Extend T008 or add a sub-task to run `specify doctor` in CI and assert exit code 0. |
| F-13 | Coverage | LOW | NFR-004 | NFR-004 (exact semver, no ranges) is implicitly covered by T018 ("exact semver version pins") but has no explicit verification task that asserts the absence of range specifiers. | Add a verification step to T031 that parses `config.yml` and rejects range syntax. |
| F-14 | Inconsistency | MEDIUM | Plan Phase 0.5 / Tasks | Plan Phase 0 task 0.5 ("Evaluate community extensions") is part of inventory phase, but in tasks.md this work appears as T027 in Phase 6 (much later). | Align phasing: either move community evaluation earlier in tasks or note in the plan that Phase 0.5 is a lightweight scan with detailed evaluation deferred to Phase 6. |
| F-15 | Inconsistency | LOW | Spec FR-005 / Plan 1.10, 2.7 | FR-005 says "Publish both packages to public repositories" (single requirement). Plan splits this into two independent publish tasks (1.10, 2.7) which is correct, but tasks T016/T017 are in Phase 3 while Plan has them in Phase 1/2. | Cosmetic — note the phase renumbering in the mapping table (already partially done). |
| F-16 | Task Dedup | HIGH | T001, T033 | T001 scaffolds `speckit-ext-agdt` repo with README.md. T033 writes comprehensive README for `speckit-ext-agdt`. Both target the same file. | Clarify T001 creates a minimal stub README; T033 replaces it with the full version. Add dependency T001 → T033. |
| F-17 | Task Dedup | HIGH | T002, T034 | T002 scaffolds `speckit-preset-agdt` repo with README.md. T034 writes comprehensive README for `speckit-preset-agdt`. Both target the same file. | Same as F-16: T002 is stub, T034 is final. Add dependency T002 → T034. |
| F-18 | Task Dedup | HIGH | T024, T025, T026, T032 | T024, T025, T026, and T032 all write to `SPEC_DRIVEN_DEVELOPMENT.md`. T024 covers installation/setup instructions, T025 covers preset-vs-override guidance, T026 covers upgrade strategy, and T032 covers version-pin update workflow. Same file, different sections — transitive overlap cluster. | Single-dimension overlap (file_path). Keep all four tasks separate but define non-overlapping section boundaries. |

### Category G Structured Findings

[
  {
    "id": "F-16",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T001", "T033"],
    "dimensions": ["file_path"],
    "rationale": "T001 scaffolds speckit-ext-agdt README; T033 writes comprehensive README for same file. Stub vs full version. Single-dimension overlap."
  },
  {
    "id": "F-17",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T002", "T034"],
    "dimensions": ["file_path"],
    "rationale": "T002 scaffolds speckit-preset-agdt with README.md. T034 writes comprehensive README for same repo. Same output file, stub vs final version. Single-dimension overlap."
  },
  {
    "id": "F-18",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T024", "T025", "T026", "T032"],
    "dimensions": ["file_path"],
    "rationale": "T024/T025/T026/T032 all target SPEC_DRIVEN_DEVELOPMENT.md (install, preset, upgrade, version-pin). Same file, different sections — transitive overlap."
  }
]

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T003 | Inventory task |
| FR-002 | ✅ | T004 | Categorization task |
| FR-003 | ✅ | T005, T007, T008, T010, T011, T012, T016, T019, T021, T022, T023, T043, T046 | Well-covered |
| FR-004 | ✅ | T006, T009, T013, T014, T015, T017, T020, T021, T043, T046 | Well-covered |
| FR-005 | ✅ | T015, T016, T017 | Publish tasks |
| FR-006 | ✅ | T024, T025, T044 | Documentation tasks |
| FR-007 | ✅ | T018, T029, T031, T045 | Version pin tasks |
| FR-008 | ✅ | T027 | Community evaluation |
| FR-009 | ✅ | T028 | Community replacement |
| FR-010 | ✅ | T036, T037, T038, T039, T043 | Cleanup tasks |
| FR-011 | ✅ | T041 | README update |
| FR-012 | ✅ | T026 | Upgrade strategy docs |
| NFR-001 | ⚠️ | (T045 partial) | No explicit timing verification — see F-11 |
| NFR-002 | ✅ | T021 | Spec validation |
| NFR-003 | ⚠️ | T005, T008 (partial) | `specify doctor` CI step missing — see F-12 |
| NFR-004 | ✅ | T018, T031 | Implicit coverage via exact semver wording |
| NFR-005 | ✅ | T015 | Dependency audit |
| NFR-006 | ✅ | T044 | Markdownlint validation |

## Metrics

| Metric | Value |
|--------|-------|
| Total Functional Requirements | 12 |
| Total Non-Functional Requirements | 6 |
| Total Tasks | 46 |
| FR Coverage % | 100% (12/12) |
| NFR Coverage % | 67% (4/6 fully covered; NFR-001, NFR-003 partial) |
| Ambiguity Count | 3 (F-03, F-04, F-05) |
| Requirement Duplication Count (Category A) | 2 (F-01, F-02) |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 3 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 3 / conflicting: 0 |
| Multi-Task Group Count | 1 (F-18 involves 4 tasks) |

---
*Generated by Copilot SDK (claude-opus-4.6)*

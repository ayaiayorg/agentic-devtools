# Implementation Plan: Update Constitution to v1.2.0

## Technical Context

- **File**: `.specify/memory/constitution.md` (single markdown file)
- **Current version**: 1.1.0 (ratified 2026-02-02)
- **Target version**: 1.2.0
- **Nature**: Pure documentation change — no code, no tests, no build artifacts
- **Branch**: `speckit/1580/phase-3-plan`
- **Issue**: [#1580](https://github.com/ayaiayorg/agentic-devtools/issues/1580)

## Research Summary

See the clarifications section in `spec.md` for detailed decisions on:

- Principle I rewrite strategy (scoped tool availability vs auto-approval)
- Principle II dual-layer state architecture phrasing
- Technology-agnostic Principle IX formulation
- Pre-1.0 flexibility policy scope

Key decisions:

1. New principles appended as IX, X, XI — no renumbering
2. Principle IX titled "Graph-Based Workflow Orchestration" with LangGraph as named current implementation
3. Auto-approval described as "transitional mechanism" (not "temporary workaround")
4. Backward-compatibility references replaced with Principle XI cross-reference

## Design Overview

The update touches the following areas of the constitution:

| Area | Change Type | FRs |
|------|-------------|-----|
| Sync Impact Report (HTML comment) | Replace | FR-012 |
| Principle I | Rewrite | FR-002 |
| Principle II | Rewrite | FR-003 |
| Principle IV | Edit (95% → 100%) | FR-004 |
| Principle VI | Edit (remove version bump bullet) | FR-005 |
| New Principles IX, X, XI | Add | FR-006, FR-007, FR-008 |
| Development Workflow → Code Changes | Edit | FR-009 |
| Quality Gates → Pre-Commit | Edit (95% → 100%) | FR-011 |
| Governance → Amendments | Edit | FR-010 |
| Version footer | Edit | FR-001 |

## Implementation Phases

### Phase 1: Update Sync Impact Report

Replace the HTML comment block (lines 1–20) with a new report reflecting v1.1.0 → v1.2.0 changes:

- List modified principles: I, II, IV, VI
- List added principles: IX, X, XI
- List removed content: "No distributed configuration", backward-compat requirement, migration plan mandate
- List templates requiring review

### Phase 2: Rewrite Principle I (Scoped Tool Availability)

Replace lines 26–35 with new content:

- Title: "Scoped Tool Availability"
- Describe: each workflow step has a precisely defined set of available tools/commands
- Acknowledge: auto-approval as a "transitional mechanism" supported until scoped declarations are fully implemented
- Retain: `**Rationale**:` block format

### Phase 3: Rewrite Principle II (Dual-Layer State Architecture)

Replace lines 37–46 with new content:

- Title: "Dual-Layer State Architecture" (or "State Architecture")
- Describe: CLI parallel-safe JSON segments for command state + LangGraph checkpointing for orchestration workflows
- Reference: parallel-safe isolated state segments for concurrent subagent execution
- Remove: "No distributed configuration"
- Retain: file path reference, `agdt-show` transparency, file locking

### Phase 4: Update Principle IV (Coverage 95% → 100%)

- Change "Minimum 95% code coverage" to "100% code coverage" (coverage bullet under Principle IV)
- Reference ADR-011 alignment

### Phase 5: Update Principle VI (Remove Version Bump Requirement)

- Remove bullet: "Breaking changes to CLI UX require a major version bump and migration notes"
- Replace with reference to Principle XI: "Breaking changes to CLI UX are permitted per Principle XI (Pre-1.0 Flexibility) and require changelog documentation"

### Phase 6: Add New Principles IX, X, XI

Insert after Principle VIII (after line 115):

- **IX. Graph-Based Workflow Orchestration** — graph-based orchestration pattern, LangGraph as current implementation, checkpoint state recovery, human-in-the-loop interrupts
- **X. Dual-Engine Compatibility** — coexistence via opt-in routing (`--engine` flag), fault isolation between engines
- **XI. Pre-1.0 Flexibility** — breaking changes allowed pre-1.0, no migration plans required, active removal of dead code

### Phase 7: Update Development Workflow → Code Changes

- Replace line 121 ("All changes must maintain backward compatibility unless major version bump") with: "Breaking changes are permitted per Principle XI (Pre-1.0 Flexibility)"

### Phase 8: Update Quality Gates → Pre-Commit

- Replace line 150 ("Code coverage ≥ 95% for changed files") with: "Code coverage = 100% for changed files (per Principle IV and ADR-011)"

### Phase 9: Update Governance → Amendments

- Remove item 3 ("Migration plan for affected code") from the amendments requirements list
- Renumber remaining items

### Phase 10: Update Version Footer

- Change: `**Version**: 1.1.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-02-03`
- To: `**Version**: 1.2.0 | **Ratified**: 2026-05-26 | **Last Amended**: 2026-05-26`

### Phase 11: Verification

Run success criteria checks:

```bash
# SC-001: Full version footer updated to 1.2.0 with new ratification and last amended dates
grep -Fx '**Version**: 1.2.0 | **Ratified**: 2026-05-26 | **Last Amended**: 2026-05-26' .specify/memory/constitution.md

# SC-002: No "95%" references
if grep -q "95%" .specify/memory/constitution.md; then
  echo "FAIL: 95% still present"
  exit 1
else
  echo "OK: no 95% references"
fi

# SC-003: No "No distributed configuration"
if grep -q "No distributed configuration" .specify/memory/constitution.md; then
  echo "FAIL: removed text still present"
  exit 1
else
  echo "OK: removed text not present"
fi

# SC-004: No version bump requirement
if grep -q "Breaking changes to CLI UX require a major version bump" .specify/memory/constitution.md; then
  echo "FAIL: version bump requirement still present"
  exit 1
else
  echo "OK: version bump requirement removed"
fi

# SC-005: No migration plan mandate
if grep -q "Migration plan for affected code" .specify/memory/constitution.md; then
  echo "FAIL: migration plan mandate still present"
  exit 1
else
  echo "OK: migration plan mandate removed"
fi

# SC-006: Principles IX, X, XI exist
grep "### IX\." .specify/memory/constitution.md
grep "### X\." .specify/memory/constitution.md
grep "### XI\." .specify/memory/constitution.md

# SC-007: Sync Impact Report updated
grep -E "1\.1\.0 (→|->) 1\.2\.0" .specify/memory/constitution.md

# SC-008: Existing principles III, V, VII, VIII remain and new principles are appended after VIII (no renumbering)
awk '
/^### III\./ { iii=NR }
/^### V\./ { v=NR }
/^### VII\./ { vii=NR }
/^### VIII\./ { viii=NR }
/^### IX\./ { ix=NR }
/^### X\./ { x=NR }
/^### XI\./ { xi=NR }
END {
  if (iii && v && vii && viii && ix && x && xi && iii < v && v < vii && vii < viii && viii < ix && ix < x && x < xi) {
    print "OK: principle ordering/append behavior preserved"
    exit 0
  }
  print "FAIL: principle ordering/append behavior not preserved"
  exit 1
}' .specify/memory/constitution.md

# NFR-004: Principle formatting consistency (`### N. Title` + `**Rationale**:`)
# Visual diff review
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Downstream templates reference removed text | Medium | Low | Sync Impact Report explicitly lists templates needing review |
| Formatting inconsistency in new principles | Low | Medium | NFR-004 mandates exact `### N. Title` + `**Rationale**:` format — include explicit visual formatting review in Phase 11 |
| Stale docs reference 95% coverage | Medium | Low | Out of scope for this PR but noted in Sync Impact Report |

## Dependencies

- **Internal**: ADR-011 (100% coverage policy) — already ratified
- **Internal**: Specs #1428, #1430, #1525 — referenced by Principle II and IX updates
- **External**: None — this is a pure documentation change

---
*Generated by Copilot SDK (claude-opus-4.6)*

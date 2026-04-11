# Specification: Enhance agdt.analyze-workflow (#1179)

**5 clarification questions auto-resolved:**

1. **Output location** → Always write to the caller's state directory (read-only safety for external worktrees)
2. **Multi-identity logs** → Scan all identity directories; attribute evidence with `[identity: {name}]` prefix
3. **Cross-repo source scope** → Source analysis always reads from the agent's own repo; external worktrees provide only log evidence
4. **Parameter conflicts** → `--issue-key` + `--pr-id` are mutually exclusive with a clear error
5. **"Static-only" meaning** → Refers to no-external-worktree mode (not skipping log collection)

---

## User Stories

| Label | Story | Priority |
|-------|-------|----------|
| US1 | As an AI agent, I can invoke `agdt.analyze-workflow` with `--issue-key K` or `--pr-id N` to scope the analysis to a specific worktree's state and logs, so I don't have to rely on the current bootstrap context. | P1 |
| US2 | As an AI agent, I can scan all identity directories under `.agdt/workflows/` for log evidence related to the target worktree, so analysis captures evidence from all agents—not just the current identity. | P1 |
| US3 | As an AI agent, I can collect read-only log evidence from external git worktrees sharing the same `.agdt/` root, so I get a complete picture of cross-worktree activity. | P2 |
| US4 | As an AI agent, I can include an `external_context` field in the analysis JSON output that captures external worktree evidence in a structured schema, so downstream consumers can process it programmatically. | P2 |
| US5 | As a consumer of analysis JSON, existing outputs (without `external_context`) continue to validate against the updated schema, so nothing breaks for the `create-issues-from-analysis` agent or any other reader. | P3 |

### Acceptance Criteria

**US1 — Parameterized invocation:**

- `--issue-key PROJECT-123` resolves `worktree_key = "PROJECT-123"`
- `--pr-id 42` resolves `worktree_key = "PR42"`
- Omitting both falls back to the current bootstrap worktree key
- Providing both `--issue-key` and `--pr-id` raises a mutual exclusion error

**US2 — Multi-identity log scanning:**

- All directories under `.agdt/workflows/` are scanned (except `_unscoped`)
- Each log entry is prefixed with `[identity: {name}]` for attribution
- Empty identity directories are skipped gracefully

**US3 — External worktree context:**

- `git worktree list --porcelain` discovers external worktrees
- Log evidence is collected read-only — no writes to external paths
- `--static-only` flag disables external worktree scanning
- Inaccessible worktrees produce a warning, not an error

**US4 — `external_context` output field:**

- Field is present in JSON output as `null` when no external context (static-only or no external worktrees)
- Field contains `worktrees_scanned`, `log_evidence`, `identities_scanned` when populated
- Schema uses `oneOf [ExternalContext, null]` (not in `required` array)

**US5 — Backward compatibility:**

- Existing analysis JSON without `external_context` still validates
- `create-issues-from-analysis` agent ignores unknown top-level fields
- No changes to `COMMAND_MAP` or existing CLI entry points

---

## Functional Requirements

| # | Priority | Requirement |
|---|----------|-------------|
| FR-001 | **Must** | Accept `--issue-key <K>` parameter to scope analysis to issue worktree |
| FR-002 | **Must** | Accept `--pr-id <N>` parameter to scope analysis to PR worktree |
| FR-003 | **Must** | Accept `--static-only` flag to disable external worktree scanning |
| FR-004 | **Must** | `--issue-key` and `--pr-id` are mutually exclusive; providing both is an error |
| FR-005 | **Must** | When neither `--issue-key` nor `--pr-id` is provided, use current bootstrap worktree key |
| FR-006 | **Must** | Resolution precedence matches `state.py`'s `_sync_bootstrap_for_context_key()` chain |
| FR-007 | **Must** | Scan all identity directories under `.agdt/workflows/` (excluding `_unscoped`) |
| FR-008 | **Must** | Attribute each log entry with `[identity: {name}]` prefix |
| FR-009 | **Should** | Discover external worktrees via `git worktree list --porcelain` |
| FR-010 | **Should** | Collect log evidence from external worktrees in read-only mode |
| FR-011 | **Must** | Return `None` when `--static-only` or no external worktrees found |
| FR-012 | **Must** | Serialize `None` as `"external_context": null` in JSON output (field always present) |
| FR-013 | **Must** | Write analysis output to the caller's state directory only |
| FR-014 | **Should** | New Python helpers go in `agentic_devtools/cli/analysis/` package |
| FR-015 | **Should** | Extend SKILL.md JSON schema with optional `external_context` field |
| FR-016 | **Must** | `external_context` must not appear in the schema's `required` array |

---

## Non-Functional Requirements

| # | Requirement | Metric |
|---|-------------|--------|
| NFR-001 | Backward compatibility | Existing analysis JSON without `external_context` validates against the updated schema |
| NFR-002 | Latency | Identity directory scan completes in < 2s for ≤ 20 identity directories |
| NFR-003 | Read-only safety | Helper functions never call `open(..., 'w')` or `Path.write_*()` on external paths |
| NFR-004 | Error clarity | Every error message includes the specific parameter or path that caused the failure |
| NFR-005 | Determinism | Given the same inputs and filesystem state, analysis output is identical |

---

## Edge Cases

| # | Condition | Expected Behavior |
|---|-----------|-------------------|
| EC1 | Both `--issue-key` and `--pr-id` provided | Error: "--issue-key and --pr-id are mutually exclusive. Provide one or neither." |
| EC2 | `--issue-key` with empty value | Error: usage error, stop |
| EC3 | No `.agdt/workflows/` directory exists | Proceed with code-only evidence; note in findings |
| EC4 | No identity directories found | Proceed with code-only evidence; note in findings |
| EC5 | External worktree path is inaccessible | Log warning, continue with available evidence |
| EC6 | `--static-only` with external worktrees present | Respect flag — skip external scanning, set `external_context: null` |
| EC7 | Identity directory has no logs for the target worktree key | Skip silently, include only identities with matching logs |

---

## Success Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| SC1 | `--issue-key` and `--pr-id` correctly resolve worktree key | Unit tests for `resolve_analysis_context()` |
| SC2 | Multi-identity scanning discovers logs across all identity directories | Unit tests for `scan_identity_logs()` |
| SC3 | External worktree evidence is collected read-only | Unit tests assert no write calls on external paths |
| SC4 | `external_context` field validates against the extended JSON schema | Schema validation test with both `null` and populated values |
| SC5 | Existing analysis outputs remain valid | Backward compatibility test: validate old output against new schema |
| SC6 | Full test suite passes with 100% coverage on new code | `agdt-test` + `agdt-task-wait` |

---

## Dependencies

- `agentic_devtools/state.py` — `get_state_dir()`, `_sync_bootstrap_for_context_key()`, `_resolve_identity()`
- `agentic_devtools/cli/git/agdt_branch.py` — `resolve_worktree_key()` resolution chain
- `agentic_devtools/_bundled_skills/workflow-analysis/SKILL.md` — JSON schema to extend
- `git worktree list --porcelain` — requires git ≥ 2.5

## Out of Scope

- New CLI entry point `agdt-analyze-workflow` (future enhancement)
- Explicit target repo/worktree path parameters (e.g., `--worktree-path /path/to/worktree`) — issue #1179 mentions this as a future goal; deferred to a follow-up enhancement
- Modifying external worktree state files
- Adding new bug taxonomy categories to SKILL.md
- Changing existing JSON schema `required` fields
- Overlay file creation (tracked separately in #1135)

---
*Generated by Copilot SDK (claude-opus-4.6)*

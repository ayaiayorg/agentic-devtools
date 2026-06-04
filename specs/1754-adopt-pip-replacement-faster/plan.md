# Implementation Plan: Adopt uv as pip Replacement

## Technical Context

- **Stack**: Python 3.12, GitHub Actions, Azure DevOps Pipelines, devcontainers
- **Package**: `agentic-devtools` with `pyproject.toml`-based build (hatch-vcs)
- **CI Platforms**: GitHub Actions (4 workflow files) + Azure DevOps (1 pipeline) + Copilot cloud agent setup (1 file)
- **Key Dependency**: `uv>=0.7,<1.0` — Rust-based pip replacement, 10-100× faster installs
- **Action**: `astral-sh/setup-uv@v4` for GitHub Actions workflows

## Research Summary

See [research.md](research.md) for detailed decisions on:

- uv provisioning strategy per environment type
- Fallback guard pattern design
- Version pinning rationale

## Design Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Install Step Pattern                          │
├─────────────────────────────────────────────────────────────────┤
│  1. Provision uv (setup-uv action OR pip bootstrap)             │
│  2. Guard: command -v uv >/dev/null 2>&1                        │
│  3a. uv branch: uv pip install [flags] <package>                │
│  3b. fallback: python -m pip install --upgrade pip && pip inst.  │
└─────────────────────────────────────────────────────────────────┘
```

Each target file gets the same logical pattern, adapted to its environment constraints.

## Implementation Phases

### Phase 1: GitHub Actions Workflows (FR-001, FR-002, FR-003, FR-006)

**Deliverable**: All 3 GHA workflow files use `setup-uv` + guarded `uv pip install`.

| File | Current Install Lines | Changes |
|------|----------------------|---------|
| `.github/workflows/ai-pr-loop.yml` (L60-66) | `pip install --upgrade pip` + 3 pip installs | Add `setup-uv` step before; replace with guarded uv block; preserve `--force-reinstall --no-deps` |
| `.github/workflows/speckit-phase-progression.yml` (L480-487) | Same pattern | Add `setup-uv` step; replace; preserve `--no-deps` on local install |
| `.github/workflows/copilot-setup-steps.yml` (L22-25) | `pip install --upgrade pip` + `pip install -e ".[dev]"` | Add `setup-uv` step; replace with guarded uv block |

**Tasks**:

1. Add `astral-sh/setup-uv@v4` step (with `version: ">=0.7,<1.0"`) after `setup-python` in each workflow
2. Replace install steps with guarded pattern; remove `pip install --upgrade pip` from uv branch
3. Preserve all existing flags (`--force-reinstall`, `--no-deps`, `-e ".[dev]"`)

### Phase 2: Copilot Cloud Agent Setup-Steps (FR-001, FR-002, FR-003)

**Deliverable**: `.github/copilot-setup-steps.yml` bootstraps uv via pip and uses it.

| File | Current | Changes |
|------|---------|---------|
| `.github/copilot-setup-steps.yml` (L2) | `pip install 'agentic-devtools[dev]'` | Add uv bootstrap + guarded install |

**Tasks**:

1. Replace single `pip install` line with multi-line run block
2. Bootstrap: `pip install "uv>=0.7,<1.0" 2>/dev/null || true`
3. Guarded install: `if command -v uv; then uv pip install ...; else pip install ...; fi`

### Phase 3: Azure DevOps Pipeline (FR-001, FR-002, FR-003)

**Deliverable**: `pipelines/ai-review-stage.yaml` bootstraps uv and uses guarded installs.

| File | Lines | Changes |
|------|-------|---------|
| `pipelines/ai-review-stage.yaml` | L63-65, L85-87 | Add bootstrap step; replace both install scripts with guarded pattern |

**Tasks**:

1. Add a `bash` step to bootstrap uv: `python -m pip install "uv>=0.7,<1.0"` with `continueOnError: true`
2. Replace both `python -m pip install agentic-devtools` scripts with guarded pattern

### Phase 4: Devcontainer (FR-004)

**Deliverable**: `.devcontainer/devcontainer.json` uses uv for local dev setup.

**Tasks**:

1. Change `postCreateCommand` to: `pip install "uv>=0.7,<1.0" && uv pip install -e '.[dev]' && git config core.hooksPath .githooks`

### Phase 5: Documentation Updates (FR-005)

**Deliverable**: Docs reference uv as recommended installer.

**Files**:

1. `.devcontainer/README.md` — update post-create command section
2. `.github/copilot-instructions.md` — update installation section (L1116-1119)
3. `docs/04-solution-strategy.md` — update distribution reference (L229)

### Phase 6: Validation & PR (NFR-001, NFR-002)

**Tasks**:

1. Run full test suite (`agdt-test` + `agdt-task-wait`) — must pass unchanged
2. Measure install time before/after on a representative workflow
3. Document timing comparison in PR description
4. Ensure all success criteria (SC-001 through SC-005) are met

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `uv` unavailable on restricted runners | Low | High | Fallback guard ensures pip path always works |
| `uv` resolves different package versions than pip | Very Low | High | NFR-002: full test suite validates functional equivalence |
| `setup-uv` action unavailable (GitHub outage) | Very Low | Medium | Fallback guard handles this transparently |
| `uv` version `>=0.7,<1.0` has breaking change | Low | Medium | Bounded pin limits blast radius; can narrow if needed |
| Copilot cloud agent `run:` syntax limitations | Low | Medium | Tested in Phase 2; uses only shell commands |

## Dependencies

- **External**: `astral-sh/setup-uv@v4` GitHub Action, `uv` PyPI package
- **Internal**: No changes to `pyproject.toml`, source code, or test files
- **Ordering**: Phases 1-4 are independent (can be done in any order); Phase 5 depends on 1-4; Phase 6 depends on all

---
*Generated by Copilot SDK (claude-opus-4.6)*

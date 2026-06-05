# Tasks: Adopt uv as pip Replacement for Faster CI Installs

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Working-reference setup for guarded install pattern |
| Phase 2: Foundational — uv Provisioning Steps | Phase 1: GitHub Actions Workflows, Phase 3: Azure DevOps Pipeline | Provision `uv` before guarded install replacements |
| Phase 3: User Story 1 — Happy Path | Phase 1: GitHub Actions Workflows, Phase 2: Copilot Cloud Agent Setup-Steps | uv-first install implementation tasks for US1 |
| Phase 4: User Story 2 — Graceful Fallback | Phase 1: GitHub Actions Workflows, Phase 2: Copilot Cloud Agent Setup-Steps, Phase 3: Azure DevOps Pipeline | Fallback verification tasks for US2 |
| Phase 5: User Story 4 — Azure DevOps Pipeline | Phase 3: Azure DevOps Pipeline | Azure-specific guarded install implementation for US4 |
| Phase 6: User Story 3 — Devcontainer | Phase 4: Devcontainer | Devcontainer install-path update for US3 |
| Phase 7: User Story 5 — Documentation | Phase 5: Documentation Updates | Documentation updates for US5 |
| Phase 8: Polish & Cross-Cutting — Validation | Phase 6: Validation & PR | Cross-cutting validation, coverage, and final checks |

## Phase 1: Setup

- [ ] T001 Define the guarded install shell snippet to be reused across all files (no file change — working reference for subsequent tasks)

## Phase 2: Foundational — uv Provisioning Steps

- [ ] T002 Add `astral-sh/setup-uv@v4` step (with `version: ">=0.7,<1.0"`) after `actions/setup-python@v5` in `.github/workflows/ai-pr-loop.yml`
- [ ] T003 [P] Add `astral-sh/setup-uv@v4` step (with `version: ">=0.7,<1.0"`) after `actions/setup-python@v5` in `.github/workflows/speckit-phase-progression.yml`
- [ ] T004 [P] Add `astral-sh/setup-uv@v4` step (with `version: ">=0.7,<1.0"`) after `actions/setup-python@v5` in `.github/workflows/copilot-setup-steps.yml`
- [ ] T005 [P] Add uv bootstrap step (`pip install "uv>=0.7,<1.0"` with `continueOnError: true`) in `pipelines/ai-review-stage.yaml` before the ValidateConfig job install script at L63
- [ ] T006 [P] Add uv bootstrap step (`pip install "uv>=0.7,<1.0"` with `continueOnError: true`) in `pipelines/ai-review-stage.yaml` before the DispatchReview job install script at L85

## Phase 3: User Story 1 — Happy Path: uv present in CI [P1]

- [ ] T007 [US1] Replace install step in `.github/workflows/ai-pr-loop.yml` (L60-66) with guarded uv block preserving `--force-reinstall --no-deps` on copilot-sdk and plain install for
  agentic-devtools; remove `pip install --upgrade pip` from uv branch
- [ ] T008 [US1] [P] Replace install step in `.github/workflows/speckit-phase-progression.yml` (L481-488) with guarded uv block preserving `--force-reinstall --no-deps` on copilot-sdk and `--no-deps`
  on local package install; remove `pip install --upgrade pip` from uv branch
- [ ] T009 [US1] [P] Replace install step in `.github/workflows/copilot-setup-steps.yml` (L22-25) with guarded uv block using `uv pip install -e ".[dev]"`; remove `pip install --upgrade pip` from uv
  branch
- [ ] T010 [US1] [P] Replace install script in `.github/copilot-setup-steps.yml` (L2) with multi-line run block:
  non-fatal `pip install "uv>=0.7,<1.0" 2>/dev/null || true` bootstrap followed by guarded `uv pip install 'agentic-devtools[dev]'` with pip fallback

## Phase 4: User Story 2 — Graceful Fallback: uv unavailable [P1]

- [ ] T011 [US2] Verify happy-path success for fallback branch in `.github/workflows/ai-pr-loop.yml`: includes `python -m pip install --upgrade pip` before pip installs
- [ ] T012 [US2] [P] Verify fallback branch in `.github/workflows/speckit-phase-progression.yml` includes `python -m pip install --upgrade pip` before pip installs
- [ ] T013 [US2] [P] Verify fallback branch in `.github/workflows/copilot-setup-steps.yml` includes `python -m pip install --upgrade pip` before pip installs
- [ ] T014 [US2] [P] Verify fallback branch in `.github/copilot-setup-steps.yml` uses `python -m pip install --upgrade pip` before pip install
- [ ] T015 [US2] [P] Verify fallback branch in `pipelines/ai-review-stage.yaml` ValidateConfig job (L63-64) uses `python -m pip install --upgrade pip` before pip install
- [ ] T016 [US2] [P] Verify fallback branch in `pipelines/ai-review-stage.yaml` DispatchReview job (L85-86) uses `python -m pip install --upgrade pip` before pip install

## Phase 5: User Story 4 — Azure DevOps Pipeline: uv bootstrapped via pip [P1]

- [ ] T017 [US4] Replace install script in `pipelines/ai-review-stage.yaml` ValidateConfig job (L63-64) with guarded uv block (`uv pip install agentic-devtools` primary, pip fallback)
- [ ] T018 [US4] Replace install script in `pipelines/ai-review-stage.yaml` DispatchReview job (L85-86) with guarded uv block (`uv pip install agentic-devtools` primary, pip fallback)

## Phase 6: User Story 3 — Devcontainer: fast local setup [P2]

- [ ] T019 [US3] Update `postCreateCommand` in `.devcontainer/devcontainer.json` (L39) to: `pip install "uv>=0.7,<1.0" && uv pip install -e '.[dev]' && git config core.hooksPath .githooks`

## Phase 7: User Story 5 — Documentation reflects uv-first installs [P3]

- [ ] T020 [US5] Update `.devcontainer/README.md` to document uv bootstrap in `postCreateCommand` and describe `uv` as the recommended installer
- [ ] T021 [US5] [P] Update `.github/copilot-instructions.md` installation section to reference `uv pip install` as the recommended method with fallback context
- [ ] T022 [US5] [P] Update `docs/04-solution-strategy.md` distribution/install reference to mention `uv` as recommended installer

## Phase 8: Polish & Cross-Cutting — Validation

- [ ] T023 [US3] Verify FR-004 by running full test suite (`agdt-test` + `agdt-task-wait`) to confirm no regressions from workflow file changes (NFR-002)
- [ ] T024 Check all modified YAML files pass syntax check (e.g., `python -c "import yaml; yaml.safe_load(open(...))"`)
- [ ] T025 Verify FR-001 happy-path behavior and document before/after install timing comparison in PR description (NFR-001)
- [ ] T026 Test FR-002 happy-path provisioning criteria across all modified install targets
- [ ] T027 Verify FR-006 happy-path install-flag preservation by asserting workflow scripts retain required flags (`--force-reinstall --no-deps`, `--no-deps`, `-e ".[dev]"`)
- [ ] T028 Verify FR-005 happy-path documentation coverage by confirming all three doc targets describe uv-first installation guidance

## Dependencies

```text
T001 → T007, T008, T009, T010, T017, T018 (pattern reference)
T002 → T007 (setup-uv must precede install replacement)
T003 → T008
T004 → T009
T005 → T017 (bootstrap must precede guarded install in ValidateConfig)
T006 → T018 (bootstrap must precede guarded install in DispatchReview)
T007 → T011 (fallback verification follows install replacement)
T008 → T012
T009 → T013
T010 → T014
T017 → T015 (fallback verification for ValidateConfig job)
T018 → T016 (fallback verification for DispatchReview job)
T007-T019 → T023 (validation after all changes)
T023 → T024 → T025 → T026
T025, T026 → T027, T028
```

## Notes

- **T017 and T018 intentionally target the same file** (`pipelines/ai-review-stage.yaml`) at two distinct install locations: the ValidateConfig job (L63-64) and the DispatchReview job (L85-86). These
  are separate CI jobs with independent install scripts that must each receive the guarded uv pattern.
- All guarded blocks use `command -v uv >/dev/null 2>&1` as the detection mechanism.
- The `pip install --upgrade pip` line is **only** present in the fallback (else) branch, never in the uv branch.
- No changes to `pyproject.toml`, source code, or test files are required.

---
*Generated by Copilot SDK (claude-opus-4.6)*

# Tasks: Adopt uv as pip Replacement for Faster CI Installs

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | Phase 1: GitHub Actions Workflows, Phase 2: Copilot Cloud Agent Setup-Steps, Phase 3: Azure DevOps Pipeline | Shared setup pre-work for guarded install pattern across all execution contexts |
| Phase 2: Foundational — uv Provisioning Steps | Phase 1: GitHub Actions Workflows, Phase 2: Copilot Cloud Agent Setup-Steps, Phase 3: Azure DevOps Pipeline | uv provisioning prerequisites before install-step migration |
| Phase 3: User Story 1 — Happy Path: uv Present in CI (P1) | Phase 1: GitHub Actions Workflows, Phase 2: Copilot Cloud Agent Setup-Steps | Happy-path uv install migration in GitHub-hosted and Copilot setup flows |
| Phase 4: User Story 2 — Graceful Fallback: uv Unavailable (P1) | Phase 1: GitHub Actions Workflows, Phase 2: Copilot Cloud Agent Setup-Steps, Phase 3: Azure DevOps Pipeline | Explicit fallback verification tasks for guarded pip behavior |
| Phase 5: User Story 3 — Devcontainer: Fast Local Setup (P2) | Phase 4: Devcontainer | Devcontainer uv bootstrap and install migration |
| Phase 6: User Story 4 — Azure DevOps Pipeline: uv Bootstrapped via pip (P1) | Phase 3: Azure DevOps Pipeline | Azure pipeline uv bootstrap and guarded install migration |
| Phase 7: Polish & Cross-Cutting | Phase 5: Documentation Updates, Phase 6: Validation & PR | Documentation updates, cross-cutting rationale, and validation/timing checks |

## Phase 1: Setup

- [ ] T001 Define the guarded install shell pattern as a reusable reference snippet for consistency across all files

## Phase 2: Foundational — uv Provisioning Steps

- [ ] T002 Add `astral-sh/setup-uv@v4` step with `version: ">=0.7,<1.0"` after `actions/setup-python@v5` in `.github/workflows/ai-pr-loop.yml` (FR-002)
- [ ] T003 [P] Add `astral-sh/setup-uv@v4` step with `version: ">=0.7,<1.0"` after `actions/setup-python@v5` in `.github/workflows/speckit-phase-progression.yml` (FR-002)
- [ ] T004 [P] Add `astral-sh/setup-uv@v4` step with `version: ">=0.7,<1.0"` after `actions/setup-python@v5` in `.github/workflows/copilot-setup-steps.yml` (FR-002)
- [ ] T005 [P] Add uv bootstrap via `pip install "uv>=0.7,<1.0" 2>/dev/null || true` in `.github/copilot-setup-steps.yml` (FR-002, non-fatal, run-only file)
- [ ] T006 [P] Add uv bootstrap step `python -m pip install "uv>=0.7,<1.0"` with `continueOnError: true` in `pipelines/ai-review-stage.yaml` before both install scripts (FR-002)

## Phase 3: User Story 1 — Happy Path: uv Present in CI (P1)

- [ ] T007 [US1] Replace install step in `.github/workflows/ai-pr-loop.yml` (L60-66) with guarded uv pattern; remove `pip install --upgrade pip` from uv branch; preserve `--force-reinstall --no-deps`
  on github-copilot-sdk install (FR-001, FR-003, FR-006)
- [ ] T008 [US1] [P] Replace install step in `.github/workflows/speckit-phase-progression.yml` (L480-487) with guarded uv pattern; preserve `--force-reinstall --no-deps` on github-copilot-sdk and `--no-deps`
  on local package install (FR-001, FR-003, FR-006)
- [ ] T009 [US1] [P] Replace install step in `.github/workflows/copilot-setup-steps.yml` (L22-25) with guarded uv pattern; preserve `-e ".[dev]"` flag; remove `pip install --upgrade pip` from uv
  branch (FR-001, FR-003, FR-006)
- [ ] T010 [US1] [P] Replace `pip install 'agentic-devtools[dev]'` in `.github/copilot-setup-steps.yml` with guarded uv pattern using `uv pip install 'agentic-devtools[dev]'` as primary path (FR-001,
  FR-003)

## Phase 4: User Story 2 — Graceful Fallback: uv Unavailable (P1)

- [ ] T011 [US2] Verify fallback happy-path branch in `.github/workflows/ai-pr-loop.yml` includes `python -m pip install --upgrade pip` before pip installs (FR-003)
- [ ] T012 [US2] [P] Verify fallback happy-path branch in `.github/workflows/speckit-phase-progression.yml` includes `python -m pip install --upgrade pip` before pip installs (FR-003)
- [ ] T013 [US2] [P] Verify fallback happy-path branch in `.github/workflows/copilot-setup-steps.yml` includes `python -m pip install --upgrade pip` before pip installs (FR-003)
- [ ] T014 [US2] [P] Verify fallback happy-path branch in `.github/copilot-setup-steps.yml` uses `python -m pip install` when `uv` is not on PATH (FR-003)
- [ ] T015 [US2] [P] Verify fallback happy-path branch in `pipelines/ai-review-stage.yaml` uses `python -m pip install` with `pip --upgrade` when `uv` is not available (FR-003)

## Phase 5: User Story 3 — Devcontainer: Fast Local Setup (P2)

- [ ] T016 [US3] Update `postCreateCommand` in `.devcontainer/devcontainer.json` (L39) to `pip install "uv>=0.7,<1.0" && uv pip install -e '.[dev]' && git config core.hooksPath .githooks` (FR-004)

## Phase 6: User Story 4 — Azure DevOps Pipeline: uv Bootstrapped via pip (P1)

- [ ] T017 [US4] Replace `python -m pip install agentic-devtools` at L63-64 in `pipelines/ai-review-stage.yaml` (ValidateConfig job) with guarded uv install pattern (FR-001, FR-003)
- [ ] T018 [US4] [P] Replace `python -m pip install agentic-devtools` at L85-86 in `pipelines/ai-review-stage.yaml` (DispatchReview job) with guarded uv install pattern (FR-001, FR-003)

## Phase 7: Polish & Cross-Cutting

- [ ] T019 [P] Update `.devcontainer/README.md` to document uv as the recommended installer and explain the bootstrap + guarded fallback pattern (FR-005)
- [ ] T020 [P] Update `.github/copilot-instructions.md` installation section to reference `uv pip install` as the primary install method (FR-005)
- [ ] T021 [P] Update `docs/04-solution-strategy.md` to reference `uv` as the recommended installer for distribution and CI (FR-005)
- [ ] T022 Add version pinning rationale comment (`# Pin to 0.x series...`) adjacent to each `setup-uv` version or pip bootstrap command across all modified files
- [ ] T023 Run full test suite (`agdt-test` + `agdt-task-wait`) to verify the uv-installed
      environment is functionally identical to pip installs across workflows and devcontainer acceptance scenarios (FR-004, NFR-002)
- [ ] T024 Measure before/after install time on a representative workflow run and document in PR description (NFR-001)
- [ ] T025 Validate happy-path coverage: all targeted install steps use `uv pip install` as the primary path with guarded pip fallback in each modified workflow/pipeline context (FR-001)
- [ ] T026 Verify happy-path provisioning prerequisites are present before install steps (`setup-uv` in GitHub Actions and non-fatal pip bootstrap where `uses:` is unsupported) (FR-002)
- [ ] T027 Verify happy-path flag behavior: existing install flags (`--force-reinstall`, `--no-deps`, `-e`) remain preserved in uv commands (FR-006)
- [ ] T028 Verify happy-path documentation coverage: `.devcontainer/README.md`, `.github/copilot-instructions.md`, and `docs/04-solution-strategy.md` reference uv as the recommended installer (FR-005)

## Dependency Graph

```text
T001 → T002, T003, T004, T005, T006 (pattern defined before application)
T002 → T007 (setup-uv must exist before guarded install)
T003 → T008
T004 → T009
T005 → T010
T006 → T017, T018
T007 → T011 (fallback verification after install replacement)
T008 → T012
T009 → T013
T010 → T014
T017, T018 → T015
T007-T018 → T022 (comments added after all installs updated)
T007-T018 → T019, T020, T021 (docs updated after implementation complete)
T007-T021 → T025, T026, T027, T028 (cross-file verification after implementation and docs updates)
T019-T022, T025, T026, T027, T028 → T023 (full test suite validates everything)
T023, T025 → T024 (timing measured after validation passes)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*

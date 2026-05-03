# Implementation Plan: GitHub App Token for Copilot Review Requests

**Issue**: [#1283](https://github.com/ayaiayorg/agentic-devtools/issues/1283)

## Technical Context

- **Stack**: GitHub Actions YAML workflows, shell scripts, Python (Copilot SDK)
- **Key dependency**: `actions/create-github-app-token@v1` — generates short-lived installation tokens from App credentials
- **Affected workflows**: 3 YAML files under `.github/workflows/`
- **Affected scripts**: 2 under `.github/scripts/speckit-trigger/` plus 1 template
- **Affected docs**: `README.md`, `CONTRIBUTING.md`
- **Existing pinning strategy**: Major version tags (e.g., `actions/checkout@v4`, `actions/github-script@v7`)

## Research Summary

Key decisions on action pinning, token step placement, and env-var naming compatibility:

- **Action pinning**: Use major version tags (e.g., `@v1`) consistent with existing strategy
- **Token step placement**: Insert early in each job, before any step that needs the token
- **Env-var naming**: Preserve `COPILOT_GITHUB_TOKEN` env-var name for Copilot SDK compatibility; only the source changes (from PAT secret to App token output)

## Design Overview

Each workflow gains a single new step (`actions/create-github-app-token@v1`) early in the job that generates an installation token. All downstream steps that previously consumed
`secrets.COPILOT_GITHUB_TOKEN` now consume `steps.app-token.outputs.token`. The `COPILOT_GITHUB_TOKEN` **env-var name** is preserved in `env:` blocks for Copilot SDK compatibility (FR-003), but the
**secret reference** is eliminated. The "Validate Copilot Token" bash step is replaced with a lighter validation that checks the App token output is non-empty.

```text
Before:  secrets.COPILOT_GITHUB_TOKEN → env / github-token
After:   secrets.COPILOT_APP_ID + secrets.COPILOT_APP_PRIVATE_KEY
           → actions/create-github-app-token@v1 (step id: app-token)
           → steps.app-token.outputs.token → env / github-token
```

## Implementation Phases

### Phase 1 — Workflow Migration (all 3 workflows)

**Deliverable**: All three workflow files use App token; zero `secrets.COPILOT_GITHUB_TOKEN` references.

#### 1.1 `speckit-copilot-review-request.yml` (simplest — start here)

| Anchor | Current | Change |
|--------|---------|--------|
| Step `name: "Validate Copilot Token"` | Bash step checking `secrets.COPILOT_GITHUB_TOKEN` | Replace with `actions/create-github-app-token@v1` step (id: `app-token`) using `secrets.COPILOT_APP_ID` / `secrets.COPILOT_APP_PRIVATE_KEY` |
| — | — | Add validation step: check `steps.app-token.outputs.token` is non-empty, error message references `COPILOT_APP_ID` / `COPILOT_APP_PRIVATE_KEY` |
| Step `id: idempotency` → `github-token` input | `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` | `github-token: ${{ steps.app-token.outputs.token }}` |
| Step `id: request-copilot-review` → `github-token` input | `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` | `github-token: ${{ steps.app-token.outputs.token }}` |

**Detailed step insertion** (replacing the existing `"Validate Copilot Token"` step):

```yaml
- name: Generate GitHub App Token
  id: app-token
  uses: actions/create-github-app-token@v1
  with:
    app-id: ${{ secrets.COPILOT_APP_ID }}
    private-key: ${{ secrets.COPILOT_APP_PRIVATE_KEY }}

- name: Validate App Token
  run: |
    if [[ -z "$APP_TOKEN" ]]; then
      echo "::error::GitHub App token generation failed. Verify that COPILOT_APP_ID and COPILOT_APP_PRIVATE_KEY secrets are configured. App installation: https://github.com/organizations/ayaiayorg/settings/installations"
      exit 1
    fi
    echo "✓ GitHub App installation token generated"
  env:
    APP_TOKEN: ${{ steps.app-token.outputs.token }}
```

#### 1.2 `speckit-issue-trigger.yml`

| Anchor | Current | Change |
|--------|---------|--------|
| Step `name: "Validate Copilot Token"` | Bash step checking `secrets.COPILOT_GITHUB_TOKEN` | Replace with App token generation + validation (same pattern as 1.1) |
| Step `name: "Generate Specification"` (id: `generate`) → env `COPILOT_GITHUB_TOKEN` | `COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}` | `COPILOT_GITHUB_TOKEN: ${{ steps.app-token.outputs.token }}` — preserves env-var name for SDK compat (FR-003) |
| Step `name: "Request Copilot Review"` (id: `request-copilot-review`) → `github-token` input | `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` | `github-token: ${{ steps.app-token.outputs.token }}` |
| Step `name: "Post Failed Comment"` → troubleshooting body text | References `COPILOT_GITHUB_TOKEN` | Update to reference `COPILOT_APP_ID` / `COPILOT_APP_PRIVATE_KEY` (FR-006) |

**Conditional gates**: The `app-token` step must inherit the same `if:` condition as the current "Validate Copilot Token" step:

```text
steps.validate-label.outputs.label_matches == 'true' && steps.idempotency.outputs.skipped != 'true'
```

#### 1.3 `speckit-phase-progression.yml`

| Anchor | Current | Change |
|--------|---------|--------|
| Step `name: "Validate Copilot Token"` | Bash step checking `secrets.COPILOT_GITHUB_TOKEN` | Replace with App token generation + validation (same pattern) |
| Step `name: "Generate Phase Artifacts"` (id: `generate`) → env `COPILOT_GITHUB_TOKEN` | `COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}` | `COPILOT_GITHUB_TOKEN: ${{ steps.app-token.outputs.token }}` — preserves env-var name for SDK compat (FR-003) |
| Step `name: "Request Copilot Review"` (id: `request-copilot-review`) → `github-token` input | `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` | `github-token: ${{ steps.app-token.outputs.token }}` |
| Step `name: "Handle Failure (Comment + Label)"` → troubleshooting body text | References `COPILOT_GITHUB_TOKEN` | Update to reference `COPILOT_APP_ID` / `COPILOT_APP_PRIVATE_KEY` (FR-006) |

**Conditional gates**: Same `if:` as existing validate step:

```text
steps.extract.outcome == 'success' && steps.extract.outputs.next_phase != '6' && steps.extract.outputs.next_phase != '0' && steps.idempotency.outputs.skipped != 'true'
```

### Phase 2 — Script & Template Updates

**Deliverable**: All supporting scripts and templates reference App credentials.

| File | Anchor | Change |
|------|--------|--------|
| `.github/scripts/speckit-trigger/copilot_generate.py` | Docstring line `COPILOT_GITHUB_TOKEN  - Required. Fine-grained PAT...` and error branch `"Error: COPILOT_GITHUB_TOKEN is required"` | Update docstring and error message from PAT description → note it's provided by the workflow (env-var name stays the same; source changes from PAT to App token) |
| `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` | Env header comment `COPILOT_GITHUB_TOKEN - Fine-grained PAT...` and parameter expansion `${COPILOT_GITHUB_TOKEN:?...}` | Update comment description and `:?` error text — the env-var name is unchanged, but the description should say "provided by workflow via GitHub App token" |
| `.github/scripts/speckit-trigger/templates/failed.md` | Troubleshooting list item mentioning `COPILOT_GITHUB_TOKEN` | Change from "Verify COPILOT_GITHUB_TOKEN" to "Verify COPILOT_APP_ID and COPILOT_APP_PRIVATE_KEY secrets are configured" |

> **Important**: The env-var **name** `COPILOT_GITHUB_TOKEN` stays in `copilot_generate.py` and `generate-spec-from-issue.sh` because it's what the Copilot SDK reads (FR-003). Only the
> descriptions/comments change.

### Phase 3 — Documentation Updates

**Deliverable**: `README.md` and `CONTRIBUTING.md` updated.

| File | Anchor | Change |
|------|--------|--------|
| `README.md` | "Required Secrets" table → row `\| \`COPILOT_GITHUB_TOKEN\` \|` | Replace single row with two rows: `COPILOT_APP_ID` and `COPILOT_APP_PRIVATE_KEY`, including App permissions note |
| `CONTRIBUTING.md` | Same secrets table → row `\| \`COPILOT_GITHUB_TOKEN\` \|` | Same table update |

**New table content** (identical in both files):

```markdown
| Secret | Description |
|--------|-------------|
| `COPILOT_APP_ID` | App ID of the `agentic-devtools-copilot-reviewer` GitHub App. Required permissions: `Pull requests: Read & Write`, `Contents: Read` |
| `COPILOT_APP_PRIVATE_KEY` | PEM private key for the `agentic-devtools-copilot-reviewer` GitHub App |
```

### Phase 4 — Test & Peripheral File Updates

**Deliverable**: Test files and spec references updated.

| File | Change |
|------|--------|
| `tests/workflows/test_copilot_generate.py` | Update any assertions/mocks referencing `COPILOT_GITHUB_TOKEN` secret description; the env-var name stays |
| `.github/ISSUE_TEMPLATE/speckit-test.md` | If references `COPILOT_GITHUB_TOKEN`, update to App credentials |

### Phase 5 — Verification & Cleanup

1. **Grep verification**: `grep -r 'secrets\.COPILOT_GITHUB_TOKEN' .github/` must return zero results (SC-001)
2. **Doc verification**: `grep -r 'COPILOT_GITHUB_TOKEN' README.md CONTRIBUTING.md` must return zero results (SC-002)
3. **Functional test**: Merge a test phase PR → verify `copilot-pull-request-reviewer[bot]` appears as requested reviewer (SC-003)
4. **Secret deletion**: After all workflows pass, delete `COPILOT_GITHUB_TOKEN` from repository secrets (SC-004)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| App not installed or permissions insufficient | Low | High — all review requests fail | Validate step produces actionable error with installation URL (NFR-003) |
| Token generation adds latency | Low | Low — typically 2–4s | NFR-001 budget is 10s; SC-005 budget is 15s total |
| Copilot SDK rejects non-PAT token | Low | High — spec generation fails | The SDK reads `COPILOT_GITHUB_TOKEN` env-var; App installation tokens are standard GitHub tokens and work identically. Clarification confirms this. |
| `actions/create-github-app-token` breaking change | Very Low | Medium | Pinned to `@v1` major version; only patches/minors auto-update |
| Fork PRs fail differently | Low | Low — existing behavior preserved | Secrets unavailable on forks → App token step fails → validation step surfaces clear error |
| Transition period confusion | Medium | Low | NFR-002 is inherently satisfied: deleted secret resolves to empty string, old validation step on old commit produces a clear error |

## Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `agentic-devtools-copilot-reviewer` GitHub App installed | External | ✅ Installed |
| `COPILOT_APP_ID` repo secret | External | Must be configured before merge |
| `COPILOT_APP_PRIVATE_KEY` repo secret | External | Must be configured before merge |
| `actions/create-github-app-token@v1` | External (GitHub Action) | ✅ Available |
| `actions/github-script@v7` | External (existing) | ✅ Already used |

---
*Generated by Copilot SDK (claude-opus-4.6)*

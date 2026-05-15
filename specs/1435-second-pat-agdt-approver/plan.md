# Implementation Plan: Dedicated PR Approver PAT (AGDT_PR_APPROVER_PAT)

## Technical Context

- **Workflow file**: `.github/workflows/ai-pr-loop.yml` (81KB, ~1600 lines)
- **Target step**: "Approve PR" (line 942), uses `actions/github-script@v7`
- **Current auth**: Default `GITHUB_TOKEN` (implicit via `actions/github-script`)
- **Merge step**: Uses default `GITHUB_TOKEN` — must remain unchanged
- **Existing secrets**: `GITHUB_TOKEN`, `COPILOT_GITHUB_TOKEN`
- **Pattern precedent**: The `agentic-repair` job already validates `COPILOT_GITHUB_TOKEN` with an early-exit guard (line 1222)

## Research Summary

See [research.md](research.md) for detailed decisions on token type, account naming, and guard placement.

Key decisions:

1. Fine-grained PAT scoped to single repo with `Pull requests: Write` only
2. Inject via `github-token` input of `actions/github-script@v7` (no custom Octokit)
3. Early-exit guard inside existing step (no new workflow step)
4. Secondary account named `ayaiayorg-pr-approver`

## Design Overview

```text
┌─────────────────────────────────────────────────┐
│  "Approve PR" step (line 942)                   │
│                                                 │
│  1. Early-exit guard: check AGDT_PR_APPROVER_PAT│
│     is non-empty → warn + approved=false if not │
│  2. SHA mismatch check (PRESERVED as-is)        │
│  3. createReview with APPROVE event             │
│     (authenticated as approver account)         │
│                                                 │
│  with:                                          │
│    github-token: ${{ secrets.AGDT_PR_APPROVER_PAT }}
└─────────────────────────────────────────────────┘
```

The only code change is in the "Approve PR" step:

- Add `github-token` input pointing to the new secret
- Add early-exit guard before existing SHA check
- Add inline comment explaining why a separate PAT is needed

## Implementation Phases

### Phase 1: Account & Secret Setup (Manual / Out-of-Code)

**Deliverables**: Secondary GitHub account created, PAT generated, repository secret configured.

1. Create GitHub account `ayaiayorg-pr-approver`
2. Add account to `ayaiayorg` organization with Write role on `agentic-devtools`
3. Generate fine-grained PAT:
   - Resource owner: `ayaiayorg`
   - Repository access: `ayaiayorg/agentic-devtools` only
   - Permission: `Pull requests: Write`
   - Expiration: 90 days (document rotation schedule)
4. Add secret `AGDT_PR_APPROVER_PAT` to repository settings → Secrets → Actions

### Phase 2: Workflow Modification

**Deliverables**: Updated `ai-pr-loop.yml` with approver PAT integration.

**Changes to "Approve PR" step (line 942–980)**:

```yaml
      - name: Approve PR
        id: approve
        if: >
          steps.merge-check.outputs.ready == 'true' &&
          steps.merge-check.outputs.touches_privileged != 'true'
        uses: actions/github-script@v7
        with:
          # Use a dedicated approver PAT from a separate account.
          # GitHub prevents a user from approving their own PR, so bot-authored
          # PRs require a distinct identity for the approval step.
          github-token: ${{ secrets.AGDT_PR_APPROVER_PAT }}
          script: |
            // Early-exit guard: ensure the approver PAT is available.
            // When github-token is empty/missing, the octokit client uses
            // GITHUB_TOKEN as fallback which would fail for self-approval.
            const token = '${{ secrets.AGDT_PR_APPROVER_PAT }}';
            if (!token || !token.trim()) {
              core.warning(
                'AGDT_PR_APPROVER_PAT secret is not configured. ' +
                'Cannot approve PR without a dedicated approver token. ' +
                'See repository documentation for setup instructions.'
              );
              core.setOutput('approved', 'false');
              return;
            }

            const prNumber = parseInt('${{ steps.pr-meta.outputs.pr_number }}', 10);
            const headSha = '${{ steps.pr-meta.outputs.head_sha }}';

            // Verify head SHA hasn't changed since merge-check validated it
            const { data: pr } = await github.rest.pulls.get({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: prNumber,
            });

            if (pr.head.sha !== headSha) {
              core.warning(`PR head SHA changed (expected ${headSha.slice(0,7)}, got ${pr.head.sha.slice(0,7)}) — aborting approval.`);
              core.setOutput('approved', 'false');
              return;
            }

            try {
              await github.rest.pulls.createReview({
                owner: context.repo.owner,
                repo: context.repo.repo,
                pull_number: prNumber,
                commit_id: headSha,
                event: 'APPROVE',
                body: '✅ All checks passing, no outstanding review comments. Approved by AI PR Loop.',
              });
              core.info(`Approved PR #${prNumber} at commit ${headSha.slice(0,7)}.`);
              core.setOutput('approved', 'true');
            } catch (error) {
              core.warning(`Failed to approve PR: ${error.message}`);
              core.setOutput('approved', 'false');
            }
```

### Phase 3: Documentation

**Deliverables**: Inline workflow comments + repository documentation.

1. Add inline YAML comment above `github-token` explaining the rationale (included in Phase 2 above)
2. Add section to repository documentation (new file or section in existing doc):
   - Purpose of `AGDT_PR_APPROVER_PAT`
   - Required permissions (fine-grained, single repo, `Pull requests: Write`)
   - Rotation procedure
   - Troubleshooting (401, 403, self-approval errors)

### Phase 4: Validation

**Deliverables**: Verified end-to-end approval flow.

1. Create a test PR from the primary bot account
2. Trigger the `ai-pr-loop` workflow
3. Verify approval is attributed to `ayaiayorg-pr-approver`
4. Verify merge step still uses default token (check step logs)
5. Test missing-secret scenario (temporarily remove secret, verify warning)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| PAT expires without rotation | Medium | High (approvals fail) | Document 90-day rotation; add calendar reminder; consider GitHub App long-term |
| Approver account loses repo access | Low | High | Organization membership (harder to accidentally remove than collaborator) |
| Token interpolation in `${{ }}` exposes value | Low | Medium | `github-token` input auto-masks; never echo in script body |
| `actions/github-script` fallback to GITHUB_TOKEN when input is empty | Medium | Low | Early-exit guard checks token before any API call |
| Branch protection requires CODEOWNERS approval | Low | N/A | Out of scope — documented as known limitation |

## Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| Secondary GitHub account creation | Manual | Not started |
| Organization membership invitation | Manual | Not started |
| Fine-grained PAT generation | Manual | Not started |
| Repository secret configuration | Manual (Settings → Secrets) | Not started |
| `actions/github-script@v7` `github-token` input | External action feature | Available (documented) |

---
*Generated by Copilot SDK (claude-opus-4.6)*

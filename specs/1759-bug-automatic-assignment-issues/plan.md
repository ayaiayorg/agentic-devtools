# Implementation Plan: Fix Agent Assignment Token in speckit-implement-trigger Workflow

## Technical Context

- **Target file**: `.github/workflows/speckit-implement-trigger.yml`
- **Technology**: GitHub Actions YAML, `actions/github-script@v7` (JavaScript/octokit)
- **Authentication pattern**: `github-token` input with `secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN` fallback chain
- **Reference implementation**: `speckit-phase-progression.yml` lines 455–471 (token validation) and line 552 (`GH_TOKEN` pattern for PR creation)
- **Constraint**: NFR-004 limits changes to this single workflow file

## Research Summary

See [research.md](research.md) for details on:

- Token injection mechanism (`github-token` input vs `env` var)
- Response validation approach for `agent_assignment` field
- Preflight check implementation pattern (shell step vs github-script)

Key decisions:

1. Use `github-token` input (not env var) — aligns with `actions/github-script` design
2. Preflight as a shell `run:` step (not github-script) — simpler, faster, no octokit overhead
3. Response body validation in the assignment step itself — no follow-up GET needed

## Design Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│ trigger-implementation job                                       │
├─────────────────────────────────────────────────────────────────┤
│ ... existing steps (issue extract, discover, check-pr) ...      │
│                                                                 │
│ ┌─── NEW ────────────────────────────────────────────────────┐  │
│ │ Step: Validate Agent Assignment Token                       │  │
│ │ • Shell run: step, checks env vars for token presence       │  │
│ │ • Emits ::error:: if neither token is set                   │  │
│ │ • Outputs: token_identity (for logging downstream)          │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─── MODIFIED ───────────────────────────────────────────────┐  │
│ │ Step: Assign Copilot Coding Agent                           │  │
│ │ • Added: github-token input (elevated PAT)                  │  │
│ │ • Added: token identity logging before API call             │  │
│ │ • Added: response validation (status + agent_assignment)    │  │
│ │ • Added: error handling (401, 404, non-2xx, null field)     │  │
│ │ • Added: if: condition depends on preflight success         │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─── MODIFIED ───────────────────────────────────────────────┐  │
│ │ Step: Update Labels                                         │  │
│ │ • Added: github-token input (elevated PAT)                  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─── MODIFIED ───────────────────────────────────────────────┐  │
│ │ Step: Post Implementation Triggered Comment                 │  │
│ │ • Added: github-token input (elevated PAT)                  │  │
│ └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Add Preflight Token Validation Step (FR-002, US-2)

Insert a new step **before** the "Assign Copilot Coding Agent" step (before line 381):

```yaml
      - name: Validate Agent Assignment Token
        id: validate-token
        if: steps.discover.outputs.found == 'true' && steps.check-pr.outputs.exists != 'true'
        env:
          SPECKIT_PR_TOKEN: ${{ secrets.SPECKIT_PR_TOKEN }}
          COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
        run: |
          if [[ -n "$SPECKIT_PR_TOKEN" ]]; then
            echo "Agent assignment token: SPECKIT_PR_TOKEN (primary)"
            echo "token_identity=SPECKIT_PR_TOKEN (primary)" >> "$GITHUB_OUTPUT"
          elif [[ -n "$COPILOT_GITHUB_TOKEN" ]]; then
            echo "Agent assignment token: COPILOT_GITHUB_TOKEN (fallback)"
            echo "token_identity=COPILOT_GITHUB_TOKEN (fallback)" >> "$GITHUB_OUTPUT"
          else
            echo "::error::Neither SPECKIT_PR_TOKEN nor COPILOT_GITHUB_TOKEN is configured. At least one of these secrets must be set for Copilot coding agent assignment. Configure one in Settings > Secrets and variables > Actions."
            exit 1
          fi
```

**Deliverable**: Preflight step that fails loudly on missing tokens, outputs `token_identity`.

### Phase 2: Fix Agent Assignment Step Authentication (FR-001, FR-003, FR-004, FR-005, US-1)

Modify the "Assign Copilot Coding Agent" step:

1. Add `github-token` input to `with:` block
2. Add `if:` dependency on preflight step success
3. Add token identity logging (reading from preflight output)
4. Add response validation (HTTP status + `agent_assignment` field check)
5. Add error handling for 401, 404, and null `agent_assignment`

```yaml
      - name: Assign Copilot Coding Agent
        id: assign-agent
        if: steps.discover.outputs.found == 'true' && steps.check-pr.outputs.exists != 'true' && steps.validate-token.outcome == 'success'
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}
          script: |
            const issueNumber = ${{ steps.issue.outputs.number }};
            const specDir = ${{ toJSON(steps.discover.outputs.spec_dir) }};
            const model = ${{ toJSON(env.COPILOT_MODEL) }};
            const tokenIdentity = `${{ steps.validate-token.outputs.token_identity }}`;

            console.log(`Agent assignment token: ${tokenIdentity}`);

            let response;
            try {
              response = await github.request('PATCH /repos/{owner}/{repo}/issues/{issue_number}', {
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: issueNumber,
                agent_assignment: {
                  target_repo: `${context.repo.owner}/${context.repo.repo}`,
                  base_branch: 'main',
                  custom_instructions: `Implement all tasks defined in the planning artifacts located at ${specDir}/ (path is relative to the repository root — resolve to an absolute path before reading files). Read ${specDir}/tasks.md for the task list, ${specDir}/plan.md for architecture, and ${specDir}/spec.md for requirements. Follow the speckit.implement agent workflow.`,
                  custom_agent: 'speckit.implement',
                  model: model
                }
              });
            } catch (error) {
              if (error.status === 404) {
                console.log(`Issue #${issueNumber} not found (may have been deleted). Skipping assignment.`);
                core.setOutput('assigned', 'false');
                return;
              }
              if (error.status === 401) {
                core.setFailed(`Token authentication failed — verify token has not expired. HTTP 401: ${error.message}`);
                return;
              }
              core.setFailed(`Agent assignment API call failed with HTTP ${error.status}: ${error.message}`);
              return;
            }

            // Validate response - check agent_assignment field is present and non-null
            if (!response.data.agent_assignment) {
              core.warning(`Agent assignment API returned HTTP ${response.status} but agent_assignment field is null or absent in response. Assignment may not have taken effect.`);
              core.setOutput('assigned', 'false');
              return;
            }

            core.setOutput('assigned', 'true');
            console.log(`Copilot coding agent assigned to issue #${issueNumber} with model: ${model}`);
            console.log(`Custom agent: speckit.implement`);
            console.log(`Spec directory: ${specDir}`);
```

**Deliverable**: Assignment step with proper auth, logging, and response validation.

### Phase 3: Add Elevated Token to Downstream Steps (FR-007, US-1 scenario 5)

Add `github-token` input to both "Update Labels" and "Post Implementation Triggered Comment":

```yaml
      - name: Update Labels
        if: steps.assign-agent.outputs.assigned == 'true'
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}
          script: |
            ...existing script unchanged...
```

```yaml
      - name: Post Implementation Triggered Comment
        if: steps.assign-agent.outputs.assigned == 'true' && vars.SPECKIT_COMMENT_ON_ISSUE != 'false'
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}
          script: |
            ...existing script unchanged...
```

**Deliverable**: Both downstream steps use elevated token pattern.

### Phase 4: Validation & Testing

1. **YAML lint**: Validate workflow YAML syntax (`actionlint` or YAML parser)
2. **Dry-run verification**: Check workflow renders correctly in GitHub Actions UI
3. **Manual test**: Trigger via `workflow_dispatch` with a test issue
4. **Negative test**: Verify preflight fails when tokens are absent (local env simulation)

**Deliverable**: Verified workflow passes linting and runs correctly.

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `agent_assignment` API requires scopes not on existing PATs | High | Low | Both PATs already used for PR creation with repo write; verify scope docs |
| Preflight step condition mismatch causes it to be skipped | Medium | Low | Mirror exact `if:` condition from assignment step |
| `github-token` input doesn't propagate to octokit in `github.request()` | High | Very Low | Documented behavior of `actions/github-script@v7`; used elsewhere |
| Response body schema changes (no `agent_assignment` field) | Medium | Low | Warning annotation + `assigned=false` makes this observable |
| YAML indentation error breaks workflow | High | Low | Validate with `actionlint` before merge |

## Dependencies

- **External**: `actions/github-script@v7` (pinned, no change needed)
- **Secrets**: `SPECKIT_PR_TOKEN` and/or `COPILOT_GITHUB_TOKEN` must be configured in target repos
- **Internal**: No code changes — workflow-only fix (NFR-004)
- **Prerequisite**: Issue #1759 must be on the `speckit/1759/phase-2-clarify` branch

---
*Generated by Copilot SDK (claude-opus-4.6)*

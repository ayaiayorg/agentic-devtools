// agent-fallback.js — Copilot Coding Agent fallback on SpecKit structural validation failures
//
// Loaded via actions/github-script@v7 in both speckit-issue-trigger.yml and
// speckit-phase-progression.yml.  All shared logic lives here; workflow files
// pass only environment-specific parameters.
//
// FR coverage: FR-001 through FR-013, NFR-001 through NFR-005

'use strict';

// ---------------------------------------------------------------------------
// Structural validation error signatures (FR-001, NFR-002)
// Co-located with the same categories defined in lib/spec-validation.sh
// ---------------------------------------------------------------------------
const STRUCTURAL_ERROR_SIGNATURES = [
  'MISSING_SECTIONS',
  'INSUFFICIENT_REQUIREMENTS',
  'INSUFFICIENT_USER_STORIES',
  'MISSING_SUCCESS_CRITERIA',
  'NON_MEASURABLE_CRITERIA',
  'BELOW_SIZE_THRESHOLD',
  'BULLET_SUMMARY_DETECTED',
  'MISSING_FILE',
];

// Maximum issue body size in bytes (48KB = 49,152 bytes) for problem statement (FR-003, NFR-004)
const MAX_ISSUE_BODY_BYTES = 49152;
const TRUNCATION_MARKER = '[truncated]';

// Default reference spec path (FR-003)
const DEFAULT_REFERENCE_SPEC_PATH = 'specs/1505-structural-validation-and-retry/spec.md';

// Phase name mapping
const PHASE_NAMES = {
  1: 'specify',
  2: 'clarify',
  3: 'plan',
  4: 'tasks',
  5: 'analyze',
};

// ---------------------------------------------------------------------------
// detectStructuralFailure(validationErrors, workspaceFile, fs)
//
// Reads validation_errors from step outputs or falls back to workspace file.
// Returns structured error array or null for non-structural failures.
// (FR-001, FR-002)
// ---------------------------------------------------------------------------
function detectStructuralFailure(validationErrors, workspaceFile, fs) {
  // Try step output first
  if (validationErrors && validationErrors.trim()) {
    const errors = parseValidationErrorsString(validationErrors);
    if (errors.length > 0) {
      return errors;
    }
  }

  // Fall back to workspace file
  if (workspaceFile && fs) {
    try {
      if (fs.existsSync(workspaceFile)) {
        const content = fs.readFileSync(workspaceFile, 'utf8');
        const data = JSON.parse(content);
        if (Array.isArray(data.errors) && data.errors.length > 0) {
          // Verify at least one known structural signature
          const hasStructural = data.errors.some(e =>
            STRUCTURAL_ERROR_SIGNATURES.includes(e.category)
          );
          if (hasStructural) {
            return data.errors;
          }
        }
      }
    } catch (e) {
      // File not found or malformed — not a structural failure
    }
  }

  return null;
}

// ---------------------------------------------------------------------------
// parseValidationErrorsString(str)
//
// Parses semicolon-delimited "CATEGORY: detail" pairs from GITHUB_OUTPUT.
// ---------------------------------------------------------------------------
function parseValidationErrorsString(str) {
  const errors = [];
  const parts = str.split(';');
  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;
    const colonIdx = trimmed.indexOf(':');
    if (colonIdx === -1) continue;
    const category = trimmed.substring(0, colonIdx).trim();
    const detail = trimmed.substring(colonIdx + 1).trim();
    if (STRUCTURAL_ERROR_SIGNATURES.includes(category)) {
      errors.push({ category, detail });
    }
  }
  return errors;
}

// ---------------------------------------------------------------------------
// buildProblemStatement(issueTitle, issueBody, phase, validationErrors, referenceSpecPath)
//
// Constructs the agent prompt with 48KB UTF-8 truncation on issue body only.
// (FR-003, NFR-004)
// ---------------------------------------------------------------------------
function buildProblemStatement(issueTitle, issueBody, phase, validationErrors, referenceSpecPath) {
  const phaseName = PHASE_NAMES[phase] || `phase-${phase}`;
  const refPath = referenceSpecPath || DEFAULT_REFERENCE_SPEC_PATH;

  // Truncate issue body if needed (FR-003 — 49,152 bytes max for issue body portion)
  let truncatedBody = issueBody || '';
  const bodyBytes = Buffer.byteLength(truncatedBody, 'utf8');
  if (bodyBytes > MAX_ISSUE_BODY_BYTES) {
    const markerBytes = Buffer.byteLength(TRUNCATION_MARKER, 'utf8');
    const budget = MAX_ISSUE_BODY_BYTES - markerBytes;
    // Truncate at character boundary within byte budget
    let truncated = '';
    let currentBytes = 0;
    for (const char of truncatedBody) {
      const charBytes = Buffer.byteLength(char, 'utf8');
      if (currentBytes + charBytes > budget) break;
      truncated += char;
      currentBytes += charBytes;
    }
    truncatedBody = truncated + TRUNCATION_MARKER;
  }

  // Format validation errors
  const errorsFormatted = validationErrors
    .map(e => `  ${e.category}: ${e.detail}`)
    .join('\n');

  return `## SpecKit Agent Fallback — Phase ${phase} (${phaseName})

The SpecKit LLM pipeline failed structural validation after exhausting all retries for Phase ${phase} (${phaseName}). Please generate the required specification artifact.

### Task

Generate the Phase ${phase} (${phaseName}) artifact for the issue below. The artifact must pass structural validation (all required sections present, minimum requirements met).

### Validation Errors Encountered

\`\`\`text
${errorsFormatted}
\`\`\`

### Reference

Use \`${refPath}\` in this repository as a structural reference for the expected output format.

### Issue Title

${issueTitle}

### Issue Body

${truncatedBody}
`;
}

// ---------------------------------------------------------------------------
// checkIdempotency(octokit, owner, repo, issueNumber, phase)
//
// Checks for existing open PRs or marker comments to prevent duplicates.
// Returns { skip: boolean, reason: string, url: string } (FR-008, FR-013)
// ---------------------------------------------------------------------------
async function checkIdempotency(octokit, owner, repo, issueNumber, phase) {
  const phaseName = PHASE_NAMES[phase] || `phase-${phase}`;
  const expectedBranch = `speckit/${issueNumber}/phase-${phase}-${phaseName}`;

  // Check 1: Existing open PR on the expected branch (FR-008)
  try {
    const { data: prs } = await octokit.rest.pulls.list({
      owner,
      repo,
      head: `${owner}:${expectedBranch}`,
      state: 'open',
      per_page: 1,
    });
    if (prs.length > 0) {
      return {
        skip: true,
        reason: `Existing open PR #${prs[0].number} on branch \`${expectedBranch}\``,
        url: prs[0].html_url,
        source: 'open_pr',
      };
    }
  } catch (e) {
    // Non-fatal — continue to next check
  }

  // Check 2: Existing marker comment for this issue/phase (FR-013)
  try {
    const markerRegex = new RegExp(
      `<!-- speckit:agent-fallback task_id=([^ ]+) task_url=([^ ]+) issue=${issueNumber} phase=${phase} -->`
    );
    let page = 1;
    while (true) {
      const { data: comments } = await octokit.rest.issues.listComments({
        owner,
        repo,
        issue_number: issueNumber,
        per_page: 100,
        page,
      });
      for (const comment of comments) {
        const match = comment.body && comment.body.match(markerRegex);
        if (match) {
          return {
            skip: true,
            reason: `Existing agent fallback task for issue #${issueNumber} phase ${phase}`,
            url: match[2],
            taskId: match[1],
            source: 'marker',
          };
        }
      }
      if (comments.length < 100) {
        break;
      }
      page += 1;
    }
  } catch (e) {
    // Non-fatal — continue
  }

  return { skip: false, reason: '', url: '', source: '' };
}

// ---------------------------------------------------------------------------
// triggerCodingAgent(octokit, owner, repo, problemStatement, token)
//
// Calls the Copilot Coding Agent API. Returns { id, url } or throws.
// (FR-004, FR-011)
// ---------------------------------------------------------------------------
async function triggerCodingAgent(octokit, owner, repo, problemStatement, token) {
  const response = await octokit.request('POST /repos/{owner}/{repo}/copilot/coding-agent/tasks', {
    owner,
    repo,
    problem_statement: problemStatement,
    headers: {
      authorization: `token ${token}`,
      'X-GitHub-Api-Version': '2022-11-28',
    },
  });

  const { id, url } = response.data;
  if (!id || !url) {
    throw new Error(`API response missing required fields: id=${id}, url=${url}`);
  }

  return { id, url, status: response.data.status || 'queued' };
}

// ---------------------------------------------------------------------------
// applyLabelsAndComment(octokit, owner, repo, issueNumber, taskId, taskUrl, phase, validationErrors)
//
// Adds speckit:agent-fallback label, posts comment with marker, removes
// speckit:failed if present. Does NOT remove speckit:processing (FR-012).
// (FR-005, FR-006, FR-007)
// ---------------------------------------------------------------------------
async function applyLabelsAndComment(octokit, owner, repo, issueNumber, taskId, taskUrl, phase, validationErrors, core) {
  const phaseName = PHASE_NAMES[phase] || `phase-${phase}`;
  const errorsFormatted = validationErrors
    .map(e => `- \`${e.category}\`: ${e.detail}`)
    .join('\n');

  const marker = `<!-- speckit:agent-fallback task_id=${taskId} task_url=${taskUrl} issue=${issueNumber} phase=${phase} -->`;
  const body = [
    `## 🔄 SpecKit: Agent Fallback Triggered`,
    '',
    `The SpecKit LLM pipeline failed structural validation for **Phase ${phase} (${phaseName})**. A Copilot coding agent task has been automatically created to generate the specification.`,
    '',
    `**Agent Task**: [View task](${taskUrl})`,
    '',
    '### Validation Errors',
    '',
    errorsFormatted,
    '',
    '---',
    marker,
  ].join('\n');

  // Post comment (FR-006) — respect SPECKIT_COMMENT_ON_ISSUE kill switch
  const commentOnIssue = process.env.SPECKIT_COMMENT_ON_ISSUE !== 'false';
  if (commentOnIssue) {
    await octokit.rest.issues.createComment({
      owner,
      repo,
      issue_number: issueNumber,
      body,
    });
  } else if (core) {
    core.info('Skipping issue comment: SPECKIT_COMMENT_ON_ISSUE=false');
  }

  // Add speckit:agent-fallback label (FR-005) and ensure speckit:processing remains present (FR-012)
  try {
    await octokit.rest.issues.addLabels({
      owner,
      repo,
      issue_number: issueNumber,
      labels: ['speckit:agent-fallback', 'speckit:processing'],
    });
  } catch (e) {
    // Label may not exist — log but don't fail
    if (core) {
      core.warning(`Could not add speckit labels: ${e.message}`);
    } else {
      console.log(`Warning: Could not add speckit labels: ${e.message}`);
    }
  }

  // Remove speckit:failed if present (FR-007)
  try {
    await octokit.rest.issues.removeLabel({
      owner,
      repo,
      issue_number: issueNumber,
      name: 'speckit:failed',
    });
  } catch (e) {
    // Label may not exist — that's fine
  }
}

// ---------------------------------------------------------------------------
// run(params) — Main entry point called from workflow steps
//
// params: { github, context, core, phase, validationErrors, workspaceFile,
//           issueNumber, issueTitle, issueBody, token, killSwitch,
//           referenceSpecPath }
// ---------------------------------------------------------------------------
async function run(params) {
  const {
    github,
    context,
    core,
    phase,
    validationErrors,
    workspaceFile,
    issueNumber,
    issueTitle,
    issueBody,
    token,
    killSwitch,
    referenceSpecPath,
  } = params;

  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const fs = require('fs');
  const normalizedIssueNumber = Number(issueNumber);
  const normalizedPhase = Number(phase);

  // Kill-switch check (FR-009)
  if (killSwitch === 'false') {
    core.info('Agent fallback disabled via SPECKIT_AGENT_FALLBACK=false');
    core.setOutput('triggered', 'false');
    core.setOutput('handled', 'false');
    return;
  }

  if (
    !Number.isInteger(normalizedIssueNumber) || normalizedIssueNumber <= 0 ||
    !Number.isInteger(normalizedPhase) || normalizedPhase < 1 || normalizedPhase > 5
  ) {
    core.warning(`Skipping agent fallback due to invalid input: issueNumber=${issueNumber}, phase=${phase}`);
    core.setOutput('triggered', 'false');
    core.setOutput('handled', 'false');
    return;
  }

  // Detect structural failure (FR-001, FR-002)
  const errors = detectStructuralFailure(validationErrors, workspaceFile, fs);
  if (!errors) {
    core.info('No structural validation failure detected — skipping agent fallback');
    core.setOutput('triggered', 'false');
    core.setOutput('handled', 'false');
    return;
  }

  core.info(`Structural validation failure detected: ${errors.map(e => e.category).join(', ')}`);

  // Idempotency check (FR-008, FR-013)
  const idempotency = await checkIdempotency(github, owner, repo, normalizedIssueNumber, normalizedPhase);
  if (idempotency.skip) {
    core.info(`Idempotency guard: ${idempotency.reason}`);
    // Only treat marker-based idempotency as handled when the referenced task is non-terminal.
    // This prevents stale marker comments from suppressing normal failure handling.
    let handled = true;
    if (idempotency.source === 'marker') {
      handled = false;
      if (idempotency.taskId && token) {
        try {
          const resp = await github.request('GET /repos/{owner}/{repo}/copilot/coding-agent/tasks/{task_id}', {
            owner,
            repo,
            task_id: idempotency.taskId,
            headers: {
              authorization: `token ${token}`,
              'X-GitHub-Api-Version': '2022-11-28',
            },
          });
          const status = String(resp?.data?.status || '').toLowerCase();
          const nonTerminalStatuses = new Set(['queued', 'in_progress', 'requested', 'waiting']);
          handled = nonTerminalStatuses.has(status);
          core.info(`Idempotency marker task status=${status || 'unknown'} (handled=${handled})`);
        } catch (e) {
          core.warning(`Could not verify idempotency marker task status: ${e.message}`);
        }
      } else {
        core.warning('Cannot verify idempotency marker task status (missing task id or token)');
      }
    }
    core.setOutput('triggered', 'false');
    core.setOutput('handled', handled ? 'true' : 'false');
    // Post skip comment
    const commentOnIssue = process.env.SPECKIT_COMMENT_ON_ISSUE !== 'false';
    if (commentOnIssue) {
      try {
        await github.rest.issues.createComment({
          owner,
          repo,
          issue_number: normalizedIssueNumber,
          body: `## ℹ️ SpecKit: Agent Fallback Skipped\n\nFallback was not triggered because: ${idempotency.reason}\n\n**Existing**: [View](${idempotency.url})\n\n**Handled by fallback guard**: ${handled ? 'yes' : 'no'}`,
        });
      } catch (e) {
        core.warning(`Could not post idempotency skip comment: ${e.message}`);
      }
    }
    return;
  }

  // Build problem statement (FR-003)
  const problemStatement = buildProblemStatement(
    issueTitle,
    issueBody,
    normalizedPhase,
    errors,
    referenceSpecPath
  );

  // Guard: token required to call the Coding Agent API (FR-011)
  if (!token) {
    core.warning('COPILOT_GITHUB_TOKEN is not set — skipping agent fallback. Configure the secret to enable this feature.');
    core.setOutput('triggered', 'false');
    core.setOutput('handled', 'false');
    return;
  }

  // Trigger Copilot Coding Agent (FR-004, FR-011)
  let taskResult;
  try {
    taskResult = await triggerCodingAgent(github, owner, repo, problemStatement, token);
  } catch (e) {
    // Graceful degradation (FR-011) — fall through to standard failure handler
    core.warning(`Agent fallback API call failed: ${e.message}`);
    core.setOutput('triggered', 'false');
    core.setOutput('handled', 'false');
    return;
  }

  core.info(`Agent task created: id=${taskResult.id}, url=${taskResult.url}`);

  // Apply labels and post comment (FR-005, FR-006, FR-007)
  try {
    await applyLabelsAndComment(
      github, owner, repo, normalizedIssueNumber,
      taskResult.id, taskResult.url, normalizedPhase, errors, core
    );
  } catch (e) {
    core.warning(`Failed to apply labels/comment: ${e.message}`);
    // Still mark as triggered since the agent task was created
  }

  core.setOutput('triggered', 'true');
  core.setOutput('handled', 'true');
}

module.exports = {
  run,
  detectStructuralFailure,
  buildProblemStatement,
  checkIdempotency,
  triggerCodingAgent,
  applyLabelsAndComment,
  STRUCTURAL_ERROR_SIGNATURES,
  MAX_ISSUE_BODY_BYTES,
  TRUNCATION_MARKER,
  DEFAULT_REFERENCE_SPEC_PATH,
  PHASE_NAMES,
  parseValidationErrorsString,
};

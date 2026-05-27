#!/usr/bin/env node
//
// test_agent_fallback.js - Tests for agent-fallback.js module
//
// Run: node .github/scripts/speckit-trigger/tests/test_agent_fallback.js
//
'use strict';

const path = require('path');
const fs = require('fs');
const os = require('os');

const fallback = require(path.join(__dirname, '..', 'agent-fallback.js'));

let PASS = 0;
let FAIL = 0;

function assertEqual(desc, expected, actual) {
  if (JSON.stringify(expected) === JSON.stringify(actual)) {
    console.log(`  ✓ ${desc}`);
    PASS++;
  } else {
    console.log(`  ✗ ${desc} (expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)})`);
    FAIL++;
  }
}

function assertTruthy(desc, value) {
  if (value) {
    console.log(`  ✓ ${desc}`);
    PASS++;
  } else {
    console.log(`  ✗ ${desc} (expected truthy, got ${JSON.stringify(value)})`);
    FAIL++;
  }
}

function assertNull(desc, value) {
  if (value === null) {
    console.log(`  ✓ ${desc}`);
    PASS++;
  } else {
    console.log(`  ✗ ${desc} (expected null, got ${JSON.stringify(value)})`);
    FAIL++;
  }
}

// ---------------------------------------------------------------------------
// Tests for parseValidationErrorsString
// ---------------------------------------------------------------------------
console.log('=== Testing parseValidationErrorsString ===');

{
  const result = fallback.parseValidationErrorsString(
    'MISSING_SECTIONS: ## Problem Statement, ## Requirements;INSUFFICIENT_REQUIREMENTS: found=2, minimum=5'
  );
  assertEqual('parses two structural errors', 2, result.length);
  assertEqual('first category', 'MISSING_SECTIONS', result[0].category);
  assertEqual('first detail', '## Problem Statement, ## Requirements', result[0].detail);
  assertEqual('second category', 'INSUFFICIENT_REQUIREMENTS', result[1].category);
  assertEqual('second detail', 'found=2, minimum=5', result[1].detail);
}

{
  const result = fallback.parseValidationErrorsString('');
  assertEqual('empty string returns empty array', 0, result.length);
}

{
  const result = fallback.parseValidationErrorsString('UNKNOWN_CATEGORY: some detail');
  assertEqual('unknown category is filtered out', 0, result.length);
}

{
  const result = fallback.parseValidationErrorsString(
    '  MISSING_SECTIONS: ## Problem Statement  ;  INSUFFICIENT_USER_STORIES: found=0, minimum=3  '
  );
  assertEqual('handles whitespace around delimiters', 2, result.length);
}

// ---------------------------------------------------------------------------
// Tests for detectStructuralFailure
// ---------------------------------------------------------------------------
console.log('=== Testing detectStructuralFailure ===');

{
  const result = fallback.detectStructuralFailure(
    'MISSING_SECTIONS: ## Problem Statement',
    null,
    null
  );
  assertTruthy('detects structural failure from step output', result);
  assertEqual('returns one error', 1, result.length);
}

{
  const result = fallback.detectStructuralFailure('', null, null);
  assertNull('returns null for empty step output', result);
}

{
  const result = fallback.detectStructuralFailure(null, null, null);
  assertNull('returns null for null step output', result);
}

{
  // Test workspace file fallback
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-fallback-test-'));
  const tmpFile = path.join(tmpDir, 'validation-errors.json');
  fs.writeFileSync(tmpFile, JSON.stringify({
    phase: 1,
    phase_name: 'specify',
    errors: [
      { category: 'MISSING_SECTIONS', detail: '## Requirements' },
      { category: 'INSUFFICIENT_REQUIREMENTS', detail: 'found=2, minimum=5' },
    ],
  }));

  const result = fallback.detectStructuralFailure('', tmpFile, fs);
  assertTruthy('detects structural failure from workspace file', result);
  assertEqual('returns two errors from file', 2, result.length);

  // Cleanup
  fs.unlinkSync(tmpFile);
  fs.rmdirSync(tmpDir);
}

{
  // Test non-structural failure in workspace file
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-fallback-test-'));
  const tmpFile = path.join(tmpDir, 'validation-errors.json');
  fs.writeFileSync(tmpFile, JSON.stringify({
    phase: 1,
    phase_name: 'specify',
    errors: [
      { category: 'AUTH_FAILURE', detail: 'token expired' },
    ],
  }));

  const result = fallback.detectStructuralFailure('', tmpFile, fs);
  assertNull('returns null for non-structural errors in file', result);

  fs.unlinkSync(tmpFile);
  fs.rmdirSync(tmpDir);
}

// ---------------------------------------------------------------------------
// Tests for buildProblemStatement
// ---------------------------------------------------------------------------
console.log('=== Testing buildProblemStatement ===');

{
  const result = fallback.buildProblemStatement(
    'Test Issue',
    'Test body content',
    1,
    [{ category: 'MISSING_SECTIONS', detail: '## Requirements' }],
    null
  );
  assertTruthy('includes issue title', result.includes('Test Issue'));
  assertTruthy('includes issue body', result.includes('Test body content'));
  assertTruthy('includes phase number', result.includes('Phase 1'));
  assertTruthy('includes phase name', result.includes('specify'));
  assertTruthy('includes validation error', result.includes('MISSING_SECTIONS'));
  assertTruthy('includes default reference spec', result.includes(fallback.DEFAULT_REFERENCE_SPEC_PATH));
}

{
  const result = fallback.buildProblemStatement(
    'Title',
    'Body',
    3,
    [{ category: 'MISSING_SECTIONS', detail: '## Foo' }],
    'specs/custom/spec.md'
  );
  assertTruthy('uses custom reference spec path', result.includes('specs/custom/spec.md'));
  assertTruthy('includes phase 3 name', result.includes('plan'));
}

{
  // Test truncation
  const longBody = 'x'.repeat(60000); // > 49,152 bytes
  const result = fallback.buildProblemStatement(
    'Title',
    longBody,
    1,
    [{ category: 'MISSING_SECTIONS', detail: '## Foo' }],
    null
  );
  assertTruthy('truncates long body', result.includes(fallback.TRUNCATION_MARKER));
  // Check the issue body portion is within limits
  const bodyStart = result.indexOf('### Issue Body\n\n') + '### Issue Body\n\n'.length;
  const bodyPortion = result.substring(bodyStart);
  const bodyBytes = Buffer.byteLength(bodyPortion, 'utf8');
  assertTruthy(
    `truncated body portion <= ${fallback.MAX_ISSUE_BODY_BYTES} bytes (got ${bodyBytes})`,
    bodyBytes <= fallback.MAX_ISSUE_BODY_BYTES + 1 // +1 for trailing newline from template
  );
}

// ---------------------------------------------------------------------------
// Tests for kill-switch (FR-009)
// ---------------------------------------------------------------------------
console.log('=== Testing kill-switch ===');

(async () => {
  // Mock core and github objects
  const outputs = {};
  const mockCore = {
    info: () => {},
    warning: () => {},
    setOutput: (key, val) => { outputs[key] = val; },
  };
  const mockGithub = { rest: { pulls: { list: async () => ({ data: [] }) }, issues: {} } };
  const mockContext = { repo: { owner: 'test', repo: 'repo' } };

  // Save and restore env
  const origEnv = process.env.SPECKIT_COMMENT_ON_ISSUE;
  process.env.SPECKIT_COMMENT_ON_ISSUE = 'false';

  // The kill-switch path returns before any await, so outputs are set
  // synchronously — but we still await for correctness.
  await fallback.run({
    github: mockGithub,
    context: mockContext,
    core: mockCore,
    phase: 1,
    validationErrors: 'MISSING_SECTIONS: ## Foo',
    workspaceFile: null,
    issueNumber: 123,
    issueTitle: 'Test',
    issueBody: 'Body',
    token: 'fake-token',
    killSwitch: 'false',
    referenceSpecPath: '',
  });
  assertEqual('kill-switch sets triggered to false', 'false', outputs.triggered);

  if (origEnv === undefined) {
    delete process.env.SPECKIT_COMMENT_ON_ISSUE;
  } else {
    process.env.SPECKIT_COMMENT_ON_ISSUE = origEnv;
  }
  // ---------------------------------------------------------------------------
  // Tests for checkIdempotency pagination
  // ---------------------------------------------------------------------------
  console.log('=== Testing checkIdempotency pagination ===');

  {
    const calls = [];
    const mockOctokit = {
      rest: {
        pulls: { list: async () => ({ data: [] }) },
        issues: {
          listComments: async ({ page }) => {
            calls.push(page);
            if (page === 1) {
              return { data: Array.from({ length: 100 }, () => ({ body: 'no marker' })) };
            }
            return {
              data: [{
                body: '<!-- speckit:agent-fallback task_id=abc123 task_url=https://example.com/task issue=42 phase=2 -->',
              }],
            };
          },
        },
      },
    };
    const result = await fallback.checkIdempotency(mockOctokit, 'test-owner', 'test-repo', 42, 2);
    assertEqual('checkIdempotency finds marker on later page', true, result.skip);
    assertEqual('checkIdempotency requests second page when first page is full', 2, calls.length);
  }

  // ---------------------------------------------------------------------------
  // Tests for input guardrails in run()
  // ---------------------------------------------------------------------------
  console.log('=== Testing run() input guardrails ===');

  {
    const outputsInvalidIssue = {};
    let pullChecksInvalidIssue = 0;
    const mockCoreInvalidIssue = {
      info: () => {},
      warning: () => {},
      setOutput: (key, val) => { outputsInvalidIssue[key] = val; },
    };
    const mockGithubInvalidIssue = {
      rest: {
        pulls: { list: async () => { pullChecksInvalidIssue += 1; return { data: [] }; } },
        issues: {},
      },
      request: async () => ({ data: { id: 'x', url: 'https://example.com' } }),
    };
    await fallback.run({
      github: mockGithubInvalidIssue,
      context: mockContext,
      core: mockCoreInvalidIssue,
      phase: 1,
      validationErrors: 'MISSING_SECTIONS: ## Foo',
      workspaceFile: null,
      issueNumber: 0,
      issueTitle: 'Test',
      issueBody: 'Body',
      token: 'fake-token',
      killSwitch: 'true',
      referenceSpecPath: '',
    });
    assertEqual('invalid issue number sets triggered to false', 'false', outputsInvalidIssue.triggered);
    assertEqual('invalid issue number exits before PR checks', 0, pullChecksInvalidIssue);
  }

  {
    const outputsInvalidPhase = {};
    let pullChecksInvalidPhase = 0;
    const mockCoreInvalidPhase = {
      info: () => {},
      warning: () => {},
      setOutput: (key, val) => { outputsInvalidPhase[key] = val; },
    };
    const mockGithubInvalidPhase = {
      rest: {
        pulls: { list: async () => { pullChecksInvalidPhase += 1; return { data: [] }; } },
        issues: {},
      },
      request: async () => ({ data: { id: 'x', url: 'https://example.com' } }),
    };
    await fallback.run({
      github: mockGithubInvalidPhase,
      context: mockContext,
      core: mockCoreInvalidPhase,
      phase: 0,
      validationErrors: 'MISSING_SECTIONS: ## Foo',
      workspaceFile: null,
      issueNumber: 123,
      issueTitle: 'Test',
      issueBody: 'Body',
      token: 'fake-token',
      killSwitch: 'true',
      referenceSpecPath: '',
    });
    assertEqual('invalid phase sets triggered to false', 'false', outputsInvalidPhase.triggered);
    assertEqual('invalid phase exits before PR checks', 0, pullChecksInvalidPhase);
  }

  // ---------------------------------------------------------------------------
  // Tests for empty/undefined token guard in run()
  // ---------------------------------------------------------------------------
  console.log('=== Testing run() token guard ===');

  {
    const outputsNoToken = {};
    const warningsNoToken = [];
    let codingAgentApiCalls = 0;
    const mockCoreNoToken = {
      info: () => {},
      warning: (msg) => { warningsNoToken.push(msg); },
      setOutput: (key, val) => { outputsNoToken[key] = val; },
    };
    const mockGithubNoToken = {
      paginate: async () => [],
      rest: {
        pulls: { list: async () => ({ data: [] }) },
        issues: { listComments: async () => ({ data: [] }) },
      },
      request: async (url) => {
        // Only count Coding Agent task creation (POST endpoint)
        if (url && url.includes('coding-agent/tasks')) codingAgentApiCalls += 1;
        return { data: { id: 'x', url: 'https://example.com' } };
      },
    };
    const mockContextNoToken = { repo: { owner: 'test', repo: 'repo' } };
    process.env.SPECKIT_COMMENT_ON_ISSUE = 'false';
    await fallback.run({
      github: mockGithubNoToken,
      context: mockContextNoToken,
      core: mockCoreNoToken,
      phase: 1,
      validationErrors: 'MISSING_SECTIONS: ## Foo',
      workspaceFile: null,
      issueNumber: 123,
      issueTitle: 'Test',
      issueBody: 'Body',
      token: '',
      killSwitch: 'true',
      referenceSpecPath: '',
    });
    assertEqual('empty token sets triggered to false', 'false', outputsNoToken.triggered);
    assertEqual('empty token does not call Coding Agent API', 0, codingAgentApiCalls);
    assertTruthy('empty token emits warning', warningsNoToken.some(w => w.includes('COPILOT_GITHUB_TOKEN')));
  }

  {
    // Verify undefined token is also rejected
    const outputsUndefinedToken = {};
    const warningsUndefinedToken = [];
    let codingAgentCallsUndefined = 0;
    const mockCoreUndefinedToken = {
      info: () => {},
      warning: (msg) => { warningsUndefinedToken.push(msg); },
      setOutput: (key, val) => { outputsUndefinedToken[key] = val; },
    };
    const mockGithubUndefinedToken = {
      paginate: async () => [],
      rest: {
        pulls: { list: async () => ({ data: [] }) },
        issues: { listComments: async () => ({ data: [] }) },
      },
      request: async (url) => {
        if (url && url.includes('coding-agent/tasks')) codingAgentCallsUndefined += 1;
        return { data: { id: 'x', url: 'https://example.com' } };
      },
    };
    const mockContextUndefinedToken = { repo: { owner: 'test', repo: 'repo' } };
    process.env.SPECKIT_COMMENT_ON_ISSUE = 'false';
    await fallback.run({
      github: mockGithubUndefinedToken,
      context: mockContextUndefinedToken,
      core: mockCoreUndefinedToken,
      phase: 1,
      validationErrors: 'MISSING_SECTIONS: ## Foo',
      workspaceFile: null,
      issueNumber: 123,
      issueTitle: 'Test',
      issueBody: 'Body',
      token: undefined,
      killSwitch: 'true',
      referenceSpecPath: '',
    });
    assertEqual('undefined token sets triggered to false', 'false', outputsUndefinedToken.triggered);
    assertEqual('undefined token does not call Coding Agent API', 0, codingAgentCallsUndefined);
    assertTruthy('undefined token emits warning', warningsUndefinedToken.some(w => w.includes('COPILOT_GITHUB_TOKEN')));
  }

  // ---------------------------------------------------------------------------
  // Tests for marker persistence when SPECKIT_COMMENT_ON_ISSUE=false
  // ---------------------------------------------------------------------------
  console.log('=== Testing marker persistence with comments disabled ===');

  {
    const outputsMarkerOnly = {};
    const createdComments = [];
    const mockCoreMarkerOnly = {
      info: () => {},
      warning: () => {},
      setOutput: (key, val) => { outputsMarkerOnly[key] = val; },
    };
    const mockGithubMarkerOnly = {
      rest: {
        pulls: { list: async () => ({ data: [] }) },
        issues: {
          listComments: async () => ({ data: [] }),
          createComment: async ({ body }) => {
            createdComments.push(body);
            return {};
          },
          addLabels: async () => ({}),
          removeLabel: async () => ({}),
        },
      },
      request: async (route) => {
        if (route && route.includes('coding-agent/tasks')) {
          return { data: { id: 'task-123', url: 'https://example.com/task/123', status: 'queued' } };
        }
        return { data: {} };
      },
    };
    process.env.SPECKIT_COMMENT_ON_ISSUE = 'false';
    await fallback.run({
      github: mockGithubMarkerOnly,
      context: mockContext,
      core: mockCoreMarkerOnly,
      phase: 1,
      validationErrors: 'MISSING_SECTIONS: ## Foo',
      workspaceFile: null,
      issueNumber: 123,
      issueTitle: 'Test',
      issueBody: 'Body',
      token: 'fake-token',
      killSwitch: 'true',
      referenceSpecPath: '',
    });
    assertEqual('comments-disabled success sets triggered to true', 'true', outputsMarkerOnly.triggered);
    assertEqual('comments-disabled success sets handled to true', 'true', outputsMarkerOnly.handled);
    assertEqual('creates one marker-only comment', 1, createdComments.length);
    assertTruthy('marker-only comment contains task id marker', createdComments[0].includes('<!-- speckit:agent-fallback task_id=task-123'));
    assertTruthy('marker-only comment omits user-facing heading', !createdComments[0].includes('SpecKit: Agent Fallback Triggered'));
  }

  // ---------------------------------------------------------------------------
  // Tests for marker idempotency handling in run()
  // ---------------------------------------------------------------------------
  console.log('=== Testing run() marker idempotency handling ===');

  {
    const outputsMarkerTerminal = {};
    const mockCoreMarkerTerminal = {
      info: () => {},
      warning: () => {},
      setOutput: (key, val) => { outputsMarkerTerminal[key] = val; },
    };
    const mockGithubMarkerTerminal = {
      rest: {
        pulls: { list: async () => ({ data: [] }) },
        issues: {
          listComments: async () => ({
            data: [{
              body: '<!-- speckit:agent-fallback task_id=abc123 task_url=https://example.com/task issue=123 phase=1 -->',
            }],
          }),
          createComment: async () => ({}),
        },
      },
      request: async (route) => {
        if (route && route.includes('/copilot/coding-agent/tasks/')) {
          return { data: { status: 'failed' } };
        }
        return { data: { id: 'x', url: 'https://example.com' } };
      },
    };
    process.env.SPECKIT_COMMENT_ON_ISSUE = 'false';
    await fallback.run({
      github: mockGithubMarkerTerminal,
      context: mockContext,
      core: mockCoreMarkerTerminal,
      phase: 1,
      validationErrors: 'MISSING_SECTIONS: ## Foo',
      workspaceFile: null,
      issueNumber: 123,
      issueTitle: 'Test',
      issueBody: 'Body',
      token: 'fake-token',
      killSwitch: 'true',
      referenceSpecPath: '',
    });
    assertEqual('marker skip with terminal task sets triggered to false', 'false', outputsMarkerTerminal.triggered);
    assertEqual('marker skip with terminal task sets handled to false', 'false', outputsMarkerTerminal.handled);
  }

  {
    const outputsMarkerRunning = {};
    const mockCoreMarkerRunning = {
      info: () => {},
      warning: () => {},
      setOutput: (key, val) => { outputsMarkerRunning[key] = val; },
    };
    const mockGithubMarkerRunning = {
      rest: {
        pulls: { list: async () => ({ data: [] }) },
        issues: {
          listComments: async () => ({
            data: [{
              body: '<!-- speckit:agent-fallback task_id=abc123 task_url=https://example.com/task issue=123 phase=1 -->',
            }],
          }),
          createComment: async () => ({}),
        },
      },
      request: async (route) => {
        if (route && route.includes('/copilot/coding-agent/tasks/')) {
          return { data: { status: 'in_progress' } };
        }
        return { data: { id: 'x', url: 'https://example.com' } };
      },
    };
    process.env.SPECKIT_COMMENT_ON_ISSUE = 'false';
    await fallback.run({
      github: mockGithubMarkerRunning,
      context: mockContext,
      core: mockCoreMarkerRunning,
      phase: 1,
      validationErrors: 'MISSING_SECTIONS: ## Foo',
      workspaceFile: null,
      issueNumber: 123,
      issueTitle: 'Test',
      issueBody: 'Body',
      token: 'fake-token',
      killSwitch: 'true',
      referenceSpecPath: '',
    });
    assertEqual('marker skip with non-terminal task sets triggered to false', 'false', outputsMarkerRunning.triggered);
    assertEqual('marker skip with non-terminal task sets handled to true', 'true', outputsMarkerRunning.handled);
  }

  // ---------------------------------------------------------------------------
  // Tests for triggerCodingAgent() failure graceful degradation in run()
  // ---------------------------------------------------------------------------
  console.log('=== Testing run() triggerCodingAgent failure paths ===');

  {
    // Test 1: github.request throws — must set triggered=false, handled=false
    const outputsApiThrows = {};
    const warningsApiThrows = [];
    const mockCoreApiThrows = {
      info: () => {},
      warning: (msg) => { warningsApiThrows.push(msg); },
      setOutput: (key, val) => { outputsApiThrows[key] = val; },
    };
    const mockGithubApiThrows = {
      rest: {
        pulls: { list: async () => ({ data: [] }) },
        issues: { listComments: async () => ({ data: [] }) },
      },
      request: async (route) => {
        if (route && route.includes('coding-agent/tasks')) {
          throw new Error('API unreachable');
        }
        return { data: {} };
      },
    };
    process.env.SPECKIT_COMMENT_ON_ISSUE = 'false';
    await fallback.run({
      github: mockGithubApiThrows,
      context: mockContext,
      core: mockCoreApiThrows,
      phase: 1,
      validationErrors: 'MISSING_SECTIONS: ## Foo',
      workspaceFile: null,
      issueNumber: 123,
      issueTitle: 'Test',
      issueBody: 'Body',
      token: 'fake-token',
      killSwitch: 'true',
      referenceSpecPath: '',
    });
    assertEqual('API throw sets triggered to false', 'false', outputsApiThrows.triggered);
    assertEqual('API throw sets handled to false', 'false', outputsApiThrows.handled);
    assertTruthy('API throw emits warning', warningsApiThrows.some(w => w.includes('Agent fallback API call failed')));
  }

  {
    // Test 2: github.request returns {data:{}} (missing id/url) — triggerCodingAgent throws
    const outputsMissingFields = {};
    const warningsMissingFields = [];
    const mockCoreMissingFields = {
      info: () => {},
      warning: (msg) => { warningsMissingFields.push(msg); },
      setOutput: (key, val) => { outputsMissingFields[key] = val; },
    };
    const mockGithubMissingFields = {
      rest: {
        pulls: { list: async () => ({ data: [] }) },
        issues: { listComments: async () => ({ data: [] }) },
      },
      request: async (route) => {
        if (route && route.includes('coding-agent/tasks')) {
          // Return a response missing the required id and url fields
          return { data: {} };
        }
        return { data: {} };
      },
    };
    process.env.SPECKIT_COMMENT_ON_ISSUE = 'false';
    await fallback.run({
      github: mockGithubMissingFields,
      context: mockContext,
      core: mockCoreMissingFields,
      phase: 1,
      validationErrors: 'MISSING_SECTIONS: ## Foo',
      workspaceFile: null,
      issueNumber: 123,
      issueTitle: 'Test',
      issueBody: 'Body',
      token: 'fake-token',
      killSwitch: 'true',
      referenceSpecPath: '',
    });
    assertEqual('missing id/url sets triggered to false', 'false', outputsMissingFields.triggered);
    assertEqual('missing id/url sets handled to false', 'false', outputsMissingFields.handled);
    assertTruthy('missing id/url emits warning', warningsMissingFields.some(w => w.includes('Agent fallback API call failed')));
  }

  // ---------------------------------------------------------------------------
  // Tests for STRUCTURAL_ERROR_SIGNATURES constant
  // ---------------------------------------------------------------------------
  console.log('=== Testing STRUCTURAL_ERROR_SIGNATURES ===');

  assertTruthy('contains MISSING_SECTIONS', fallback.STRUCTURAL_ERROR_SIGNATURES.includes('MISSING_SECTIONS'));
  assertTruthy('contains INSUFFICIENT_REQUIREMENTS', fallback.STRUCTURAL_ERROR_SIGNATURES.includes('INSUFFICIENT_REQUIREMENTS'));
  assertTruthy('contains INSUFFICIENT_USER_STORIES', fallback.STRUCTURAL_ERROR_SIGNATURES.includes('INSUFFICIENT_USER_STORIES'));
  assertTruthy('contains MISSING_SUCCESS_CRITERIA', fallback.STRUCTURAL_ERROR_SIGNATURES.includes('MISSING_SUCCESS_CRITERIA'));
  assertTruthy('contains NON_MEASURABLE_CRITERIA', fallback.STRUCTURAL_ERROR_SIGNATURES.includes('NON_MEASURABLE_CRITERIA'));
  assertTruthy('contains BELOW_SIZE_THRESHOLD', fallback.STRUCTURAL_ERROR_SIGNATURES.includes('BELOW_SIZE_THRESHOLD'));
  assertTruthy('contains BULLET_SUMMARY_DETECTED', fallback.STRUCTURAL_ERROR_SIGNATURES.includes('BULLET_SUMMARY_DETECTED'));
  assertTruthy('contains MISSING_FILE', fallback.STRUCTURAL_ERROR_SIGNATURES.includes('MISSING_FILE'));

  // ---------------------------------------------------------------------------
  // Summary
  // ---------------------------------------------------------------------------
  console.log('');
  console.log(`=== Results: ${PASS} passed, ${FAIL} failed ===`);
  if (FAIL > 0) {
    process.exit(1);
  }
})().catch(e => {
  console.error('Test error:', e);
  process.exit(1);
});

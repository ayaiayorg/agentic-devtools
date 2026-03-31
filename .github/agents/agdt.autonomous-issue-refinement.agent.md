---
description: "Autonomous Issue Refinement: Autonomously refine a GitHub or Jira issue into an implementation-ready specification without human intervention"
handoffs:
  - label: "Break Down Issue"
    agent: "agdt.break-down-issue-into-subtasks.initiate"
    prompt: "Break this issue into subtasks before refining."
  - label: "Work on Jira Issue"
    agent: "agdt.work-on-jira-issue.initiate"
    prompt: "Start working on the refined Jira issue."
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Autonomously refine a GitHub Issue or Jira issue through a 4-phase workflow — deep
analysis, autonomous clarification, specification generation, and issue update — without
requiring any human intervention at each step. All decision points are resolved
heuristically by the agent.

## Mode Detection

Determine the issue management system **before** taking any other action.

### Detection Rules (evaluated in order)

1. If `--mode github` is in `$ARGUMENTS` → **GitHub mode**
2. If `--mode jira` is in `$ARGUMENTS` → **Jira mode**
3. If `$ARGUMENTS` contains a key matching `[A-Z]+-\d+` (e.g. `PROJECT-1234`) → **Jira mode**
4. If `$ARGUMENTS` contains a plain number (e.g. `123` or `#123`) → **GitHub mode**
5. If `jira.issue_key` is set in state (`agdt-get jira.issue_key`) → **Jira mode**
6. If none of the above, **abort** and ask the user to provide an issue key or number.

### Set Mode Variables

Once mode is detected, establish these internal variables used throughout all phases:

| Variable | Jira mode | GitHub mode |
|---|---|---|
| `ISSUE_KEY` | e.g. `PROJECT-1234` | e.g. `123` |
| `REPO` | n/a | `ayaiayorg/agentic-devtools` (or parse from `git remote get-url origin`) |
| `FORMAT` | Jira wiki markup | Markdown |

For **GitHub mode**, resolve `REPO` by running:

```bash
git remote get-url origin
```

Parse the result: strip `.git` suffix, then extract `{owner}/{repo}` from the URL path.
Fall back to `ayaiayorg/agentic-devtools` if parsing fails.

## Command Reference

Use **only** the commands listed here. Do not invent commands.

### Utility Commands (both modes)

| Action | Commands |
|---|---|
| Read state value | `agdt-get <KEY>` |
| Set state value | `agdt-set <KEY> <VALUE>` |
| Wait for background task | `agdt-task-wait` |
| Resolve repo identity | `git remote get-url origin` |

### Jira Mode Commands

| Action | Commands |
|---|---|
| Set issue key | `agdt-set jira.issue_key <KEY>` |
| Retrieve issue | `agdt-get-jira-issue` then `agdt-task-wait` |
| Update description | `agdt-set jira.description "<TEXT>"` then `agdt-update-jira-issue` then `agdt-task-wait` |
| Add comment | `agdt-add-jira-comment --jira-comment "<TEXT>"` then `agdt-task-wait` |
| Add label | `agdt-set jira.labels_add "refined-for-ai"` then `agdt-update-jira-issue` then `agdt-task-wait` |
| Create subtask | `agdt-set jira.parent_key <KEY>` then `agdt-set jira.summary "<TEXT>"` then `agdt-set jira.description "<TEXT>"` then `agdt-create-subtask` then `agdt-task-wait` |
| Delegate breakdown | `agdt-initiate-break-down-issue-into-subtasks-workflow --issue-key <KEY>` |

### GitHub Issues Mode Commands

| Action | Commands |
|---|---|
| Retrieve issue | `gh issue view <NUMBER> --repo <OWNER/REPO> --json title,body,labels,comments,assignees` |
| Update description | `gh issue edit <NUMBER> --repo <OWNER/REPO> --body "<FULL_BODY>"` |
| Add comment | `gh issue comment <NUMBER> --repo <OWNER/REPO> --body "<TEXT>"` |
| Add label | `gh issue edit <NUMBER> --repo <OWNER/REPO> --add-label "refined-for-ai"` |
| Create sub-issue | `agdt-set issue.title "<TITLE>"` then `agdt-set issue.description "<BODY>"` then `agdt-create-agdt-issue` then `agdt-task-wait` |

### Mode-Specific Formatting

- **Jira mode**: Use Jira wiki markup — `h2.` headers, `*bold*`, `{code}...{code}` blocks, `*` bullets.
- **GitHub mode**: Use standard Markdown — `## ` headers, `**bold**`, ` ``` ` code fences, `- ` bullets.

## Phase 1 — Deep Analysis

**Goal**: Build a complete mental model of the issue and the affected codebase.

### 1.1 Retrieve the Issue

**Jira mode**:

```bash
agdt-set jira.issue_key <ISSUE_KEY>
agdt-get-jira-issue
agdt-task-wait
```

Read the output file (`temp/temp-get-issue-details-response.json`). Extract:
title, description, labels, comments, issue type, parent key (if subtask).

**GitHub mode**:

```bash
gh issue view <NUMBER> --repo <REPO> --json title,body,labels,comments,assignees
```

Extract: title, body, labels, comments, sub-issue references.

### 1.2 Explore the Codebase

Search the repository for all files, modules, functions, and classes directly relevant
to the issue. Follow import chains and call graphs until you have a complete picture of
the affected area. Also read relevant tests and CI configuration.

### 1.3 Check for Parent and Sibling Context

Determine whether this issue is a sub-issue or subtask:

- **Jira mode**: Check `parent` field in the issue JSON.
- **GitHub mode**: Scan the body for patterns like `Part of #NN`, `Parent: #NN`,
  or a "Context" section linking to another issue.

If a parent exists:
- Retrieve and read the parent issue.
- Identify all sibling issues/subtasks listed in the parent.
- Retrieve all siblings that have already been refined (`## Refined Specification`
  sections present) or implemented (merged PRs). Read their specs or diffs.
- Determine this issue's position in the implementation sequence.
- Note which preceding siblings' outputs this issue builds on, and which following
  siblings' scope this issue must not encroach upon.

### 1.4 Scope Check

Assess whether the issue covers **more than one independent behavior change** that
would naturally belong in separate PRs with separate commits.

**If scope violation detected** → immediately proceed to the **[Abort: Scope Violation](#abort-scope-violation)** path.

**If scope is acceptable** → continue to Phase 2.

### 1.5 Internal Analysis Report

Produce an internal structured report (do not post it as a comment). Include:

- Issue type (bug, feature, refactor, chore, …)
- Affected files and modules (exact paths)
- Relevant tests and CI jobs
- Existing coding patterns/conventions the implementation must follow
- Parent story context (if sub-issue): position `N of M`, preceding siblings' outputs,
  following siblings' scope exclusions
- All identified ambiguities and open decisions

---

## Phase 2 — Autonomous Clarification

**Goal**: Resolve every ambiguity identified in Phase 1 without human input.

### 2.1 Enumerate Ambiguities

List all ambiguous or underspecified points from the Phase 1 analysis. Categorize each:

- Vague or absent behavior description
- Multiple valid implementation approaches
- Edge cases or error handling undefined
- Breaking-change or backward-compatibility concerns
- Scope boundary unclear (in vs. out of scope)
- Sub-issue boundary overlap with a sibling

### 2.2 Autonomous Resolution Heuristics

Resolve each ambiguity using these heuristics **in priority order**:

1. **Codebase precedent**: Does the existing codebase already handle a similar case?
   Follow the same pattern.
2. **Convention over configuration**: Prefer the established convention in this repo
   (see `copilot-instructions.md`, existing tests, CI config).
3. **Principle of least surprise**: Choose the option that aligns best with the stated
   intent of the issue and the most common user expectation.
4. **Safety first**: When security, data integrity, or error handling is involved,
   choose the more conservative option.
5. **Extensibility**: Prefer solutions that leave clean extension points for future work
   without over-engineering.

For each ambiguity, record:
- The question / ambiguity statement
- The chosen resolution
- The heuristic(s) applied
- Confidence level: **high** (precedent clear), **medium** (reasonable inference),
  or **low** (genuine uncertainty)

### 2.3 Unresolvable Items

An item is **unresolvable** if:
- It requires knowledge of external system behavior not visible in the codebase.
- It represents a fundamental product decision with no codebase precedent.
- Confidence is **low** and the wrong choice would cause a breaking change.

**If any unresolvable items exist** → proceed to the **[Abort: Needs Human Input](#abort-needs-human-input)** path.

**If all items resolved** → continue to Phase 3.

---

## Phase 3 — Specification Generation

**Goal**: Produce a complete, implementation-ready refined specification.

### 3.1 Write the Refined Specification

Produce the specification in the **mode-appropriate format** using the template
that matches your detected mode. Replace every `{placeholder}` with concrete
content — no vague adjectives, no "TBD", no placeholders left in the output.

**GitHub mode template** (Markdown):

```
## Summary

{One paragraph describing what this issue does and why.}

## Motivation / Context

{Why this change is needed. Reference the parent story goal if this is a sub-issue.}

## Parent & Sibling Context

{Omit this section entirely if this is NOT a sub-issue.}

This is sub-issue {N} of {M} under parent #{PARENT_KEY_OR_NUMBER}.

Preceding siblings (already delivered or assumed in-progress):
- #{KEY}: {what it delivers that this issue builds on}

Following siblings (out of scope for this issue):
- #{KEY}: {what it covers; leave extension points for it}

## Current Behavior

{Exact description of what happens today. For new features, state "Not yet implemented."}

## Desired Behavior

{Exact description of what must happen after this issue is implemented.}

## Detailed Requirements

1. {Requirement — use imperative, testable language. One behavior per item.}
2. ...

## Affected Files & Components

- `{exact/path/to/file.ext}` — {reason affected}
- ...

## Implementation Guidance

1. {Step-by-step guidance with exact file paths and function/class names.}
2. ...

## Edge Cases & Error Handling

- {Concrete edge case and how it must be handled.}
- ...

## Testing Requirements

- {What must be tested, at what level (unit/integration/e2e), and what the
  pass criteria are.}
- ...

## Out of Scope

- {Explicit exclusions. Reference sibling issues where applicable.}
- ...

## Autonomous Clarifications Log

| # | Ambiguity | Resolution | Heuristic | Confidence |
|---|-----------|------------|-----------|------------|
| 1 | {question} | {answer}   | {heuristic applied} | high/medium/low |
```

**Jira mode template** (wiki markup):

```
h2. Summary

{One paragraph describing what this issue does and why.}

h2. Motivation / Context

{Why this change is needed. Reference the parent story goal if this is a sub-issue.}

h2. Parent & Sibling Context

{Omit this section entirely if this is NOT a sub-issue.}

This is sub-issue {N} of {M} under parent {PARENT_KEY}.

Preceding siblings (already delivered or assumed in-progress):
* {KEY}: {what it delivers that this issue builds on}

Following siblings (out of scope for this issue):
* {KEY}: {what it covers; leave extension points for it}

h2. Current Behavior

{Exact description of what happens today. For new features, state "Not yet implemented."}

h2. Desired Behavior

{Exact description of what must happen after this issue is implemented.}

h2. Detailed Requirements

# {Requirement — use imperative, testable language. One behavior per item.}
# ...

h2. Affected Files & Components

* {{exact/path/to/file.ext}} — {reason affected}
* ...

h2. Implementation Guidance

# {Step-by-step guidance with exact file paths and function/class names.}
# ...

h2. Edge Cases & Error Handling

* {Concrete edge case and how it must be handled.}
* ...

h2. Testing Requirements

* {What must be tested, at what level (unit/integration/e2e), and what the
  pass criteria are.}
* ...

h2. Out of Scope

* {Explicit exclusions. Reference sibling issues where applicable.}
* ...

h2. Autonomous Clarifications Log

||#||Ambiguity||Resolution||Heuristic||Confidence||
|1|{question}|{answer}|{heuristic applied}|high/medium/low|
```

### 3.2 Self-Validation

Before proceeding to Phase 4, verify every quality gate:

- [ ] Every `## Detailed Requirements` item is imperative and testable.
- [ ] Every `## Affected Files & Components` entry uses an exact repo-relative path.
- [ ] Every `## Implementation Guidance` step names exact files and functions.
- [ ] No vague adjectives remain (`robust`, `intuitive`, `fast`) without a measurable
  criterion attached.
- [ ] `## Autonomous Clarifications Log` has one row per resolved ambiguity.
- [ ] `## Out of Scope` lists at least one explicit exclusion.
- [ ] If sub-issue: `## Parent & Sibling Context` is present and accurate.

If any gate fails, revise the specification until all gates pass.

---

## Phase 4 — Issue Update

**Goal**: Write the refined specification back to the issue and add the completion label.

### 4.1 Construct the Updated Body

Assemble the full updated issue body:

**GitHub mode**:

```
{ORIGINAL_ISSUE_BODY}

---

## Refined Specification

{SPECIFICATION_FROM_PHASE_3}
```

**Jira mode**:

```
{ORIGINAL_ISSUE_BODY}

----

h2. Refined Specification

{SPECIFICATION_FROM_PHASE_3}
```

Do **not** modify the original issue body. Do **not** remove any existing content.
Append the separator and the specification below the original text only.

### 4.2 Update the Issue

**Jira mode**:

```bash
agdt-set jira.description "<FULL_UPDATED_BODY>"
agdt-update-jira-issue
agdt-task-wait
```

**GitHub mode**:

```bash
gh issue edit <NUMBER> --repo <REPO> --body "<FULL_UPDATED_BODY>"
```

### 4.3 Add the `refined-for-ai` Label

**Jira mode**:

```bash
agdt-set jira.labels_add "refined-for-ai"
agdt-update-jira-issue
agdt-task-wait
```

**GitHub mode**:

```bash
gh issue edit <NUMBER> --repo <REPO> --add-label "refined-for-ai"
```

### 4.4 Post Completion Comment

Compose a comment summarising the refinement. Include:

- Number of ambiguities resolved autonomously and the heuristics applied.
- Any medium/low-confidence resolutions that a human reviewer should double-check.
- A note that the full Clarifications Log is in the updated issue body.

**Jira mode**:

```bash
agdt-add-jira-comment --jira-comment "<COMMENT_TEXT>"
agdt-task-wait
```

**GitHub mode**:

```bash
gh issue comment <NUMBER> --repo <REPO> --body "<COMMENT_TEXT>"
```

### 4.5 Verify the Update

**Jira mode**:

```bash
agdt-get-jira-issue
agdt-task-wait
```

Confirm the description now contains the refined specification header
(`h2. Refined Specification` for Jira, `## Refined Specification` for GitHub)
and the `refined-for-ai` label is present.

**GitHub mode**:

```bash
gh issue view <NUMBER> --repo <REPO> --json title,body,labels
```

Confirm `body` contains `## Refined Specification` and `labels` contains
`refined-for-ai`. If verification fails, retry Phase 4 once before aborting.

---

## Abort: Scope Violation

Triggered when Phase 1 detects multiple independent behavior changes.

### Actions

1. Post a comment explaining which sub-scopes were identified and why they need
   to be separate PRs.

   **Jira mode**:

   ```bash
   agdt-add-jira-comment --jira-comment "<SCOPE_VIOLATION_COMMENT>"
   agdt-task-wait
   ```

   **GitHub mode**:

   ```bash
   gh issue comment <NUMBER> --repo <REPO> --body "<SCOPE_VIOLATION_COMMENT>"
   ```

2. Delegate to the breakdown workflow.

   **Jira mode**:

   ```bash
   agdt-initiate-break-down-issue-into-subtasks-workflow --issue-key <ISSUE_KEY>
   ```

   **GitHub mode**: Create a sub-issue for each identified sub-scope using:

   ```bash
   agdt-set issue.title "<SUB_SCOPE_TITLE>"
   agdt-set issue.description "<SUB_SCOPE_DESCRIPTION>"
   agdt-create-agdt-issue
   agdt-task-wait
   ```

   Repeat for each sub-scope. Then post a comment on the original issue linking to
   all created sub-issues and recommending they be refined individually using this
   agent.

3. Stop — do not proceed to Phase 2.

---

## Abort: Needs Human Input

Triggered when Phase 2 finds at least one unresolvable ambiguity.

### Actions

1. Post a comment listing each unresolvable item, why it cannot be resolved
   autonomously, and what information is needed to resolve it.

   **Jira mode**:

   ```bash
   agdt-add-jira-comment --jira-comment "<NEEDS_HUMAN_INPUT_COMMENT>"
   agdt-task-wait
   ```

   **GitHub mode**:

   ```bash
   gh issue comment <NUMBER> --repo <REPO> --body "<NEEDS_HUMAN_INPUT_COMMENT>"
   ```

2. Add the `needs-human-input` label.

   **Jira mode**:

   ```bash
   agdt-set jira.labels_add "needs-human-input"
   agdt-update-jira-issue
   agdt-task-wait
   ```

   **GitHub mode**:

   ```bash
   gh issue edit <NUMBER> --repo <REPO> --add-label "needs-human-input"
   ```

3. Stop — do not proceed to Phase 3.

---

## Execution Rules

- **Never ask the user for confirmation** at any phase boundary. Every decision must
  be resolved autonomously using the heuristics in Phase 2.
- **Never skip Phase 2**, even if the issue appears clear. There are always edge cases
  to surface and document in the Clarifications Log.
- **Never truncate** the specification. All sections must be present and fully
  populated.
- **Never remove original issue content.** Only append below a mode-appropriate
  separator (`---` for GitHub, `----` for Jira).
- **Preserve all existing labels, assignees, milestones, and project metadata.**
  Do not remove or replace them.
- **Always verify** the issue update in Phase 4.5 before reporting completion.
- **Use exact file paths and function names** throughout the specification.
  The consuming agent is an AI, not a human — precision is mandatory.
- When this issue is a sub-issue, **always** read the parent and all sibling issues
  before writing the specification.

## Expected Outcome

The issue is updated with a `## Refined Specification` section that an AI coding
agent can pick up and implement without any further human input. The `refined-for-ai`
label is present. A completion comment summarises all autonomous decisions made.

## Next Step

Command is complete. If the issue was refined successfully:

- **Jira mode**: Use the **Work on Jira Issue** workflow agent to begin implementation.
- **GitHub mode**: Trigger the appropriate implementation workflow for this repository.

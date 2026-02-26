---
name: SpecKit Trigger Test
about: Test issue for manually validating the SpecKit GitHub Action trigger
title: "[SpecKit Test] "
labels: ''
assignees: ''
---

## Purpose

This is a test issue for validating the **SpecKit Issue Trigger** GitHub Action.

Add the `speckit` label to this issue to trigger automatic specification generation.

## Feature Description

<!--
  Describe the feature you want SpecKit to generate a specification for.
  Be as detailed as possible — the AI will use this to generate a complete spec.
-->

**What feature should be specified?**

<!-- Replace this line with your feature description -->

## Expected Behavior

When the `speckit` label is applied to this issue, the GitHub Action should:

1. ✅ Post a "Specification Creation Started" comment within 30 seconds
2. ✅ Replace the `speckit` label with `speckit:processing`
3. ✅ Generate a feature specification using the configured AI provider
4. ✅ Create a new branch named `NNN-feature-name`
5. ✅ Commit the generated `spec.md` to that branch
6. ✅ Open a Pull Request with the specification
7. ✅ Post a "Specification Created Successfully" comment with links
8. ✅ Replace `speckit:processing` with `speckit:completed`

## Validation Checklist

- [ ] "Started" comment posted within 30 seconds of label application
- [ ] `speckit:processing` label appears on the issue
- [ ] Workflow run is visible in the Actions tab
- [ ] A new branch `NNN-*` is created in the repository
- [ ] `spec.md` exists in `specs/NNN-*/` with correct content
- [ ] Spec contains `Source Issue: #N (URL)` reference
- [ ] Pull Request is created with `Relates to #N` in description
- [ ] "Completed" comment includes links to spec file and PR
- [ ] `speckit:completed` label replaces `speckit:processing`

## Troubleshooting

If the action fails:

1. Check the [Actions tab](../../actions/workflows/speckit-issue-trigger.yml) for logs
2. Verify `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`) repository secret is set
3. Ensure the `SPECKIT_TRIGGER_LABEL` repository variable matches the label used
4. Review the "Failed" comment on this issue for specific error details

---

> **Note**: This template is for testing only. For real features, create a regular issue and apply the `speckit` label.

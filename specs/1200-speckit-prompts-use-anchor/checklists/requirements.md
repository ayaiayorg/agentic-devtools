# Specification Quality Checklist: SpecKit prompts — Use anchor descriptions instead of hardcoded line numbers in tasks

**Purpose**: Validate specification completeness before proceeding to planning
**Created**: 2026-04-23
**Feature**: [spec.md](../spec.md)
**Source Issue**: #1200

## Content Quality

- [ ] CHK001 User stories clearly describe the value of replacing hardcoded line numbers with semantic anchors from the user/developer perspective, not just the mechanical change
- [ ] CHK002 All user stories follow the "As a [role], I want [goal], so that [benefit]" format and avoid prescribing implementation mechanisms
- [ ] CHK003 User stories have an explicit priority such as P1/P2/... (or another scheme explicitly defined in `spec.md`), and functional requirements use RFC-2119 style MUST/SHOULD/MAY language
- [ ] CHK004 Requirements describe *what* semantic anchors achieve without dictating internal data structures, regex patterns, prompt template syntax, or other code-level implementation details

## Requirement Completeness

- [ ] CHK005 Each user story has at least one testable acceptance scenario, including any story focused on validation-only behaviour if such a story exists in the spec
- [ ] CHK006 Edge cases cover cross-task symbol references and also address missing anchors, ambiguous anchors, anchors in deleted or renamed files, and files with no recognizable semantic structure
- [ ] CHK007 Acceptance scenarios use Given/When/Then format with concrete examples of semantic anchor descriptions replacing specific hardcoded line numbers
- [ ] CHK008 Any token budget, prompt size limit, baseline, or similar non-functional constraint has a measurable success criterion explaining how conformance is verified
- [ ] CHK009 Scope boundaries explicitly identify the files, prompts, or generation stages in scope, and list clear out-of-scope items such as runtime
  anchor resolution or unrelated prompt changes
- [ ] CHK010 Dependencies and assumptions are documented, including any dependency on the existing SpecKit task generation pipeline and any assumptions about
  extracting semantic anchors from supported file types

## Feature Readiness

- [ ] CHK011 Every functional requirement has at least one acceptance criterion that can be verified without subjective judgment
- [ ] CHK012 User scenarios cover the primary workflow, relevant edge-case workflows such as cross-task newly-created-symbol references, and at least one
  regression scenario confirming existing non-anchor tasks still work if that behaviour remains in scope
- [ ] CHK013 Success criteria include at least one quantitative measure and one qualitative measure, with both tied to language that actually appears in the spec
- [ ] CHK014 Any clarifications, notes, or Q&A content in the spec constrains *behaviour* and terminology without prescribing code-level solutions

## Notes

- This checklist must match the current `spec.md` content and terminology for issue #1200
- If the spec does not use numbered user stories or requirements, validate against the equivalent sections actually present in `spec.md`
- Items marked incomplete require spec or checklist updates before proceeding to planning

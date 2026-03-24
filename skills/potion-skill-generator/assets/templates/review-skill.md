---
{{#unless plugin_mode}}name: {{project_name}}-review
{{/unless}}description: >
  Reviews code for {{project_name}} against its actual standards, not generic
  best practices. This skill should be used when someone asks to review a PR,
  diff, file, or implementation. It also triggers for "does this look right",
  "review my changes", "check this code", "audit this", or "what's wrong with
  this".
allowed-tools: Read, Glob, Grep
model: sonnet
effort: medium
---

# {{project_name}} — Code Review

Before reviewing, read `{{guidelines_path}}` for this project's standards.

## Review strategy

Choose the approach based on the size of the change:

### Small changes (1-3 files, single module)
Run the review checklist below directly — no need for sub-agents.

### Medium changes (4-10 files, 1-2 modules)
Spawn 2-3 relevant sub-agents based on what the changes touch:
- Backend route/service changes → pattern-reviewer + architecture-reviewer
- Frontend component changes → style-reviewer + test-reviewer
- Database migrations → security-reviewer + architecture-reviewer
- New feature across modules → architecture-reviewer + pattern-reviewer + test-reviewer

### Large changes (10+ files, multiple modules)
Spawn all available sub-agents in parallel, then aggregate findings.

{{#if reviewer_agents}}
## Available sub-agents

{{#each reviewer_agents}}
- **{{name}}** — {{focus}}. Reads: `{{guidelines_file}}`
{{/each}}

Each sub-agent returns findings in JSON format. After all complete:
1. Collect all findings
2. Deduplicate (same file:line from multiple agents → keep the most specific)
3. Sort by severity (blockers first, then suggestions)
4. Present unified report using the format below
{{/if}}

## Review checklist (for direct review)

### Architecture & Design
- [ ] Change is in the correct module
- [ ] Respects layer boundaries
- [ ] No circular dependencies introduced
- [ ] Public API surface is intentional

### Pattern compliance
{{patterns_checklist}}

### Error handling
{{error_handling_checklist}}

### Testing
{{testing_checklist}}

### Types & safety
{{typing_checklist}}

### Naming & style
{{naming_checklist}}

### Observability
{{#if observability_patterns}}
- [ ] Uses the project's logging framework ({{logging_framework}})
- [ ] Log levels are appropriate (not logging debug info at ERROR)
- [ ] Structured logging format followed (if applicable)
- [ ] No PII or secrets in log messages
- [ ] Correlation/request IDs propagated where applicable
{{#if metrics_framework}}
- [ ] New endpoints/operations have appropriate metrics
{{/if}}
{{else}}
- [ ] Logging is consistent with existing patterns in the module
- [ ] No sensitive data in log output
{{/if}}

## Module-specific notes

{{module_specific_notes}}

## Severity classification

**Blockers** (must fix before merge):
- Security issues
- Missing error handling in critical paths
- Pattern violations that set a bad precedent
- Missing tests for new functionality

**Suggestions** (nice to have):
- Minor naming improvements
- Extra test cases for edge cases
- Documentation improvements
- Performance optimizations

## How to report each finding

For each finding, use this format:

```
**[BLOCKER/SUGGESTION]** {file}:{line} — {what's wrong}
  Why: {reference to guideline or pattern that this violates}
  Fix: {specific suggestion, ideally with code or a reference to the canonical example}
```

## Common pitfalls to watch for

These are real issues found during codebase analysis:

{{#each pitfalls}}
- **{{description}}** ({{severity}}) — {{context}}
{{/each}}

## For large reviews

For PRs touching more than 5 files or multiple modules, consider delegating
to the `{{project_name}}-reviewer` agent for a focused, fresh-context review.

## Reference files

- Canonical implementation: `{{canonical_implementation_path}}`
- Canonical test: `{{canonical_test_path}}`
- Guidelines: `{{guidelines_path}}`

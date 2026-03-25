---
{{#unless plugin_mode}}name: {{project_name}}-review
{{/unless}}description: >
  Reviews code for {{project_name}} across multiple language stacks. Determines
  which stacks are in the diff, passes stack context to topic reviewers, and
  aggregates findings. Use when someone asks to "review", "check", or "audit" code.
allowed-tools: Read, Glob, Grep
model: opus
effort: high
---

# {{project_name}} — Multi-Stack Code Review

## Load guidelines

Before reviewing, read the shared conventions and each stack's overview:

- **Shared conventions:** `{{shared_guidelines_path}}`
{{#each stacks}}
- {{display_name}}: `{{guidelines_path}}/index.md`
{{/each}}

## Stack routing

Map every file in the diff to a stack using paths and module ownership.

{{#each stacks}}
### {{display_name}}
- **Modules:** {{modules}}
- **Paths:** {{module_paths}}
- **Guidelines:** `{{guidelines_path}}/`
{{/each}}

## Review strategy

Choose the approach based on the size and stack spread of the change.

### Small changes (1-3 files, single stack)
Run the review checklist below directly using that stack's guidelines — no need
for sub-agents.

### Medium changes (4-10 files, 1-2 stacks)
Spawn 2-3 relevant topic reviewers based on what the changes touch. Tell each
reviewer which stack's guidelines to load:
- Backend route/service changes → pattern-reviewer + architecture-reviewer
- Frontend component changes → style-reviewer + test-reviewer
- Database migrations → security-reviewer + architecture-reviewer
- New feature across modules → architecture-reviewer + pattern-reviewer + test-reviewer

### Large changes (10+ files, multiple stacks)
Spawn all available topic reviewers in parallel. For each reviewer, pass the
stack context so it knows which guidelines to load:
```
Review these files using {stack_name} guidelines:
- Architecture: {stack_guidelines_path}/index.md
- Patterns: {stack_guidelines_path}/patterns.md
- Conventions: {stack_guidelines_path}/conventions.md
- Testing: {stack_guidelines_path}/testing.md
```

## Topic reviewer dispatch with stack context

The master reviewer PASSES stack context to each topic reviewer — reviewers do
not detect it themselves.

{{#if reviewer_agents}}
{{#each reviewer_agents}}
- **{{name}}** — {{focus}}:
  {{#each affected_stacks}}
  - For {{stack_name}} files → load `{{stack_guidelines_path}}/{{topic_file}}`
  {{/each}}
{{/each}}

Each sub-agent returns findings in JSON format. After all complete:
1. Collect all findings
2. Deduplicate (same file:line from multiple agents → keep the most specific)
3. Sort by severity (blockers first, then suggestions)
4. Group findings by stack
5. Present unified report using the format below
{{/if}}

## Cross-stack review

For changes spanning multiple stacks, additionally check:

- [ ] **API contract alignment** — does the frontend consume what the backend provides?
- [ ] **Shared type consistency** — protobuf/OpenAPI/schema definitions match their implementations
- [ ] **Cross-stack imports** — flag if a stack imports directly from another stack's internals (should go through contracts)
- [ ] **Migration ordering** — database/schema changes are applied before code that depends on them

## Review checklist (for direct review — single stack)

### Architecture & Design
- [ ] Change is in the correct module (see stack module map)
- [ ] Respects layer boundaries for this stack
- [ ] No circular dependencies introduced
- [ ] Public API surface is intentional

### Pattern compliance ({{stack_name}})
{{stack_patterns_checklist}}

### Error handling ({{stack_name}})
{{stack_error_handling_checklist}}

### Testing ({{stack_name}})
{{stack_testing_checklist}}

### Types & safety ({{stack_name}})
{{stack_typing_checklist}}

### Naming & style ({{stack_name}})
{{stack_naming_checklist}}

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

## Severity classification

**Blockers** (must fix before merge):
- Security issues
- Missing error handling in critical paths
- Pattern violations that set a bad precedent
- Missing tests for new functionality
- Cross-stack contract mismatches

**Suggestions** (nice to have):
- Minor naming improvements
- Extra test cases for edge cases
- Documentation improvements
- Performance optimizations

## How to report each finding

For each finding, use this format:

```
**[BLOCKER/SUGGESTION]** {file}:{line} — {what's wrong}
  Stack: {stack_name}
  Why: {reference to stack-specific guideline or pattern that this violates}
  Fix: {specific suggestion, ideally with code or a reference to the canonical example}
```

## Aggregation

After all topic reviewers have returned their findings:

1. **Collect** all findings from every reviewer
2. **Deduplicate** — same file:line reported by multiple reviewers → keep the most specific finding
3. **Sort** by severity (blockers first, then suggestions)
4. **Group by stack** — present findings under their stack heading so the developer knows which context to look at
5. **Cross-stack summary** — if the change spans multiple stacks, add a summary section highlighting any cross-stack issues (contract mismatches, type inconsistencies, import violations)

## Common pitfalls to watch for

These are real issues found during codebase analysis:

{{#each pitfalls}}
- **{{description}}** ({{severity}}) — {{context}}
{{/each}}

## Reference files

{{#each stacks}}
### {{display_name}}
- Canonical implementation: `{{canonical_implementation_path}}`
- Canonical test: `{{canonical_test_path}}`
- Guidelines: `{{guidelines_path}}/`
{{/each}}
- Shared guidelines: `{{shared_guidelines_path}}`

---
{{#unless plugin_mode}}name: {{project_name}}-plan
{{/unless}}description: >
  Plans feature implementations, refactors, and architectural changes in
  {{project_name}} before writing code. This skill should be used when someone
  asks to "plan", "design", "break down", "spec out", "architect", or "how
  should I implement" something. It also triggers for tickets, user stories,
  feature requests, or specs that need an implementation approach. Even "what
  files would I need to change for X" or "what's the best approach for X"
  should activate this skill.
allowed-tools: Read, Glob, Grep
model: inherit
effort: high
---

# {{project_name}} — Implementation Planning

{{#if multi_guidelines}}Before planning, read the guidelines at `{{guidelines_path}}` — start
with `index.md` and `architecture.md`, then check `patterns.md` for the
patterns relevant to your plan.
{{else}}Before planning, read `{{guidelines_path}}` for architecture and patterns.
{{/if}}

## When to use this skill

Use this BEFORE the implement skill. Planning catches architectural mistakes
when they're cheapest to fix — before any code is written.

## Planning process

### 1. Understand the requirement
- What is being asked? Restate in your own words.
- What is the expected user-facing behavior?
- What are the acceptance criteria (explicit or implied)?

### 2. Identify scope
Which modules does this touch? Use the module map:

{{module_map_table}}

For each affected module, check its specific patterns in the guidelines.

### 3. Design the approach

For each module touched, answer:
- **What pattern to follow?** Reference the canonical example for that module.
- **What layer does this change live in?** (route, service, domain, UI, etc.)
- **What existing code to reuse?** Grep for similar functionality before designing new abstractions.
- **What's the data flow?** Trace how data moves through the change.

### 4. Check for pitfalls

These are real issues found in this codebase — check each one against your plan:

{{#each pitfalls}}
- **{{description}}** ({{severity}}) — {{context}}
{{/each}}

### 5. Produce the plan

Structure your output as:

```
## Plan: {feature name}

### Summary
{1-2 sentences: what this plan achieves}

### Modules affected
| Module | What changes | Pattern to follow |
|--------|-------------|-------------------|

### Implementation steps
{Ordered list of steps, each with:}
1. **{Step name}** — {what to do}
   - File: `{path to create or modify}`
   - Pattern: reference canonical example
   - Tests: what to test

### Files to create
| File | Purpose | Template/Example |
|------|---------|-----------------|

### Files to modify
| File | What changes | Lines affected (approx) |
|------|-------------|------------------------|

### Testing plan
- {What tests to write}
- {What test patterns to follow}
- {Run command: `{{test_command}}`}

### Risks and open questions
- {Anything unclear or risky about this approach}
```

## Key patterns quick reference

{{patterns_summary}}

## Canonical examples

When suggesting patterns, point to these real files:

{{#each canonical_examples}}
- `{{file}}` — {{why}}
{{/each}}

## Rules

- Never guess file paths. Glob/Grep to verify they exist.
- Reference real patterns from the guidelines, not generic advice.
- If the requirement is ambiguous, list what needs clarification.
- For complex plans touching 3+ modules, consider delegating to the
  `{{project_name}}-planner` agent for a focused planning session.
- Plans should be implementable by someone who only reads the plan
  and the guidelines — no assumed tribal knowledge.

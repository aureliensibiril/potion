---
{{#unless plugin_mode}}name: {{project_name}}-plan
{{/unless}}description: >
  Plans features for {{project_name}} across multiple language stacks. Identifies
  which stacks are involved, determines execution order based on data flow, and
  creates stack-labeled implementation sections. Use when someone asks to "plan",
  "design", "architect", or "think about" a feature.
allowed-tools: Read, Glob, Grep
model: opus
effort: high
---

# {{project_name}} — Multi-Stack Implementation Planning

Before planning, load shared conventions and each stack's architecture:
- `{{shared_guidelines_path}}` for cross-cutting conventions
{{#each stacks}}
- `{{guidelines_path}}/index.md` for {{display_name}} architecture
{{/each}}

## When to use this skill

- Planning a new feature that may span stacks
- Designing an architecture change
- Breaking down a large task into stack-aware steps

Use this BEFORE the implement skill. Planning catches architectural mistakes
when they're cheapest to fix — before any code is written.

## Planning process

### 1. Understand the requirement
- What is being asked? Restate in your own words.
- What is the expected user-facing behavior?
- What are the acceptance criteria (explicit or implied)?

### 2. Identify stacks involved
Which stacks are affected by this change? Read each stack's module map and
guidelines to determine whether it participates:

{{#each stacks}}
- **{{display_name}}** ({{language}}) — modules: {{modules}}
{{/each}}

### 3. Determine execution order
Which stack is upstream (provides data/API) vs downstream (consumes)?
Order implementation so that dependencies are built before consumers.

### 4. Reference stack-specific patterns
For each affected stack, consult its patterns and conventions:

{{#each stacks}}
For {{display_name}} work: see `{{guidelines_path}}/patterns.md`
{{/each}}

### 5. Identify cross-stack integration points
- API contracts between stacks (endpoints, payloads, status codes)
- Shared types or data structures that must stay in sync
- Data flow direction — which stack owns the source of truth?

### 6. Check pitfalls per stack
These are real issues found in this codebase — check each one against your plan:

{{#each pitfalls}}
- **{{description}}** ({{severity}}) — {{context}}
{{/each}}

### 7. Produce structured plan

Structure your output as:

```
## Summary
{What we're building and why}

## Stacks Involved
{Which stacks and why each is needed}

## Execution Order
{Which stack goes first and why — dependency direction}

{{#each involved_stacks}}
## {{display_name}} ({{language}})
### Implementation Steps
{Numbered steps, each referencing real files and patterns from this stack}
### Files to Create/Modify
{Exact paths}
### Testing
{Stack-specific test approach}
{{/each}}

## Cross-Stack Integration Points
{API contracts, shared types, data flow between stacks}

## Risks & Pitfalls
{Per-stack pitfalls that apply to this feature}
```

## Stack reference

{{#each stacks}}
### {{display_name}} ({{language}})
- Modules: {{modules}}
- Patterns: `{{guidelines_path}}/patterns.md`
- Testing: `{{guidelines_path}}/testing.md`
- Canonical example: `{{canonical_file}}`
{{/each}}

## Rules

- Never guess file paths. Glob/Grep to verify they exist.
- Each stack section references that stack's actual patterns from the guidelines.
- Cross-stack integration points must be explicit (API shape, type contract).
- Execution order must be justified by data flow direction.
- If the requirement is ambiguous, list what needs clarification.
- Plans should be implementable by someone who only reads the plan
  and the guidelines — no assumed tribal knowledge.

---
{{#unless plugin_mode}}name: potion-plan
{{/unless}}description: >
  Plans feature implementations, refactors, and architectural changes in
  {{project_name}} before writing code. This skill should be used when someone
  asks to "plan", "design", "break down", "spec out", "architect", or "how
  should I implement" something. It also triggers for tickets, user stories,
  feature requests, or specs that need an implementation approach. Even "what
  files would I need to change for X" or "what's the best approach for X"
  should activate this skill.
allowed-tools: Read, Write, Glob, Grep, AskUserQuestion, Agent
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

---

## Phase 0: Pre-planning — Gather context

Before designing anything, understand the requirement deeply. Skipping this
phase is the #1 cause of plans that miss the mark.

### 1. Classify the task type

Determine which kind of change this is — it shapes the entire planning approach:

| Type | Signals | Planning focus |
|------|---------|---------------|
| **New feature** | "add", "create", "build", "new" | Entry point, data flow, layers to touch, wiring |
| **Refactor** | "refactor", "extract", "move", "rename", "split" | Migration path, backward compat, affected dependents |
| **Bug fix** | "fix", "broken", "doesn't work", "regression" | Root cause vs. symptoms, minimal fix, regression test |
| **Migration** | "upgrade", "migrate", "replace", "switch to" | Rollback strategy, incremental steps, feature parity |

### 2. Explore the codebase

Before asking questions, do your homework:

- **Read relevant code.** Grep for related functionality, read the modules
  that will be affected. Understand what exists before proposing what to build.
- **Check recent changes.** Look at recent commits in the affected areas for
  context on what's in flux.
- **Identify unknowns.** Note what you couldn't determine from the code alone.

### 3. Ask targeted clarifying questions

Use `AskUserQuestion` to surface ambiguity. Only ask questions whose answers
you could NOT determine from the code. Focus on:

- **Acceptance criteria** — What does "done" look like? What behaviors are expected?
- **Scope boundaries** — What is explicitly out of scope?
- **Constraints** — Performance requirements? Backward compatibility? Deadlines?
- **Edge cases** — How should the system behave in non-happy-path scenarios?
- **Prior decisions** — Has this been attempted before? Any rejected approaches?

Structure questions with options when possible — they're easier to answer:

```
AskUserQuestion({
  questions: [{
    question: "What should happen when [edge case]?",
    options: [
      { label: "Option A", description: "..." },
      { label: "Option B", description: "..." },
      { label: "Something else", description: "I'll describe" }
    ]
  }]
})
```

**Skip this step** if the requirement is already clear and specific (e.g., a
well-written ticket with acceptance criteria, or a trivial change).

---

## Phase 1: Design the plan

### 1. Restate the requirement

Write a clear, specific summary. This is your contract:
- What is being built or changed?
- What is the expected user-facing behavior?
- What are the acceptance criteria (explicit or gathered in Phase 0)?

### 2. Identify scope

Which modules does this touch? Use the module map:

{{module_map_table}}

For each affected module, check its specific patterns in the guidelines.

**Scope check:** If the plan touches more than 5 modules or will need more
than 15 implementation steps, recommend splitting into smaller plans. State
what each sub-plan would cover.

### 3. Design the approach (by task type)

#### For new features
1. Identify the entry point (API route? UI page? CLI command? Event handler?)
2. Trace the data flow through layers (request → service → domain → storage)
3. For each layer, identify the file to create/modify and the pattern to follow
4. Identify wiring points (registrations, exports, route tables, DI containers)
5. Plan tests for each layer

#### For refactors
1. Identify all files affected (Grep for usage of the thing being refactored)
2. Design the migration path — can it be done incrementally?
3. Define backward compatibility strategy during migration (if needed)
4. Identify what tests need updating vs. what tests validate the refactor worked
5. Consider: is this a rename, extract, split, merge, or replace?

#### For bug fixes
1. Reproduce: trace the bug through the code to the root cause
2. Distinguish root cause from symptoms — fix the cause, not just the visible effect
3. Plan the minimal fix (smallest change that resolves the root cause)
4. Plan a regression test that would have caught this bug

#### For migrations
1. Define feature parity — what must the new version do that the old one did?
2. Plan rollback strategy — how to revert if the migration fails
3. Design incremental migration steps (avoid big-bang switches)
4. Plan for coexistence period if old and new must run simultaneously
5. Identify data migration needs (if applicable)

### 4. Check for pitfalls

These are real issues found in this codebase — check each one against your plan:

{{#each pitfalls}}
- **{{description}}** ({{severity}}) — {{context}}
{{/each}}

---

## Phase 2: Produce the plan

### Step granularity

Each step must be a **single, concrete action** completable in 2-5 minutes.

**Bad step:** "Implement the service layer"
**Good step:** "Create `src/billing/services/invoice.service.ts` with the
`createInvoice` method following the pattern in
`src/orders/services/order.service.ts:23-45`"

Each step must include:
- **Exact file path** (verified with Glob/Grep — never guessed)
- **What to do** (create, modify specific lines, delete, wire up)
- **Pattern to follow** (canonical example with file path and line range)
- **Verification** (exact command to run and expected output)

### Plan output format

```
## Plan: {feature name}

### Type
{Feature | Refactor | Bug fix | Migration}

### Summary
{2-3 sentences: what this plan achieves and why this approach was chosen
over alternatives}

### Acceptance criteria
- [ ] {Criterion 1 — specific, testable}
- [ ] {Criterion 2}

### Modules affected
| Module | What changes | Pattern to follow | Canonical example |
|--------|-------------|-------------------|-------------------|

### Implementation steps
{Ordered list. Each step is 2-5 minutes of work.}

1. **{Step name}**
   - File: `{exact path to create or modify}`
   - Action: {create | modify lines N-M | delete | wire up in X}
   - Pattern: follow `{canonical_example_path}:{line_range}`
   - Verify: run `{exact command}` → expect `{expected output}`

2. **{Step name}**
   ...

### Dependency graph
{Which steps depend on which. Identify parallel-safe steps.}
- Step 1 → Step 2 (Step 2 uses types defined in Step 1)
- Step 3 ∥ Step 4 (independent, can run in parallel)
- Step 5 depends on Steps 3 and 4

### Files to create
| File | Purpose | Based on (template/example) |
|------|---------|----------------------------|

### Files to modify
| File | What changes | Lines affected (approx) |
|------|-------------|------------------------|

### Testing plan
- {Exact test file to create and test names}
- {Test pattern to follow with canonical test example path}
- Run: `{{test_command}}`
- Expected: all pass, including {specific new test names}

### Risks and mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| {Specific risk} | {What goes wrong} | {How to prevent or recover} |
```

---

## Phase 3: Self-review

Before presenting the plan, run through this checklist. Fix any failures
before the user sees the plan.

### Completeness
- [ ] Every acceptance criterion maps to at least one implementation step
- [ ] Every step has: file path, action, pattern reference, verification command
- [ ] Every file path has been verified with Glob/Grep (not guessed)
- [ ] Testing plan covers all new behavior and at least one regression case

### Placeholder scan

Search the plan for these banned patterns — each one is a plan failure:

| Banned phrase | What to write instead |
|--------------|----------------------|
| "TBD", "TODO", "fill in later" | The actual content, or add to Risks as an open question |
| "Add appropriate error handling" | Which error type, how to catch it, what to return |
| "Add validation" | Which fields, what constraints, what error messages |
| "Write tests for the above" | Exact test file, test names, and key assertions |
| "Similar to step N" | Repeat the full details — steps may be read out of order |
| "See docs for details" | Include the relevant details inline |
| "Handle edge cases" | List each edge case and its expected behavior |
| "As needed" / "if applicable" | Decide now whether it's needed and say so |

### Dependencies
- [ ] Steps are ordered so each step's inputs exist when it runs
- [ ] Parallel-safe steps are explicitly identified
- [ ] No circular dependencies

### Scope
- [ ] Plan solves the stated requirement — no more, no less
- [ ] No speculative features or "while we're at it" additions
- [ ] If > 5 modules touched, splitting has been considered and justified

---

## Phase 4: Save and present

1. Save the completed plan to `docs/plans/{YYYY-MM-DD}-{feature-name}.md` in
   the project. This makes it persistent across sessions and reviewable by
   teammates.
2. Present a summary to the user highlighting key design decisions and any
   remaining open questions from the Risks section.

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
- If the requirement is ambiguous after Phase 0, list what still needs clarification.
- For complex plans touching 3+ modules, consider delegating to the
  `potion-planner` agent for a focused planning session.
- Plans should be implementable by someone who only reads the plan
  and the guidelines — no assumed tribal knowledge.
- Every risk must have a mitigation. "Might be slow" is not a risk —
  "Query may exceed 500ms for tables > 1M rows; mitigate with index on
  `user_id`" is.

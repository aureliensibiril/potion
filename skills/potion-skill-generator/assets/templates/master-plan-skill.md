---
{{#unless plugin_mode}}name: potion-plan
{{/unless}}description: >
  Plans feature implementations, refactors, and architectural changes in
  {{project_name}} across multiple language stacks. Identifies which stacks are
  involved, determines execution order based on data flow, and creates
  stack-labeled implementation sections. Use when someone asks to "plan",
  "design", "break down", "spec out", "architect", or "how should I implement"
  something. It also triggers for tickets, user stories, feature requests, or
  specs that need an implementation approach. Even "what files would I need to
  change for X" or "what's the best approach for X" should activate this skill.
allowed-tools: Read, Write, Glob, Grep, AskUserQuestion, Agent
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

---

## Phase 0: Pre-planning — Gather context

Before designing anything, understand the requirement deeply. Skipping this
phase is the #1 cause of plans that miss the mark.

### 1. Classify the task type

Determine which kind of change this is — it shapes the entire planning approach:

| Type | Signals | Planning focus |
|------|---------|---------------|
| **New feature** | "add", "create", "build", "new" | Entry point, data flow, stacks involved, API contracts |
| **Refactor** | "refactor", "extract", "move", "rename", "split" | Migration path, backward compat, cross-stack contracts |
| **Bug fix** | "fix", "broken", "doesn't work", "regression" | Root cause vs. symptoms, which stack owns the bug |
| **Migration** | "upgrade", "migrate", "replace", "switch to" | Rollback strategy, incremental steps, feature parity |

### 2. Explore the codebase

Before asking questions, do your homework:

- **Read relevant code** in each potentially affected stack. Grep for related
  functionality. Understand what exists before proposing what to build.
- **Check cross-stack contracts.** Read the API endpoints, shared types, or
  data contracts between stacks that this change may affect.
- **Check recent changes.** Look at recent commits in the affected areas.
- **Identify unknowns.** Note what you couldn't determine from the code alone.

### 3. Ask targeted clarifying questions

Use `AskUserQuestion` to surface ambiguity. Only ask questions whose answers
you could NOT determine from the code. Focus on:

- **Acceptance criteria** — What does "done" look like? What behaviors are expected?
- **Scope boundaries** — What is explicitly out of scope?
- **Constraints** — Performance requirements? Backward compatibility? Deadlines?
- **Edge cases** — How should the system behave in non-happy-path scenarios?
- **Prior decisions** — Has this been attempted before? Any rejected approaches?
- **Stack preferences** — Should both stacks change, or should one adapt to the other?

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

### 2. Identify stacks involved

Which stacks are affected by this change? Read each stack's module map and
guidelines to determine whether it participates:

{{#each stacks}}
- **{{display_name}}** ({{language}}) — modules: {{modules}}
{{/each}}

### 3. Determine execution order

Which stack is upstream (provides data/API) vs downstream (consumes)?
Order implementation so dependencies are built before consumers.

| Task type | Order | Reasoning |
|-----------|-------|-----------|
| New API + frontend page | Backend → Frontend | Frontend consumes the API |
| Frontend form + backend validation | Backend → Frontend | Validation defines constraints |
| Independent changes | Parallel | No dependency |
| Shared type change | Shared → Backend → Frontend | Types flow downstream |
| Database migration + API update | Backend → Frontend | Schema change flows up |

### 4. Reference stack-specific patterns

For each affected stack, consult its patterns and conventions:

{{#each stacks}}
For {{display_name}} work: see `{{guidelines_path}}/patterns.md`
{{/each}}

### 5. Identify cross-stack integration points

- API contracts between stacks (endpoints, payloads, status codes)
- Shared types or data structures that must stay in sync
- Data flow direction — which stack owns the source of truth?

### 6. Design the approach (by task type)

#### For new features
1. Identify the entry point in each stack
2. Trace the data flow across stack boundaries
3. Define the API contract (endpoint, request/response shapes, error codes)
4. For each stack, follow the type-specific approach from its guidelines
5. Plan integration tests that verify cross-stack behavior

#### For refactors
1. Identify all files affected across stacks (Grep for usage)
2. Design the migration path — can stacks be migrated independently?
3. Define backward compatibility strategy for cross-stack contracts
4. Plan: update contract first, then consumers, then remove old contract

#### For bug fixes
1. Determine which stack owns the root cause (not just where the symptom appears)
2. Plan the minimal fix in the owning stack
3. If the fix changes a contract, plan downstream stack updates
4. Plan regression tests in the owning stack

#### For migrations
1. Define feature parity across all affected stacks
2. Plan rollback strategy for each stack independently
3. Design incremental migration: one stack at a time when possible
4. Plan for contract coexistence (old and new API versions)

### 7. Check pitfalls per stack

These are real issues found in this codebase — check each one against your plan:

{{#each pitfalls}}
- **{{description}}** ({{severity}}) — {{context}}
{{/each}}

---

## Phase 2: Produce the plan

### Step granularity

Each step must be a **single, concrete action** completable in 2-5 minutes.

**Bad step:** "Implement the backend service"
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
{2-3 sentences: what this plan achieves and why this approach}

### Acceptance criteria
- [ ] {Criterion 1 — specific, testable}
- [ ] {Criterion 2}

### Stacks involved
| Stack | Role | Why needed |
|-------|------|-----------|

### Execution order
{Which stack goes first and why — justified by data flow direction}

{{#each stacks}}
## {{display_name}} ({{language}})

### Implementation steps
{Numbered steps, each 2-5 minutes. Reference real files and patterns.}

1. **{Step name}**
   - File: `{exact path}`
   - Action: {create | modify lines N-M | wire up in X}
   - Pattern: follow `{canonical_example}:{line_range}`
   - Verify: run `{command}` → expect `{output}`

### Files to create/modify
| File | Action | Based on |
|------|--------|----------|

### Testing
- {Exact test file and test names}
- Run: `{{stack_test_command}}`
{{/each}}

### Cross-stack integration points
| Contract | Upstream | Downstream | Shape |
|----------|----------|------------|-------|
| {Endpoint/type} | {Stack} | {Stack} | {Request/response/type definition} |

### Dependency graph
- {Stack A} Step 1 → {Stack A} Step 2
- {Stack A} completes → {Stack B} begins (needs API from A)
- {Stack B} Step 2 ∥ {Stack B} Step 3 (parallel-safe)

### Risks and mitigations
| Risk | Stack | Impact | Mitigation |
|------|-------|--------|------------|
| {Specific risk} | {Which stack} | {What goes wrong} | {How to prevent/recover} |
```

---

## Phase 3: Self-review

Before presenting the plan, run through this checklist. Fix any failures
before the user sees the plan.

### Completeness
- [ ] Every acceptance criterion maps to at least one implementation step
- [ ] Every step has: file path, action, pattern reference, verification command
- [ ] Every file path has been verified with Glob/Grep (not guessed)
- [ ] Testing plan covers all new behavior and cross-stack integration

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

### Cross-stack coherence
- [ ] API contracts match between upstream and downstream steps
- [ ] Shared types are defined before any stack references them
- [ ] Execution order is justified by data flow direction
- [ ] No orphaned references (e.g., frontend calling an API not in the plan)

### Dependencies
- [ ] Steps are ordered so each step's inputs exist when it runs
- [ ] Parallel-safe steps (within and across stacks) are explicitly identified
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
2. Present a summary to the user highlighting key design decisions, execution
   order rationale, and any remaining open questions from the Risks section.

## Key patterns quick reference

{{patterns_summary}}

## Stack reference

{{#each stacks}}
### {{display_name}} ({{language}})
- Modules: {{modules}}
- Patterns: `{{guidelines_path}}/patterns.md`
- Testing: `{{guidelines_path}}/testing.md`
- Canonical example: `{{canonical_file}}`
{{/each}}

## Canonical examples

When suggesting patterns, point to these real files:

{{#each canonical_examples}}
- `{{file}}` — {{why}}
{{/each}}

## Rules

- Never guess file paths. Glob/Grep to verify they exist.
- Each stack section references that stack's actual patterns from the guidelines.
- Cross-stack integration points must be explicit (API shape, type contract).
- Execution order must be justified by data flow direction.
- If the requirement is ambiguous after Phase 0, list what still needs clarification.
- For complex plans touching 3+ modules within a single stack, consider
  delegating to the `potion-planner` agent for a focused planning session.
- Plans should be implementable by someone who only reads the plan
  and the guidelines — no assumed tribal knowledge.
- Every risk must have a mitigation. "API might be slow" is not a risk —
  "Query may exceed 500ms for tables > 1M rows; mitigate with index on
  `user_id`" is.

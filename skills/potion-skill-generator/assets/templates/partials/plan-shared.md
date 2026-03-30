# Shared Planning Sections

Shared by `plan-skill.md` and `master-plan-skill.md`. Referenced via
`{{> partials/plan-shared#section-id}}` — the skill-writer inlines each
section when generating the final skill.

---

## file-structure-mapping

### File structure mapping

Before defining steps, map every file that will be created or modified.
This locks in decomposition decisions before writing steps.

For each file:
- **Path** — verified with Glob (never guessed)
- **Action** — create, modify, or delete
- **Responsibility** — one clear purpose
- **Based on** — canonical example it follows

Follow codebase conventions for file organization. Files that change
together should live together. Split by responsibility, not by layer.

---

## step-granularity

### Step granularity

Each step must be a **single, concrete action** completable in 2-5 minutes.

**Bad step:** "Implement the service layer"
**Good step:** "Create `src/billing/services/invoice.service.ts` with the
`createInvoice` method following the pattern in
`src/orders/services/order.service.ts:23-45`"

Each step must include:
- **Exact file path** (verified with Glob/Grep — never guessed)
- **What to do** (create, modify specific lines, delete, wire up)
- **Code** — actual code or detailed pseudo-code for the change. If the
  step creates a file, show the file contents. If it modifies a file, show
  the before/after or the new code to insert. Never write "follow pattern X"
  without also showing what the resulting code looks like.
- **Verification** (exact command to run and expected output)

---

## verify-save-draft

### 1. Save as draft

Save to `docs/plans/{YYYY-MM-DD}-{feature-name}.md` (referred to as
`{plan-file}` below). This makes the plan available for tool-assisted
verification in the next steps.

---

## verify-mechanical

### 2. Mechanical checks

Run these tool-assisted checks on the saved draft. Fix any failures
before proceeding to cognitive review.

**Placeholder scan** — Grep the plan for banned phrases:
```
Grep({
  pattern: "TBD|TODO|fill in later|add appropriate|add validation|write tests|similar to step|see docs|handle edge cases|as needed|if applicable",
  path: "{plan-file}",
  "-i": true,
  output_mode: "content"
})
```
Any matches are plan failures. Replace each with concrete content:

| Banned phrase | What to write instead |
|--------------|----------------------|
| "TBD", "TODO", "fill in later" | The actual content, or add to Risks as an open question |
| "Add appropriate error handling" | Which error type, how to catch it, what to return |
| "Add validation" | Which fields, what constraints, what error messages |
| "Write tests for the above" | Exact test file, test names, and key assertions |
| "Similar to step N" | Repeat the full details — steps may be read out of order |
| "Handle edge cases" | List each edge case and its expected behavior |

**File path verification** — for every file path mentioned in the plan,
verify it exists:
```
Glob({ pattern: "{exact_path}" })
```
Remove or correct any path that doesn't resolve.

**Criteria coverage** — read the acceptance criteria and verify each one
maps to at least one implementation step. List any uncovered criteria and
add steps for them.

---

## verify-cognitive

### 3. Cognitive review

These checks require judgment — re-read the plan and verify:

- [ ] **Type consistency** — function names, type names, and method
      signatures used in later steps match earlier definitions (e.g.,
      `createInvoice` in step 3 is not called `buildInvoice` in step 7).
      Import paths reference files actually created in prior steps.
- [ ] **Dependencies** — steps are ordered so each step's inputs exist
      when it runs. Parallel-safe steps are explicitly identified.
      No circular dependencies.
- [ ] **Scope** — plan solves the stated requirement, no more, no less.
      No speculative features or "while we're at it" additions.
      If > 5 modules touched, splitting has been considered and justified.
- [ ] **Step completeness** — every step has: file path, action, code
      block, verification command. File structure table accounts for every
      file mentioned in steps. Testing plan covers all new behavior.

---

## verify-parallel-agents

### 4. Parallel review agents (non-trivial plans only)

Dispatch parallel review agents if the plan meets **any** of these:
- Touches 3+ modules
- Has 10+ implementation steps
- Involves cross-cutting architectural changes

Launch 3 agents in parallel, each reading the saved plan file. Each agent
rates findings on a 0-100 confidence scale and reports only issues >= 80.

**Agent 1 — Completeness:**
> Review the plan at `{plan-file}` for gaps.
> Check: does every acceptance criterion have matching steps? Are there
> untested behaviors? Missing error handling paths? Edge cases not
> addressed? Read the project guidelines at `{guidelines_path}` for
> context on what patterns are expected.
> Rate each finding 0-100 confidence. Report only >= 80.

**Agent 2 — Consistency:**
> Review the plan at `{plan-file}` for internal consistency.
> Check: do names, types, and signatures match across steps? Are
> dependencies ordered correctly? Do import paths reference files created
> in prior steps? Does the dependency graph have gaps?
> Rate each finding 0-100 confidence. Report only >= 80.

**Agent 3 — Feasibility:**
> Review the plan at `{plan-file}` against the actual codebase.
> Check: do the referenced canonical examples exist and support the plan?
> Are verification commands realistic? Is step granularity appropriate?
> Read the cited files and verify the patterns match.
> Rate each finding 0-100 confidence. Report only >= 80.

Skip this step for trivial plans (< 3 modules, < 10 steps, no
architectural changes).

---

## verify-fix

### 5. Fix and re-save

Fix all issues found in steps 2-4. Re-save the plan to
`{plan-file}`.

---

## present-and-handoff

1. **Track** — call the TodoWrite tool with one entry per implementation
   step so progress is visible in Claude Code's native task list:
   ```json
   {
     "todos": [
       { "id": "{feature-name}-1", "task": "Foundation — Step 1: {description}", "status": "pending" },
       { "id": "{feature-name}-2", "task": "Foundation — Step 2: {description}", "status": "pending" }
     ]
   }
   ```
2. **Present** a summary highlighting key design decisions and any
   remaining open questions from the Risks section.
3. **Hand off** — offer to start implementation:

   > Plan saved to `{plan-file}` with {N} steps tracked.
   >
   > Ready to implement? Use `/potion-implement` to start execution.

---

---
name: potion-skill-generator
description: "Analyzes any codebase and generates a complete, tailored skill pack — coding skills, review agents, Q&A agents, and a shared guidelines document, all grounded in the actual architecture and patterns of the target project. Use when the user asks to generate skills, create agents, make a skill pack, analyze a repo, package codebase knowledge, or create dev workflows. Also triggers on: refresh skills, update the skill pack, re-analyze this codebase."
effort: high
argument-hint: "[project-root-path]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion
---

# Codebase Skill Generator

Analyze a codebase and produce a ready-to-use skill pack that any team member
can install. The pack includes skills for asking questions, implementing features,
and reviewing code — all grounded in the project's real patterns.

## When to use this skill

- User wants to generate skills/agents tailored to a specific codebase
- User wants to onboard their team onto a project via Claude Code
- User wants a guidelines document that captures codebase knowledge
- User wants to distribute project conventions as reusable agents

## What gets generated

| Output                  | Purpose                                          |
|-------------------------|--------------------------------------------------|
| `guidelines.md` (or `guidelines/`) | Shared codebase knowledge: architecture, patterns, conventions |
| `skills/ask/SKILL.md`   | Q&A skill — answers questions about the codebase |
| `skills/plan/SKILL.md`  | Planning skill — designs implementation approaches before coding |
| `skills/implement/SKILL.md` | Coding skill — implements features following project patterns |
| `skills/review/SKILL.md`    | Review skill — reviews code against project standards |
| `agents/explorer.md`    | Read-only agent for codebase navigation          |
| `agents/planner.md`     | Planning agent for complex feature design        |
| `agents/implementer.md` | Write agent scoped to project conventions        |
| `agents/reviewer.md`    | Review agent with checklist from actual patterns |
| `agents/reviewers/`     | Specialized reviewer sub-agents (optional, for larger projects) |
| `test-prompts.md`       | Sample prompts for evaluating generated skills    |

## Pipeline overview

The generation runs in 5 phases. Each phase saves its output to a workspace
so the user can inspect, correct, and resume at any point.

```
Phase 1: DISCOVER     → module-mapper agent     → module-map.json
Phase 2: EXPLORE      → module-explorer agents   → per-module profiles
Phase 3: SYNTHESIZE   → pattern-synthesizer agent → guidelines.md
Phase 4: GENERATE     → skill-writer agent        → final skill pack
Phase 5: EVALUATE     → evaluation agents         → test results + iteration
```

**Load references on demand:** When you reach a phase, read only the relevant
`§ Phase N` section from `references/phases.md`. Read `references/output-schemas.md`
only when you need to check a schema. Do not read the full files upfront.

## Quick context

!`ls -la | head -20`
!`git log --oneline -5 2>/dev/null || echo "Not a git repo"`
!`cat README.md 2>/dev/null | head -5 || echo "No README"`

## How to run

### Setup

1. Get the project root from the user (default: current directory).
   Use $ARGUMENTS if provided (Claude Code injects the skill's argument
   string, e.g. `/potion-skill-generator /path/to/project`), otherwise
   the current working directory.
2. Create workspace: `{project_root}/.skill-gen-workspace/`
3. Initialize `state.json` in the workspace following the schema in
   `references/output-schemas.md § State`:
   ```json
   {
     "started_at": "<ISO 8601>",
     "updated_at": "<ISO 8601>",
     "project_root": "<absolute path>",
     "phases": {
       "1": { "status": "pending", "started_at": null, "completed_at": null, "output_file": null, "error": null },
       "2": { "status": "pending", "started_at": null, "completed_at": null, "output_file": null, "error": null, "module_statuses": {} },
       "3": { "status": "pending", "started_at": null, "completed_at": null, "output_file": null, "error": null },
       "4": { "status": "pending", "started_at": null, "completed_at": null, "output_file": null, "error": null },
       "5": { "status": "pending", "started_at": null, "completed_at": null, "output_file": null, "error": null }
     },
     "user_choices": {
       "selected_outputs": [],
       "skip_evaluation": false,
       "delivery_mode": "standalone",
       "guidelines_mode": null,
       "stack_mode": null,
       "stacks": []
     }
   }
   ```
4. Check for existing workspace — if `state.json` exists, read it and offer to
   resume from the first non-completed phase.

### Phase 1: Module Discovery

Delegate to the **module-mapper** agent. It scans the codebase structure and
returns a JSON module map. Read `references/phases.md § Phase 1` for the full
procedure including the user validation step.

Update `state.json`: set `phases.1.status` to `"in_progress"` and `phases.1.started_at`
at start. Set `"completed"` and `phases.1.completed_at` on success, or `"failed"` with
`phases.1.error` on failure. Always update `updated_at`.

### Stack Detection (between Phase 1 and Phase 2)

After the user validates the module map, determine `stack_mode`:

1. **Group modules by language.** Read each module's `language` field from the
   validated module map. Group modules into language clusters.

2. **Apply threshold.** A language group qualifies as a "stack" if it has
   ≥2 modules OR ≥20 source files across its modules. Groups below threshold
   are tagged as "minor" and folded into shared conventions.

3. **Determine mode:**
   - 1 qualifying stack → `stack_mode: "single"` (current behavior)
   - 2+ qualifying stacks → `stack_mode: "multi"`

4. **Auto-generate stack names** from `{language}-{role}`:
   - Look at module paths to infer role: paths containing `backend`, `server`,
     `api`, `worker` → role is `backend`
   - Paths containing `frontend`, `web`, `app`, `client`, `ui` → role is `frontend`
   - Paths containing `infra`, `deploy`, `terraform` → role is `infra`
   - If role is ambiguous, use just the language name
   - Examples: `python-backend`, `typescript-frontend`, `go-infra`

5. **Detect frameworks** per stack by checking dependency files:
   - Python: read `pyproject.toml` or `requirements.txt` for FastAPI, Django, Flask, Dagster, etc.
   - TypeScript: read `package.json` for Next.js, React, Vue, Angular, Express, etc.
   - Go: read `go.mod` for framework imports
   - Store in `stacks[].frameworks`

6. **Update state.json** with `stack_mode` and `stacks` array.

7. **Present to user** as part of the Phase 1 → 2 transition (after the module
   map gate, before launching Phase 2 agents):
   ```
   Stack analysis:
   - python-backend (FastAPI, Dagster): backend/webapp, backend/automation, backend/sidekiq
   - typescript-frontend (Next.js, React): frontend/web, frontend/admin, frontend/auth

   Stack mode: multi (2 stacks detected)
   ```

### Phase 2: Module Exploration + Documentation Discovery + PR Review Mining

Build the exploration list from Phase 1: for modules with `submodules`, explore
each submodule independently (not the parent). For modules without submodules,
explore the module itself.

**Before spawning agents**, detect if PR review mining is possible:

1. Run: `gh repo view --json nameWithOwner 2>/dev/null`
   → If success: platform = `"github"`
2. Else run: `glab repo view 2>/dev/null`
   → If success: platform = `"gitlab"`
3. Else: PR review mining unavailable, will skip the agent.

Spawn agents in two independent tracks that run concurrently:

**Track A — Module exploration (batched):**
Launch module-explorer agents in batches. When a batch completes,
immediately launch the next batch — do NOT wait for Track B agents.
Include the doc-scanner and git-workflow-scanner in the first batch.

**Track B — PR review mining (long-running):**
If platform was detected, spawn the pr-review-miner agent alongside
Track A's first batch. It runs independently and may take longer than
all explorer batches combined. That's fine.

Output files:
- Module explorers: `{workspace}/phase2-profiles/{name}.json`
- Doc-scanner: `{workspace}/phase2-docs.json`
- Git-workflow-scanner: `{workspace}/phase2-git-workflow.json`
- PR-review-miner: `{workspace}/phase2-reviews.json`

Read `references/phases.md § Phase 2` for batching rules and how to present
findings.

**At the end:** wait for BOTH tracks to complete before proceeding to the
user gate. All explorer batches must finish AND the pr-review-miner must
finish. If any agent times out, re-run it before moving on.

Update `state.json`: set `phases.2.status` to `"in_progress"` at start. Track each
unit in `phases.2.module_statuses` using `{parent}/{submodule}` keys for submodules,
`"doc_scanner"` for the doc-scanner, `"git_workflow_scanner"` for the git workflow
scanner, and `"pr_review_miner"` for the PR review miner (set to `"skipped"` if no
platform was detected). Set phase status to `"completed"`
when all units succeed, or `"failed"` with error if any fail — but keep successful
profiles so they can be reused on retry. Always update `updated_at`.

### Phase 3: Pattern Synthesis

First, select the guidelines mode. Count the total exploration units (modules
without submodules + individual submodules). If >= 8 units, use `"multi"` mode;
otherwise `"single"`. Store in `state.json.user_choices.guidelines_mode`.

Delegate to the **pattern-synthesizer** agent with all module profiles,
the documentation profile (`phase2-docs.json`) from the doc-scanner,
the git workflow profile (`phase2-git-workflow.json`) from the git-workflow-scanner,
AND the review patterns profile (`phase2-reviews.json`) from the pr-review-miner
(if it exists).

- **Single mode:** produces `phase3-guidelines.md`
- **Multi mode:** produces `phase3-guidelines/` directory with topic files

Pass `guidelines_mode` to the synthesizer. Read `references/phases.md § Phase 3`
for the synthesis process and quality checks.

Update `state.json`: set `phases.3.status` to `"in_progress"` at start, `"completed"`
on success, or `"failed"` with error. Always update `updated_at`.

### Phase 4: Skill Pack Generation

Ask the user which outputs to generate (default: all). Delegate to the
**skill-writer** agent. Read `references/phases.md § Phase 4` for generation
details.

Update `state.json`: set `phases.4.status` to `"in_progress"` at start, `"completed"`
on success, or `"failed"` with error. Always update `updated_at`.

### Phase 5: Evaluation

Before delivering, test the generated skills. This step is optional but strongly
recommended. Ask the user if they want to run the evaluation or skip it.

1. Build eval plans (`evals.json`) with assertions for each skill/agent.
2. Run with/without-skill comparison: spawn agents WITH and WITHOUT the skill
   for each eval prompt. Compare output quality.
3. Run description trigger tests: verify skills activate for intended prompts
   and don't activate for unrelated ones.
4. Grade responses against assertions. Iterate on failures (up to 3 rounds).
5. Save results to `phase5-workspace/` and `phase5-evaluation.json`.

Read `references/phases.md § Phase 5` for the full evaluation procedure.

Update `state.json`: set `phases.5.status` to `"in_progress"` at start, `"completed"`
on success, `"skipped"` if the user opts out, or `"failed"` with error. Always
update `updated_at`.

### Delivery

Read `state.json.user_choices.delivery_mode` to determine the delivery method.

#### If delivery_mode is "standalone" (default)

Standalone mode places skills, agents, and guidelines directly in `.claude/`
where Claude Code auto-discovers them. Skill names are prefixed with `potion-`
to avoid conflicts (e.g., `/potion-ask`, `/potion-review`).

Before installing, check for conflicts with existing files at the target paths.

1. **Scan target paths** for existing files:
   - `{project_root}/.claude/skills/potion-*`
   - `{project_root}/.claude/agents/potion-*`
   - `{project_root}/.claude/guidelines/` or `{project_root}/.claude/guidelines.md`

2. **If conflicts found**, warn the user and offer options:
   - **Backup + install:** Move existing files to `{project_root}/.claude/backup-{timestamp}/` then install
   - **Overwrite:** Replace existing files without backup
   - **Merge** (for `guidelines.md` only): Attempt to merge new guidelines into existing, preserving user edits
   - **Cancel:** Abort delivery so the user can handle it manually

3. **Install the pack:**
   ```bash
   mkdir -p {project_root}/.claude/skills {project_root}/.claude/agents
   cp -r {workspace}/phase4-output/skills/potion-ask/ {project_root}/.claude/skills/potion-ask/
   cp -r {workspace}/phase4-output/skills/potion-plan/ {project_root}/.claude/skills/potion-plan/
   cp -r {workspace}/phase4-output/skills/potion-implement/ {project_root}/.claude/skills/potion-implement/
   cp -r {workspace}/phase4-output/skills/potion-review/ {project_root}/.claude/skills/potion-review/
   cp -r {workspace}/phase4-output/agents/ {project_root}/.claude/agents/
   ```

   For guidelines, copy depending on mode:
   ```bash
   # Single-file mode:
   cp {workspace}/phase4-output/guidelines.md {project_root}/.claude/guidelines.md
   # Multi-file mode:
   cp -r {workspace}/phase4-output/guidelines/ {project_root}/.claude/guidelines/
   ```

4. **Update the project's CLAUDE.md** to reference the generated skills.
   Read `references/phases.md § Delivery` for the CLAUDE.md update procedure.

4. **Show activation instructions:**
   ```
   Plugin installed at {project_root}/.claude/plugins/potion/

   Skills available as:
     /potion:ask       — Ask questions about this codebase
     /potion:plan      — Plan features before implementing
     /potion:implement — Implement following project patterns
     /potion:review    — Review code against project standards
   ```

#### If delivery_mode is "review-only"

Display all generated files for review. Do not install or copy anything.

## Workspace layout

```
.skill-gen-workspace/
├── state.json
├── phase1-module-map.json
├── phase2-profiles/
│   ├── frontend.json                       # top-level module profiles
│   ├── backend-billing.json                # submodule profiles: {parent}-{sub}.json
│   ├── backend-card-market.json
│   └── ...
├── phase2-docs.json                        # documentation profile from doc-scanner
├── phase2-git-workflow.json                # git workflow profile from git-workflow-scanner
├── phase2-reviews.json                     # review patterns profile from pr-review-miner (optional)
├── phase3-guidelines.md                    # single-file mode
├── phase3-guidelines/                      # multi-file mode (alternative)
│   ├── index.md
│   ├── architecture.md
│   ├── patterns.md
│   ├── conventions.md
│   ├── testing.md
│   ├── pitfalls.md
│   └── module-notes/
├── phase4-output/                          # standalone mode layout (default):
│   ├── guidelines.md (or guidelines/)
│   ├── skills/{potion-ask,potion-plan,potion-implement,potion-review}/SKILL.md
│   ├── agents/{explorer,planner,implementer,reviewer}.md
│   ├── test-prompts.md
│   ├── manifest.json
│   └── potion/                              # plugin mode layout (alternative):
│       ├── .claude-plugin/plugin.json
│       ├── skills/{ask,plan,implement,review}/SKILL.md
│       ├── agents/{explorer,planner,implementer,reviewer}.md
│       ├── guidelines.md
│       ├── test-prompts.md
│       └── README.md
├── phase5-workspace/
│   ├── evals/{skill}-evals.json
│   └── iteration-{N}/{skill}/eval-{id}/
│       ├── with_skill/output.md
│       └── without_skill/output.md
└── phase5-evaluation.json
```

## Handling user interaction

Follow the doc-coauthoring pattern: at each phase boundary, present findings
and ask for validation before proceeding. The user knows their codebase better
than the agents — their corrections are the most valuable input.

### Confidence-based gates

Apply confidence per-finding, not per-phase. A phase can have high-confidence
modules that get brief treatment and low-confidence modules that get detailed
review.

| Confidence | Criteria | Gate depth |
|-----------|---------|------------|
| High | Standard patterns, clear boundaries, strong documentation | Brief summary, proceed unless objections |
| Medium | Some ambiguity, mixed patterns, sparse docs | Present findings with questions, wait for response |
| Low | Unusual architecture, conflicting patterns, no docs | Detailed presentation, explicit approval required |

### Gate prompts

Use `AskUserQuestion` at every gate to present structured choices. Always show
the relevant summary (table, list, etc.) BEFORE calling `AskUserQuestion`.

**Phase 1 → 2 gate:**
```
AskUserQuestion({
  questions: [{
    question: "Does this module breakdown look right?",
    header: "Modules",
    multiSelect: false,
    options: [
      { label: "Looks good", description: "Proceed to Phase 2 — explore each module in depth" },
      { label: "Needs changes", description: "I'll describe what to split, merge, or rename" },
      { label: "Re-scan", description: "Run Phase 1 again with different parameters" }
    ]
  }]
})
```

**Phase 2 → 3 gate:**
```
AskUserQuestion({
  questions: [{
    question: "Anything to correct in the exploration findings?",
    header: "Patterns",
    multiSelect: false,
    options: [
      { label: "Looks good", description: "Proceed to synthesize guidelines from these findings" },
      { label: "Needs corrections", description: "I'll point out what's wrong or missing" },
      { label: "Re-explore modules", description: "Re-run specific module explorations" }
    ]
  }]
})
```

**Phase 3 → 4 gate:**
```
AskUserQuestion({
  questions: [{
    question: "How do the guidelines look?",
    header: "Guidelines",
    multiSelect: false,
    options: [
      { label: "Looks good", description: "Proceed to generate the skill pack" },
      { label: "Needs edits", description: "I'll point out what to change" },
      { label: "Regenerate", description: "Re-run synthesis with different focus" }
    ]
  }]
})
```

**Phase 4 → 5 gate:**
```
AskUserQuestion({
  questions: [{
    question: "How would you like to proceed with the skill pack?",
    header: "Delivery",
    multiSelect: false,
    options: [
      { label: "Run evaluation (Recommended)", description: "Test skills with realistic prompts before installing" },
      { label: "Install to .claude/", description: "Auto-discovered standalone skills — /potion-ask, /potion-review, etc." },
      { label: "Package as plugin", description: "Distributable plugin for sharing via marketplace — /potion:ask, /potion:review" },
      { label: "Review files first", description: "Show me each generated file before deciding" }
    ]
  }]
})
```

**Phase 5 → delivery:**
```
AskUserQuestion({
  questions: [{
    question: "Evaluation complete. Ready to deliver?",
    header: "Deliver",
    multiSelect: false,
    options: [
      { label: "Install", description: "Install the skill pack to the project" },
      { label: "Iterate", description: "Fix issues and re-run failed evaluations" },
      { label: "Review first", description: "Show me the evaluation details before installing" }
    ]
  }]
})
```

If the user says "just do it" or wants to skip validation, that's fine — proceed
without gates. Adapt to their pace.

## Refresh mode

When the user already has a generated skill pack and wants to update it after
codebase changes, use refresh mode instead of regenerating from scratch.

**Triggers:** "refresh skills", "update the skill pack", "re-analyze this codebase",
or when an existing workspace with completed phases is detected.

**How it works:**
1. Detect what changed (git diff or directory comparison against module map)
2. Re-explore only changed modules (selective Phase 2)
3. Merge new findings into existing guidelines, preserving `<!-- user-edited -->` sections
4. Regenerate affected skills, showing diffs instead of full documents
5. Run evaluation on changed skills only

Read `references/phases.md § Refresh Mode` for the full procedure.

## Scaling rules

Adapt strategy based on codebase size:

| Codebase size | Modules | Phase 2 strategy | Notes |
|--------------|---------|-------------------|-------|
| Small (<100 files) | 1-3 | Sequential, all at once | Full exploration, no batching needed |
| Medium (100-500) | 3-8 | Parallel, all at once | Launch all explorers in the same turn |
| Large (500-2000) | 8-15 | Batch in groups of 3-5 | Interleave batches with early synthesis |
| Very large (2000+) | 15-30 | Batch in groups of 5-8 | DDD monorepos can easily reach 20-30 modules; scan 6-8 levels deep |
| Massive (5000+) | 30+ | Top 30 by importance, skim rest | Ask user to prioritize; batch in groups of 8-10 |

Additional tips:
- Existing CLAUDE.md or ARCHITECTURE.md: read first, shortcut discovery
- Monorepo: treat each workspace member as a separate module
- If agent times out: reduce scope, ask user to identify top directories

## References

- **[`references/phases.md`](references/phases.md)** — Detailed phase-by-phase
  instructions, user interaction scripts, error handling
- **[`references/output-schemas.md`](references/output-schemas.md)** — JSON
  contracts for all agent inputs/outputs
- **[`assets/templates/`](assets/templates/)** — Starter templates for generated
  skills and agents
- **[`scripts/validate_output.py`](scripts/validate_output.py)** — Validates
  outputs between phases

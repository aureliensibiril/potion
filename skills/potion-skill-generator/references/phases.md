# Phase-by-Phase Instructions

Read this file when you need detailed guidance on a specific phase.
Jump to the relevant section — don't read the whole thing upfront.

## Contents

- [Phase 1: Module Discovery](#-phase-1-module-discovery)
- [Phase 2: Module Exploration](#-phase-2-module-exploration)
- [Phase 3: Pattern Synthesis](#-phase-3-pattern-synthesis)
- [Phase 4: Skill Pack Generation](#-phase-4-skill-pack-generation)
- [Phase 5: Evaluation](#-phase-5-evaluation)
- [Recovery and Resumption](#recovery-and-resumption)
- [Refresh Mode](#refresh-mode)

---

## § Phase 1: Module Discovery

### Goal

Produce a module map — a structured inventory of the codebase's major
components, their boundaries, entry points, and relationships.

### Procedure

1. **Quick structural scan** (do this yourself before delegating):
   - Read the top-level directory structure (2 levels deep)
   - Check for monorepo markers (workspaces in package.json, Cargo.toml
     members, lerna.json, nx.json, turborepo.json)
   - Read README.md, ARCHITECTURE.md, CONTRIBUTING.md if they exist
   - Check for .claude/CLAUDE.md for existing project context
   - Note the primary language stack and build system

2. **Delegate to module-mapper agent:**

   ```
   Use the module-mapper agent to analyze the codebase at {project_root}.

   Here is what I found from the initial scan:
   {your_initial_findings}

   Return the module map as JSON following the schema in
   references/output-schemas.md § Module Map.
   Save the result to {workspace}/phase1-module-map.json
   ```

3. **Validate output:**
   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/validate_output.py \
     --phase 1 --workspace {workspace}
   ```

4. **User gate — present the module map:**

   Show a readable summary (not raw JSON) with a table and dependency list,
   then use `AskUserQuestion` for structured feedback:

   ```
   I found {N} modules in your codebase:

   | Module | Path | Purpose | Size |
   |--------|------|---------|------|
   | auth   | src/auth/ | Authentication and session management | medium |
   | ...    | ...  | ...     | ...  |

   Dependencies: auth → core, billing → core, billing → auth
   ```

   Then call:
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

   Apply corrections if the user selects "Needs changes".

### Error handling

- If the module-mapper returns empty modules: the codebase might be flat
  (no clear module boundaries). Ask the user how they think about the
  codebase's organization.
- If the agent times out: the codebase is probably very large. Ask the
  user to identify the top 5-10 most important directories.

---

## § Phase 2: Module Exploration

### Goal

For each module (and submodule), produce a detailed profile covering its
purpose, patterns, dependencies, and conventions. Simultaneously discover
all existing documentation in the codebase and mine PR review comments
for tribal knowledge.

### Procedure

1. **Read the validated module map** from Phase 1. Build the exploration list:
   - For modules WITHOUT submodules: add the module itself
   - For modules WITH submodules: add each submodule instead of the parent
     (the parent's patterns emerge from its submodules)
   - Skip config/tooling modules unless they have significant logic

2. **Spawn module-explorer agents AND the doc-scanner in parallel.**

   For each exploration unit (module or submodule):

   ```
   Use the module-explorer agent to analyze the module "{name}"
   located at {path}.

   Context from the module map:
   {module_or_submodule_entry}

   Return a module profile as JSON following the schema in
   references/output-schemas.md § Module Profile.
   Save to {workspace}/phase2-profiles/{profile_name}.json
   ```

   Profile naming:
   - Top-level modules: `{module_name}.json` (e.g., `frontend.json`)
   - Submodules: `{parent}-{submodule}.json` (e.g., `backend-billing.json`)

   **Simultaneously**, spawn the doc-scanner:

   ```
   Use the doc-scanner agent to scan the codebase at {project_root}
   for all existing documentation, coding standards, and developer
   instructions.

   Return a documentation profile as JSON following the schema in
   references/output-schemas.md § Documentation Profile.
   Save to {workspace}/phase2-docs.json
   ```

   **If PR review mining is available** (platform detected in pre-check),
   also spawn the pr-review-miner:

   ```
   Use the pr-review-miner agent to analyze merged PR review comments
   for {project_root}.

   Platform: {github|gitlab}
   Repository: {owner/repo from detection step}
   Module map: {workspace}/phase1-module-map.json (for correlating comments to modules)

   Return a review patterns profile as JSON following the schema in
   references/output-schemas.md § Review Patterns Profile.
   Save to {workspace}/phase2-reviews.json
   ```

   Launch ALL agents (explorers + doc-scanner + pr-review-miner) in the same turn.

3. **Batching for large codebases:** Count each exploration unit individually
   (a module with 3 submodules = 3 units). If more than 8 units, batch
   explorers in groups of 3-5. The doc-scanner and pr-review-miner always
   run with the first batch.

4. **As explorers complete**, collect profiles and watch for:
   - Conflicting pattern descriptions (sign of codebase inconsistency)
   - Modules referencing each other heavily (important for guidelines)
   - Shared utilities or common patterns
   - Modules with no tests (flag for the user)

5. **Validate all profiles:**
   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/validate_output.py \
     --phase 2 --workspace {workspace}
   ```

6. **User gate — present findings summary:**

   Show the summary first:
   ```
   Exploration complete. Here's what I found across {N} modules:

   **Dominant patterns:**
   - All modules use repository pattern for data access
   - Jest + Testing Library for all tests
   - Zod for validation everywhere

   **Inconsistencies:**
   - auth uses callbacks, payments uses async/await
   - Some modules define errors locally, others use shared types

   **Notable findings:**
   - No test coverage in the billing module
   - The core module is imported by every other module

   **From PR reviews ({N} PRs analyzed, {M} human comments):** (if available)
   - Top enforced conventions: early returns preferred, error types required
   - Common mistakes caught in review: missing input validation, N+1 queries
   - Review-only knowledge: "always add migration tests for schema changes"
   ```

   Then call:
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

### Per-module status tracking

Track each exploration unit's status in `state.json` at
`phases.2.module_statuses`. For submodules, use `{parent}/{submodule}` keys:

```json
"module_statuses": {
  "frontend": "completed",
  "shared": "completed",
  "backend/billing": "completed",
  "backend/card-market": "in_progress",
  "backend/sync-engine": "pending",
  "doc_scanner": "completed",
  "pr_review_miner": "completed"
}
```

On retry, only re-run failed units — reuse completed profiles as-is.
The doc-scanner is tracked as `"doc_scanner"` in `module_statuses`.
The pr-review-miner is tracked as `"pr_review_miner"` — set to `"skipped"`
if no platform was detected during the pre-check.

### Error handling

- Explorer returns incomplete profile: re-run that specific explorer with
  more targeted instructions (e.g., "focus on the testing patterns, I need
  more detail there").
- Explorer can't determine patterns: the module may be too small or too
  generic. Note "insufficient data" and move on — the user can fill gaps.
- PR review miner: `gh`/`glab` CLI not installed → warn with install
  instructions, skip agent. Not authenticated → warn with auth instructions
  (`gh auth login` / `glab auth login`), skip agent. No merged PRs or no
  review comments → agent completes with empty patterns, notes in `coverage_gaps`.

---

## § Phase 3: Pattern Synthesis

### Goal

Distill module profiles into a coherent `guidelines.md` that captures the
codebase's architecture, conventions, patterns, and anti-patterns.

### Procedure

1. **Gather all inputs:**
   - Module map from Phase 1
   - All module profiles from Phase 2 (including submodule profiles)
   - Documentation profile from Phase 2 (`phase2-docs.json`, if it exists)
   - Review patterns profile from Phase 2 (`phase2-reviews.json`, if it exists)
   - User corrections from both gates

2. **Delegate to pattern-synthesizer agent:**

   ```
   Use the pattern-synthesizer agent.

   Module map: {workspace}/phase1-module-map.json
   Module profiles: {workspace}/phase2-profiles/
   Documentation profile: {workspace}/phase2-docs.json (if available)
   Review patterns profile: {workspace}/phase2-reviews.json (if available)

   The documentation profile contains existing coding standards, AI
   instructions (Cursor rules, CLAUDE.md), architecture decisions, and
   config-enforced rules. Use it to reconcile discovered patterns with
   documented intent. See Step 2.5 in the synthesizer instructions.

   The review patterns profile contains conventions enforced during PR
   review, common mistakes caught by reviewers, and tribal knowledge.
   Use it to reconcile code patterns with team review culture.
   See Step 2.7 in the synthesizer instructions.

   Guidelines mode: {guidelines_mode from state.json}

   If single mode:
     Generate one guidelines document following the template in
     references/output-schemas.md § Guidelines Template (single-file).
     Save to {workspace}/phase3-guidelines.md

   If multi mode:
     Generate topic files following the structure in
     references/output-schemas.md § Guidelines Template (multi-file).
     Save to {workspace}/phase3-guidelines/ (directory)
   ```

3. **Review the output yourself.** Before showing the user, verify:
   - Every code example references a real file path from the profiles
   - Patterns are labeled (universal / dominant / module-specific)
   - Canonical examples are diverse (not all from one module)
   - The document would be useful to someone who's never seen the codebase

4. **Validate:**
   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/validate_output.py \
     --phase 3 --workspace {workspace}
   ```

5. **User gate — present guidelines for review:**

   The guidelines are the foundation for Phase 4. Getting them right matters
   more than speed. Show the full guidelines.md content (or link to the file),
   highlighting key sections to review: Core Patterns, Canonical Examples,
   Known Pitfalls, Open Questions.

   Then call:
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

   Apply corrections. If the user answers open questions, fold those
   answers into the guidelines.

### Quality standards (from skill-creator patterns)

The guidelines document needs to pass this bar:
- **Specific over generic.** "Uses Result<T, AppError>" beats "handles errors."
- **Evidence-based.** Every claim backed by a file path the user can check.
- **Current-state.** If migrating from pattern A to B, say so. Don't list
  both as equally valid.
- **Actionable.** A developer reading this should know exactly what to do
  when implementing a new feature.

---

## § Phase 4: Skill Pack Generation

### Goal

Generate the final skill pack — skills, agents, and guidelines — ready to
install or distribute.

### Procedure

1. **Ask the user what to generate** (default: all):
   - guidelines.md — shared codebase knowledge
   - skills/ask/ — Q&A skill
   - skills/plan/ — planning skill
   - skills/implement/ — coding skill
   - skills/review/ — review skill
   - agents/explorer.md — read-only navigation
   - agents/planner.md — planning agent
   - agents/implementer.md — implementation agent
   - agents/reviewer.md — review agent
   - Custom additions based on exploration findings

2. **Delegate to skill-writer agent:**

   ```
   Use the skill-writer agent.

   Generate the following outputs: {selected_outputs}

   Source materials:
   - Guidelines: {workspace}/phase3-guidelines.md
   - Module map: {workspace}/phase1-module-map.json
   - Module profiles: {workspace}/phase2-profiles/

   Use the templates in ${CLAUDE_SKILL_DIR}/assets/templates/
   as starting points.
   Write all outputs to {workspace}/phase4-output/

   Follow the structure defined in references/output-schemas.md § Skill Pack.
   ```

   **If `delivery_mode` is `"plugin"`**, append to the skill-writer prompt:

   ```
   Delivery mode: plugin
   Project name: {project_name}

   Generate the output in plugin directory structure under
   {workspace}/phase4-output/potion/.
   See references/output-schemas.md § Plugin Pack for the structure.

   Critical rules for plugin mode:
   - Omit the `name` field from ALL SKILL.md and agent frontmatter
   - Use ${CLAUDE_PLUGIN_ROOT}/guidelines.md as the guidelines path
   - Generate .claude-plugin/plugin.json with name: "potion"
   - Generate README.md from the readme-plugin.md template
   - Place manifest.json at {workspace}/phase4-output/manifest.json
     (outside the plugin directory)
   ```

3. **Review generated files.** Check:
   - Skills reference `guidelines.md` (not duplicating content)
   - Agent tool restrictions are correct (reviewer = read-only)
   - Descriptions are "pushy" enough for reliable triggering
   - Code examples are real file paths, not hallucinated
   - Each skill is self-contained (works without the others)

4. **Validate:**
   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/validate_output.py \
     --phase 4 --workspace {workspace}
   ```

5. **User gate:**

   List each generated file with a 1-sentence description, then call:
   ```
   AskUserQuestion({
     questions: [{
       question: "How would you like to proceed with the skill pack?",
       header: "Delivery",
       multiSelect: false,
       options: [
         { label: "Run evaluation (Recommended)", description: "Test skills with realistic prompts before installing" },
         { label: "Install as plugin", description: "Package and install directly without testing" },
         { label: "Install to .claude/", description: "Copy skills/agents/guidelines directly to .claude/" },
         { label: "Review files first", description: "Show me each generated file before deciding" }
       ]
     }]
   })
   ```

   Store the user's choice in `state.json.user_choices.delivery_mode`:
   - "Run evaluation" → keep current mode, proceed to Phase 5
   - "Install as plugin" → `"plugin"`
   - "Install to .claude/" → `"install"`
   - "Review files first" → keep current mode, show files then re-ask

### Evaluation step (recommended)

Borrowed from the skill-creator pattern: before delivering, test the
generated skills with realistic prompts.

For each generated skill:

1. Craft 2-3 prompts a real developer would say:
   - Ask skill: "Where is the auth middleware?" or "How does billing work?"
   - Implement skill: "Add a new endpoint for user preferences"
   - Review skill: "Review my changes to the payment flow"

2. Spawn a subagent with the skill loaded and the test prompt.

3. Check: Does the response reference real files? Follow project patterns?
   Give useful, specific guidance?

4. If issues: iterate on the skill, then re-test.

Present test results to the user before final delivery.

### Installation

Based on `delivery_mode` in state.json:

#### Standalone install (delivery_mode: "standalone" — default)

Standalone mode places skills, agents, and guidelines directly in `.claude/`
where Claude Code auto-discovers them. Skill directory names are prefixed with
`potion-` to avoid conflicts with other skills.

```bash
mkdir -p {project_root}/.claude/skills {project_root}/.claude/agents
cp -r {workspace}/phase4-output/skills/potion-ask/ {project_root}/.claude/skills/potion-ask/
cp -r {workspace}/phase4-output/skills/potion-plan/ {project_root}/.claude/skills/potion-plan/
cp -r {workspace}/phase4-output/skills/potion-implement/ {project_root}/.claude/skills/potion-implement/
cp -r {workspace}/phase4-output/skills/potion-review/ {project_root}/.claude/skills/potion-review/
cp -r {workspace}/phase4-output/agents/ {project_root}/.claude/agents/

# Guidelines (single-file or multi-file):
cp {workspace}/phase4-output/guidelines.md {project_root}/.claude/guidelines.md
# OR:
cp -r {workspace}/phase4-output/guidelines/ {project_root}/.claude/guidelines/
```

These files should be committed to git so the whole team gets them.

Update the project's CLAUDE.md — see § CLAUDE.md Update below.

Show the user what's available:
```
Skills installed to .claude/ (run /reload-plugins to activate):
  /potion-ask       — Ask questions about this codebase
  /potion-plan      — Plan features before implementing
  /potion-implement — Implement following project patterns
  /potion-review    — Review code against project standards

Commit .claude/skills/, .claude/agents/, and .claude/guidelines/
to share with your team.
```

#### Plugin packaging (delivery_mode: "plugin")

For distributing via a marketplace. The skill-writer generates the plugin
structure inside `phase4-output/potion/`. Plugin skills use namespaced names
(`/potion:ask`). See the skill-writer agent instructions for the full plugin
directory structure.

1. **Validate:**
   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/validate_output.py \
     --phase 4 --workspace {workspace} --delivery-mode plugin
   ```

2. **Copy** to the project:
   ```bash
   mkdir -p {project_root}/.claude/plugins
   cp -r {workspace}/phase4-output/potion/ {project_root}/.claude/plugins/potion/
   ```

3. **Distribute** — team members install via marketplace or `--plugin-dir`.

4. **Update CLAUDE.md** — see § CLAUDE.md Update below.

#### § CLAUDE.md Update

After installing, update the project's CLAUDE.md to help developers discover
and use the generated skills.

1. **Read** `{project_root}/CLAUDE.md` (or `{project_root}/.claude/CLAUDE.md`).
   If neither exists, create `{project_root}/CLAUDE.md`.

2. **Prepend** the following block at the top of the file (after any existing
   frontmatter but before other content). Adapt skill names based on delivery mode:

   For **standalone** mode:
   ```markdown
   ## Potion Skills

   This project has Potion-generated skills tailored to its architecture and
   patterns. Use them instead of generic approaches:

   - `/potion-ask` — Ask questions about the codebase (architecture, patterns, where things are)
   - `/potion-plan` — Plan a feature or refactor before writing code
   - `/potion-implement` — Implement features following this project's actual patterns
   - `/potion-review` — Review code against this project's real standards

   > Skills reference shared guidelines at `.claude/guidelines.md` (or `.claude/guidelines/`).
   > Edit sections marked `<!-- user-edited -->` to customize.
   ```

   For **plugin** mode:
   ```markdown
   ## Potion Skills

   This project has Potion-generated skills tailored to its architecture and
   patterns. Use them instead of generic approaches:

   - `/potion:ask` — Ask questions about the codebase (architecture, patterns, where things are)
   - `/potion:plan` — Plan a feature or refactor before writing code
   - `/potion:implement` — Implement features following this project's actual patterns
   - `/potion:review` — Review code against this project's real standards

   > Skills reference shared guidelines at `.claude/plugins/potion/guidelines.md`.
   > Edit sections marked `<!-- user-edited -->` to customize.
   ```

3. **Do not overwrite** existing CLAUDE.md content — prepend only. If the block
   already exists (from a previous generation), replace it in place.

#### Review-only (delivery_mode: "review-only")

Display all generated files for the user to review. Do not install or copy.

---

## § Phase 5: Evaluation

### Goal

Verify generated skills and agents produce correct, useful responses before
delivering to the user. Catch issues that static validation can't find.
Uses structured evals with assertions, with/without-skill comparison,
and description trigger testing.

### Procedure

1. **Ask the user:**
   ```
   AskUserQuestion({
     questions: [{
       question: "Want to run evaluation tests before delivery?",
       header: "Evaluate",
       multiSelect: false,
       options: [
         { label: "Run tests (Recommended)", description: "Verify skills produce correct, useful responses" },
         { label: "Skip evaluation", description: "Proceed directly to delivery" }
       ]
     }]
   })
   ```
   If the user skips, mark Phase 5 as `skipped` in state.json and proceed to delivery.

2. **Create the evaluation workspace:**
   ```
   {workspace}/phase5-workspace/
   ├── evals/           (test plans per skill/agent)
   └── iteration-1/     (first pass results)
   ```

3. **Build eval plans.** For each generated skill/agent, create an `evals.json`
   file in `{workspace}/phase5-workspace/evals/` following the schema in
   `references/output-schemas.md § Evaluation Evals`. Include:
   - **Functional evals** (minimum 2 per skill/agent): realistic prompts
     with assertions about what the response must contain.
   - **Trigger evals** (4-5 should-trigger + 4-5 should-not-trigger): test
     whether the description activates correctly.

   Example assertions for an ask skill eval:
   ```json
   {
     "id": 0,
     "prompt": "Where is the auth middleware?",
     "expected_output": "Points to the exact file and line where auth middleware is defined",
     "assertions": [
       "References a real file path that exists in the codebase",
       "Mentions the specific middleware function name",
       "Does not say 'probably' or 'likely' without confirming"
     ],
     "type": "functional"
   }
   ```

4. **Run with/without comparison.** For each functional eval:
   a. Spawn an agent **WITH** the generated skill loaded and give it the prompt.
      Save output to `iteration-N/{skill}/eval-{id}-{name}/with_skill/output.md`.
      Record `total_tokens` and `duration_ms` from the agent result and save
      to `.../with_skill/timing.json`.
   b. Spawn an agent **WITHOUT** the skill (vanilla Claude Code) and give it
      the same prompt. Save to `.../without_skill/output.md` and
      `.../without_skill/timing.json`.
   c. Compare: the with-skill response should be meaningfully better — more
      specific, references real files, follows project patterns.

5. **Grade each response.** For each eval, check:
   - `references_real_files`: Does it cite files that actually exist?
   - `follows_patterns`: Does it follow the patterns from guidelines.md?
   - `assertions_passed`: How many assertions are satisfied?
   - Classify result: `pass` (all assertions met), `partial` (some met,
     response still useful), `fail` (incorrect, hallucinated, or generic)

6. **Run description trigger tests.** For each skill:
   a. Take the should-trigger prompts — would Claude activate this skill?
   b. Take the should-not-trigger prompts — would Claude correctly NOT activate?
   c. Record trigger precision. If below 80%, revise the description.

7. **Handle failures.** If a skill/agent fails or is partial:
   - Identify root cause: missing context, bad description, wrong patterns,
     or hallucinated file paths
   - Fix the skill and create a new iteration directory (`iteration-2/`, etc.)
   - Re-test ONLY failed/partial items with the same prompts
   - Maximum 3 iterations per skill — if still failing, flag for user review

8. **Validate output:**
   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/validate_output.py \
     --phase 5 --workspace {workspace}
   ```

9. **Present results:**
   ```
   Evaluation complete (iteration {N}):

   | Output | Evals | Pass | Partial | Fail | Trigger precision | Iterations |
   |--------|-------|------|---------|------|-------------------|------------|
   | ask skill | 3 | 3 | 0 | 0 | 5/5 trigger, 5/5 reject | 0 |
   | implement skill | 2 | 1 | 1 | 0 | 4/5 trigger, 5/5 reject | 1 |
   | review skill | 2 | 2 | 0 | 0 | 5/5 trigger, 4/5 reject | 0 |
   | explorer | 2 | 2 | 0 | 0 | — | 0 |
   | implementer | 2 | 1 | 1 | 0 | — | 2 |
   | reviewer | 2 | 2 | 0 | 0 | — | 0 |

   With/without comparison:
   - ask skill: with-skill scored 4.5/5 vs without-skill 2.0/5
   - implement skill: with-skill scored 4.0/5 vs without-skill 2.5/5
   ...

   Benchmark:
   | Metric | With skill | Without skill | Delta |
   |--------|-----------|---------------|-------|
   | Pass rate | 92% | 45% | +47% |
   | Avg tokens | 1,850 | 3,200 | -42% |
   | Avg duration | 12.3s | 18.7s | -34% |
   | Quality (1-5) | 4.2 | 2.3 | +1.9 |

   {details on partials and iterations}

   ```

   Then call:
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

   Compute the benchmark section by aggregating timing data from all
   `timing.json` files across the iteration. See the benchmark schema
   in `references/output-schemas.md § Evaluation Results`.

### Fresh-context reader testing

The most important quality signal is whether a skill works for someone who
has ZERO prior context about the codebase. The with/without comparison
in step 4 above captures this — the "without" agent represents a fresh user.

Additionally:

1. Spawn an agent with ONLY the generated skill loaded — no module map,
   no profiles, no conversation history.
2. Give it a realistic prompt that a new team member might ask.
3. Compare the response against what an agent WITH full context would produce.
4. If the fresh-context agent misses critical information, the skill needs
   more embedded context (more file paths, more pattern details, etc.).

### Description optimization loop

For each generated skill, optimize the description for trigger precision:

1. Generate 10 eval queries: 5 should-trigger, 5 should-NOT-trigger.
   - Should-trigger: diverse phrasings a real user would say for this skill
   - Should-NOT-trigger: adjacent requests that belong to a different skill
     or need no skill at all
2. Run each query and record whether the skill activates.
3. If precision is below 80%:
   - For missed triggers: add the phrasing to the description
   - For false triggers: narrow the description scope
   - Re-test with the same queries
4. Maximum 3 revision rounds for the description.
5. Record final trigger stats in the evaluation results.

Save all evaluation results to `{workspace}/phase5-evaluation.json` following
the schema in `references/output-schemas.md § Evaluation Results`.

---

## Recovery and Resumption

Each phase saves to the workspace. On resumption:

1. Check what exists in `{workspace}/`
2. Show the user what's already done
3. Offer to re-run or skip completed phases
4. Resume from the last incomplete phase

This supports incremental work across sessions and lets the user
run phases independently (e.g., "just redo the guidelines").

---

## Refresh Mode

Use refresh mode when the codebase has changed since the last skill generation
and the user wants to update the skill pack without starting from scratch.

### When to use

- User says "refresh skills", "update the skill pack", "re-analyze"
- Significant code changes since last generation (new modules, refactors)
- Guidelines are outdated but not completely wrong

### Procedure

1. **Detect changes.** Compare current codebase state against the existing
   module map:
   - If git is available: `git diff --stat {last_generation_commit}..HEAD`
   - Otherwise: compare directory structure against module map paths

2. **Selective Phase 2.** Only re-explore modules where:
   - Files have changed significantly (>20% of files modified)
   - New files or directories appeared
   - Module was added or removed from the module map
   Keep unchanged module profiles as-is.

3. **Incremental Phase 3.** Merge new findings into existing guidelines:
   - Preserve sections marked with `<!-- user-edited -->` — the user
     manually updated these and they should not be overwritten
   - Update pattern descriptions where profiles changed
   - Add new modules to the architecture overview
   - Re-prioritize pitfalls based on updated profiles

4. **Regenerate skills.** Run Phase 4 with the updated guidelines.
   Show diffs instead of full documents so the user can see what changed.

5. **Review diffs.** Present changes as:
   ```
   Updated skill pack. Changes:

   guidelines.md: +12 -3 lines (added new-module section, updated error patterns)
   skills/implement/SKILL.md: +5 -2 lines (added new component type)
   agents/reviewer.md: unchanged
   ...
   ```

6. **Evaluate changes.** Run evaluation on changed skills only:
   - Reuse existing evals from `phase5-workspace/evals/` for unchanged skills
   - Create new evals for skills that changed significantly
   - Run with/without comparison only for changed skills

7. **User gate:**

   Show the refresh summary, then call:
   ```
   AskUserQuestion({
     questions: [{
       question: "Ready to install the updated skill pack?",
       header: "Refresh",
       multiSelect: false,
       options: [
         { label: "Install", description: "Replace the existing skill pack with the updated version" },
         { label: "Review diffs", description: "Show me what changed before installing" },
         { label: "Discard", description: "Keep the current skill pack unchanged" }
       ]
     }]
   })
   ```

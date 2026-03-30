# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Codebase Skill Generator** is a Claude Code plugin that analyzes any codebase and generates a tailored skill pack (coding skills, review agents, Q&A agents, and a shared guidelines document) grounded in the target project's actual architecture and patterns.

## Architecture

The plugin follows a **5-phase pipeline** orchestrated by `skills/potion-skill-generator/SKILL.md`:

1. **Phase 1 — Discover:** `agents/module-mapper.md` scans the codebase and produces `module-map.json`
2. **Phase 2 — Explore:** `agents/module-explorer.md` (one per module, run in parallel) produces per-module JSON profiles
3. **Phase 3 — Synthesize:** `agents/pattern-synthesizer.md` distills profiles into a unified `guidelines.md`
4. **Phase 4 — Generate:** `agents/skill-writer.md` produces the final skill pack from templates + guidelines
5. **Phase 5 — Evaluate (optional):** Structured evaluation with assertions, with/without-skill comparison, description trigger testing, and iteration

Each phase has a **human-in-the-loop gate** where the user validates findings before proceeding. Phases save to `.skill-gen-workspace/` for resumability.

### Key design decisions

- **Progressive disclosure:** SKILL.md is the lean orchestrator; detailed instructions live in `references/phases.md` and `references/output-schemas.md`
- **Guidelines as single source of truth:** All generated skills reference one `guidelines.md` instead of duplicating knowledge
- **Parallel exploration:** Phase 2 spawns all module-explorer agents simultaneously (batches of 3-5 for large codebases)
- **Least-privilege agents:** Reviewer agents get read-only tools (Read, Glob, Grep). Explorer/doc-scanner agents get Read + Write (to save profiles). PR review miner gets Read + Write + Bash (for gh/glab CLI). Write-capable agents: module-mapper (Bash + Glob for structural scanning), pattern-synthesizer (Write for guidelines output), skill-writer (Write/Edit for generating the skill pack)
- **Multi-stack awareness:** For monorepos with 2+ language stacks (e.g., Python backend + TypeScript frontend), the pipeline auto-detects stacks, generates per-stack guidelines, and creates stack-specific implementation agents coordinated by a master

### Potion Learn (Continuous Evolution)

A separate skill (`skills/potion-learn/SKILL.md`) that evolves guidelines after
initial generation. It runs a 3-phase pipeline:

1. **Phase 1 — Gather:** `agents/pr-miner.md` (PR comments), `agents/text-parser.md`
   (free-form text), and `agents/drift-detector.md` (guideline drift) run in parallel
2. **Phase 2 — Challenge:** `agents/challenger.md` argues against each finding
3. **Phase 3 — Write:** `agents/learnings-writer.md` stages learnings in `.claude/learnings.md`
   and optionally merges approved items into guidelines

Findings accumulate in `.claude/learnings.md` as a staging area. Merge into
guidelines is a deliberate, user-reviewed action.

## File Layout

```
.claude-plugin/plugin.json              # Plugin manifest
agents/                                 # Subagent definitions (YAML frontmatter + markdown)
  module-mapper.md                      # Phase 1 agent
  module-explorer.md                    # Phase 2 agent (spawned per module)
  doc-scanner.md                        # Phase 2 agent (documentation discovery)
  git-workflow-scanner.md               # Phase 2 agent (git history, branching, merge, PR analysis)
  pr-review-miner.md                    # Phase 2 agent (PR review comment mining, optional)
  pattern-synthesizer.md                # Phase 3 agent
  shared-synthesizer.md                 # Phase 3 agent (cross-cutting conventions, multi-stack only)
  stack-synthesizer.md                  # Phase 3 agent (per-stack synthesis, multi-stack only)
  skill-writer.md                       # Phase 4 agent
  pr-miner.md                           # Single-PR review comment extractor (potion-learn)
  text-parser.md                        # Free-form text normalizer (potion-learn)
  drift-detector.md                     # Guidelines vs. codebase divergence (potion-learn)
  challenger.md                         # Devil's advocate for findings (potion-learn)
  learnings-writer.md                   # Staging file writer + merge proposer (potion-learn)
skills/potion-skill-generator/
  SKILL.md                              # Main orchestrator skill
  references/phases.md                  # Detailed phase-by-phase instructions
  references/output-schemas.md          # JSON contracts for all agent I/O
  scripts/validate_output.py            # Inter-phase output validation
  scripts/tree_structure.py             # Filtered directory tree generator (manual use only)
  assets/templates/                     # Handlebars-style templates for generated outputs
    ask-skill.md, implement-skill.md, review-skill.md, plan-skill.md
    explorer-agent.md, implementer-agent.md, reviewer-agent.md, planner-agent.md
    readme-plugin.md, test-prompts.md
    master-implement-skill.md, master-plan-skill.md, master-review-skill.md
    stack-implementer-agent.md
    partials/                           # Shared sections referenced via {{> partials/name#section}}
    reviewers/                          # Specialized reviewer sub-agent templates
skills/potion-learn/
  SKILL.md                              # Orchestrator for continuous guideline evolution
  references/finding-schema.md          # JSON contracts for learn pipeline agents
  references/learnings-format.md        # .claude/learnings.md structure specification
  assets/templates/learnings.md         # Template for initial learnings file
```

## Validation

Run inter-phase validation with:
```bash
python skills/potion-skill-generator/scripts/validate_output.py --phase {1|2|3|4|5|all} --workspace <path>
```

Add `--project-root <path>` to verify file paths referenced in outputs exist on disk.
Add `--verbose` for detailed output. When `--phase all`, cross-phase validation runs automatically.

## Conventions

- **Agent definitions** use YAML frontmatter (`name`, `description`, `tools`, `model`, `effort`, `maxTurns`) followed by markdown instructions
- **Skill definitions** use the same frontmatter format in `SKILL.md` files
- **Output contracts** are JSON schemas defined in `references/output-schemas.md` — agents must return valid JSON matching these schemas
- **Templates** in `assets/templates/` use `{{placeholder}}` and `{{#each}}` Handlebars-style syntax
- Agent tool restrictions must match their role: reviewers/explorers are read-only, implementers get write access
- Skill descriptions should be "pushy" — include multiple trigger phrasings so Claude reliably activates them
- Skill and agent descriptions must be in **third person** ("Analyzes..." not "Analyze...")
- Skills use `allowed-tools` in frontmatter; agents use `tools`
- Generated guidelines include `<!-- user-edited -->` markers for sections preserved during refresh

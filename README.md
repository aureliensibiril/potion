# 🧪 Potion

> *"We are in a small village of indomitable Gauls who still hold out against
> the invaders. And life is not easy for the legionaries who garrison the
> fortified camps..."*
>
> Their secret? A magic potion that gives them superhuman strength.

**Build your own superpowers.**

Potion is a Claude Code plugin that reads your codebase — its architecture,
patterns, conventions, review culture — and generates a skill pack tailored
to that project. The result is a set of skills and agents that actually know
how *your* team writes code, not generic best practices from a training set.

When a new developer joins and asks "how does auth work here?", the generated
ask skill points them to the exact files. When someone implements a feature,
the implement skill follows your actual patterns — your error types, your
repository abstractions, your test conventions. When code gets reviewed, the
review skill checks against standards your team actually enforces, including
the ones that only exist in PR comments.

There's more to it than generating files. Potion runs a five-phase pipeline
with human checkpoints at every stage. It discovers your modules, explores
each one in depth, mines your PR review history for tribal knowledge, synthesizes
everything into a guidelines document, then generates skills and agents from
that foundation. You validate and correct at each step — because you know
your codebase better than any agent.

## Installation

### Claude Code marketplace

```bash
/plugin marketplace add aureliensibiril/potion

/plugin install potion-skill-generator@aureliensibiril-potion
```

### Manual (project-local)

```bash
git clone https://github.com/aureliensibiril/potion.git .claude/plugins/potion-skill-generator
```

### Manual (global)

```bash
git clone https://github.com/aureliensibiril/potion.git ~/.claude/plugins/potion-skill-generator
```

## Usage

After installing, just tell Claude what you want:

```
Generate a skill pack for this codebase
```

Or be more specific:

```
Analyze this project and create development skills and agents for my team
```

If a skill pack already exists and your codebase has changed, ask for a refresh:

```
Refresh the skill pack — we've added a new module
```

The generator will diff against the existing output and update only what changed.

## How it works

The pipeline runs in five phases. Each saves to a workspace so you can review,
correct, and resume at any point.

**Phase 1 — Discover.** The module-mapper agent scans your codebase structure
and produces a module map. You validate the boundaries before moving on.

**Phase 2 — Explore.** One module-explorer agent per module, all running in
parallel, each producing a detailed profile of patterns, conventions, and
pitfalls. Simultaneously, a doc-scanner finds existing documentation (CLAUDE.md,
Cursor rules, ADRs, config files) and a pr-review-miner extracts tribal
knowledge from your merged PR comments — filtering out bot noise to surface
what your team actually enforces during review.

**Phase 3 — Synthesize.** The pattern-synthesizer cross-references all
profiles, documentation, and review patterns into a unified guidelines
document. Code patterns get reconciled with documented standards and
review-enforced conventions.

**Phase 4 — Generate.** The skill-writer produces the final skill pack
from templates grounded in your guidelines. Skills, agents, review checklists,
test prompts — all referencing your real files and patterns.

**Phase 5 — Evaluate (optional).** Test generated skills with realistic
prompts. Compare responses with and without the skill loaded. Iterate on
failures before delivery.

## What gets generated

| Output | What it does |
|--------|-------------|
| **guidelines.md** | The codebase DNA — architecture, patterns, conventions, pitfalls |
| **ask skill** | Answers questions about the codebase with real file references |
| **plan skill** | Designs implementation approaches following your architecture |
| **implement skill** | Writes code following your actual patterns and conventions |
| **review skill** | Reviews code against your real standards, not generic rules |
| **explorer agent** | Read-only codebase navigation |
| **planner agent** | Plans complex features respecting your architecture |
| **implementer agent** | Implements features scoped to your conventions |
| **reviewer agent** | Reviews code with your checklist (plus specialized sub-agents for larger projects) |
| **test-prompts.md** | Realistic prompts for evaluating the generated skills |

## What's inside

The plugin itself is a pipeline of specialized agents:

- **module-mapper** — Phase 1. Scans codebase structure, identifies modules and boundaries.
- **module-explorer** — Phase 2. Deep-dives into each module to extract patterns, conventions, and canonical examples.
- **doc-scanner** — Phase 2. Discovers existing documentation, AI instructions, ADRs, config-enforced rules.
- **pr-review-miner** — Phase 2. Mines merged PR review comments for enforced conventions and tribal knowledge. Filters out bot comments (CodeRabbit, Copilot, SonarQube, etc.) to focus on what humans actually say during review.
- **pattern-synthesizer** — Phase 3. Reconciles code patterns, documented standards, and review culture into a unified guidelines document.
- **skill-writer** — Phase 4. Generates the skill pack from templates grounded in the guidelines.

Templates for all generated outputs live in `assets/templates/`. JSON contracts
for agent I/O live in `references/output-schemas.md`. Phase instructions live
in `references/phases.md`. The orchestrator (`SKILL.md`) routes to these on
demand — agents only load what they need.

## Philosophy

- **Your patterns, not generic ones.** Every generated skill references real
  files in your codebase. "Uses Result<T, AppError>" beats "handles errors."

- **Human-in-the-loop.** Each phase boundary is a validation checkpoint. The
  generator presents findings and waits — your corrections are the most
  valuable input in the pipeline.

- **Guidelines as single source of truth.** All generated skills reference one
  guidelines document instead of duplicating knowledge. Update the guidelines,
  all skills benefit.

- **Tribal knowledge belongs in skills.** PR review comments, undocumented
  conventions, patterns enforced through review but never written down — these
  are captured and codified so the next developer doesn't have to learn them
  the hard way.

- **Evaluation before delivery.** Skills are tested with realistic prompts
  before packaging. With-and-without comparison shows the actual improvement.

## Requirements

- Claude Code with plugin and subagent support
- A codebase to analyze (any language, any framework)
- For PR review mining: `gh` CLI (GitHub) or `glab` CLI (GitLab), authenticated

## License

MIT

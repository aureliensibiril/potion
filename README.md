# 🧪 Codebase Skill Generator

A Claude Code plugin that analyzes any codebase and generates a tailored skill
pack — coding skills, review agents, Q&A agents, and a shared guidelines
document — all grounded in the project's actual architecture and patterns.

## What it produces

| Output | Description |
|--------|-------------|
| `guidelines.md` (or `guidelines/`) | Shared knowledge: architecture, patterns, conventions, pitfalls |
| `skills/ask/` | Q&A skill — answers questions about the codebase |
| `skills/plan/` | Planning skill — designs implementation approaches |
| `skills/implement/` | Coding skill — follows your project's actual patterns |
| `skills/review/` | Review skill — checks code against your real standards |
| `agents/explorer.md` | Read-only codebase navigation agent |
| `agents/planner.md` | Planning agent for complex feature design |
| `agents/implementer.md` | Implementation agent scoped to your conventions |
| `agents/reviewer.md` | Code review agent (read-only, uses your checklist) |
| `agents/reviewers/` | Specialized reviewer sub-agents (optional, for larger projects) |
| `test-prompts.md` | Realistic prompts for evaluating generated skills |

## Installation

### Via Claude Code plugin marketplace (recommended)

```bash
# Add the marketplace
/plugin marketplace add aureliensibiril/potion

# Install the plugin
/plugin install potion-skill-generator@aureliensibiril-potion
```

### Manual installation

Clone into your project's `.claude/plugins/` directory:

```bash
git clone https://github.com/aureliensibiril/potion.git <project-root>/.claude/plugins/potion-skill-generator
```

Or for global installation across all projects:

```bash
git clone https://github.com/aureliensibiril/potion.git ~/.claude/plugins/potion-skill-generator
```

## Usage

```
Generate a skill pack for this codebase
```

Or more specifically:

```
Analyze this project and create development skills and agents
for my team. I want Q&A, implementation, and review workflows.
```

**Refresh mode:** If a skill pack already exists, ask the generator to refresh
it. It will re-scan the codebase, diff against existing guidelines, and update
only what changed — no need to start from scratch.

## How it works

```
Phase 1: module-mapper agent
  Scans codebase → module-map.json
  User validates module boundaries
            │
Phase 2: module-explorer + doc-scanner agents (parallel)
  One per module → per-module profiles + documentation profile
  User reviews pattern findings
            │
Phase 3: pattern-synthesizer agent
  Cross-references profiles → guidelines.md
  User reviews the guidelines document
            │
Phase 4: skill-writer agent
  Generates skills + agents from guidelines
            │
Phase 5 (optional): evaluation
  Test generated skills with realistic prompts
  Iterate on failures, validate before delivery
            │
Delivery:
  Install to .claude/ or package as plugin
```

Each phase saves to a workspace — you can review, correct, and resume
at any point.

## Plugin structure

```
potion-skill-generator/
├── .claude-plugin/
│   └── plugin.json                         # Plugin manifest
├── skills/
│   └── potion-skill-generator/
│       ├── SKILL.md                        # Orchestrator
│       ├── references/
│       │   ├── phases.md                   # Detailed phase instructions
│       │   └── output-schemas.md           # JSON contracts for agents
│       ├── scripts/
│       │   ├── validate_output.py          # Inter-phase validation
│       │   └── tree_structure.py           # Filtered directory tree generator
│       └── assets/
│           └── templates/                  # Templates for generated outputs
│               ├── ask-skill.md
│               ├── plan-skill.md
│               ├── implement-skill.md
│               ├── review-skill.md
│               ├── explorer-agent.md
│               ├── planner-agent.md
│               ├── implementer-agent.md
│               ├── reviewer-agent.md
│               ├── readme-plugin.md
│               ├── test-prompts.md
│               └── reviewers/              # Specialized reviewer sub-agent templates
├── agents/
│   ├── module-mapper.md                    # Phase 1: discovers modules
│   ├── module-explorer.md                  # Phase 2: profiles each module
│   ├── doc-scanner.md                      # Phase 2: discovers documentation
│   ├── pattern-synthesizer.md              # Phase 3: synthesizes guidelines
│   └── skill-writer.md                     # Phase 4: generates skill pack
└── README.md
```

## Design decisions

**Progressive disclosure.** SKILL.md is the lean orchestrator and routes to
`references/` for detailed phase instructions and schemas. Agents only
load what they need.

**Guidelines as single source of truth.** Every generated skill references
one `guidelines.md` rather than duplicating knowledge. Update the guidelines,
all skills benefit.

**Human-in-the-loop gates.** Each phase boundary is a validation checkpoint.
The user knows their codebase better than any agent — their corrections are
the most valuable input.

**Parallel exploration.** Phase 2 spawns one agent per module simultaneously.
For large codebases, batches of 3-5 to avoid overload.

**Evaluation before delivery.** Inspired by the skill-creator pattern: test
generated skills with realistic prompts before packaging.

## Requirements

- Claude Code with subagent support
- A codebase to analyze (any language/framework)

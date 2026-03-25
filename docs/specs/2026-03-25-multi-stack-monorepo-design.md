# Multi-Stack Monorepo Support

> Design spec for Potion's multi-stack monorepo capabilities.
> Generated: 2026-03-25

## Problem

Potion currently treats all modules equally — a Python FastAPI backend and a
TypeScript Next.js frontend get their patterns merged into one guidelines file.
This loses specificity: Python error handling conventions dilute TypeScript
patterns, pytest instructions mix with Vitest instructions, and DDD patterns
sit next to React component patterns.

For monorepos with multiple language stacks, we need:
- Per-stack guidelines that capture each stack's conventions at full fidelity
- Stack-specific implementation agents that load only relevant context
- A master orchestrator that decomposes cross-stack tasks and coordinates agents
- All of this activating automatically when multiple stacks are detected

## When It Activates

**Detection:** During Phase 1, the module-mapper already captures `language_stack`
per module. The orchestrator groups modules by primary language:
- `python`, `typescript/javascript`, `go`, `rust`, `java`, etc.
- Framework differences (FastAPI vs Dagster) are same-stack — they share language
  conventions and are handled by `module-notes/` within the stack

**Threshold:** A stack needs ≥2 modules OR ≥20 source files to qualify for
dedicated guidelines + agents. Below that, fold into `shared.md` under
"Minor Stacks."

**Mode:** Stored in `state.json`:
```json
{
  "stack_mode": "single | multi",
  "stacks": [
    {
      "name": "python-backend",
      "language": "python",
      "frameworks": ["FastAPI", "Dagster"],
      "modules": ["backend/webapp", "backend/automation", "backend/sidekiq"]
    },
    {
      "name": "typescript-frontend",
      "language": "typescript",
      "frameworks": ["Next.js", "React"],
      "modules": ["frontend/web", "frontend/admin", "frontend/auth"]
    }
  ]
}
```

Single-stack repos: `stack_mode: "single"`, current behavior unchanged.

## Guidelines Structure (Multi-Stack)

```
.claude/guidelines/
├── shared.md                         # Cross-cutting: git workflow, CI/CD,
│                                     # monorepo tooling, shared types/contracts
├── python-backend/
│   ├── index.md                      # Architecture overview, module map
│   ├── patterns.md                   # Error handling, data access, DI — Python
│   ├── conventions.md                # Naming, imports, project structure
│   ├── testing.md                    # pytest, fixtures, test organization
│   ├── pitfalls.md                   # Python-specific pitfalls
│   └── module-notes/                 # Per-module specifics within this stack
│       ├── webapp.md
│       └── automation.md
└── typescript-frontend/
    ├── index.md                      # Architecture overview, component tree
    ├── patterns.md                   # React patterns, state, data fetching
    ├── conventions.md                # TypeScript conventions, component structure
    ├── testing.md                    # Vitest, Testing Library, Playwright
    ├── pitfalls.md                   # TypeScript/React pitfalls
    └── module-notes/
        ├── web.md
        └── admin.md
```

### What goes in shared.md

- Git workflow (commit format, branching strategy, merge method, PR process)
- CI/CD pipeline structure
- Monorepo tooling (workspace config, build orchestration)
- Cross-stack contracts (protobuf, OpenAPI, shared types)
- Deployment conventions
- Observability strategy (if shared across stacks)

### What goes in per-stack guidelines

- Language-specific patterns (error handling, data access, DI, types)
- Framework-specific conventions (FastAPI routes vs Next.js pages)
- Stack-specific testing (pytest vs Vitest)
- Stack-specific pitfalls
- Module notes for modules in that stack

## Phase 3 — Two-Stage Synthesis

### Step 1: Shared synthesizer (sequential, opus)

**Inputs:** All module profiles + doc-scanner + git-workflow-scanner + pr-review-miner

**Produces:** `shared.md`

**Purpose:** Extract cross-cutting conventions that apply to ALL stacks. The
shared synthesizer sees all profiles to identify patterns that span stacks
(e.g., "all services use Azure Service Bus for messaging" or "all apps deploy
via GitHub Actions").

### Step 2: Per-stack synthesizers (parallel, opus)

**Inputs per stack:** Only that stack's module profiles + `shared.md` (to avoid
duplication)

**Produces:** Full topic file directory per stack

**Key instruction:** "Do NOT duplicate anything already covered in shared.md.
Reference it instead: 'See shared.md § Git Workflow for commit conventions.'"

### User gate

Present shared.md first for review. Then each stack's guidelines sequentially.
The user validates shared conventions first, then stack-specific ones.

## Phase 4 — Stack-Aware Skill Generation

All master agents and sub-agents use **opus**.

### Implementation skill: master + sub-agents

```
/potion-implement
  └── Master implementer (opus)
        Loads: shared.md + index.md from EVERY stack
        Role: analyze task, determine stacks involved, orchestrate

        For single-stack tasks:
          → Delegates to the right stack's implementer

        For cross-stack tasks:
          → Determines dependency order (upstream first)
          → Spawns upstream implementer (e.g., backend)
          → Reads the changes, extracts contract
          → Spawns downstream implementer (e.g., frontend)
            with the actual upstream changes as context
          → Verifies coherence

  Sub-agents:
    python-backend-implementer (opus)
      Loads: shared.md + python-backend/*
    typescript-frontend-implementer (opus)
      Loads: shared.md + typescript-frontend/*
```

### Cross-stack task orchestration

The master determines execution order from data flow direction:

| Task type | Order | Reasoning |
|-----------|-------|-----------|
| New API + frontend page | Backend → Frontend | Frontend consumes the API |
| Frontend form + backend validation | Backend → Frontend | Validation defines constraints |
| Independent changes | Parallel | No dependency |
| Shared type change | Shared → Backend → Frontend | Types flow downstream |

The master passes **actual changes** (not specs) from upstream to downstream:
"The backend implementer created `GET /api/preferences` returning
`{theme: string, language: string}`. Implement the frontend page consuming
this endpoint."

### Plan skill: stack-aware decomposition

```
/potion-plan
  Master planner (opus)
    Loads: shared.md + index.md from every stack
    1. Analyzes the feature requirement
    2. Identifies which stacks are involved
    3. Determines execution order (dependency direction)
    4. Creates plan with stack-labeled sections:
       - "Backend (Python): ..."
       - "Frontend (TypeScript): ..."
       - "Shared: ..."
    5. Each section references the right stack's patterns
    6. Notes inter-stack dependencies and contract points
```

### Review skill: stack-aware topic reviewers

Instead of adding stack reviewers on top of topic reviewers (which would
explode to N×M agents), make the existing topic reviewers stack-aware:

```
/potion-review
  Master reviewer
    Determines which stacks are in the diff
    For each file, routes to topic reviewers with the right stack context

  Topic reviewers (existing 6):
    architecture-reviewer → loads {stack}/architecture.md for the relevant stack
    pattern-reviewer → loads {stack}/patterns.md
    test-reviewer → loads {stack}/testing.md
    security-reviewer → loads {stack}/conventions.md + shared.md
    style-reviewer → loads {stack}/conventions.md
    duplication-reviewer → loads shared.md + both stacks (checks cross-stack duplication)
```

Each reviewer checks which stack a file belongs to and loads the appropriate
guidelines. A PR touching both Python and TypeScript files gets reviewed
against both stacks' rules.

### Ask skill: stack-aware routing

```
/potion-ask
  Determines stack from question context
  "How does auth work?" → loads both (auth spans stacks)
  "How do I add a pytest fixture?" → loads python-backend only
  "What component library do we use?" → loads typescript-frontend only
```

## Backward Compatibility

- `stack_mode: "single"` → current templates, no masters, no splitting
- Single-stack repos are completely unaffected
- The skill-writer uses different template paths based on `stack_mode`
- All new templates are additive — existing templates remain for single-stack

## Files to Create/Modify

### New files
- `agents/shared-synthesizer.md` — Phase 3 shared convention extraction
- `agents/stack-synthesizer.md` — Phase 3 per-stack synthesis
- `assets/templates/master-implement-skill.md` — Master implementer template
- `assets/templates/stack-implementer-agent.md` — Per-stack implementer
- `assets/templates/master-plan-skill.md` — Master planner template
- `assets/templates/master-review-skill.md` — Master reviewer template

### Modified files
- `skills/potion-skill-generator/SKILL.md` — Stack detection, Phase 3 routing
- `skills/potion-skill-generator/references/phases.md` — Two-stage synthesis
- `skills/potion-skill-generator/references/output-schemas.md` — Stack schema
- `agents/pattern-synthesizer.md` — Becomes the single-stack path
- `agents/skill-writer.md` — Multi-stack template selection
- `agents/module-mapper.md` — Ensure language_stack is per-module

## Open Questions

1. Should stack names be auto-generated (`python-backend`) or user-confirmed
   during the Phase 1 gate?
2. For the review skill, should the master reviewer pass stack context to
   each topic reviewer, or should each topic reviewer detect the stack from
   the file path?

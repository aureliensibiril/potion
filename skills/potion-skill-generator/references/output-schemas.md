# Output Schemas Reference

JSON contracts for each phase. Agents validate against these schemas.
The orchestrator checks outputs between phases.

---

## § Module Map (Phase 1)

```json
{
  "project_name": "string",
  "project_type": "monorepo | single-app | microservices | library | other",
  "language_stack": ["string"],
  "build_system": "string",
  "modules": [
    {
      "name": "string — unique",
      "path": "string — relative to project root",
      "purpose": "string — one sentence",
      "type": "service | library | package | domain | layer | config | tooling",
      "entry_points": ["string"],
      "depends_on": ["string — module names"],
      "depended_by": ["string — module names"],
      "estimated_size": "small | medium | large",
      "has_tests": "boolean",
      "language": "string — primary language: python | typescript | javascript | go | rust | java | other",
      "notes": "string",
      "submodules": [
        {
          "name": "string — unique within parent",
          "path": "string — relative to project root, must be under parent path",
          "purpose": "string — one sentence",
          "type": "service | library | package | domain | layer | config | tooling",
          "boundary_type": "string — free-form: hexagonal, feature-folders, vertical-slices, layered-mvc, etc.",
          "estimated_size": "small | medium | large",
          "has_tests": "boolean",
          "language": "string — primary language: python | typescript | javascript | go | rust | java | other",
          "notes": "string",
          "submodules": ["...recursive — same schema, for nested boundaries"]
        }
      ]
    }
  ],
  "shared_infrastructure": {
    "ci_cd": "string",
    "containerization": "string",
    "config_management": "string",
    "notes": "string"
  },
  "recommended_exploration_order": ["string"],
  "flags": ["string"]
}
```

**Rules:** modules non-empty, names unique, depends_on references existing names.
`submodules` is optional — only present when a module has clear internal boundaries.
Submodule names must be unique within their parent. Submodule paths must be under
the parent module's path. Submodules can be nested recursively (up to 6-8 levels)
for DDD bounded contexts, aggregates, and deep layered architectures.
Each module MUST have a `language` field. Submodules inherit parent language if not specified.

---

## § Documentation Profile (Phase 2)

Produced by the `doc-scanner` agent, running in parallel with module explorers.

```json
{
  "discovered_at": "string — ISO 8601",
  "documents": [
    {
      "path": "string — relative to project root",
      "type": "ai-instructions | developer-guide | adr | style-config | workflow | prd",
      "title": "string — extracted title or filename",
      "summary": "string — 2-3 sentence summary",
      "key_findings": ["string — actionable rules or conventions extracted"],
      "relevance": "high | medium | low",
      "line_count": "number"
    }
  ],
  "coding_standards": {
    "enforced_rules": ["string — rules that configs enforce, not just suggest"],
    "style_guide_summary": "string — consolidated style from all sources",
    "ai_instructions_summary": "string — consolidated AI-specific instructions"
  },
  "architecture_decisions": [
    {
      "title": "string",
      "source": "string — file path",
      "decision": "string — what was decided",
      "status": "accepted | proposed | deprecated | superseded"
    }
  ],
  "inline_doc_density": "high | medium | low | none",
  "gaps": ["string — areas where docs are missing or contradict code"]
}
```

**Rules:** `documents` non-empty (at least a README should exist), all paths relative,
`key_findings` backed by specific file content. Saved to `{workspace}/phase2-docs.json`.

---

## § Git Workflow Profile (Phase 2)

Produced by the `git-workflow-scanner` agent, running in parallel with module
explorers and the doc-scanner. Analyzes git history, branch structure, merge
patterns, and PR conventions.

```json
{
  "scanned_at": "string — ISO 8601",
  "commit_format": {
    "style": "conventional | scope-prefix | ticket-ref | free-form | mixed",
    "details": "string",
    "consistency": "high | medium | low",
    "examples": ["string — 5 representative commits"],
    "has_descriptions": "boolean",
    "description_pattern": "string | null"
  },
  "branching": {
    "strategy": "trunk-based | gitflow | feature-branches | other",
    "default_branch": "string",
    "branch_naming": "string",
    "branch_examples": ["string"],
    "long_lived_branches": ["string"]
  },
  "merge_strategy": {
    "method": "squash-merge | merge-commit | rebase | mixed",
    "evidence": "string"
  },
  "pr_process": {
    "platform": "github | gitlab | none",
    "template_exists": "boolean",
    "template_sections": ["string"],
    "required_reviewers": "number | null",
    "review_before_merge": "boolean | null",
    "ci_checks_on_pr": ["string"],
    "auto_merge_enabled": "boolean | null"
  },
  "releases": {
    "has_tags": "boolean",
    "tag_format": "string | null",
    "frequency": "string | null",
    "has_changelog": "boolean"
  },
  "limitations": ["string"]
}
```

**Rules:** All data must come from actual git history, not assumptions.
Saved to `{workspace}/phase2-git-workflow.json`.

---

## § Review Patterns Profile (Phase 2)

Produced by the `pr-review-miner` agent, running in parallel with module explorers
and the doc-scanner. This profile is **optional** — it is only produced when a
GitHub or GitLab CLI is available and the repository has merged PRs with review comments.

```json
{
  "mined_at": "string — ISO 8601",
  "platform": "github | gitlab | unavailable",
  "repository": "string — owner/repo",
  "prs_analyzed": "number",
  "comments_total": "number — all comments fetched (including bots)",
  "comments_human": "number — after filtering out bots",
  "comments_bot_filtered": "number — bot comments excluded",
  "time_window": {
    "from": "string — ISO 8601",
    "to": "string — ISO 8601"
  },
  "review_patterns": [
    {
      "category": "naming-convention | architecture-rule | error-handling | testing-expectation | security-concern | performance-preference | code-style | api-design | anti-pattern",
      "pattern": "string — concise description of the enforced convention",
      "frequency": "number — occurrences across distinct PRs",
      "confidence": "high | medium | low",
      "evidence": [
        {
          "pr_number": "number",
          "excerpt": "string — max 200 chars, no @-mentions or personal identifiers",
          "file_context": "string | null — file path the comment was on, if available"
        }
      ],
      "related_modules": ["string — module names from Phase 1 map, if module-specific"],
      "contradicts_docs": "boolean — true if this pattern contradicts documented standards"
    }
  ],
  "reviewer_focus_areas": {
    "most_commented_paths": ["string — top 5 file paths/directories with most human review comments"],
    "most_debated_topics": ["string — top 3 recurring discussion themes"],
    "approval_blockers": ["string — patterns that consistently block PR approval"]
  },
  "reviewer_count": "number — count of distinct human reviewers in the sample",
  "coverage_gaps": ["string — areas with no review patterns found"],
  "limitations": ["string — e.g. 'gh CLI not authenticated', 'Only last 6 months available'"]
}
```

**Confidence levels:**
- `high` — 5+ occurrences across 3+ distinct PRs
- `medium` — 2-4 occurrences
- `low` — single occurrence with strong rule language ("always", "never", "must")

**Privacy rules:**
- `evidence[].excerpt` must not contain @-mentions, full names, or email addresses
- Replace @-mentions with "reviewer" or "author" in excerpts
- Cap excerpts at 200 characters
- Do not store reviewer usernames — only the count (`reviewer_count`)

**Bot filtering:** The agent MUST filter out bot comments (AI review tools, CI bots,
dependency updaters) using `author.type`, username patterns, and content heuristics.
Only human comments count toward pattern frequency and PR ranking.

**Rules:** `review_patterns` may be empty if the repo has no human review activity.
All `related_modules` entries must reference module names from Phase 1.
All `evidence[].file_context` paths must be relative to project root.
Saved to `{workspace}/phase2-reviews.json`.

---

## § Module Profile (Phase 2)

```json
{
  "module_name": "string — must match module map",
  "module_path": "string",
  "purpose": "string — 2-3 sentences",
  "domain_concepts": [
    { "name": "string", "description": "string", "key_file": "string" }
  ],
  "architecture": {
    "pattern": "MVC | hexagonal | clean | feature-slices | flat | other",
    "layers": ["string"],
    "data_flow": "string",
    "key_abstractions": [
      { "name": "string", "file": "string", "role": "string" }
    ]
  },
  "patterns": {
    "error_handling": {
      "strategy": "string", "example_file": "string", "custom_types": ["string"]
    },
    "data_access": {
      "strategy": "string", "example_file": "string", "transaction_handling": "string"
    },
    "testing": {
      "framework": "string", "organization": "co-located | separate | both",
      "naming_convention": "string", "utilities": ["string"],
      "example_test_file": "string"
    },
    "dependency_injection": { "approach": "string", "config_loading": "string" },
    "typing": {
      "strictness": "strict | moderate | loose | untyped",
      "type_location": "string", "shared_types": ["string"]
    },
    "observability": {
      "logging_framework": "string — e.g. 'Python logging', 'Winston', 'slog', 'loguru', 'none'",
      "logging_style": "structured | unstructured | mixed",
      "log_levels_used": ["string — e.g. 'DEBUG', 'INFO', 'WARNING', 'ERROR'"],
      "metrics_framework": "string | null — e.g. 'Prometheus', 'StatsD', 'OpenTelemetry', 'none'",
      "tracing": "string | null — e.g. 'OpenTelemetry', 'Jaeger', 'Datadog', 'none'",
      "conventions": ["string — e.g. 'structured JSON logs', 'correlation IDs in all requests', 'no PII in logs'"],
      "example_file": "string"
    }
  },
  "conventions": {
    "file_naming": "string", "directory_structure": "string",
    "export_pattern": "string", "code_style_notes": ["string"],
    "commit_conventions": "string"
  },
  "pitfalls": [
    { "description": "string", "severity": "high | medium | low", "context": "string" }
  ],
  "dependencies": {
    "internal": ["string"],
    "external_key": [
      { "name": "string", "purpose": "string", "version_note": "string" }
    ]
  },
  "code_samples": {
    "canonical_implementation": { "file": "string", "why": "string" },
    "canonical_test": { "file": "string", "why": "string" }
  },
  "open_questions": ["string"]
}
```

**Rules:** module_name matches Phase 1, all file paths relative to project root,
pitfalls non-empty.

---

## § Guidelines Template (Phase 3)

Two modes: single-file (default for small codebases) and multi-file (for larger
codebases). The orchestrator selects the mode based on codebase size.

### Single-file mode

Single markdown file. Required sections:

1. **Architecture Overview** — with module map table
2. **Core Patterns** — error handling, data access, testing, types, DI
3. **Conventions** — naming, code style, git workflow
4. **Module-Specific Notes** — for modules with unique patterns
5. **Canonical Examples** — table of 3-5 files with explanations
6. **Known Pitfalls** — aggregated from profiles, prioritized
7. **Open Questions** — for user to fill in

**Rules:** file paths from profiles, patterns labeled universal/dominant/specific,
at least 3 canonical examples. Saved to `{workspace}/phase3-guidelines.md`.

### Multi-file mode

A directory of topic files. Each file is self-contained — a developer reading
only that file gets useful, actionable context.

```
phase3-guidelines/
├── index.md              # Overview, module map, canonical examples, links to topics
├── architecture.md       # Architecture patterns, module boundaries, data flow
├── patterns.md           # Error handling, data access, DI, types, observability, code examples
├── conventions.md        # Naming, code style, git workflow, documented standards
├── testing.md            # Frameworks, organization, naming, utilities, test examples
├── pitfalls.md           # Known pitfalls, aggregated and prioritized
└── module-notes/         # Per-module specifics (optional, only when unique patterns)
    ├── {module-name}.md
    └── ...
```

**Required files:** `index.md`, `architecture.md`, `patterns.md`, `conventions.md`,
`testing.md`, `pitfalls.md`. The `module-notes/` directory is optional.

**File requirements:**
- `index.md`: project name, generation date, module map table, canonical examples
  table (3-5 files), links to each topic file, `<!-- user-edited -->` Team Notes
  and Open Questions sections
- `architecture.md`: architecture overview, module boundaries, data flow diagrams
- `patterns.md`: error handling (with code example), data access, DI, type system
- `conventions.md`: naming, code style, git workflow, documented standards (from
  doc-scanner if available)
- `testing.md`: frameworks, organization, naming conventions, utilities, example test
- `pitfalls.md`: all pitfalls from profiles, prioritized by severity
- `module-notes/{name}.md`: module-specific patterns that differ from project-wide
  conventions (only created when needed)

Each file must:
- Start with a header: `# {Project Name} — {Topic}`
- Include `<!-- user-edited -->` markers where users might customize
- Cross-reference other files via relative paths: `See [Error Handling](./patterns.md#error-handling)`
- Label patterns as universal/dominant/module-specific

**Rules:** saved to `{workspace}/phase3-guidelines/`. All file paths from profiles.
At least 3 canonical examples in `index.md`. Every required file must exist.

### Mode selection

The orchestrator selects the mode and stores it in `state.json.user_choices.guidelines_mode`:
- `"single"` — single `phase3-guidelines.md` file
- `"multi"` — `phase3-guidelines/` directory with topic files
- Auto-select: use `"multi"` when >= 8 exploration units (modules + submodules) or
  the synthesizer estimates >= 400 lines; otherwise `"single"`

---

## § Skill Pack (Phase 4)

Directory structure:

```
phase4-output/
├── guidelines.md                           (single-file mode)
├── guidelines/                             (multi-file mode)
│   ├── index.md
│   ├── architecture.md
│   ├── patterns.md
│   ├── conventions.md
│   ├── testing.md
│   ├── pitfalls.md
│   └── module-notes/                       (optional)
├── skills/
│   ├── ask/SKILL.md
│   ├── plan/SKILL.md
│   ├── implement/
│   │   ├── SKILL.md
│   │   └── references/patterns-by-module.md  (optional, for overflow)
│   └── review/
│       ├── SKILL.md
│       └── references/review-checklist.md    (optional)
├── agents/
│   ├── explorer.md
│   ├── planner.md
│   ├── implementer.md
│   ├── reviewer.md                         (generalist, always present)
│   └── reviewers/                          (specialized, optional for larger projects)
│       ├── architecture-reviewer.md
│       ├── pattern-reviewer.md
│       ├── style-reviewer.md
│       ├── security-reviewer.md
│       ├── test-reviewer.md
│       └── duplication-reviewer.md
├── test-prompts.md
└── manifest.json
```

**Rules:**
- All SKILL.md and agent .md files have YAML frontmatter
- All skills reference guidelines (single file or directory depending on mode)
- reviewer.md and all reviewers/*.md have no Write/Edit in tools
- No file path in any skill that doesn't exist in the profiles
- Specialized reviewers (agents/reviewers/) are optional — generated based on
  project size (see skill-writer scaling rules)

**Reviewer scaling rules:**
- Small projects (1-3 modules): generalist reviewer only, no sub-agents
- Medium projects (4-7 modules): 3 core sub-agents (architecture, pattern, test)
- Large projects (8+ modules): all 6 sub-agents

---

## § Review Finding (Phase 4 — reviewer sub-agent output)

Each specialized reviewer sub-agent returns findings in this format:

```json
{
  "findings": [
    {
      "severity": "blocker | suggestion",
      "category": "architecture | pattern | style | security | testing | duplication",
      "file": "string — relative path",
      "line": "number | null",
      "issue": "string — what's wrong",
      "guideline_ref": "string — which guideline section this violates",
      "fix": "string — specific suggestion with code or canonical example reference",
      "confidence": "high | medium | low"
    }
  ],
  "summary": "string — 1-2 sentence overview of findings",
  "files_reviewed": ["string — files actually examined"]
}
```

**Rules:** `findings` may be empty (no issues found). `severity` must be either
`blocker` or `suggestion`. `guideline_ref` must reference a real section in
the guidelines. The review skill aggregates findings from all sub-agents,
deduplicates (same file:line from multiple agents), and sorts by severity.

---

## § Manifest (Phase 4)

```json
{
  "generated_at": "string — ISO 8601 timestamp",
  "project_name": "string",
  "modules_analyzed": "number",
  "generated": [
    {
      "path": "string — relative to phase4-output/",
      "type": "guidelines | skill | agent",
      "lines": "number",
      "description": "string"
    }
  ],
  "total_lines": "number — sum of all generated[].lines",
  "notes": ["string — any warnings or observations from generation"]
}
```

**Rules:** `generated_at` is valid ISO 8601, every `generated[].path` exists in
the output directory, `total_lines` equals sum of individual `lines` values.

**Note:** `manifest.json` is generation metadata — it tracks what was produced and
when. It is NOT a plugin manifest. In plugin mode, a separate `plugin.json` is
generated inside `.claude-plugin/` with a different schema (see § Plugin Pack).

---

## § Plugin Pack (Phase 4 — plugin delivery mode)

When `delivery_mode` is `"plugin"`, Phase 4 generates a complete, distributable
Claude Code plugin instead of loose files.

### Directory structure

```
phase4-output/
├── potion/
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── skills/
│   │   ├── ask/SKILL.md
│   │   ├── plan/SKILL.md
│   │   ├── implement/
│   │   │   ├── SKILL.md
│   │   │   └── references/patterns-by-module.md  (optional)
│   │   └── review/
│   │       ├── SKILL.md
│   │       └── references/review-checklist.md    (optional)
│   ├── agents/
│   │   ├── explorer.md
│   │   ├── planner.md
│   │   ├── implementer.md
│   │   ├── reviewer.md
│   │   └── reviewers/                            (optional, larger projects)
│   ├── guidelines.md                             (or guidelines/ directory)
│   ├── test-prompts.md
│   └── README.md
└── manifest.json              (generation metadata — outside the plugin)
```

### plugin.json schema

```json
{
  "name": "potion",
  "version": "1.0.0",
  "description": "string — what this skill pack covers",
  "author": {
    "name": "string — user name or 'Generated'"
  },
  "keywords": ["string — project name, language stack, 'skills'"],
  "license": "MIT"
}
```

**Naming convention:** The `name` field is always `"potion"` — the generator's
brand, not the target project's name. Skills are invoked as `/potion:ask`,
`/potion:plan`, `/potion:implement`, `/potion:review`.

### Plugin-mode frontmatter rules

Skills (`SKILL.md`) and agents (`.md`) in plugin mode **must omit the `name` field**
from YAML frontmatter. The name derives from the directory name (for skills) or
filename (for agents). This ensures the plugin namespace prefix is applied correctly.

If a `name` field is present, Claude Code bypasses the plugin namespace — the skill
appears as `/ask` instead of `/potion:ask` (GitHub issue #22063).

### Guidelines path in plugin mode

All references to the guidelines document must use:
```
${CLAUDE_PLUGIN_ROOT}/guidelines.md
```

`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's install directory at runtime.
Do NOT use `.claude/guidelines.md` or relative paths — those break when the plugin
is installed in a different location.

**Rules:**
- `.claude-plugin/plugin.json` must exist and be valid JSON
- `plugin.json` `name` must be kebab-case, no "claude" or "anthropic"
- No SKILL.md or agent .md may contain a `name` field in frontmatter
- All skills/agents must reference `${CLAUDE_PLUGIN_ROOT}/guidelines.md`
- `manifest.json` must be outside the plugin directory (at `phase4-output/`)

---

## § State (Orchestrator)

```json
{
  "started_at": "string — ISO 8601",
  "updated_at": "string — ISO 8601",
  "project_root": "string — absolute path",
  "phases": {
    "1": {
      "status": "pending | in_progress | completed | skipped | failed",
      "started_at": "string | null",
      "completed_at": "string | null",
      "output_file": "string | null",
      "error": "string | null"
    },
    "2": {
      "status": "pending | in_progress | completed | skipped | failed",
      "started_at": "string | null",
      "completed_at": "string | null",
      "output_file": "string | null",
      "error": "string | null",
      "module_statuses": {
        "<module_name>": "pending | in_progress | completed | failed",
        "doc_scanner": "pending | in_progress | completed | failed",
        "pr_review_miner": "pending | in_progress | completed | skipped | failed"
      }
    },
    "3": { "...same fields..." },
    "4": { "...same fields..." },
    "5": { "...same fields..." }
  },
  "user_choices": {
    "selected_outputs": ["string — e.g. 'ask', 'implement', 'review'"],
    "skip_evaluation": "boolean",
    "delivery_mode": "standalone | plugin | review-only",
    "guidelines_mode": "single | multi | null"
  }
}
```

**Rules:** `updated_at` refreshed on every phase transition, `status` transitions
follow `pending → in_progress → completed | skipped | failed`, phases cannot
regress (except via explicit user request to re-run a phase).

---

## § Evaluation Evals (Phase 5 — input)

Before running evaluation, produce `evals.json` — the test plan:

```json
{
  "skill_name": "string — name of generated skill or agent",
  "evals": [
    {
      "id": "number — unique per skill",
      "prompt": "string — realistic user prompt",
      "expected_output": "string — description of what a good response looks like",
      "assertions": [
        "string — verifiable claim the response must satisfy"
      ],
      "type": "should_trigger | should_not_trigger | functional"
    }
  ]
}
```

**Rules:** minimum 2 `functional` evals per skill/agent. For description testing,
include 4-5 `should_trigger` and 4-5 `should_not_trigger` evals.

---

## § Evaluation Results (Phase 5 — output)

```json
{
  "evaluated_at": "string — ISO 8601",
  "iteration": "number — current iteration (starts at 1)",
  "skills_tested": [
    {
      "skill": "string — e.g. 'ask', 'implement', 'review'",
      "test_prompts": [
        {
          "prompt": "string",
          "result": "pass | fail | partial",
          "references_real_files": "boolean",
          "follows_patterns": "boolean",
          "assertions_passed": "number",
          "assertions_total": "number",
          "timing": {
            "with_skill": { "total_tokens": "number", "duration_ms": "number" },
            "without_skill": { "total_tokens": "number", "duration_ms": "number" }
          },
          "notes": "string"
        }
      ],
      "with_without_comparison": {
        "with_skill_quality": "number — 1-5 rating",
        "without_skill_quality": "number — 1-5 rating",
        "improvement": "string — what the skill added"
      },
      "description_triggers": {
        "should_trigger_total": "number",
        "should_trigger_passed": "number",
        "should_not_trigger_total": "number",
        "should_not_trigger_passed": "number"
      },
      "overall": "pass | fail | partial",
      "iterations": "number — how many revisions needed"
    }
  ],
  "agents_tested": [
    {
      "agent": "string — e.g. 'explorer', 'implementer', 'reviewer'",
      "test_prompts": [
        {
          "prompt": "string",
          "result": "pass | fail | partial",
          "references_real_files": "boolean",
          "assertions_passed": "number",
          "assertions_total": "number",
          "timing": {
            "with_skill": { "total_tokens": "number", "duration_ms": "number" },
            "without_skill": { "total_tokens": "number", "duration_ms": "number" }
          },
          "notes": "string"
        }
      ],
      "overall": "pass | fail | partial",
      "iterations": "number"
    }
  ],
  "summary": {
    "total_tested": "number",
    "passed": "number",
    "failed": "number",
    "partial": "number",
    "iterated": "number — items that needed revision"
  },
  "benchmark": {
    "pass_rate": {
      "with_skill": "number — 0-1",
      "without_skill": "number — 0-1",
      "delta": "number — positive means skill improved results"
    },
    "tokens": {
      "with_skill_mean": "number",
      "without_skill_mean": "number",
      "delta_pct": "number — percentage change, negative means fewer tokens"
    },
    "duration_ms": {
      "with_skill_mean": "number",
      "without_skill_mean": "number",
      "delta_pct": "number"
    },
    "quality_score": {
      "with_skill_mean": "number — 1-5",
      "without_skill_mean": "number — 1-5",
      "delta": "number"
    }
  }
}
```

**Result classification:**
- `pass` — all assertions satisfied, references real files, follows patterns
- `partial` — some assertions pass but at least one fails, or response is useful
  but misses non-critical information
- `fail` — response is incorrect, references hallucinated files, or ignores
  project patterns

**Rules:** minimum 2 `test_prompts` per skill, no `fail` overall statuses in a
passing evaluation, `total_tested` equals `skills_tested.length + agents_tested.length`.

---

## § Evaluation Workspace (Phase 5)

```
phase5-workspace/
├── evals/
│   ├── ask-evals.json
│   ├── plan-evals.json
│   ├── implement-evals.json
│   ├── review-evals.json
│   ├── explorer-evals.json
│   ├── planner-evals.json
│   ├── implementer-evals.json
│   └── reviewer-evals.json
├── iteration-1/
│   ├── ask/
│   │   ├── eval-0-where-is-auth/
│   │   │   ├── with_skill/
│   │   │   │   ├── output.md
│   │   │   │   └── timing.json      # { "total_tokens": N, "duration_ms": N }
│   │   │   └── without_skill/
│   │   │       ├── output.md
│   │   │       └── timing.json
│   │   └── eval-1-how-billing-works/
│   │       ├── with_skill/
│   │       │   ├── output.md
│   │       │   └── timing.json
│   │       └── without_skill/
│   │           ├── output.md
│   │           └── timing.json
│   └── implement/
│       └── ...
├── iteration-2/
│   └── ...  (only re-tested items)
└── phase5-evaluation.json   (final results)
```

---

## Cross-phase validation

After Phase 4, verify (automated by `validate_output.py --phase all`):

1. Every module from Phase 1 covered by at least one skill
2. Every canonical example from Phase 3 appears in at least one skill
3. Every pitfall from Phase 3 covered by the review checklist
4. Implement skill patterns match guidelines' Core Patterns
5. Review checklist covers guidelines' Conventions section
6. Evaluation results (if Phase 5 ran) have no `fail` overall statuses

---
{{#unless plugin_mode}}name: {{project_name}}-ask
{{/unless}}description: >
  Answers questions about the {{project_name}} codebase. This skill should be
  used when someone asks "where is...", "how does X work", "why is Y done this
  way", "what pattern does Z use", "explain the architecture", "find the code
  that handles...", "what does this module do", or any question about
  understanding this project. It also triggers for onboarding questions like
  "how do I get started", "what should I know", or "walk me through the
  codebase".
allowed-tools: Read, Glob, Grep
model: sonnet
effort: medium
---

# {{project_name}} — Codebase Q&A

{{#if multi_guidelines}}Before answering, read the guidelines at `{{guidelines_path}}` — start
with `index.md` for architecture overview, then check the relevant topic file
(e.g., `patterns.md`, `conventions.md`, `pitfalls.md`).
{{else}}Before answering, read `{{guidelines_path}}` for architecture and patterns.
{{/if}}

## Answering strategy

1. **Check guidelines first.** Most architecture and pattern questions are
   already answered there. Don't explore what's already documented.
2. **Locate the module.** Use the module map below to narrow scope.
3. **Explore with precision.** Grep and Glob to find specific code. Read
   files to confirm. Never say "it's probably in..." — find it.
4. **Cite your sources.** Reference specific files and line numbers.

## Module map

| Module | Path | Purpose |
|--------|------|---------|
{{#each modules}}
| {{name}} | `{{path}}` | {{purpose}} |
{{/each}}

## Canonical examples

These files represent "the right way" in this project:

| File | Demonstrates |
|------|-------------|
{{#each canonical_examples}}
| `{{file}}` | {{why}} |
{{/each}}

## How to handle different question types

**"Where is X?"** → Grep, check module map, return exact file + lines.

**"How does X work?"** → Find entry point, trace data flow through layers,
explain each step with file references.

**"Why is X done this way?"** → Check guidelines for rationale, then ADRs,
then code comments. If no rationale exists, say so — don't invent.

**"What pattern for X?"** → Reference Core Patterns in guidelines. Point to
the canonical example that best matches.

**"How do I get started?"** → Walk through: structure → architecture →
patterns → canonical examples → how to run tests.

## Key patterns quick reference

{{patterns_summary}}

## Module-specific entry points

{{#each modules}}
- **{{name}}** (`{{path}}`): {{purpose}}
{{/each}}

## Rules

- Never guess. If you cannot find it, say so and suggest where to look.
- Prefer code snippets from the actual codebase over abstract descriptions.
- Note migrations or inconsistencies when relevant (e.g., "module X uses the
  old pattern, the rest of the codebase uses the new one").
- Keep answers focused. Answer the question, then offer to go deeper.
- For complex exploration, delegate to the `{{project_name}}-explorer` agent.

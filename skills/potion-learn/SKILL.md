---
name: potion-learn
description: "Learns from PR reviews, free-form feedback, and codebase drift to evolve project guidelines. Mines human review comments from a specific PR, parses free-form text input (CodeRabbit exports, meeting notes), detects when the codebase has drifted from guidelines, challenges every finding with devil's advocate reasoning, and stages learnings for reviewed merge into guidelines. Use when the user asks to learn from a PR, absorb feedback, update guidelines from reviews, check for guideline drift, or evolve project conventions."
effort: high
argument-hint: "[--pr NUMBER] [--text \"...\"] [--file path] [--drift-only] [--merge]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion
---

# Potion Learn — Continuous Guidelines Evolution

Learn from PR reviews, free-form feedback, and codebase drift to evolve
project guidelines over time.

## When to use this skill

- User wants to learn conventions from a PR's review comments
- User wants to absorb team decisions, meeting notes, or tool exports
- User wants to check if guidelines match codebase reality (drift detection)
- User wants to update or evolve their project guidelines
- User says "learn from PR", "absorb feedback", "check drift", "update guidelines"

## Prerequisites check

Before anything else, verify guidelines exist:

```
Glob: .claude/guidelines.md
Glob: .claude/guidelines/**/*.md
```

If no guidelines found, stop and tell the user:
> No project guidelines found at `.claude/guidelines.md` or `.claude/guidelines/`.
> Run the `potion-skill-generator` skill first to generate initial guidelines,
> then come back to evolve them with `potion-learn`.

## Parse input mode

Parse `$ARGUMENTS` to determine the input mode:

| Flag | Mode | Example |
|------|------|---------|
| `--pr NUMBER` | PR mode | `--pr 142` |
| `--text "..."` | Text mode (inline) | `--text "Always validate webhooks"` |
| `--file PATH` | Text mode (from file) | `--file notes.txt` |
| `--drift-only` | Drift-only mode | `--drift-only` |
| `--merge` | Merge pending learnings into guidelines | `--merge` |
| (none) | Auto-detect PR from current branch | — |

**Combining modes:** `--pr` and `--text`/`--file` can be combined (mixed mode).
`--drift-only` and `--merge` are exclusive — they cannot be combined with other modes.

**Merge mode:** If `--merge` is specified, skip Phase 1 (Gather) and Phase 2
(Challenge) entirely. Jump straight to reading existing `.claude/learnings.md`
and presenting User Gate 2 (merge decision). This allows users to review and
merge previously staged learnings without re-running the full pipeline.

**Auto-detect PR:** If no `--pr` flag and not `--drift-only`:
```bash
gh pr view --json number -q '.number' 2>/dev/null
```
If a PR is found, use it. If not, and no `--text`/`--file` either, ask the
user what they want to do.

## Setup workspace

```bash
mkdir -p .skill-gen-workspace/learn
```

## Phase 1 — GATHER

Launch gather agents in parallel based on input mode. Drift detection
always runs (unless `--drift-only` is the only mode, in which case skip
PR and text).

**Determine guidelines path:**
```
Glob: .claude/guidelines.md
Glob: .claude/guidelines/**/*.md
```
Use whichever exists. Prefer the directory form if both exist.

### PR Miner (if PR mode)

Launch the `pr-miner` agent:
```
Agent: pr-miner
Prompt: |
  Mine review comments from PR #{pr_number}.
  output_path: .skill-gen-workspace/learn/pr-findings.json
```

### Text Parser (if text mode)

Launch the `text-parser` agent:
```
Agent: text-parser
Prompt: |
  Parse the following text into convention findings.
  {text content or file_path}
  output_path: .skill-gen-workspace/learn/text-findings.json
```

### Drift Detector (always)

Launch the `drift-detector` agent:
```
Agent: drift-detector
Prompt: |
  Check for drift between guidelines and codebase.
  guidelines_path: {guidelines_path}
  output_path: .skill-gen-workspace/learn/drift-report.json
```

**Wait for all gather agents to complete.**

### Merge findings

If both PR and text findings exist, merge them into a single file:
1. Read both JSON files
2. Re-number finding IDs sequentially (F-001, F-002, ...) across both sources
3. Write merged result to `.skill-gen-workspace/learn/merged-findings.json`

If only one source, copy it as `merged-findings.json`.

## Phase 2 — CHALLENGE

Launch the `challenger` agent:
```
Agent: challenger
Prompt: |
  Challenge each finding and drift item. Be rigorous.
  findings_path: .skill-gen-workspace/learn/merged-findings.json
  drift_path: .skill-gen-workspace/learn/drift-report.json
  guidelines_path: {guidelines_path}
  output_path: .skill-gen-workspace/learn/challenged-findings.json
```

**Wait for the challenger to complete.**

## User Gate 1 — Review challenged findings

Read the challenged findings and present a summary table:

```
## Learning Summary

Source: {sources used}

| ID | Convention | Source | Verdict | Confidence |
|----|-----------|--------|---------|------------|
| F-001 | {convention} | {source} | {verdict} | {confidence} |
| ... | ... | ... | ... | ... |
| D-001 | {claim} drift | drift scan | {verdict} | {confidence} |

Accepted: N | Modified: N | Rejected: N

Review each finding? [y/n/abort]
```

Use AskUserQuestion to get the user's choice:
- **y**: Show each finding one by one, let user override verdicts
- **n**: Accept all verdicts as-is, proceed
- **abort**: Stop here, no changes written

If the user overrides any verdicts, update the challenged findings JSON
before proceeding.

## Phase 3 — WRITE

Launch the `learnings-writer` agent in write mode:
```
Agent: learnings-writer
Prompt: |
  Stage challenged findings into the learnings file.
  challenged_path: .skill-gen-workspace/learn/challenged-findings.json
  guidelines_path: {guidelines_path}
  learnings_path: .claude/learnings.md
  archive_dir: .claude/learnings-archive
  mode: write
```

**Wait for the writer to complete.**

## User Gate 2 — Merge decision

Present the merge options:

```
## Merge into Guidelines?

{N} learnings staged in .claude/learnings.md
{N} drift alerts staged

Merge candidates:
- [L-001] → {target section} ({summary})
- [D-001] → {target section} ({summary})

Options:
1. Merge all into guidelines now
2. Select which to merge
3. Keep in learnings only (merge later with --merge)
```

Use AskUserQuestion for the user's choice.

### If merge approved (option 1 or 2)

Determine which IDs to merge (all for option 1, user-selected for option 2).

Launch the `learnings-writer` agent in merge mode:
```
Agent: learnings-writer
Prompt: |
  Merge approved learnings into guidelines.
  challenged_path: .skill-gen-workspace/learn/challenged-findings.json
  guidelines_path: {guidelines_path}
  learnings_path: .claude/learnings.md
  archive_dir: .claude/learnings-archive
  mode: merge
  merge_ids: [{selected IDs}]
```

### If kept for later (option 3)

Tell the user: "Learnings staged in `.claude/learnings.md`. Run
`potion-learn --merge` later to merge selected items into guidelines."

## Done

Summarize what happened:
- How many findings were gathered (by source)
- How many survived challenge
- How many were staged / merged / rejected
- Any drift alerts found

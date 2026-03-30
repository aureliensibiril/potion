# Finding Schemas Reference

JSON contracts for potion-learn agents. Each agent validates its output
against these schemas. The orchestrator checks outputs between phases.

---

## § Finding (PR Miner / Text Parser output)

Shared format for both PR-sourced and text-sourced findings.

```json
{
  "finding_id": "string (F-NNN, sequential)",
  "source": {
    "type": "pr | text",
    "pr_number": "number | null",
    "description": "string — e.g. 'PR #142' or 'CodeRabbit export 2026-03-28'",
    "reviewer_role": "string | null — e.g. 'maintainer', 'contributor' (no names)",
    "timestamp": "ISO 8601 | null"
  },
  "category": "naming-convention | architecture-rule | error-handling | testing-expectation | security-concern | performance-preference | code-style | api-design | anti-pattern | documentation",
  "convention": "string — the actionable rule extracted",
  "context": {
    "file_path": "string | null",
    "excerpt": "string (max 200 chars, no @-mentions)",
    "related_modules": ["string"]
  },
  "confidence": "high | medium | low"
}
```

**Rules:**
- `finding_id` is sequential within a single run (F-001, F-002, ...)
- `source.type` determines which fields are populated: PR findings have `pr_number` and `reviewer_role`, text findings have `description` and optional `timestamp`
- `excerpt` must be anonymized: strip @-mentions, full names, email addresses
- `confidence` for PR findings: `high` if imperative language ("always", "never", "must") or 3+ similar comments; `medium` for 2 occurrences; `low` for single occurrence with weak language
- `confidence` for text findings: `high` for explicit team decisions; `medium` for tool-generated learnings; `low` for ambiguous suggestions

---

## § PR Findings File

Output of the PR Miner agent. Wraps an array of findings with metadata.

```json
{
  "mined_at": "ISO 8601",
  "platform": "github | gitlab",
  "pr_number": "number",
  "pr_title": "string",
  "pr_url": "string",
  "comments_total": "number — all comments fetched",
  "comments_human": "number — after bot filtering",
  "comments_bot_filtered": "number — removed by bot filter",
  "findings": ["Finding[]"],
  "skipped_comments": "number — human comments with no actionable convention"
}
```

**Rules:** `findings` may be empty if no actionable conventions found. `comments_human` = `comments_total` - `comments_bot_filtered`.

---

## § Text Findings File

Output of the Text Parser agent.

```json
{
  "parsed_at": "ISO 8601",
  "input_source": "string — 'inline text' or file path",
  "input_length_chars": "number",
  "findings": ["Finding[]"]
}
```

---

## § Drift Item

Individual drift finding from the Drift Detector.

```json
{
  "drift_id": "string (D-NNN, sequential)",
  "guideline_claim": "string — what guidelines say",
  "guideline_location": "string — section path in guidelines (e.g. 'Architecture > Views')",
  "actual_pattern": "string — what the code actually does",
  "adherence_ratio": "number (0.0–1.0)",
  "severity": "high | medium | low",
  "evidence": [
    {"file": "string", "observation": "string"}
  ],
  "recommendation": "update-guideline | enforce-convention",
  "effort_estimate": "string (e.g. '~5 files to update')"
}
```

**Rules:**
- `severity`: `high` if adherence < 0.30, `medium` if 0.30–0.70, `low` if 0.70–0.85
- Items with adherence ≥ 0.85 are not reported (no meaningful drift)
- `evidence` contains 2-5 representative files, not exhaustive lists

---

## § Drift Report

Output of the Drift Detector agent.

```json
{
  "scanned_at": "ISO 8601",
  "guidelines_path": "string — path to guidelines file or directory",
  "claims_checked": "number — total discrete claims extracted from guidelines",
  "drift_items": ["Drift Item[]"],
  "healthy_claims": "number — claims with adherence ≥ 0.85",
  "summary": "string — one-paragraph overview of drift status"
}
```

---

## § Challenged Finding

Output of the Challenger agent, one per input finding or drift item.

```json
{
  "finding_id": "string — matches original F-NNN or D-NNN",
  "original": "Finding | Drift Item — the original object, copied verbatim",
  "verdict": "accept | reject | modify",
  "challenge_reasoning": "string — the devil's advocate argument",
  "counterarguments": ["string — arguments against adopting this convention"],
  "codebase_evidence": [
    {"file": "string", "line": "number | null", "observation": "string"}
  ],
  "trade_offs": ["string — trade-offs of adopting vs. not adopting"],
  "modified_recommendation": "string | null — only if verdict = modify",
  "confidence": "high | medium | low"
}
```

**Rules:**
- Every input finding/drift item gets exactly one challenged finding entry
- `verdict = reject` findings are included in the output (for archiving) but not written to learnings
- `modified_recommendation` is required when `verdict = modify`, null otherwise
- `confidence` reflects the challenger's confidence in its verdict, not the original finding's confidence

---

## § Challenged Findings File

Full output of the Challenger agent.

```json
{
  "challenged_at": "ISO 8601",
  "total_findings": "number",
  "verdicts": {
    "accepted": "number",
    "rejected": "number",
    "modified": "number"
  },
  "challenged_findings": ["Challenged Finding[]"]
}
```

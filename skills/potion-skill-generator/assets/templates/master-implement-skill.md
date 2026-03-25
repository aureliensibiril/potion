---
{{#unless plugin_mode}}name: {{project_name}}-implement
{{/unless}}description: >
  Master implementation orchestrator for {{project_name}}. Analyzes tasks,
  determines which language stacks are involved, and delegates to stack-specific
  implementer agents. For cross-stack tasks, orchestrates sequentially — upstream
  first, then downstream with actual changes as context. Use when someone asks
  to "add", "create", "build", "implement", "write", or "code" anything.
allowed-tools: Read, Glob, Grep, Agent
model: opus
effort: high
---

# {{project_name}} — Master Implementation Orchestrator

This skill does NOT implement code itself. It analyzes incoming tasks, determines
which stack(s) are involved, and delegates to the right stack-specific implementer
agent(s).

## Load guidelines

Before analyzing any task, read the shared guidelines and every stack's index:

- **Shared conventions:** `{{shared_guidelines_path}}`
{{#each stacks}}
- {{name}}: `{{guidelines_path}}/index.md`
{{/each}}

## Stack routing table

Use this table to map modules and file paths to their owning stack.

{{#each stacks}}
### {{display_name}} ({{language}})
- **Frameworks:** {{frameworks}}
- **Modules:** {{modules}}
- **Implementer agent:** `{{name}}-implementer`
- **Guidelines:** `{{guidelines_path}}/`
{{/each}}

## Task analysis

For every incoming task, run through these steps before spawning any agent:

1. **Read the task description.** Understand what is being asked — feature,
   bugfix, refactor, migration, etc.
2. **Identify affected modules.** Look for file paths, feature names, module
   names, or domain concepts that map to known modules.
3. **Map modules to stacks** using the routing table above. Each module belongs
   to exactly one stack.
4. **Classify the task:**
   - **Single-stack** — all affected modules belong to one stack.
   - **Cross-stack** — affected modules span two or more stacks.

## Single-stack delegation

When only one stack is involved:

1. Spawn the `{stack_name}-implementer` agent with the full task description.
2. Let it handle the implementation end-to-end.
3. No further orchestration needed.

## Cross-stack orchestration

When multiple stacks are involved, order matters. Implement upstream before
downstream so that downstream agents can reference the actual changes.

### Step-by-step

1. **Determine dependency order** using the direction rules below.
2. **Spawn the upstream implementer first.** Pass it the full task description
   scoped to its stack. Wait for it to complete.
3. **Read upstream changes.** After the upstream agent finishes, read the files
   it created or modified. Extract the contract — API shapes, response types,
   function signatures, schema changes.
4. **Spawn the downstream implementer** with upstream context:
   ```
   "The {upstream_stack} implementer created {summary of changes}.
   Here are the relevant details: {API endpoint, response shape, etc.}
   Now implement the {downstream_stack} part that integrates with these changes."
   ```
5. **Verify coherence.** After both agents finish, check that the downstream
   implementation actually uses the upstream contract correctly — matching
   endpoint paths, field names, type shapes, etc.

### Dependency direction rules

| Task type | Order | Reasoning |
|-----------|-------|-----------|
| New API + frontend page | Backend then Frontend | Frontend consumes the API |
| Frontend form + backend validation | Backend then Frontend | Validation defines constraints |
| Independent changes | Parallel | No dependency |
| Shared type change | Shared then Backend then Frontend | Types flow downstream |
| Database migration + API update | Backend then Frontend | Schema change flows up |

### More than two stacks

For tasks spanning three or more stacks, apply the same principle recursively:
build from the most-upstream (shared libraries, schemas) outward to the
most-downstream (UI, CLI). Pass accumulated context forward at each step.

## When the stack is unclear

If the task description does not clearly map to any stack in the routing table,
do NOT guess. Ask the user:

> "This task could touch {stack_a} or {stack_b}. Which stack(s) should I target?"

## Post-orchestration checklist

After all implementer agents have finished:

- [ ] Every affected stack had its implementer agent spawned
- [ ] Cross-stack contracts are coherent (types match, endpoints align)
- [ ] No orphaned references (e.g., frontend calling an API that was not created)
- [ ] Shared conventions from guidelines were respected across all stacks

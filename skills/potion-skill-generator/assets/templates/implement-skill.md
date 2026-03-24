---
{{#unless plugin_mode}}name: {{project_name}}-implement
{{/unless}}description: >
  Implements new features, services, endpoints, or components in {{project_name}}
  following its established patterns and conventions. This skill should be used
  when someone asks to "add", "create", "build", "implement", "write", or "code"
  anything in this project. It also triggers when given a ticket, spec, user
  story, or feature description to implement. Even if the user just describes
  what they want without explicitly saying "implement", this skill applies if
  the intent is to produce new code in this project.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
model: inherit
effort: high
---

# {{project_name}} — Implementation

{{#if multi_guidelines}}Before writing any code, read the guidelines at `{{guidelines_path}}` — start
with `index.md` for an overview, then read `patterns.md` and `conventions.md`
for the patterns relevant to your task.
{{else}}Before writing any code, read `{{guidelines_path}}` for this project's
patterns and conventions.
{{/if}}

## Pre-implementation checklist

Run through this before writing a single line:

1. **Identify scope.** Which module(s) does this change touch?
   {{module_map_table}}
2. **Read the reference.** Open the canonical example for that module.
   When unsure, check the Canonical Examples table in guidelines.md.
3. **Check for existing code.** Grep for similar functionality — avoid
   reinventing. The codebase may already have a utility or pattern for this.
4. **Understand data flow.** Trace how data moves through the relevant
   layers before adding to them.

## Implementation patterns

### Adding a new {{primary_component_type}}

Follow these steps in order:

1. **Create the file** at the correct path:
   {{primary_component_file_path_pattern}}
2. **Use the template pattern:**
   {{primary_component_steps}}
3. **Wire it up:** Register/export following the module's existing pattern.
4. **Read the canonical example** before writing: `{{primary_canonical_path}}`

### Adding a new {{secondary_component_type}}

Follow these steps in order:

1. **Create the file** at the correct path:
   {{secondary_component_file_path_pattern}}
2. **Use the template pattern:**
   {{secondary_component_steps}}
3. **Wire it up:** Register/export following the module's existing pattern.
4. **Read the canonical example** before writing: `{{secondary_canonical_path}}`

## Testing requirements

{{testing_instructions}}

### Test file placement
- Tests go in: {{test_directory_pattern}}
- Test file naming: {{test_file_naming_pattern}}
- Run tests with: `{{test_command}}`

## File placement and naming

{{file_placement_rules}}

## For complex tasks

For tasks touching multiple modules or requiring more than ~200 lines of new
code, consider delegating to the `{{project_name}}-implementer` agent for a
fresh context window focused on the implementation.

## Post-implementation checklist

- [ ] Follows patterns from guidelines.md
- [ ] Tests written and passing
- [ ] Types properly defined (no untyped escapes unless justified)
- [ ] Error cases handled using the project's error pattern
- [ ] File names follow project naming convention
- [ ] No debug prints left in code
- [ ] New dependencies justified (if any added)

## Common mistakes in this codebase

These are real pitfalls found during analysis — not generic advice:

{{#each pitfalls}}
- **{{description}}** ({{severity}}) — {{context}}
{{/each}}

## When in doubt

Read the canonical implementation at `{{canonical_implementation_path}}`.
It demonstrates the right way to build in this project.

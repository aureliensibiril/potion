#!/usr/bin/env python3
"""
Validate potion-skill-generator outputs between phases.

Usage:
    python validate_output.py --phase 1 --workspace ./skill-gen-workspace
    python validate_output.py --phase all --workspace ./skill-gen-workspace
    python validate_output.py --phase 2 --workspace ./skill-gen-workspace --project-root /path/to/project
"""

import json, re, sys, os
from pathlib import Path
from typing import Any


class Result:
    def __init__(self):
        self.errors, self.warnings, self.info = [], [], []

    def error(self, msg): self.errors.append(msg)
    def warn(self, msg): self.warnings.append(msg)
    def ok(self, msg): self.info.append(msg)

    @property
    def passed(self): return len(self.errors) == 0

    def summary(self):
        lines = []
        for e in self.errors: lines.append(f"  ✗ {e}")
        for w in self.warnings: lines.append(f"  ⚠ {w}")
        for i in self.info: lines.append(f"  ✓ {i}")
        status = "PASSED" if self.passed else "FAILED"
        lines.append(f"\n  {status} ({len(self.errors)} errors, {len(self.warnings)} warnings)")
        return "\n".join(lines)


def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"  [debug] JSON parse error in {p.name}: {e}")
        return None


def extract_frontmatter(content):
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    return content[3:end] if end != -1 else None


def parse_frontmatter_field(fm_text, field):
    """Extract a field value from raw YAML frontmatter text."""
    all_lines = fm_text.splitlines()
    for idx, line in enumerate(all_lines):
        stripped = line.strip()
        if stripped.startswith(f"{field}:"):
            value = stripped[len(field) + 1:].strip()
            # Handle multi-line YAML (>) by collecting continuation lines
            if value == ">" or value == "|":
                lines = []
                for next_line in all_lines[idx + 1:]:
                    if next_line and not next_line[0].isspace():
                        break
                    lines.append(next_line.strip())
                return " ".join(lines).strip()
            return value.strip('"').strip("'")
    return None


def validate_spec_compliance(file_path, content, parent_dir_name, r, require_name=True):
    """Validate a SKILL.md or agent .md file against Agent Skills spec constraints.

    Args:
        require_name: If False, skip name validation (plugin mode omits name).
    """
    fm = extract_frontmatter(content)
    if not fm:
        r.error(f"{file_path}: no frontmatter found")
        return

    label = file_path

    # --- name validation ---
    name = parse_frontmatter_field(fm, "name")
    if require_name:
        if not name:
            r.error(f"{label}: frontmatter missing 'name'")
        else:
            if len(name) > 64:
                r.error(f"{label}: name exceeds 64 chars ({len(name)})")
            if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name):
                r.warn(f"{label}: name '{name}' is not strict kebab-case (lowercase letters, numbers, single hyphens)")
            if "claude" in name.lower() or "anthropic" in name.lower():
                r.error(f"{label}: name must not contain 'claude' or 'anthropic'")
            if name.startswith("-") or name.endswith("-"):
                r.error(f"{label}: name must not start or end with hyphen")
            if "--" in name:
                r.error(f"{label}: name must not contain consecutive hyphens")
            # Check name matches parent directory (for SKILL.md files)
            if parent_dir_name and name != parent_dir_name:
                r.warn(f"{label}: name '{name}' does not match parent directory '{parent_dir_name}'")

    # --- description validation ---
    desc = parse_frontmatter_field(fm, "description")
    if not desc:
        r.warn(f"{label}: frontmatter missing 'description'")
    else:
        if len(desc) > 1024:
            r.warn(f"{label}: description exceeds 1024 chars ({len(desc)})")
        # Check for XML tags in description
        xml_tags = re.findall(r'<[a-zA-Z][^>]*>', desc)
        if xml_tags:
            r.error(f"{label}: description contains XML tags (spec violation): {xml_tags[:3]}")
        # Check description is in third person (heuristic: shouldn't start with "I ", "You ", "We ")
        first_word = desc.split()[0].lower() if desc.split() else ""
        if first_word in ("i", "you", "we"):
            r.warn(f"{label}: description should be in third person (starts with '{first_word}')")

    # Also check the full body for XML tags that might be in description block
    # (multi-line descriptions can span past the first line)
    if fm:
        xml_in_fm = re.findall(r'<(?!!)(?!/)[a-zA-Z][^>]*>', fm)
        if xml_in_fm:
            r.error(f"{label}: frontmatter contains XML tags: {xml_in_fm[:3]}")


def validate_phase1(ws):
    r = Result()
    data = load_json(ws / "phase1-module-map.json")
    if not data: r.error("Cannot read phase1-module-map.json"); return r
    r.ok("Module map is valid JSON")

    modules = data.get("modules", [])
    if not modules: r.error("No modules found")
    else: r.ok(f"{len(modules)} modules")

    names = [m.get("name") for m in modules]
    if len(names) != len(set(names)):
        r.error(f"Duplicate names: {[n for n in names if names.count(n) > 1]}")

    name_set = set(names)
    submodule_count = 0
    for m in modules:
        for dep in m.get("depends_on", []):
            if dep not in name_set:
                r.warn(f"'{m['name']}' depends on unknown '{dep}'")
        if m.get("type") in ("service", "library") and not m.get("entry_points"):
            r.warn(f"'{m['name']}' ({m['type']}) has no entry_points")
        # Validate submodules
        subs = m.get("submodules", [])
        if subs:
            sub_names = [s.get("name") for s in subs]
            if len(sub_names) != len(set(sub_names)):
                r.error(f"'{m['name']}' has duplicate submodule names")
            parent_path = m.get("path", "")
            for s in subs:
                sub_path = s.get("path", "")
                if parent_path and sub_path and not sub_path.startswith(parent_path):
                    r.warn(f"Submodule '{s.get('name')}' path '{sub_path}' not under parent '{parent_path}'")
                submodule_count += 1
    if submodule_count > 0:
        r.ok(f"{submodule_count} submodules across all modules")

    # Validate language field on each module
    valid_languages = {"python", "typescript", "javascript", "go", "rust", "java", "other"}
    for m in modules:
        lang = m.get("language")
        if not lang:
            r.warn(f"'{m['name']}' missing 'language' field")
        elif lang not in valid_languages:
            r.warn(f"'{m['name']}' has unknown language: {lang}")
        # Check submodules
        for s in m.get("submodules", []):
            sub_lang = s.get("language")
            if sub_lang and sub_lang not in valid_languages:
                r.warn(f"'{m['name']}/{s.get('name')}' has unknown language: {sub_lang}")

    # Validate recommended_exploration_order references valid module names
    exploration_order = data.get("recommended_exploration_order", [])
    if exploration_order:
        invalid_refs = [n for n in exploration_order if n not in name_set]
        if invalid_refs:
            r.warn(f"recommended_exploration_order references unknown modules: {invalid_refs}")
        else:
            r.ok(f"recommended_exploration_order: {len(exploration_order)} entries, all valid")

    return r


def validate_phase2(ws, project_root=None):
    r = Result()
    d = ws / "phase2-profiles"
    if not d.exists(): r.error("phase2-profiles/ not found"); return r

    # Build expected exploration set from module map (modules without submodules
    # + individual submodules for modules that have them).
    # Use "{parent}/{submodule}" keys for submodules to avoid name collisions
    # when a submodule shares a name with a top-level module.
    module_map = load_json(ws / "phase1-module-map.json")
    expected_names = set()
    submodule_to_parent = {}
    if module_map:
        for m in module_map.get("modules", []):
            subs = m.get("submodules", [])
            if subs:
                for s in subs:
                    sub_name = s.get("name", "")
                    parent_name = m.get("name", "")
                    composite_key = f"{parent_name}/{sub_name}"
                    expected_names.add(composite_key)
                    submodule_to_parent[sub_name] = parent_name
            else:
                expected_names.add(m.get("name", ""))

    profiles = list(d.glob("*.json"))
    if not profiles: r.error("No profiles found"); return r
    r.ok(f"{len(profiles)} profiles")

    loaded_profiles = {}
    for pf in profiles:
        data = load_json(pf)
        if not data: r.error(f"Bad JSON: {pf.name}"); continue
        loaded_profiles[pf] = data
        name = data.get("module_name", "?")
        if not data.get("code_samples", {}).get("canonical_implementation", {}).get("file"):
            r.warn(f"'{name}' missing canonical implementation")
        if not data.get("pitfalls"):
            r.warn(f"'{name}' has no pitfalls")

        if project_root:
            root = Path(project_root)
            canonical_file = data.get("code_samples", {}).get("canonical_implementation", {}).get("file")
            if canonical_file and not (root / canonical_file).exists():
                r.warn(f"'{name}' canonical implementation path does not exist: {canonical_file}")
            test_file = data.get("code_samples", {}).get("canonical_test", {}).get("file")
            if test_file and not (root / test_file).exists():
                r.warn(f"'{name}' test file path does not exist: {test_file}")

    if expected_names:
        # Build profiled set using composite keys for submodules
        profiled = set()
        for d in loaded_profiles.values():
            mod_name = d.get("module_name", "")
            if mod_name in submodule_to_parent:
                profiled.add(f"{submodule_to_parent[mod_name]}/{mod_name}")
            else:
                profiled.add(mod_name)
        missing = expected_names - profiled
        if missing: r.warn(f"Missing profiles: {missing}")
        else: r.ok("All expected modules/submodules profiled")

    # Validate documentation profile (optional, from doc-scanner)
    docs_path = ws / "phase2-docs.json"
    if docs_path.exists():
        docs = load_json(docs_path)
        if not docs:
            r.warn("phase2-docs.json exists but is invalid JSON")
        else:
            doc_count = len(docs.get("documents", []))
            r.ok(f"Documentation profile: {doc_count} documents discovered")
            if not docs.get("documents"):
                r.warn("Doc-scanner found no documents")
            for doc in docs.get("documents", []):
                doc_path = doc.get("path", "")
                if project_root and doc_path:
                    if not (Path(project_root) / doc_path).exists():
                        r.warn(f"Doc path does not exist: {doc_path}")

    # Validate PR review patterns profile (optional, from pr-review-miner)
    reviews_path = ws / "phase2-reviews.json"
    if reviews_path.exists():
        reviews = load_json(reviews_path)
        if not reviews:
            r.warn("phase2-reviews.json exists but is invalid JSON")
        else:
            platform = reviews.get("platform", "unknown")
            prs_analyzed = reviews.get("prs_analyzed", 0)
            comments_human = reviews.get("comments_human", 0)
            comments_bot = reviews.get("comments_bot_filtered", 0)
            pattern_count = len(reviews.get("review_patterns", []))
            r.ok(f"Review patterns profile: {pattern_count} patterns from {prs_analyzed} PRs "
                 f"({comments_human} human comments, {comments_bot} bot filtered) [{platform}]")

            if platform == "unavailable":
                r.ok("PR review mining was skipped (no platform detected)")
            else:
                if prs_analyzed == 0:
                    r.warn("PR review miner found no PRs to analyze")

                valid_categories = {
                    "naming-convention", "architecture-rule", "error-handling",
                    "testing-expectation", "security-concern", "performance-preference",
                    "code-style", "api-design", "anti-pattern"
                }
                for pat in reviews.get("review_patterns", []):
                    cat = pat.get("category", "")
                    if cat not in valid_categories:
                        r.warn(f"Unknown review pattern category: {cat}")
                    # Privacy check: no @-mentions in evidence excerpts
                    for ev in pat.get("evidence", []):
                        excerpt = ev.get("excerpt", "")
                        if re.search(r"@(?!ts-|type|param|returns|override|deprecated)", excerpt):
                            r.warn(f"Evidence excerpt may contain @-mention: {excerpt[:60]}...")
                        if len(excerpt) > 200:
                            r.warn(f"Evidence excerpt exceeds 200 chars ({len(excerpt)})")

                    # Validate related_modules against Phase 1 module map
                    if module_map:
                        module_names = set()
                        for m in module_map.get("modules", []):
                            module_names.add(m.get("name", ""))
                            for s in m.get("submodules", []):
                                module_names.add(s.get("name", ""))
                        for mod in pat.get("related_modules", []):
                            if mod not in module_names:
                                r.warn(f"Review pattern references unknown module: {mod}")

    return r


def detect_guidelines_mode(ws):
    """Auto-detect whether guidelines are single-file or multi-file."""
    if (ws / "phase3-guidelines").is_dir():
        return "multi"
    if (ws / "phase3-guidelines.md").exists():
        return "single"
    return None


def detect_multi_stack(ws):
    """Check if guidelines use multi-stack layout (shared.md + stack dirs)."""
    guidelines_dir = ws / "phase3-guidelines"
    if not guidelines_dir.is_dir():
        return False, []
    shared = guidelines_dir / "shared.md"
    if not shared.exists():
        return False, []
    # Find stack directories (directories that contain index.md)
    stacks = []
    for d in sorted(guidelines_dir.iterdir()):
        if d.is_dir() and (d / "index.md").exists():
            stacks.append(d.name)
    return len(stacks) >= 2, stacks


def validate_phase3(ws, project_root=None):
    r = Result()

    # Check for multi-stack first
    is_multistack, stacks = detect_multi_stack(ws)
    if is_multistack:
        return validate_phase3_multistack(ws, stacks, project_root)

    mode = detect_guidelines_mode(ws)

    if mode == "multi":
        return validate_phase3_multi(ws, project_root)

    # Single-file mode
    p = ws / "phase3-guidelines.md"
    if not p.exists(): r.error("phase3-guidelines.md not found"); return r
    content = p.read_text()
    r.ok(f"Guidelines (single-file): {len(content.splitlines())} lines")
    for section in ["Architecture Overview", "Core Patterns", "Conventions",
                     "Canonical Examples", "Known Pitfalls"]:
        if section.lower() in content.lower(): r.ok(f"Has '{section}'")
        else: r.warn(f"Missing '{section}'")
    if len(content.splitlines()) < 50:
        r.warn("Very short (<50 lines)")

    if project_root:
        root = Path(project_root)
        file_paths = re.findall(r'`([^`\s]+\.[a-zA-Z0-9]+)`', content)
        for fp in file_paths:
            if fp.startswith(("/", "./")) or "/" in fp:
                clean = fp.lstrip("./")
                if not (root / clean).exists():
                    r.warn(f"Referenced path does not exist: {fp}")
    return r


def validate_phase3_multi(ws, project_root=None):
    """Validate multi-file guidelines directory."""
    r = Result()
    d = ws / "phase3-guidelines"
    if not d.is_dir():
        r.error("phase3-guidelines/ directory not found")
        return r
    r.ok("Guidelines (multi-file mode)")

    required = {
        "index.md": ["module", "canonical"],
        "architecture.md": ["architecture", "module"],
        "patterns.md": ["error handling", "data access"],
        "conventions.md": ["naming", "style"],
        "testing.md": ["test"],
        "pitfalls.md": ["pitfall"],
    }
    total_lines = 0
    for filename, expected_terms in required.items():
        f = d / filename
        if f.exists():
            content = f.read_text()
            lines = len(content.splitlines())
            total_lines += lines
            r.ok(f"{filename}: {lines} lines")
            for term in expected_terms:
                if term.lower() not in content.lower():
                    r.warn(f"{filename}: expected term '{term}' not found")
        else:
            r.error(f"Missing required file: {filename}")

    r.ok(f"Total guidelines: {total_lines} lines across {len(required)} files")

    # Check for module-notes (optional)
    mn = d / "module-notes"
    if mn.is_dir():
        notes = list(mn.glob("*.md"))
        if notes:
            r.ok(f"Module notes: {len(notes)} files")

    # Check index.md has links to other topic files
    idx = d / "index.md"
    if idx.exists():
        idx_content = idx.read_text()
        for fn in ["architecture.md", "patterns.md", "conventions.md", "testing.md", "pitfalls.md"]:
            if fn not in idx_content:
                r.warn(f"index.md does not link to {fn}")

    return r


def validate_phase3_multistack(ws, stacks, project_root=None):
    """Validate multi-stack guidelines (shared.md + per-stack directories)."""
    r = Result()
    d = ws / "phase3-guidelines"
    r.ok(f"Guidelines (multi-stack mode): {len(stacks)} stacks")

    # Validate shared.md
    shared = d / "shared.md"
    if shared.exists():
        content = shared.read_text()
        lines = len(content.splitlines())
        r.ok(f"shared.md: {lines} lines")
        for section in ["Git", "CI", "Deployment"]:
            if section.lower() in content.lower():
                r.ok(f"shared.md has '{section}' section")
            else:
                r.warn(f"shared.md missing '{section}' section")
    else:
        r.error("shared.md not found")

    # Validate each stack directory
    required_files = ["index.md", "patterns.md", "conventions.md", "testing.md", "pitfalls.md"]
    total_lines = len(shared.read_text().splitlines()) if shared.exists() else 0

    for stack_name in stacks:
        stack_dir = d / stack_name
        stack_lines = 0
        for fname in required_files:
            f = stack_dir / fname
            if f.exists():
                lines = len(f.read_text().splitlines())
                stack_lines += lines
                r.ok(f"{stack_name}/{fname}: {lines} lines")
            else:
                r.error(f"{stack_name}: missing required file {fname}")

        # Check for module-notes (optional)
        mn = stack_dir / "module-notes"
        if mn.is_dir():
            notes = list(mn.glob("*.md"))
            if notes:
                r.ok(f"{stack_name}/module-notes: {len(notes)} files")

        # Check index.md has links to topic files
        idx = stack_dir / "index.md"
        if idx.exists():
            idx_content = idx.read_text()
            for fn in ["patterns.md", "conventions.md", "testing.md", "pitfalls.md"]:
                if fn not in idx_content:
                    r.warn(f"{stack_name}/index.md does not link to {fn}")

        total_lines += stack_lines
        r.ok(f"{stack_name}: {stack_lines} lines across {len(required_files)} files")

    r.ok(f"Total guidelines: {total_lines} lines across all stacks + shared")
    return r


def find_plugin_dir(ws):
    """Find the plugin directory inside phase4-output/."""
    out = ws / "phase4-output"
    if not out.exists():
        return None
    # Look for a subdirectory containing .claude-plugin/
    for d in out.iterdir():
        if d.is_dir() and (d / ".claude-plugin").exists():
            return d
    return None


def validate_plugin(ws):
    """Validate plugin directory structure, plugin.json, and frontmatter rules."""
    r = Result()
    out = ws / "phase4-output"
    if not out.exists():
        r.error("phase4-output/ not found")
        return r

    plugin_dir = find_plugin_dir(ws)
    if not plugin_dir:
        r.error("No plugin directory found (expected a subdirectory with .claude-plugin/)")
        return r
    r.ok(f"Plugin directory: {plugin_dir.name}")

    # --- Validate plugin.json ---
    pj_path = plugin_dir / ".claude-plugin" / "plugin.json"
    pj = load_json(pj_path)
    if not pj:
        r.error(".claude-plugin/plugin.json missing or invalid JSON")
    else:
        r.ok("plugin.json is valid JSON")
        for field in ["name", "version", "description"]:
            if field not in pj:
                r.error(f"plugin.json missing required field: {field}")
        name = pj.get("name", "")
        if name:
            if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name):
                r.error(f"plugin.json name '{name}' is not kebab-case")
            if "claude" in name.lower() or "anthropic" in name.lower():
                r.error(f"plugin.json name must not contain 'claude' or 'anthropic'")
            r.ok(f"Plugin name: {name}")

    # --- Validate expected files ---
    expected = {
        "guidelines.md": "guidelines",
        "skills/ask/SKILL.md": "ask skill",
        "skills/plan/SKILL.md": "plan skill",
        "skills/implement/SKILL.md": "implement skill",
        "skills/review/SKILL.md": "review skill",
        "agents/explorer.md": "explorer",
        "agents/planner.md": "planner",
        "agents/implementer.md": "implementer",
        "agents/reviewer.md": "reviewer",
    }
    for path_str, label in expected.items():
        f = plugin_dir / path_str
        if f.exists():
            content = f.read_text()
            r.ok(f"{label}: {len(content.splitlines())} lines")
            # Check frontmatter exists for skills/agents
            if path_str.endswith(".md") and not content.startswith("---"):
                if "SKILL.md" in path_str or path_str.startswith("agents/"):
                    r.error(f"{label}: missing frontmatter")
            # Check guidelines reference
            if ("SKILL.md" in path_str or path_str.startswith("agents/")) and content.startswith("---"):
                if "guidelines" in content.lower():
                    if ".claude/guidelines.md" in content:
                        r.error(f"{label}: references .claude/guidelines.md (must use ${{CLAUDE_PLUGIN_ROOT}}/guidelines.md in plugin mode)")
                    elif "${CLAUDE_PLUGIN_ROOT}/guidelines.md" in content:
                        r.ok(f"{label}: correct CLAUDE_PLUGIN_ROOT guidelines reference")
                    else:
                        r.warn(f"{label}: references guidelines but not via ${{CLAUDE_PLUGIN_ROOT}}")
            # Check reviewer has no Write tools
            if "reviewer" in path_str and path_str.startswith("agents/"):
                fm = extract_frontmatter(content)
                if fm and "Write" in fm:
                    r.warn(f"{label}: should not have Write tools")
        else:
            r.warn(f"Missing: {label}")

    # --- Critical: verify NO name field in any SKILL.md or agent frontmatter ---
    # Also run spec compliance checks (description, XML tags, third-person) in plugin mode
    skill_files = list(plugin_dir.glob("skills/*/SKILL.md"))
    agent_files = list(plugin_dir.glob("agents/*.md"))
    for f in skill_files + agent_files:
        content = f.read_text()
        fm = extract_frontmatter(content)
        if fm:
            name_field = parse_frontmatter_field(fm, "name")
            if name_field:
                rel = f.relative_to(plugin_dir)
                r.error(f"{rel}: frontmatter contains 'name' field — must be omitted in plugin mode (causes namespace bypass)")
        # Run spec compliance without requiring name (plugin mode)
        rel = str(f.relative_to(plugin_dir))
        validate_spec_compliance(rel, content, None, r, require_name=False)

    # --- Validate manifest.json is outside plugin dir ---
    if (plugin_dir / "manifest.json").exists():
        r.warn("manifest.json is inside the plugin directory (should be at phase4-output/manifest.json)")
    manifest = load_json(out / "manifest.json")
    if manifest:
        r.ok("manifest.json found at phase4-output/ (correct location)")

    # --- Check README.md ---
    if (plugin_dir / "README.md").exists():
        r.ok("README.md present")
    else:
        r.warn("No README.md in plugin directory")

    # --- Check guidelines mode ---
    if (plugin_dir / "guidelines").is_dir():
        r.ok("Multi-file guidelines detected in plugin")
    elif (plugin_dir / "guidelines.md").exists():
        r.ok("Single-file guidelines in plugin")
    else:
        r.warn("No guidelines found in plugin directory")

    # --- Check specialized reviewer sub-agents ---
    validate_reviewer_subagents(plugin_dir, r)

    return r


def validate_phase4(ws, delivery_mode="standalone"):
    if delivery_mode == "plugin":
        return validate_plugin(ws)

    r = Result()
    out = ws / "phase4-output"
    if not out.exists(): r.error("phase4-output/ not found"); return r

    expected = {
        "skills/ask/SKILL.md": "ask skill",
        "skills/plan/SKILL.md": "plan skill",
        "skills/implement/SKILL.md": "implement skill",
        "skills/review/SKILL.md": "review skill",
        "agents/explorer.md": "explorer",
        "agents/planner.md": "planner",
        "agents/implementer.md": "implementer",
        "agents/reviewer.md": "reviewer",
    }

    # Check guidelines (single-file or multi-file)
    if (out / "guidelines").is_dir():
        r.ok("Multi-file guidelines detected")
    elif (out / "guidelines.md").exists():
        r.ok(f"guidelines: {len((out / 'guidelines.md').read_text().splitlines())} lines")
    else:
        r.warn("Missing: guidelines (no guidelines.md or guidelines/ directory)")

    for path_str, label in expected.items():
        f = out / path_str
        if f.exists():
            content = f.read_text()
            r.ok(f"{label}: {len(content.splitlines())} lines")
            if path_str.endswith(".md") and not content.startswith("---"):
                if "SKILL.md" in path_str or path_str.startswith("agents/"):
                    r.error(f"{label}: missing frontmatter")
            if "SKILL.md" in path_str and "guidelines" not in content.lower():
                r.warn(f"{label}: no reference to guidelines.md")
            if "reviewer" in path_str and path_str.startswith("agents/"):
                fm = extract_frontmatter(content)
                if fm and "Write" in fm:
                    r.warn(f"{label}: should not have Write tools")
            # Check frontmatter fields for SKILL.md and agent files
            if "SKILL.md" in path_str or path_str.startswith("agents/"):
                fm = extract_frontmatter(content)
                if fm:
                    is_agent = path_str.startswith("agents/")
                    tools_key = "tools" if is_agent else "allowed-tools"
                    if tools_key not in fm:
                        r.warn(f"{label}: frontmatter missing '{tools_key}'")
                    if "model" not in fm:
                        r.warn(f"{label}: frontmatter missing 'model'")
        else:
            r.warn(f"Missing: {label}")

    # Validate manifest.json
    manifest = load_json(out / "manifest.json")
    if not manifest:
        r.warn("Missing or invalid manifest.json")
    else:
        r.ok("manifest.json is valid JSON")
        for field in ["generated_at", "project_name", "modules_analyzed", "generated", "total_lines"]:
            if field not in manifest:
                r.error(f"manifest.json missing required field: {field}")
        generated = manifest.get("generated", [])
        for entry in generated:
            entry_path = entry.get("path")
            if entry_path and not (out / entry_path).exists():
                r.warn(f"manifest.json references non-existent path: {entry_path}")

    # Agent Skills spec compliance for all generated skills and agents
    spec_files = {
        "skills/ask/SKILL.md": "ask",
        "skills/plan/SKILL.md": "plan",
        "skills/implement/SKILL.md": "implement",
        "skills/review/SKILL.md": "review",
        "agents/explorer.md": None,
        "agents/planner.md": None,
        "agents/implementer.md": None,
        "agents/reviewer.md": None,
    }
    for path_str, parent_dir in spec_files.items():
        f = out / path_str
        if f.exists():
            validate_spec_compliance(path_str, f.read_text(), parent_dir, r)

    # Validate specialized reviewer sub-agents (optional)
    validate_reviewer_subagents(out, r)

    return r


def validate_reviewer_subagents(out_dir, r):
    """Validate specialized reviewer sub-agents if present."""
    reviewers_dir = out_dir / "agents" / "reviewers"
    if not reviewers_dir.exists():
        return  # Optional — no error if missing

    reviewer_files = list(reviewers_dir.glob("*.md"))
    if not reviewer_files:
        r.warn("agents/reviewers/ directory exists but is empty")
        return

    r.ok(f"{len(reviewer_files)} specialized reviewer agents")
    for f in reviewer_files:
        content = f.read_text()
        label = f"reviewers/{f.name}"
        if not content.startswith("---"):
            r.error(f"{label}: missing frontmatter")
            continue
        fm = extract_frontmatter(content)
        if fm:
            if "Write" in fm or "Edit" in fm:
                r.error(f"{label}: reviewer must be read-only (has Write/Edit tools)")
            if "tools" not in fm:
                r.warn(f"{label}: frontmatter missing 'tools'")
            if "model" not in fm:
                r.warn(f"{label}: frontmatter missing 'model'")
        if "guidelines" not in content.lower():
            r.warn(f"{label}: no reference to guidelines")


def validate_phase5(ws):
    r = Result()
    data = load_json(ws / "phase5-evaluation.json")
    if not data: r.error("Cannot read phase5-evaluation.json"); return r
    r.ok("Evaluation file is valid JSON")

    skills_tested = data.get("skills_tested")
    if skills_tested is None:
        r.error("Missing 'skills_tested' array")
    elif not isinstance(skills_tested, list):
        r.error("'skills_tested' is not an array")
    else:
        r.ok(f"{len(skills_tested)} skills tested")
        for skill in skills_tested:
            name = skill.get("skill", "?")
            prompts = skill.get("test_prompts", [])
            if len(prompts) < 2:
                r.warn(f"Skill '{name}' has fewer than 2 test_prompts ({len(prompts)})")
            overall = skill.get("overall", "")
            if overall == "fail":
                r.error(f"Skill '{name}' has overall status 'fail'")
            for tp in prompts:
                if tp.get("result") == "fail":
                    r.warn(f"Skill '{name}' has a failing test prompt: {tp.get('prompt', '?')[:60]}")
                if "references_real_files" in tp and not tp["references_real_files"]:
                    r.warn(f"Skill '{name}' prompt does not reference real files")

    agents_tested = data.get("agents_tested")
    if agents_tested is None:
        r.error("Missing 'agents_tested' array")
    elif not isinstance(agents_tested, list):
        r.error("'agents_tested' is not an array")
    else:
        r.ok(f"{len(agents_tested)} agents tested")
        for agent in agents_tested:
            name = agent.get("agent", "?")
            prompts = agent.get("test_prompts", [])
            if len(prompts) < 2:
                r.warn(f"Agent '{name}' has fewer than 2 test_prompts ({len(prompts)})")
            overall = agent.get("overall", "")
            if overall == "fail":
                r.error(f"Agent '{name}' has overall status 'fail'")
            for tp in prompts:
                if tp.get("result") == "fail":
                    r.warn(f"Agent '{name}' has a failing test prompt: {tp.get('prompt', '?')[:60]}")
                if "references_real_files" in tp and not tp["references_real_files"]:
                    r.warn(f"Agent '{name}' prompt does not reference real files")

    if not data.get("summary"):
        r.warn("Missing 'summary'")
    else:
        r.ok("Has summary")

    # Validate benchmark section
    benchmark = data.get("benchmark")
    if not benchmark:
        r.warn("Missing 'benchmark' — no quantitative comparison data")
    else:
        r.ok("Has benchmark")
        for metric in ["pass_rate", "tokens", "duration_ms", "quality_score"]:
            if metric not in benchmark:
                r.warn(f"Benchmark missing '{metric}'")
        pr = benchmark.get("pass_rate", {})
        if pr.get("with_skill") is not None and pr.get("without_skill") is not None:
            delta = pr.get("delta", 0)
            if delta <= 0:
                r.warn(f"Skills did not improve pass rate (delta: {delta})")
            else:
                r.ok(f"Pass rate improved by {delta:.0%}" if isinstance(delta, float) else f"Pass rate delta: {delta}")
        qs = benchmark.get("quality_score", {})
        if qs.get("delta") is not None and qs["delta"] <= 0:
            r.warn(f"Skills did not improve quality score (delta: {qs['delta']})")

    # Validate timing data in test prompts
    all_items = (data.get("skills_tested") or []) + (data.get("agents_tested") or [])
    timing_count = 0
    for item in all_items:
        for tp in item.get("test_prompts", []):
            if tp.get("timing"):
                timing_count += 1
    if timing_count == 0 and all_items:
        r.warn("No test prompts have timing data")
    elif timing_count > 0:
        r.ok(f"{timing_count} test prompts with timing data")

    return r


def validate_cross_phase(ws, verbose=False, delivery_mode="standalone"):
    """Cross-phase validation: verify consistency across all phase outputs."""
    r = Result()

    # Load all available data
    module_map = load_json(ws / "phase1-module-map.json")

    # Handle both single-file and multi-file guidelines
    guidelines_mode = detect_guidelines_mode(ws)
    guidelines = ""
    if guidelines_mode == "multi":
        guidelines_dir = ws / "phase3-guidelines"
        for md_file in sorted(guidelines_dir.glob("**/*.md")):
            guidelines += md_file.read_text() + "\n"
    elif guidelines_mode == "single":
        guidelines = (ws / "phase3-guidelines.md").read_text()

    out = ws / "phase4-output"

    # In plugin mode, resolve to the plugin subdirectory
    if delivery_mode == "plugin":
        plugin_dir = find_plugin_dir(ws)
        if plugin_dir:
            out = plugin_dir
        else:
            r.warn("Cannot run cross-phase validation: no plugin directory found")
            return r

    if not module_map:
        r.warn("Cannot run cross-phase validation: missing phase1-module-map.json")
        return r
    if not guidelines:
        r.warn("Cannot run cross-phase validation: missing phase3-guidelines.md")
        return r
    if not out.exists():
        r.warn("Cannot run cross-phase validation: missing phase4-output/")
        return r

    modules = module_map.get("modules", [])
    module_names = {m["name"] for m in modules}

    # 1. Every module from Phase 1 covered by at least one skill
    skills_content = ""
    for skill_path in ["skills/ask/SKILL.md", "skills/implement/SKILL.md", "skills/review/SKILL.md"]:
        sp = out / skill_path
        if sp.exists():
            skills_content += sp.read_text() + "\n"
    uncovered = {name for name in module_names if name.lower() not in skills_content.lower()}
    if uncovered:
        r.warn(f"Modules not mentioned in any skill: {uncovered}")
    else:
        r.ok("All modules referenced in at least one skill")

    # 2. Every canonical example from Phase 3 appears in at least one skill
    canonical_lines = []
    in_canonical = False
    for line in guidelines.splitlines():
        if "canonical example" in line.lower():
            in_canonical = True
            continue
        if in_canonical and line.startswith("##"):
            break
        if in_canonical and "`" in line:
            paths = re.findall(r'`([^`\s]+\.[a-zA-Z0-9]+)`', line)
            canonical_lines.extend(paths)
    missing_canonical = [p for p in canonical_lines if p not in skills_content]
    if missing_canonical and canonical_lines:
        r.warn(f"Canonical examples not in any skill: {missing_canonical[:5]}")
    elif canonical_lines:
        r.ok(f"All {len(canonical_lines)} canonical examples referenced in skills")

    # 3. Every pitfall from Phase 3 covered by the review checklist
    review_path = out / "skills/review/SKILL.md"
    review_content = review_path.read_text() if review_path.exists() else ""
    pitfall_lines = []
    in_pitfalls = False
    for line in guidelines.splitlines():
        if "pitfall" in line.lower() and line.startswith("##"):
            in_pitfalls = True
            continue
        if in_pitfalls and line.startswith("##"):
            break
        if in_pitfalls and line.strip().startswith("-"):
            pitfall_lines.append(line.strip())
    if pitfall_lines and not review_content:
        r.warn("Pitfalls found in guidelines but review skill is missing")
    elif pitfall_lines:
        r.ok(f"{len(pitfall_lines)} pitfalls found in guidelines (verify review covers them)")

    # 4. Implement skill patterns match guidelines' Core Patterns
    impl_path = out / "skills/implement/SKILL.md"
    impl_content = impl_path.read_text() if impl_path.exists() else ""
    if impl_content and "pattern" not in impl_content.lower():
        r.warn("Implement skill does not mention any patterns")
    elif impl_content:
        r.ok("Implement skill references patterns")

    # 5. Review checklist covers guidelines' Conventions section
    if review_content and "convention" not in review_content.lower() and "naming" not in review_content.lower():
        r.warn("Review skill does not reference conventions")
    elif review_content:
        r.ok("Review skill references conventions/naming")

    # 6. Evaluation results (if Phase 5 ran) have no fail overall statuses
    eval_data = load_json(ws / "phase5-evaluation.json")
    if eval_data:
        all_tested = eval_data.get("skills_tested", []) + eval_data.get("agents_tested", [])
        failures = [t for t in all_tested if t.get("overall") == "fail"]
        if failures:
            names = [t.get("skill") or t.get("agent") for t in failures]
            r.error(f"Evaluation failures: {names}")
        else:
            r.ok(f"All {len(all_tested)} evaluated items passed")

    # 7. Review patterns from Phase 2 reflected in guidelines (if available)
    reviews = load_json(ws / "phase2-reviews.json")
    if reviews and reviews.get("platform") != "unavailable":
        high_conf = [p for p in reviews.get("review_patterns", [])
                     if p.get("confidence") == "high"]
        if high_conf and guidelines:
            found = sum(1 for p in high_conf
                        if p.get("pattern", "").lower().split()[0] in guidelines.lower())
            if found == 0:
                r.warn(f"{len(high_conf)} high-confidence review patterns not reflected in guidelines")
            else:
                r.ok(f"Review patterns: {found}/{len(high_conf)} high-confidence patterns found in guidelines")

        anti_patterns = [p for p in reviews.get("review_patterns", [])
                         if p.get("category") == "anti-pattern"]
        if anti_patterns and guidelines:
            pitfalls_lower = guidelines.lower()
            if "pitfall" in pitfalls_lower:
                r.ok(f"{len(anti_patterns)} anti-patterns from reviews (verify they appear in pitfalls)")
            else:
                r.warn("Anti-patterns found in reviews but guidelines has no pitfalls section")

    return r


def validate_state(ws):
    """Validate state.json structure and field values."""
    r = Result()
    data = load_json(ws / "state.json")
    if not data:
        r.error("Cannot read state.json")
        return r
    r.ok("state.json is valid JSON")

    # Required top-level fields
    for field in ["started_at", "updated_at", "project_root", "phases"]:
        if field not in data:
            r.error(f"state.json missing required field: {field}")

    # Validate timestamps are ISO 8601-ish
    for ts_field in ["started_at", "updated_at"]:
        val = data.get(ts_field)
        if val and not re.match(r'^\d{4}-\d{2}-\d{2}T', str(val)):
            r.warn(f"state.json {ts_field} does not look like ISO 8601: {val}")

    # Validate phases
    phases = data.get("phases", {})
    valid_statuses = {"pending", "in_progress", "completed", "skipped", "failed"}
    for phase_id in ["1", "2", "3", "4", "5"]:
        if phase_id not in phases:
            r.error(f"state.json missing phase {phase_id}")
            continue
        phase = phases[phase_id]
        status = phase.get("status")
        if status not in valid_statuses:
            r.error(f"Phase {phase_id} has invalid status: {status}")
        else:
            r.ok(f"Phase {phase_id}: {status}")
        if status in ("completed", "failed") and not phase.get(f"{'completed' if status == 'completed' else 'started'}_at"):
            r.warn(f"Phase {phase_id} is {status} but missing timestamp")

    # Validate user_choices
    choices = data.get("user_choices", {})
    if not choices:
        r.warn("state.json missing user_choices")
    else:
        dm = choices.get("delivery_mode")
        if dm and dm not in ("standalone", "plugin", "review-only"):
            r.error(f"Invalid delivery_mode: {dm}")
        gm = choices.get("guidelines_mode")
        if gm and gm not in ("single", "multi"):
            r.error(f"Invalid guidelines_mode: {gm}")

    # Validate stack_mode and stacks
    choices = data.get("user_choices", {})
    stack_mode = choices.get("stack_mode")
    if stack_mode and stack_mode not in ("single", "multi"):
        r.warn(f"Invalid stack_mode: {stack_mode}")
    stacks = choices.get("stacks", [])
    if stack_mode == "multi" and len(stacks) < 2:
        r.warn(f"stack_mode is 'multi' but only {len(stacks)} stacks defined")
    for stack in stacks:
        if not stack.get("name"):
            r.warn("Stack missing 'name' field")
        if not stack.get("modules"):
            r.warn(f"Stack '{stack.get('name')}' has no modules")

    return r


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--phase", required=True,
                   help="Phase to validate (1-5, 'all', or 'state')")
    p.add_argument("--workspace", required=True)
    p.add_argument("--project-root", default=None)
    p.add_argument("--delivery-mode", default="standalone", choices=["standalone", "plugin"],
                   help="Delivery mode to validate against (default: standalone)")
    p.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = p.parse_args()

    ws = Path(args.workspace)
    if not ws.exists(): print(f"Not found: {ws}"); sys.exit(1)

    dm = args.delivery_mode
    validators = {
        "1": ("Phase 1: Discovery", lambda w: validate_phase1(w)),
        "2": ("Phase 2: Exploration", lambda w: validate_phase2(w, project_root=args.project_root)),
        "3": ("Phase 3: Synthesis", lambda w: validate_phase3(w, project_root=args.project_root)),
        "4": ("Phase 4: Generation", lambda w: validate_phase4(w, delivery_mode=dm)),
        "5": ("Phase 5: Evaluation", lambda w: validate_phase5(w)),
    }
    if args.phase == "state":
        print(f"\n{'='*50}\n  State Validation\n{'='*50}")
        result = validate_state(ws)
        print(result.summary())
        sys.exit(0 if result.passed else 1)

    phases = list(validators.keys()) if args.phase == "all" else [args.phase]
    ok = True

    # Always validate state.json first when running all phases
    if args.phase == "all":
        print(f"\n{'='*50}\n  State Validation\n{'='*50}")
        result = validate_state(ws)
        print(result.summary())
        if not result.passed: ok = False

    for phase in phases:
        label, fn = validators[phase]
        print(f"\n{'='*50}\n  {label}\n{'='*50}")
        result = fn(ws)
        print(result.summary())
        if not result.passed: ok = False

    # Run cross-phase validation when --phase all
    if args.phase == "all":
        print(f"\n{'='*50}\n  Cross-Phase Validation\n{'='*50}")
        result = validate_cross_phase(ws, verbose=args.verbose, delivery_mode=dm)
        print(result.summary())
        if not result.passed: ok = False

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

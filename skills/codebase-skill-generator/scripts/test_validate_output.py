#!/usr/bin/env python3
"""Tests for validate_output.py."""

import json, os, shutil, tempfile, unittest
from pathlib import Path

from validate_output import (
    Result,
    extract_frontmatter,
    parse_frontmatter_field,
    validate_spec_compliance,
    validate_phase1,
    validate_phase2,
    validate_phase3,
    detect_guidelines_mode,
    validate_phase4,
    validate_plugin,
    validate_reviewer_subagents,
    validate_phase5,
    validate_cross_phase,
    validate_state,
)


class TestResult(unittest.TestCase):
    def test_empty_result_passes(self):
        r = Result()
        self.assertTrue(r.passed)

    def test_error_causes_failure(self):
        r = Result()
        r.error("bad")
        self.assertFalse(r.passed)

    def test_warning_still_passes(self):
        r = Result()
        r.warn("meh")
        self.assertTrue(r.passed)

    def test_summary_contains_status(self):
        r = Result()
        r.ok("good")
        self.assertIn("PASSED", r.summary())
        r.error("bad")
        self.assertIn("FAILED", r.summary())


class TestExtractFrontmatter(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(extract_frontmatter("---\nfoo: bar\n---\nbody"), "\nfoo: bar\n")

    def test_no_frontmatter(self):
        self.assertIsNone(extract_frontmatter("no frontmatter here"))

    def test_unclosed(self):
        self.assertIsNone(extract_frontmatter("---\nfoo: bar\n"))


class TestParseFrontmatterField(unittest.TestCase):
    def test_simple_value(self):
        fm = "name: my-skill\ndescription: hello"
        self.assertEqual(parse_frontmatter_field(fm, "name"), "my-skill")
        self.assertEqual(parse_frontmatter_field(fm, "description"), "hello")

    def test_missing_field(self):
        self.assertIsNone(parse_frontmatter_field("name: foo", "description"))

    def test_multiline_folded(self):
        fm = "description: >\n  First line\n  second line\ntools: Read"
        result = parse_frontmatter_field(fm, "description")
        self.assertIn("First line", result)
        self.assertIn("second line", result)

    def test_multiline_literal(self):
        fm = "description: |\n  Line one\n  Line two\ntools: Read"
        result = parse_frontmatter_field(fm, "description")
        self.assertIn("Line one", result)

    def test_quoted_value(self):
        fm = "name: \"my-skill\""
        self.assertEqual(parse_frontmatter_field(fm, "name"), "my-skill")

    def test_duplicate_lines_uses_first_match(self):
        # Verifies the index-based fix works with duplicate content
        fm = "  indent line\nname: first\n  indent line\ntools: Read"
        self.assertEqual(parse_frontmatter_field(fm, "name"), "first")


class TestValidateSpecCompliance(unittest.TestCase):
    def _content(self, fm_body):
        return f"---\n{fm_body}\n---\n# Body"

    def test_valid_install_mode(self):
        r = Result()
        validate_spec_compliance(
            "test.md",
            self._content("name: my-skill\ndescription: Analyzes code patterns"),
            "my-skill", r, require_name=True,
        )
        self.assertTrue(r.passed)

    def test_missing_name_install_mode(self):
        r = Result()
        validate_spec_compliance(
            "test.md",
            self._content("description: Analyzes code"),
            None, r, require_name=True,
        )
        self.assertFalse(r.passed)

    def test_missing_name_plugin_mode_ok(self):
        r = Result()
        validate_spec_compliance(
            "test.md",
            self._content("description: Analyzes code"),
            None, r, require_name=False,
        )
        self.assertTrue(r.passed)

    def test_xml_tags_in_description(self):
        r = Result()
        validate_spec_compliance(
            "test.md",
            self._content("name: foo\ndescription: >\n  Has <example> tags"),
            None, r,
        )
        self.assertFalse(r.passed)

    def test_name_not_kebab_case(self):
        r = Result()
        validate_spec_compliance(
            "test.md",
            self._content("name: MySkill\ndescription: Does things"),
            None, r,
        )
        # Should warn, not error
        self.assertTrue(r.passed)
        self.assertTrue(any("kebab" in w for w in r.warnings))

    def test_name_contains_claude(self):
        r = Result()
        validate_spec_compliance(
            "test.md",
            self._content("name: claude-helper\ndescription: Does things"),
            None, r,
        )
        self.assertFalse(r.passed)

    def test_first_person_description(self):
        r = Result()
        validate_spec_compliance(
            "test.md",
            self._content("name: foo\ndescription: I analyze code"),
            None, r,
        )
        self.assertTrue(any("third person" in w for w in r.warnings))


class TestValidatePhase1(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.ws)

    def _write_map(self, data):
        (self.ws / "phase1-module-map.json").write_text(json.dumps(data))

    def test_valid_map(self):
        self._write_map({
            "project_name": "test",
            "modules": [
                {"name": "core", "depends_on": [], "type": "library", "entry_points": ["index.ts"]},
                {"name": "api", "depends_on": ["core"], "type": "service", "entry_points": ["server.ts"]},
            ],
            "recommended_exploration_order": ["core", "api"],
        })
        r = validate_phase1(self.ws)
        self.assertTrue(r.passed)

    def test_missing_file(self):
        r = validate_phase1(self.ws)
        self.assertFalse(r.passed)

    def test_duplicate_names(self):
        self._write_map({
            "modules": [
                {"name": "core", "depends_on": []},
                {"name": "core", "depends_on": []},
            ],
        })
        r = validate_phase1(self.ws)
        self.assertFalse(r.passed)

    def test_unknown_dependency(self):
        self._write_map({
            "modules": [{"name": "api", "depends_on": ["nonexistent"]}],
        })
        r = validate_phase1(self.ws)
        self.assertTrue(any("unknown" in w for w in r.warnings))

    def test_invalid_exploration_order(self):
        self._write_map({
            "modules": [{"name": "core", "depends_on": []}],
            "recommended_exploration_order": ["core", "nonexistent"],
        })
        r = validate_phase1(self.ws)
        self.assertTrue(any("unknown modules" in w for w in r.warnings))

    def test_submodule_validation(self):
        self._write_map({
            "modules": [{
                "name": "backend",
                "depends_on": [],
                "path": "src/backend",
                "submodules": [
                    {"name": "billing", "path": "src/backend/billing"},
                    {"name": "auth", "path": "src/other/auth"},  # not under parent
                ],
            }],
        })
        r = validate_phase1(self.ws)
        self.assertTrue(any("not under parent" in w for w in r.warnings))


class TestValidatePhase2(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / "phase2-profiles").mkdir()

    def tearDown(self):
        shutil.rmtree(self.ws)

    def test_valid_profiles(self):
        # Write module map
        (self.ws / "phase1-module-map.json").write_text(json.dumps({
            "modules": [{"name": "core", "depends_on": []}],
        }))
        # Write profile
        (self.ws / "phase2-profiles" / "core.json").write_text(json.dumps({
            "module_name": "core",
            "code_samples": {"canonical_implementation": {"file": "src/core.ts"}},
            "pitfalls": [{"description": "watch out"}],
        }))
        r = validate_phase2(self.ws)
        self.assertTrue(r.passed)

    def test_no_profiles(self):
        r = validate_phase2(self.ws)
        self.assertFalse(r.passed)


class TestDetectGuidelinesMode(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.ws)

    def test_single_file(self):
        (self.ws / "phase3-guidelines.md").write_text("# Guidelines")
        self.assertEqual(detect_guidelines_mode(self.ws), "single")

    def test_multi_file(self):
        (self.ws / "phase3-guidelines").mkdir()
        self.assertEqual(detect_guidelines_mode(self.ws), "multi")

    def test_neither(self):
        self.assertIsNone(detect_guidelines_mode(self.ws))


class TestValidatePhase3(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.ws)

    def test_single_file_valid(self):
        content = "\n".join([
            "# Project — Development Guidelines",
            "## Architecture Overview",
            "Some architecture content " * 5,
            "## Core Patterns",
            "Pattern content " * 5,
            "## Conventions",
            "Convention content " * 5,
            "## Canonical Examples",
            "| File | What |",
            "## Known Pitfalls",
            "Pitfall content " * 5,
        ] + ["filler line"] * 50)
        (self.ws / "phase3-guidelines.md").write_text(content)
        r = validate_phase3(self.ws)
        self.assertTrue(r.passed)

    def test_multi_file_valid(self):
        d = self.ws / "phase3-guidelines"
        d.mkdir()
        (d / "index.md").write_text("# Index\nmodule map\ncanonical\n[arch](architecture.md)\n[pat](patterns.md)\n[conv](conventions.md)\n[test](testing.md)\n[pit](pitfalls.md)")
        (d / "architecture.md").write_text("# Architecture\narchitecture overview\nmodule boundaries")
        (d / "patterns.md").write_text("# Patterns\nerror handling\ndata access patterns")
        (d / "conventions.md").write_text("# Conventions\nnaming rules\nstyle guide")
        (d / "testing.md").write_text("# Testing\ntest framework\ntest patterns")
        (d / "pitfalls.md").write_text("# Pitfalls\ncommon pitfall items")
        r = validate_phase3(self.ws)
        self.assertTrue(r.passed)

    def test_missing_file(self):
        r = validate_phase3(self.ws)
        self.assertFalse(r.passed)


class TestValidatePhase5(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.ws)

    def test_valid_evaluation(self):
        data = {
            "evaluated_at": "2024-01-01T00:00:00Z",
            "iteration": 1,
            "skills_tested": [{
                "skill": "ask",
                "test_prompts": [
                    {"prompt": "q1", "result": "pass", "assertions_passed": 3, "assertions_total": 3},
                    {"prompt": "q2", "result": "pass", "assertions_passed": 2, "assertions_total": 2},
                ],
                "overall": "pass",
            }],
            "agents_tested": [{
                "agent": "explorer",
                "test_prompts": [
                    {"prompt": "q1", "result": "pass", "assertions_passed": 2, "assertions_total": 2},
                    {"prompt": "q2", "result": "pass", "assertions_passed": 1, "assertions_total": 1},
                ],
                "overall": "pass",
            }],
            "summary": {"total_tested": 2, "passed": 2, "failed": 0, "partial": 0},
            "benchmark": {
                "pass_rate": {"with_skill": 0.9, "without_skill": 0.4, "delta": 0.5},
                "tokens": {"with_skill_mean": 1000, "without_skill_mean": 2000, "delta_pct": -50},
                "duration_ms": {"with_skill_mean": 5000, "without_skill_mean": 10000, "delta_pct": -50},
                "quality_score": {"with_skill_mean": 4.0, "without_skill_mean": 2.0, "delta": 2.0},
            },
        }
        (self.ws / "phase5-evaluation.json").write_text(json.dumps(data))
        r = validate_phase5(self.ws)
        self.assertTrue(r.passed)

    def test_failing_skill(self):
        data = {
            "skills_tested": [{"skill": "ask", "test_prompts": [], "overall": "fail"}],
            "agents_tested": [],
        }
        (self.ws / "phase5-evaluation.json").write_text(json.dumps(data))
        r = validate_phase5(self.ws)
        self.assertFalse(r.passed)


def _make_skill_md(name=None, desc="Analyzes code patterns"):
    """Helper: generate a valid SKILL.md content string."""
    name_line = f"name: {name}\n" if name else ""
    return f"---\n{name_line}description: {desc}\nallowed-tools: Read, Glob, Grep\nmodel: sonnet\n---\n# Skill\nReferences guidelines.md for patterns."


def _make_agent_md(name=None, desc="Analyzes code patterns", tools="Read, Glob, Grep"):
    """Helper: generate a valid agent .md content string."""
    name_line = f"name: {name}\n" if name else ""
    return f"---\n{name_line}description: {desc}\ntools: {tools}\nmodel: sonnet\n---\n# Agent\nReferences guidelines.md for conventions and naming."


def _populate_phase4_install(ws):
    """Populate a workspace with valid phase4-output/ for install mode."""
    out = ws / "phase4-output"
    out.mkdir(parents=True)
    (out / "guidelines.md").write_text("# Guidelines\n## Architecture Overview\nContent")
    for skill in ["ask", "plan", "implement", "review"]:
        d = out / "skills" / skill
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(_make_skill_md(name=skill))
    for agent_name, tools in [("explorer", "Read, Glob, Grep"),
                               ("planner", "Read, Glob, Grep"),
                               ("implementer", "Read, Write, Edit, Glob, Grep, Bash"),
                               ("reviewer", "Read, Glob, Grep")]:
        (out / "agents").mkdir(exist_ok=True)
        (out / "agents" / f"{agent_name}.md").write_text(_make_agent_md(name=agent_name, tools=tools))
    # Manifest
    (out / "manifest.json").write_text(json.dumps({
        "generated_at": "2024-01-01T00:00:00Z",
        "project_name": "test",
        "modules_analyzed": 2,
        "generated": [{"path": "guidelines.md", "type": "guidelines", "lines": 3, "description": "Guidelines"}],
        "total_lines": 3,
    }))


def _populate_phase4_plugin(ws):
    """Populate a workspace with valid phase4-output/potion/ for plugin mode."""
    out = ws / "phase4-output"
    out.mkdir(parents=True)
    plugin = out / "potion"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "potion", "version": "1.0.0", "description": "Test skill pack",
    }))
    (plugin / "guidelines.md").write_text("# Guidelines\nContent")
    (plugin / "README.md").write_text("# README")
    for skill in ["ask", "plan", "implement", "review"]:
        d = plugin / "skills" / skill
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(_make_skill_md())  # no name in plugin mode
    for agent_name, tools in [("explorer", "Read, Glob, Grep"),
                               ("planner", "Read, Glob, Grep"),
                               ("implementer", "Read, Write, Edit, Glob, Grep, Bash"),
                               ("reviewer", "Read, Glob, Grep")]:
        (plugin / "agents").mkdir(exist_ok=True)
        (plugin / "agents" / f"{agent_name}.md").write_text(_make_agent_md(tools=tools))
    # Manifest outside plugin dir
    (out / "manifest.json").write_text(json.dumps({
        "generated_at": "2024-01-01T00:00:00Z",
        "project_name": "test",
        "modules_analyzed": 2,
        "generated": [],
        "total_lines": 0,
    }))


class TestValidatePhase4Install(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.ws)

    def test_valid_install(self):
        _populate_phase4_install(self.ws)
        r = validate_phase4(self.ws, delivery_mode="install")
        self.assertTrue(r.passed)

    def test_missing_output_dir(self):
        r = validate_phase4(self.ws, delivery_mode="install")
        self.assertFalse(r.passed)

    def test_missing_guidelines_warns(self):
        _populate_phase4_install(self.ws)
        (self.ws / "phase4-output" / "guidelines.md").unlink()
        r = validate_phase4(self.ws, delivery_mode="install")
        self.assertTrue(any("guidelines" in w.lower() for w in r.warnings))

    def test_multi_guidelines_install(self):
        """C5 fix: install mode should accept guidelines/ directory."""
        _populate_phase4_install(self.ws)
        (self.ws / "phase4-output" / "guidelines.md").unlink()
        gdir = self.ws / "phase4-output" / "guidelines"
        gdir.mkdir()
        (gdir / "index.md").write_text("# Index")
        r = validate_phase4(self.ws, delivery_mode="install")
        self.assertTrue(any("Multi-file" in i for i in r.info))

    def test_missing_frontmatter_errors(self):
        _populate_phase4_install(self.ws)
        (self.ws / "phase4-output" / "skills" / "ask" / "SKILL.md").write_text("# No frontmatter")
        r = validate_phase4(self.ws, delivery_mode="install")
        self.assertFalse(r.passed)

    def test_reviewer_write_tools_warns(self):
        _populate_phase4_install(self.ws)
        (self.ws / "phase4-output" / "agents" / "reviewer.md").write_text(
            _make_agent_md(name="reviewer", tools="Read, Write, Glob, Grep"))
        r = validate_phase4(self.ws, delivery_mode="install")
        self.assertTrue(any("Write" in w for w in r.warnings))

    def test_missing_manifest_warns(self):
        _populate_phase4_install(self.ws)
        (self.ws / "phase4-output" / "manifest.json").unlink()
        r = validate_phase4(self.ws, delivery_mode="install")
        self.assertTrue(any("manifest" in w.lower() for w in r.warnings))


class TestValidatePlugin(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.ws)

    def test_valid_plugin(self):
        _populate_phase4_plugin(self.ws)
        r = validate_plugin(self.ws)
        self.assertTrue(r.passed)

    def test_missing_plugin_dir(self):
        (self.ws / "phase4-output").mkdir()
        r = validate_plugin(self.ws)
        self.assertFalse(r.passed)

    def test_name_in_plugin_skill_errors(self):
        """C4 scenario: name field in plugin mode should error."""
        _populate_phase4_plugin(self.ws)
        plugin = self.ws / "phase4-output" / "potion"
        (plugin / "skills" / "ask" / "SKILL.md").write_text(_make_skill_md(name="ask"))
        r = validate_plugin(self.ws)
        self.assertFalse(r.passed)
        self.assertTrue(any("name" in e.lower() for e in r.errors))

    def test_invalid_plugin_json_errors(self):
        _populate_phase4_plugin(self.ws)
        (self.ws / "phase4-output" / "potion" / ".claude-plugin" / "plugin.json").write_text("not json")
        r = validate_plugin(self.ws)
        self.assertFalse(r.passed)

    def test_plugin_json_missing_fields(self):
        _populate_phase4_plugin(self.ws)
        (self.ws / "phase4-output" / "potion" / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "potion"}))  # missing version, description
        r = validate_plugin(self.ws)
        self.assertFalse(r.passed)

    def test_multi_guidelines_in_plugin(self):
        _populate_phase4_plugin(self.ws)
        plugin = self.ws / "phase4-output" / "potion"
        (plugin / "guidelines.md").unlink()
        (plugin / "guidelines").mkdir()
        (plugin / "guidelines" / "index.md").write_text("# Index")
        r = validate_plugin(self.ws)
        self.assertTrue(any("Multi-file" in i for i in r.info))

    def test_wrong_guidelines_path_errors(self):
        _populate_phase4_plugin(self.ws)
        plugin = self.ws / "phase4-output" / "potion"
        (plugin / "skills" / "ask" / "SKILL.md").write_text(
            "---\ndescription: Analyzes code\nallowed-tools: Read\nmodel: sonnet\n---\n"
            "# Skill\nRead .claude/guidelines.md for patterns.")
        r = validate_plugin(self.ws)
        self.assertFalse(r.passed)
        self.assertTrue(any("CLAUDE_PLUGIN_ROOT" in e for e in r.errors))


class TestValidateReviewerSubagents(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.ws)

    def test_no_reviewers_dir_ok(self):
        r = Result()
        validate_reviewer_subagents(self.ws, r)
        self.assertTrue(r.passed)  # optional, no error

    def test_empty_reviewers_warns(self):
        (self.ws / "agents" / "reviewers").mkdir(parents=True)
        r = Result()
        validate_reviewer_subagents(self.ws, r)
        self.assertTrue(any("empty" in w for w in r.warnings))

    def test_valid_reviewer(self):
        d = self.ws / "agents" / "reviewers"
        d.mkdir(parents=True)
        (d / "arch-reviewer.md").write_text(
            "---\ndescription: Reviews architecture\ntools: Read, Glob, Grep\nmodel: sonnet\n---\n"
            "# Arch Reviewer\nReferences guidelines.")
        r = Result()
        validate_reviewer_subagents(self.ws, r)
        self.assertTrue(r.passed)

    def test_reviewer_with_write_errors(self):
        d = self.ws / "agents" / "reviewers"
        d.mkdir(parents=True)
        (d / "bad-reviewer.md").write_text(
            "---\ndescription: Reviews code\ntools: Read, Write, Glob\nmodel: sonnet\n---\n"
            "# Bad Reviewer\nReferences guidelines.")
        r = Result()
        validate_reviewer_subagents(self.ws, r)
        self.assertFalse(r.passed)


class TestValidateCrossPhase(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.ws)

    def _setup_full_workspace(self):
        """Create a complete workspace with phases 1, 3, and 4."""
        # Phase 1
        (self.ws / "phase1-module-map.json").write_text(json.dumps({
            "modules": [
                {"name": "core", "depends_on": []},
                {"name": "api", "depends_on": ["core"]},
            ],
        }))
        # Phase 3
        (self.ws / "phase3-guidelines.md").write_text("\n".join([
            "# Guidelines",
            "## Architecture Overview",
            "The core module handles...",
            "## Core Patterns",
            "Pattern info",
            "## Canonical Examples",
            "| File | What |",
            "| `src/core.ts` | Core implementation |",
            "## Known Pitfalls",
            "- Watch out for X",
            "## Conventions",
            "Naming conventions here",
        ]))
        # Phase 4
        _populate_phase4_install(self.ws)
        # Add module references to skills
        for skill in ["ask", "implement", "review"]:
            path = self.ws / "phase4-output" / "skills" / skill / "SKILL.md"
            content = path.read_text()
            path.write_text(content + "\ncore module\napi module\n`src/core.ts`\npattern\nconvention\nnaming\n")

    def test_valid_cross_phase(self):
        self._setup_full_workspace()
        r = validate_cross_phase(self.ws)
        self.assertTrue(r.passed)

    def test_missing_module_map_warns(self):
        r = validate_cross_phase(self.ws)
        self.assertTrue(any("missing" in w.lower() for w in r.warnings))

    def test_uncovered_module_warns(self):
        self._setup_full_workspace()
        # Add a module not mentioned in any skill
        (self.ws / "phase1-module-map.json").write_text(json.dumps({
            "modules": [
                {"name": "core", "depends_on": []},
                {"name": "api", "depends_on": ["core"]},
                {"name": "obscure-module", "depends_on": []},
            ],
        }))
        r = validate_cross_phase(self.ws)
        self.assertTrue(any("obscure-module" in str(w) for w in r.warnings))

    def test_evaluation_failures_error(self):
        self._setup_full_workspace()
        (self.ws / "phase5-evaluation.json").write_text(json.dumps({
            "skills_tested": [{"skill": "ask", "overall": "fail"}],
            "agents_tested": [],
        }))
        r = validate_cross_phase(self.ws)
        self.assertFalse(r.passed)

    def test_plugin_mode_cross_phase(self):
        self._setup_full_workspace()
        # Move phase4 to plugin structure
        out = self.ws / "phase4-output"
        plugin = out / "potion"
        (plugin / ".claude-plugin").mkdir(parents=True)
        (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "potion"}))
        # Copy skills/agents into plugin dir
        shutil.copytree(out / "skills", plugin / "skills")
        shutil.copytree(out / "agents", plugin / "agents")
        r = validate_cross_phase(self.ws, delivery_mode="plugin")
        # Should not error (may warn about missing guidelines in plugin dir)
        self.assertTrue(r.passed or all("guidelines" in w.lower() for w in r.warnings if w))


class TestValidateState(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.ws)

    def _write_state(self, data):
        (self.ws / "state.json").write_text(json.dumps(data))

    def _valid_state(self):
        return {
            "started_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T01:00:00Z",
            "project_root": "/tmp/project",
            "phases": {
                "1": {"status": "completed", "started_at": "2024-01-01T00:00:00Z", "completed_at": "2024-01-01T00:10:00Z", "output_file": None, "error": None},
                "2": {"status": "completed", "started_at": "2024-01-01T00:10:00Z", "completed_at": "2024-01-01T00:30:00Z", "output_file": None, "error": None, "module_statuses": {}},
                "3": {"status": "in_progress", "started_at": "2024-01-01T00:30:00Z", "completed_at": None, "output_file": None, "error": None},
                "4": {"status": "pending", "started_at": None, "completed_at": None, "output_file": None, "error": None},
                "5": {"status": "pending", "started_at": None, "completed_at": None, "output_file": None, "error": None},
            },
            "user_choices": {
                "selected_outputs": [],
                "skip_evaluation": False,
                "delivery_mode": "plugin",
                "guidelines_mode": None,
            },
        }

    def test_valid_state(self):
        self._write_state(self._valid_state())
        r = validate_state(self.ws)
        self.assertTrue(r.passed)

    def test_missing_state(self):
        r = validate_state(self.ws)
        self.assertFalse(r.passed)

    def test_missing_required_fields(self):
        self._write_state({"started_at": "2024-01-01T00:00:00Z"})
        r = validate_state(self.ws)
        self.assertFalse(r.passed)

    def test_invalid_phase_status(self):
        state = self._valid_state()
        state["phases"]["3"]["status"] = "banana"
        self._write_state(state)
        r = validate_state(self.ws)
        self.assertFalse(r.passed)

    def test_invalid_delivery_mode(self):
        state = self._valid_state()
        state["user_choices"]["delivery_mode"] = "yolo"
        self._write_state(state)
        r = validate_state(self.ws)
        self.assertFalse(r.passed)

    def test_invalid_guidelines_mode(self):
        state = self._valid_state()
        state["user_choices"]["guidelines_mode"] = "triple"
        self._write_state(state)
        r = validate_state(self.ws)
        self.assertFalse(r.passed)

    def test_null_guidelines_mode_ok(self):
        state = self._valid_state()
        state["user_choices"]["guidelines_mode"] = None
        self._write_state(state)
        r = validate_state(self.ws)
        self.assertTrue(r.passed)

    def test_bad_timestamp_warns(self):
        state = self._valid_state()
        state["started_at"] = "not-a-date"
        self._write_state(state)
        r = validate_state(self.ws)
        self.assertTrue(any("ISO 8601" in w for w in r.warnings))


class TestValidatePhase2Submodules(unittest.TestCase):
    """Tests for I2 fix: submodule name collision handling."""

    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / "phase2-profiles").mkdir()

    def tearDown(self):
        shutil.rmtree(self.ws)

    def test_submodule_composite_keys(self):
        """Two parents with same-named submodule should not collide."""
        (self.ws / "phase1-module-map.json").write_text(json.dumps({
            "modules": [
                {"name": "backend", "depends_on": [], "submodules": [
                    {"name": "auth", "path": "src/backend/auth"},
                ]},
                {"name": "frontend", "depends_on": [], "submodules": [
                    {"name": "auth", "path": "src/frontend/auth"},
                ]},
            ],
        }))
        # Two profiles for the two auth submodules
        (self.ws / "phase2-profiles" / "backend-auth.json").write_text(json.dumps({
            "module_name": "auth",
            "code_samples": {"canonical_implementation": {"file": "src/backend/auth/index.ts"}},
            "pitfalls": [{"description": "watch out"}],
        }))
        (self.ws / "phase2-profiles" / "frontend-auth.json").write_text(json.dumps({
            "module_name": "auth",
            "code_samples": {"canonical_implementation": {"file": "src/frontend/auth/index.ts"}},
            "pitfalls": [{"description": "careful"}],
        }))
        r = validate_phase2(self.ws)
        # Both auths should be covered — composite keys backend/auth and frontend/auth
        self.assertTrue(r.passed)

    def test_missing_submodule_profile_warns(self):
        """Missing profile for a submodule should warn."""
        (self.ws / "phase1-module-map.json").write_text(json.dumps({
            "modules": [
                {"name": "backend", "depends_on": [], "submodules": [
                    {"name": "auth", "path": "src/backend/auth"},
                    {"name": "billing", "path": "src/backend/billing"},
                ]},
            ],
        }))
        (self.ws / "phase2-profiles" / "backend-auth.json").write_text(json.dumps({
            "module_name": "auth",
            "code_samples": {"canonical_implementation": {"file": "src/auth.ts"}},
            "pitfalls": [{"description": "watch out"}],
        }))
        r = validate_phase2(self.ws)
        self.assertTrue(any("Missing profiles" in w for w in r.warnings))


if __name__ == "__main__":
    unittest.main()

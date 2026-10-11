"""Integration checks for the unmodified, vendored BMad workflow renderer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from config_utils import ConfigError
from render_skill import RenderError, render


class RenderSkillTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="bmad-render-test-")
        self.addCleanup(self.workspace.cleanup)
        self.workspace_path = Path(self.workspace.name).resolve()
        self.project = self.workspace_path / "project with spaces"
        self.bmad = self.project / "_bmad"
        self.bmad.mkdir(parents=True)
        self.config = self.bmad / "config.toml"
        self.config.write_text(
            '[core]\nproject_name = "Test project"\n'
            'communication_language = "English"\n'
            '[modules.bmm]\n'
            'planning_artifacts = "{project-root}/_bmad-output/planning-artifacts"\n',
            encoding="utf-8",
        )
        self.skill = self.workspace_path / "installed skills" / "bmad-build"
        self.skill.mkdir(parents=True)
        self.workflow = self.skill / "workflow.md"
        self.workflow.write_text(
            '# {{config.core.project_name}}\n'
            'Language: {{.communication_language}}\n'
            'Planning: {{.planning_artifacts}}\n'
            '{workflow.activation_steps_prepend}\n'
            '{workflow.persistent_facts}\n'
            '{workflow.review_layers}\n'
            'Read [[bmad-snapshot:step-01.md]]\n'
            'Runtime: {spec_file} {{story_key}}\n',
            encoding="utf-8",
        )
        self.step = self.skill / "step-01.md"
        self.step.write_text("# First step\n", encoding="utf-8")
        (self.skill / "SKILL.md").write_text(
            "This entry must not be rendered.\n", encoding="utf-8"
        )
        (self.skill / "customize.toml").write_text(
            '[workflow]\nactivation_steps_prepend = []\n'
            'persistent_facts = ["file:{project-root}/project-context.md"]\n'
            '[[workflow.review_layers]]\nid = "base"\nname = "Base"\n'
            'instruction = "Read {skill-root}/step-01.md for {spec_file}."\n',
            encoding="utf-8",
        )

    def run_cli(self):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "render_skill.py"),
             "--project-root", str(self.project), "--skill", str(self.skill)],
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_render_resolves_sources_and_preserves_runtime_placeholders(self):
        original = self.workflow.read_bytes()
        entry = render(self.project, self.skill)
        content = entry.read_text(encoding="utf-8")
        self.assertTrue(entry.is_absolute())
        self.assertIn("# Test project", content)
        self.assertIn("Language: English", content)
        planning_path = next(line for line in content.splitlines() if line.startswith("Planning: "))
        self.assertEqual(
            (self.project / "_bmad-output/planning-artifacts").resolve(),
            Path(planning_path.removeprefix("Planning: ")).resolve(),
        )
        self.assertIn(str(entry.parent / "step-01.md"), content)
        self.assertIn("Runtime: {spec_file} {{story_key}}", content)
        self.assertIn("file:{project-root}/project-context.md", content)
        self.assertIn("_None._", content)
        self.assertNotIn("[[bmad-snapshot:", content)
        self.assertNotIn("{workflow.", content)
        self.assertNotIn("{skill-root}", content)
        self.assertEqual(original, self.workflow.read_bytes())
        self.assertFalse((entry.parent / "SKILL.md").exists())
        manifest = json.loads((entry.parent / "manifest.json").read_text(encoding="utf-8"))
        for name, expected in manifest["outputs"].items():
            self.assertEqual(hashlib.sha256((entry.parent / name).read_bytes()).hexdigest(), expected)

    def test_team_and_personal_overrides_merge_in_order(self):
        custom = self.bmad / "custom"
        custom.mkdir()
        (self.bmad / "config.user.toml").write_text(
            '[core]\ncommunication_language = "French"\n', encoding="utf-8"
        )
        (custom / "config.toml").write_text(
            '[core]\ncommunication_language = "Spanish"\n', encoding="utf-8"
        )
        (custom / "config.user.toml").write_text(
            '[core]\ncommunication_language = "German"\n', encoding="utf-8"
        )
        (custom / "bmad-build.toml").write_text(
            '[workflow]\nactivation_steps_prepend = ["Team step"]\n'
            '[[workflow.review_layers]]\nid = "base"\nname = "Team"\n'
            'instruction = "Team review"\n'
            '[[workflow.review_layers]]\nid = "extra"\nname = "Extra"\n'
            'instruction = "Extra review"\n', encoding="utf-8"
        )
        (custom / "bmad-build.user.toml").write_text(
            '[workflow]\nactivation_steps_prepend = ["Personal step"]\n'
            '[[workflow.review_layers]]\nid = "base"\nname = "Personal"\n'
            'instruction = "Personal review"\n', encoding="utf-8"
        )
        entry = render(self.project, self.skill)
        content = entry.read_text(encoding="utf-8")
        self.assertIn("Language: German", content)
        self.assertIn("- Team step\n- Personal step", content)
        self.assertIn("Personal review", content)
        self.assertIn("Extra review", content)
        self.assertNotIn("Team review", content)

    def test_same_inputs_reuse_snapshot_and_changes_create_new_snapshot(self):
        first = render(self.project, self.skill)
        original = first.read_bytes()
        self.assertEqual(first, render(self.project, self.skill))
        self.step.write_text("# Changed step\n", encoding="utf-8")
        second = render(self.project, self.skill)
        self.assertNotEqual(first, second)
        self.assertEqual(original, first.read_bytes())
        self.assertEqual("# Changed step\n", (second.parent / "step-01.md").read_text(encoding="utf-8"))

    def test_modified_snapshot_is_rejected_without_overwriting_it(self):
        entry = render(self.project, self.skill)
        output = entry.parent / "step-01.md"
        output.write_text("Modified snapshot\n", encoding="utf-8")
        with self.assertRaisesRegex(RenderError, "output hash mismatch"):
            render(self.project, self.skill)
        self.assertEqual("Modified snapshot\n", output.read_text(encoding="utf-8"))

    def test_missing_configuration_returns_clear_cli_failure(self):
        self.config.unlink()
        result = self.run_cli()
        self.assertEqual(1, result.returncode)
        self.assertIn("HALT: required TOML file not found", result.stdout)
        self.assertEqual("", result.stderr)
        self.assertFalse((self.bmad / "render").exists())

    def test_malformed_toml_is_rejected(self):
        self.config.write_text("[broken\n", encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "failed to parse"):
            render(self.project, self.skill)

    def test_ambiguous_short_config_key_is_rejected(self):
        with self.config.open("a", encoding="utf-8") as stream:
            stream.write('[modules.other]\ncommunication_language = "French"\n')
        with self.assertRaisesRegex(RenderError, "ambiguous config value"):
            render(self.project, self.skill)

    def test_snapshot_reference_outside_skill_is_rejected(self):
        self.workflow.write_text("[[bmad-snapshot:../outside.md]]\n", encoding="utf-8")
        with self.assertRaisesRegex(RenderError, "undeclared source"):
            render(self.project, self.skill)
        self.assertFalse((self.bmad / "render").exists())

    def test_missing_workflow_is_rejected(self):
        self.workflow.unlink()
        with self.assertRaisesRegex(RenderError, "render entry is missing"):
            render(self.project, self.skill)

    def test_cli_from_another_directory_prints_one_absolute_entry(self):
        result = self.run_cli()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(1, len(lines))
        self.assertTrue(lines[0].startswith("read and follow "))
        entry = Path(lines[0].removeprefix("read and follow "))
        self.assertTrue(entry.is_absolute())
        self.assertTrue(entry.is_file())
        self.assertEqual("", result.stderr)


if __name__ == "__main__":
    unittest.main()

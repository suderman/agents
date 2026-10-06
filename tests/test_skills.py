#!/usr/bin/env python3
"""Exercise the skill resolver with local Git repositories, never the network."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class SkillsTests(unittest.TestCase):
    def setUp(self):
        scratch = REPO / ".scratch"
        scratch.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="test-skills-", dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.root = self.work / "agents"
        (self.root / "lib").mkdir(parents=True)
        self.home = self.work / "home"
        self.personal = self.home / "profile/skills"
        self.personal.mkdir(parents=True)
        self.env = {**os.environ, "HOME": str(self.home), "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
        shutil.copy2(REPO / "lib/skills", self.root / "lib/skills")
        self.write_json("skills.json", {"skills": []})
        self.write_json("skills.lock", {"skills": []})
        self.upstream = self.work / "upstream"
        self.upstream.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.add_skill(self.upstream / "collection/alpha", "alpha")
        self.add_skill(self.upstream / "collection/beta", "beta")
        (self.upstream / "unrelated.txt").write_text("not a skill\n")
        (self.upstream / "collection/alpha/run").write_text("#!/bin/sh\necho fixture\n")
        (self.upstream / "collection/alpha/run").chmod(0o755)
        self.first = self.commit()
        self.entry = {
            "name": "alpha",
            "git": str(self.upstream),
            "path": "collection/alpha",
        }
        self.select(self.entry)

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.upstream), *args], text=True
        ).strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Fixture revision")
        return self.git("rev-parse", "HEAD")

    def add_skill(self, directory, name):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Fixture skill\n---\n\nOriginal.\n"
        )

    def write_json(self, name, value):
        (self.root / name).write_text(json.dumps(value, indent=2) + "\n")

    def select(self, *entries):
        self.write_json("skills.json", {"skills": list(entries)})

    def run_command(self, command, error=None, arguments=()):
        result = subprocess.run(
            [str(self.root / "lib/skills"), command, *arguments],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        if error:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(error, result.stderr)
        else:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def lock(self):
        return json.loads((self.root / "skills.lock").read_text())["skills"]

    def snapshot(self):
        return {
            str(path.relative_to(self.root / "skills")): (
                path.read_bytes(),
                path.stat().st_mode & 0o777,
            )
            for path in (self.root / "skills").rglob("*")
            if path.is_file() and path.name != ".state.json"
        }

    def test_empty_manifest(self):
        self.select()
        before = (self.root / "skills.lock").read_bytes()
        self.run_command("materialize")
        self.assertEqual(self.snapshot(), {})
        self.run_command("update")
        self.run_command("check")
        self.assertEqual((self.root / "skills.lock").read_bytes(), before)

    def test_locked_reproduction_and_repeat_runs(self):
        self.run_command("update")
        before = self.snapshot()
        lock = (self.root / "skills.lock").read_bytes()
        self.assertEqual(self.lock()[0]["revision"], self.first)
        self.assertEqual(self.lock()[0]["ref"], "HEAD")
        (self.upstream / "collection/alpha/SKILL.md").write_text("changed upstream\n")
        self.commit()
        shutil.rmtree(self.root / "skills")
        self.run_command("materialize")
        self.assertEqual(self.snapshot(), before)
        (self.root / "skills/alpha/run").write_text("local edit\n")
        (self.root / "skills/unselected").mkdir()
        self.run_command("materialize")
        self.run_command("materialize")
        self.run_command("check")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.root / "skills.lock").read_bytes(), lock)
        self.assertEqual(list((self.root / ".scratch").iterdir()), [])

    def test_update_advances_and_recreates_lock(self):
        self.run_command("update")
        with (self.upstream / "collection/alpha/SKILL.md").open("a") as output:
            output.write("New revision.\n")
        second = self.commit()
        self.run_command("update")
        self.assertNotEqual(second, self.first)
        self.assertEqual(self.lock()[0]["revision"], second)
        self.assertIn(
            "New revision", (self.root / "skills/alpha/SKILL.md").read_text()
        )
        lock = (self.root / "skills.lock").read_bytes()
        (self.root / "skills.lock").unlink()
        self.run_command("materialize", "skills.lock")
        self.run_command("update")
        self.assertEqual((self.root / "skills.lock").read_bytes(), lock)

    def test_select_multiple_and_remove_one(self):
        beta = {**self.entry, "name": "beta", "path": "collection/beta"}
        self.select(self.entry, beta)
        self.run_command("update")
        self.assertEqual(
            {path.name for path in (self.root / "skills").iterdir() if path.name != ".state.json"},
            {"alpha", "beta"},
        )
        self.assertFalse(list((self.root / "skills").rglob(".git")))
        self.assertFalse(list((self.root / "skills").rglob("unrelated.txt")))
        self.select(beta)
        self.run_command("update")
        self.assertFalse((self.root / "skills/alpha").exists())

    def test_add_and_remove_keep_other_revisions_locked(self):
        self.run_command("update")
        with (self.upstream / "collection/alpha/SKILL.md").open("a") as output:
            output.write("New upstream revision.\n")
        second = self.commit()
        self.run_command(
            "add",
            arguments=(
                "beta",
                str(self.upstream),
                "--path",
                "collection/beta",
                "--ref",
                "main",
            ),
        )
        self.assertEqual(
            [entry["revision"] for entry in self.lock()], [self.first, second]
        )
        self.assertEqual(self.lock()[1]["ref"], "main")
        self.assertNotIn(
            "New upstream", (self.root / "skills/alpha/SKILL.md").read_text()
        )
        (self.upstream / "collection/beta/extra").write_text("later revision\n")
        self.commit()
        self.run_command("remove", arguments=("alpha",))
        self.assertEqual(self.lock()[0]["revision"], second)
        self.assertEqual(self.lock()[0]["name"], "beta")
        self.assertFalse((self.root / "skills/alpha").exists())
        self.assertFalse((self.root / "skills/beta/extra").exists())
        self.run_command("check")
        self.run_command("remove", arguments=("beta",))
        self.assertEqual(self.lock(), [])
        self.assertEqual(self.snapshot(), {})
        self.run_command("check")

    def test_add_root_skill_defaults(self):
        self.select()
        self.add_skill(self.upstream, "root-skill")
        shutil.rmtree(self.upstream / "collection")
        revision = self.commit()
        self.run_command("add", arguments=("root-skill", str(self.upstream)))
        self.assertEqual(self.lock()[0]["path"], ".")
        self.assertEqual(self.lock()[0]["ref"], "HEAD")
        self.assertEqual(self.lock()[0]["revision"], revision)
        self.run_command("check")

    def test_selection_failures_preserve_source_files_and_tree(self):
        self.run_command("update")
        self.add_skill(self.personal / "beta", "beta")
        before = self.snapshot()
        sources = [
            (self.root / name).read_bytes() for name in ["skills.json", "skills.lock"]
        ]
        cases = [
            ("add", ("alpha", str(self.upstream)), "duplicate skill name"),
            (
                "add",
                ("beta", str(self.upstream), "--path", "collection/beta"),
                "skill name collision",
            ),
            (
                "add",
                ("missing", str(self.upstream), "--path", "missing"),
                "Git archive",
            ),
            (
                "add",
                ("wrong-name", str(self.upstream), "--path", "collection/beta"),
                "name must match",
            ),
            ("add", ("invalid--name", str(self.upstream)), "invalid skill name"),
            ("add", ("missing", str(self.work / "missing")), "Git fetch"),
            (
                "add",
                ("missing", str(self.upstream), "--path", "../escape"),
                "path must stay within",
            ),
            ("remove", ("unknown",), "skill not selected"),
        ]
        for command, arguments, error in cases:
            with self.subTest(command=command, arguments=arguments):
                self.run_command(command, error, arguments)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(
                    [
                        (self.root / name).read_bytes()
                        for name in ["skills.json", "skills.lock"]
                    ],
                    sources,
                )
        self.assertEqual(list((self.root / ".scratch").iterdir()), [])

    def test_remove_fetch_failure_preserves_selection(self):
        beta = {**self.entry, "name": "beta", "path": "collection/beta"}
        self.select(self.entry, beta)
        self.run_command("update")
        before = self.snapshot()
        sources = [
            (self.root / name).read_bytes() for name in ["skills.json", "skills.lock"]
        ]
        shutil.rmtree(self.upstream)
        self.run_command("remove", "Git fetch", ("alpha",))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(
            [
                (self.root / name).read_bytes()
                for name in ["skills.json", "skills.lock"]
            ],
            sources,
        )

    def test_list_is_read_only_without_fetch_or_vendor_tree(self):
        self.run_command("update")
        sources = [
            (self.root / name).read_bytes() for name in ["skills.json", "skills.lock"]
        ]
        shutil.rmtree(self.upstream)
        shutil.rmtree(self.root / "skills")
        result = self.run_command("list")
        self.assertIn(
            f"alpha\tHEAD\t{self.first}\t{self.upstream}\tcollection/alpha",
            result.stdout,
        )
        self.assertFalse((self.root / "skills").exists())
        self.assertEqual(
            [
                (self.root / name).read_bytes()
                for name in ["skills.json", "skills.lock"]
            ],
            sources,
        )

    def test_rebuild_discards_invalid_vendor_edits(self):
        self.run_command("update")
        before = self.snapshot()
        (self.root / "skills/alpha/SKILL.md").write_text("broken local edit\n")
        self.run_command("materialize")
        self.assertEqual(self.snapshot(), before)

    def test_deselection_allows_maintained_replacement(self):
        self.run_command("update")
        self.add_skill(self.personal / "alpha", "alpha")
        self.select()
        self.run_command("update")
        self.run_command("check")
        self.assertEqual(self.snapshot(), {})
        self.assertTrue((self.personal / "alpha/SKILL.md").exists())

    def test_root_skill_and_explicit_ref(self):
        self.add_skill(self.upstream, "root-skill")
        shutil.rmtree(self.upstream / "collection")
        revision = self.commit()
        self.select({"name": "root-skill", "git": str(self.upstream), "ref": revision})
        self.run_command("update")
        self.assertEqual(self.lock()[0]["path"], ".")
        self.assertEqual(self.lock()[0]["revision"], revision)
        self.run_command("check")

    def test_duplicate_names_fail(self):
        self.select(self.entry, {**self.entry, "path": "collection/beta"})
        self.run_command("update", "duplicate skill name: alpha")
        self.assertFalse((self.root / "skills").exists())

    def test_maintained_collision_fails_without_writes(self):
        self.run_command("update")
        before = self.snapshot()
        self.add_skill(self.personal / "alpha", "alpha")
        maintained = (self.personal / "alpha/SKILL.md").read_bytes()
        for command in ["update", "materialize", "check"]:
            self.run_command(command, "community/personal skill name collision: alpha")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.personal / "alpha/SKILL.md").read_bytes(), maintained)

    def test_declared_name_collision(self):
        for directory in ["different-directory"]:
            with self.subTest(directory=directory):
                self.add_skill(self.personal / directory, "alpha")
                self.run_command("update", "name must match")
                shutil.rmtree(self.personal / directory)

    def test_missing_path_preserves_tree_and_lock(self):
        self.run_command("update")
        before = self.snapshot()
        lock = (self.root / "skills.lock").read_bytes()
        self.select(
            self.entry, {**self.entry, "name": "missing", "path": "collection/missing"}
        )
        self.run_command("update", "missing")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.root / "skills.lock").read_bytes(), lock)

    def test_fetch_failure_preserves_tree_and_lock(self):
        self.run_command("update")
        before = self.snapshot()
        lock = (self.root / "skills.lock").read_bytes()
        self.select({**self.entry, "git": str(self.work / "nonexistent")})
        self.run_command("update", "Git fetch")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.root / "skills.lock").read_bytes(), lock)

    def test_malformed_declarations(self):
        invalid = [
            [],
            {"skills": {}},
            {"skills": ["alpha"]},
            {"skills": [{"name": "alpha"}]},
            {"skills": [{**self.entry, "unused": "x"}]},
            {"skills": [{**self.entry, "path": "../escape"}]},
            {"skills": [{**self.entry, "path": "/escape"}]},
            {"skills": [{**self.entry, "ref": False}]},
            {"skills": [{**self.entry, "name": "bad--name"}]},
            {"skills": [{**self.entry, "git": "-bad"}]},
        ]
        for declaration in invalid:
            with self.subTest(declaration=declaration):
                self.write_json("skills.json", declaration)
                self.run_command("update", "skills:")
        (self.root / "skills.json").write_text('{"skills": [], "skills": []}')
        self.run_command("update", "duplicate JSON key")

    def test_lock_mismatch_and_invalid_revision(self):
        self.run_command("materialize", "does not match")
        self.run_command("update")
        self.select({**self.entry, "ref": "main"})
        self.run_command("materialize", "does not match")
        self.select(self.entry)
        self.write_json("skills.lock", {"skills": [{**self.entry, "revision": "HEAD"}]})
        self.run_command("materialize", "exact 40-character")

    def test_incompatible_layouts(self):
        directory = self.upstream / "collection/alpha"
        (directory / "SKILL.md").unlink()
        self.commit()
        self.run_command("update", "missing requested skill path or SKILL.md")
        self.add_skill(directory, "different-name")
        self.commit()
        self.run_command("update", "name must match")
        self.add_skill(directory, "alpha")
        self.add_skill(directory / "nested", "nested")
        self.commit()
        self.run_command("update", "nested skill directories")
        shutil.rmtree(directory / "nested")
        (directory / "link").symlink_to("/etc/passwd")
        self.commit()
        self.run_command("update", "symlinks and special files")

    def test_submodule_layout_fails(self):
        self.git(
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{self.first},collection/alpha/submodule",
        )
        self.git("commit", "-qm", "Submodule fixture")
        self.run_command("update", "submodules are not supported")

    def test_bootstraps_do_not_certify_global_skills(self):
        for name in ["pi", "opencode", "hermes"]:
            shutil.copytree(REPO / name, self.root / name)
        for relative in ["shared-prompts.sh", "runtime.sh"]:
            shutil.copy2(REPO / "lib" / relative, self.root / "lib" / relative)
        self.run_command("update")
        self.add_skill(self.personal / "alpha", "alpha")
        self.run_command("check", "skill name collision")
        (self.root / "skills.lock").unlink()
        for harness, variable in [("pi", "PI_CODING_AGENT_DIR"), ("opencode", "OPENCODE_CONFIG_DIR"), ("hermes", "HERMES_HOME")]:
            runtime = self.home / harness
            self.add_skill(runtime / "skills/local", "local")
            before = (runtime / "skills/local/SKILL.md").read_bytes()
            env = {**self.env, variable: str(runtime)}
            for _ in range(2):
                subprocess.run([str(self.root / harness / "bootstrap")], env=env, check=True)
            self.assertEqual((runtime / "skills/local/SKILL.md").read_bytes(), before)

    def test_check_detects_content_and_mode_drift(self):
        self.run_command("update")
        executable = self.root / "skills/alpha/run"
        executable.write_text("edited")
        self.run_command("check", "differ from locked state")
        self.run_command("materialize")
        executable.chmod(0o644)
        self.run_command("check", "differ from locked state")

    def test_personal_symlink_preserved(self):
        self.run_command("update")
        external = self.work / "external"
        self.add_skill(external, "external")
        (self.personal / "external").symlink_to(external)
        self.run_command("materialize")
        self.run_command("check")
        self.assertTrue((self.personal / "external").is_symlink())
        self.assertEqual((external / "SKILL.md").read_text(), (self.personal / "external/SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)

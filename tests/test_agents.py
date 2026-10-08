#!/usr/bin/env python3
"""Deployment and Git sync tests. Every application home and remote is local and isolated."""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            value = ("link", os.readlink(path), path.lstat().st_ino)
        elif path.is_file():
            info = path.stat()
            value = (hashlib.sha256(path.read_bytes()).hexdigest(), info.st_ino, info.st_mtime_ns, info.st_mode)
        else:
            continue
        result[str(path.relative_to(root))] = value
    return result


class AgentsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.home = self.work / "home"
        self.root = self.home / ".agents"
        self.root.mkdir(parents=True)
        for name in ["lib", "pi", "opencode", "hermes", "claude"]:
            shutil.copytree(REPO / name, self.root / name)
        shutil.copy2(REPO / "agents", self.root / "agents")
        (self.root / ".gitignore").write_text("/skills/\n/.scratch/\n")
        (self.home / "profile/prompts").mkdir(parents=True)
        self.skill(self.home / "profile/skills/personal", "personal")
        (self.home / "profile/prompts/review.md").write_text(
            "---\ndescription: Review changes\n---\nReview $ARGUMENTS\n"
        )
        self.env = {**os.environ, "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"),
                    "XDG_STATE_HOME": str(self.home / ".local/state"), "GIT_CONFIG_GLOBAL": "/dev/null",
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
                    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
                    "AGENTS_HARNESSES": "pi,opencode,hermes,claude"}
        for variable in ["PI_CODING_AGENT_DIR", "OPENCODE_CONFIG_DIR", "OPENCODE_DIR", "HERMES_HOME", "CLAUDE_CONFIG_DIR"]:
            self.env.pop(variable, None)
        self.upstream = self.work / "upstream"
        self.upstream.mkdir()
        self.git(self.upstream, "init", "-q", "-b", "main")
        self.skill(self.upstream / "alpha", "alpha")
        (self.upstream / "alpha/run").write_text("#!/bin/sh\nexit 0\n")
        (self.upstream / "alpha/run").chmod(0o755)
        self.commit(self.upstream)
        self.revision = self.git(self.upstream, "rev-parse", "HEAD")
        self.entry = {"name": "alpha", "git": str(self.upstream), "path": "alpha", "ref": "main"}
        self.write("skills.json", {"skills": [self.entry]})
        self.write("skills.lock", {"skills": [{**self.entry, "revision": self.revision}]})
        self.native = []
        for relative in [".pi/agent", ".config/opencode", ".hermes", ".claude"]:
            runtime = self.home / relative
            self.skill(runtime / "skills/native", "native")
            for filename in [".env", "auth.json", "sessions/session.jsonl", "history.jsonl", "plugins/local/state", "cache/local"]:
                path = runtime / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("native state\n")
                path.chmod(0o600)
                self.native.append(path)
            self.native.append(runtime / "skills/native/SKILL.md")
        (self.home / ".claude.json").write_text('{"oauth":"preserve","projects":{}}\n')
        self.native.append(self.home / ".claude.json")
        (self.home / ".claude/settings.json").write_text(json.dumps({
            "runtimeOnly": True, "model": "sonnet", "hooks": {"SessionStart": []},
            "modelSettings": {"claude-opus-5-5": {"effortLevel": "medium"},
                              "claude-sonnet-5-5": {"autoCompactWindow": "auto"}},
        }) + "\n")
        self.git(self.root, "init", "-q", "-b", "main")
        self.commit(self.root)

    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data, indent=2) + "\n")

    def git(self, directory, *args):
        return subprocess.check_output(["git", "-C", str(directory), *args], text=True, env=self.env, stderr=subprocess.DEVNULL).strip()

    def commit(self, directory):
        self.git(directory, "add", ".")
        self.git(directory, "commit", "-qm", "Fixture")

    def skill(self, path, name):
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Fixture skill\n---\nFixture.\n")

    def command(self, *args, error=None, env=None):
        result = subprocess.run([str(self.root / "agents"), *args], env=env or self.env,
                                cwd=self.work, text=True, capture_output=True, check=False)
        if error:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(error, result.stdout + result.stderr)
        else:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def native_snapshot(self):
        return [(p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns, p.stat().st_mode) for p in self.native]

    def test_apply_preserves_native_state_and_repeats_without_fetch(self):
        before = self.native_snapshot()
        old_settings = (self.home / ".claude/settings.json").read_bytes()
        lock = (self.root / "skills.lock").read_bytes()
        result = self.command("apply")
        self.assertIn("Rebuilding community skills", result.stdout)
        self.assertEqual(before, self.native_snapshot())
        self.assertEqual(lock, (self.root / "skills.lock").read_bytes())
        settings = json.loads((self.home / ".claude/settings.json").read_text())
        self.assertTrue(settings["runtimeOnly"])
        self.assertEqual(settings["model"], "sonnet")
        self.assertEqual(settings["hooks"], {"SessionStart": []})
        self.assertEqual(settings["permissions"]["defaultMode"], "bypassPermissions")
        self.assertIs(settings["attribution"], False)
        self.assertEqual(settings["tui"], "fullscreen")
        self.assertEqual(settings["modelSettings"]["claude-opus-5-5"]["effortLevel"], "medium")
        self.assertEqual(settings["modelSettings"]["claude-sonnet-5-5"],
                         {"effortLevel": "high", "autoCompactWindow": "auto"})
        backups = list((self.home / ".claude/backups").glob("agents-settings.json.*"))
        self.assertEqual([p.read_bytes() for p in backups], [old_settings])
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.home / ".claude/CLAUDE.md").read_text(), "@AGENTS.md\n")
        self.assertTrue((self.home / ".claude/skills/personal").is_symlink())
        self.assertEqual(os.readlink(self.home / ".claude/skills/alpha"), str(self.root / "skills/alpha"))
        prompt = (self.home / ".claude/commands/review.md").read_text()
        self.assertIn("disable-model-invocation: true", prompt)
        self.assertIn("$ARGUMENTS", prompt)
        shutil.rmtree(self.upstream)
        before = snapshot(self.home)
        self.command("apply")
        self.assertEqual(before, snapshot(self.home))
        self.assertNotIn(".agents/prompts", "\n".join(before))
        self.assertFalse((self.home / "profile/agents").exists())

    def test_locked_apply_does_not_advance_upstream(self):
        (self.upstream / "alpha/new-file").write_text("new upstream")
        self.commit(self.upstream)
        self.command("apply")
        self.assertFalse((self.root / "skills/alpha/new-file").exists())
        self.assertEqual(json.loads((self.root / "skills.lock").read_text())["skills"][0]["revision"], self.revision)

    def test_doctor_is_read_only_even_when_deployment_is_missing(self):
        before = snapshot(self.home)
        self.command("doctor", error="FAIL community tree")
        self.assertEqual(before, snapshot(self.home))
        self.command("apply")
        before = snapshot(self.home)
        self.command("doctor")
        self.assertEqual(before, snapshot(self.home))
        (self.root / "skills/alpha/run").write_text("edited")
        before = snapshot(self.home)
        self.command("doctor", error="differ from locked state")
        self.assertEqual(before, snapshot(self.home))

    def test_preflight_failures_leave_runtime_and_sources_unchanged(self):
        cases = [("collision", lambda: self.skill(self.home / "profile/skills/alpha", "alpha"), "skill name collision"),
                 ("malformed", lambda: (self.home / "profile/skills/personal/SKILL.md").write_text("broken"), "frontmatter"),
                 ("prompt", lambda: (self.home / "profile/prompts/bad.md").write_text("---\nmodel: bad\n---\nNo."), "single plain description"),
                 ("lock", lambda: self.write("skills.lock", {"skills": []}), "does not match")]
        for _, mutation, error in cases:
            with self.subTest(error=error):
                mutation()
                before = snapshot(self.home)
                self.command("apply", error=error)
                self.assertEqual(before, snapshot(self.home))
                shutil.rmtree(self.home / "profile/skills")
                self.skill(self.home / "profile/skills/personal", "personal")
                (self.home / "profile/prompts/bad.md").unlink(missing_ok=True)
                self.write("skills.lock", {"skills": [{**self.entry, "revision": self.revision}]})

    def test_failed_fetch_preserves_runtime_lock_and_materialization(self):
        self.command("apply")
        (self.root / "skills/alpha/run").write_text("force rebuild")
        shutil.rmtree(self.upstream)
        before = snapshot(self.home)
        self.command("apply", error="Git fetch")
        after = snapshot(self.home)
        self.assertEqual(before, after)

    def test_absent_personal_roots_are_optional(self):
        shutil.rmtree(self.home / "profile")
        self.command("apply")
        self.command("doctor")
        self.assertFalse((self.home / "profile").exists())

    def test_empty_manifest(self):
        self.write("skills.json", {"skills": []})
        self.write("skills.lock", {"skills": []})
        self.command("apply")
        self.assertEqual({p.name for p in (self.root / "skills").iterdir()}, {".state.json"})
        self.command("doctor")

    def test_unsafe_destinations_and_directory_links_are_rejected(self):
        for variable, target in [("PI_CODING_AGENT_DIR", str(self.root)),
                                 ("OPENCODE_CONFIG_DIR", str(self.home / "profile")),
                                 ("HERMES_HOME", str(self.home)),
                                 ("CLAUDE_CONFIG_DIR", str(self.root / "claude"))]:
            before = snapshot(self.home)
            self.command("apply", env={**self.env, variable: target}, error="unsafe")
            self.assertEqual(before, snapshot(self.home))
        (self.home / ".pi/agent/prompts").symlink_to(self.home / "profile/prompts")
        before = snapshot(self.home)
        self.command("apply", error="must not be a symlink")
        self.assertEqual(before, snapshot(self.home))

    def test_generated_directory_links_are_rejected_before_fetch(self):
        shutil.rmtree(self.upstream)
        for name in ["skills", ".scratch"]:
            with self.subTest(name=name):
                target = self.root / name
                target.symlink_to(self.home / "profile/skills", target_is_directory=True)
                before = snapshot(self.home)
                self.command("apply", error="not a symlink or file")
                self.assertEqual(before, snapshot(self.home))
                target.unlink()

    def test_native_declared_names_cannot_shadow_shared_skills(self):
        for relative in [".pi/agent", ".config/opencode", ".hermes", ".claude"]:
            with self.subTest(runtime=relative):
                target = self.home / relative / "skills/other-folder"
                self.skill(target, "alpha")
                before = snapshot(self.home)
                self.command("apply", error="collision")
                self.assertEqual(before, snapshot(self.home))
                shutil.rmtree(target)

    def test_claude_pretrusts_home_roots_and_repositories(self):
        src = self.home / "src"
        org = self.home / "org"
        repo = src / "owner/repo"
        nested = repo / "nested"
        worktree = org / "worktree"
        repo.parent.mkdir(parents=True)
        org.mkdir()
        self.git(self.work, "clone", "-q", str(self.upstream), str(repo))
        nested.mkdir()
        self.git(nested, "init", "-q", "-b", "main")
        self.git(repo, "worktree", "add", "-q", "-b", "other", str(worktree))
        (src / "external").symlink_to(self.upstream, target_is_directory=True)
        state = self.home / ".claude.json"
        previous = {"oauth": "preserve", "projects": {
            str(repo): {"hasTrustDialogAccepted": False, "allowedTools": ["Read"], "history": ["keep"]},
            "/unrelated": {"hasTrustDialogAccepted": False, "mcpServers": {"keep": {}}},
        }}
        state.write_text(json.dumps(previous))
        before = snapshot(self.home)
        result = subprocess.run([str(self.root / "claude/bootstrap"), "--check"], env=self.env,
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, snapshot(self.home))
        self.command("apply")
        actual = json.loads(state.read_text())
        self.assertEqual(actual["oauth"], previous["oauth"])
        self.assertEqual(actual["projects"]["/unrelated"], previous["projects"]["/unrelated"])
        self.assertEqual(actual["projects"][str(repo)],
                         {**previous["projects"][str(repo)], "hasTrustDialogAccepted": True})
        self.assertEqual({p for p, value in actual["projects"].items() if value.get("hasTrustDialogAccepted")},
                         {str(src), str(org), str(repo), str(nested)})
        self.assertEqual(state.stat().st_mode & 0o777, 0o600)
        backups = list((self.home / ".claude/backups").glob("agents-.claude.json.*"))
        self.assertEqual([json.loads(p.read_text()) for p in backups], [previous])
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
        before = snapshot(self.home)
        self.command("apply")
        self.command("doctor")
        self.assertEqual(before, snapshot(self.home))
        new = src / "new-clone"
        new.mkdir()
        self.git(new, "init", "-q", "-b", "main")
        before = snapshot(self.home)
        self.command("doctor", error="workspace trust")
        self.assertEqual(before, snapshot(self.home))
        self.command("apply")
        self.assertTrue(json.loads(state.read_text())["projects"][str(new)]["hasTrustDialogAccepted"])
        custom = self.home / "custom-claude"
        self.command("apply", env={**self.env, "AGENTS_HARNESSES": "claude", "CLAUDE_CONFIG_DIR": str(custom)})
        self.assertTrue(json.loads((custom / ".claude.json").read_text())["projects"][str(repo)]["hasTrustDialogAccepted"])

    def test_claude_malformed_trust_state_fails_before_any_writes(self):
        (self.home / "src").mkdir()
        state = self.home / ".claude.json"
        for content in ["[]", '{"projects":[]}', json.dumps({"projects": {str(self.home / "src"): []}})]:
            with self.subTest(content=content):
                state.write_text(content)
                before = snapshot(self.home)
                self.command("apply", error="Claude workspace trust")
                self.assertEqual(before, snapshot(self.home))

    def test_claude_restores_writable_settings_and_instructions(self):
        self.command("apply")
        target = self.home / ".claude/CLAUDE.md"
        settings = self.home / ".claude/settings.json"
        target.chmod(0o444)
        settings.chmod(0o444)
        before = snapshot(self.home)
        self.command("doctor", error="not writable")
        self.assertEqual(before, snapshot(self.home))
        self.command("apply")
        self.assertEqual(target.stat().st_mode & 0o777, 0o644)
        self.assertEqual(settings.stat().st_mode & 0o600, 0o600)

    def test_claude_native_collision_and_managed_edits_are_preserved(self):
        self.skill(self.home / ".claude/skills/personal", "personal")
        before = snapshot(self.home)
        self.command("apply", error="collision")
        self.assertEqual(before, snapshot(self.home))
        shutil.rmtree(self.home / ".claude/skills/personal")
        self.command("apply")
        prompt = self.home / ".claude/commands/review.md"
        prompt.write_text("local edit")
        before = snapshot(self.home)
        self.command("apply", error="changed locally")
        self.assertEqual(before, snapshot(self.home))

    def test_claude_removes_only_unchanged_managed_entries(self):
        self.command("apply")
        native = self.native_snapshot()
        self.command("skill", "remove", "alpha")
        (self.home / "profile/prompts/review.md").unlink()
        shutil.rmtree(self.home / "profile/skills/personal")
        self.command("apply")
        self.assertFalse((self.home / ".claude/skills/alpha").is_symlink())
        self.assertFalse((self.home / ".claude/skills/personal").is_symlink())
        self.assertFalse((self.home / ".claude/commands/review.md").exists())
        self.assertEqual(native, self.native_snapshot())

    def origin(self):
        origin = self.work / "origin.git"
        origin.mkdir()
        self.git(origin, "init", "--bare", "-q", "-b", "main")
        self.git(self.root, "remote", "add", "origin", str(origin))
        self.git(self.root, "push", "-qu", "origin", "main")
        writer = self.work / "writer"
        self.git(self.work, "clone", "-q", str(origin), str(writer))
        return origin, writer

    def test_sync_executes_newly_pulled_entrypoint(self):
        _, writer = self.origin()
        (writer / "agents").write_text('#!/bin/sh\n[ "$1" = apply ] || exit 7\nprintf "new apply\\n"\n')
        self.commit(writer)
        self.git(writer, "push", "-q")
        before = (self.root / "skills.lock").read_bytes()
        result = self.command("sync")
        self.assertIn("new apply", result.stdout)
        self.assertEqual(before, (self.root / "skills.lock").read_bytes())

    def test_sync_refuses_dirty_detached_and_missing_upstream(self):
        self.command("sync", error="failed")
        (self.root / "untracked").write_text("keep")
        before = snapshot(self.home)
        self.command("sync", error="dirty")
        self.assertEqual(before, snapshot(self.home))
        (self.root / "untracked").unlink()
        self.git(self.root, "checkout", "--detach", "-q")
        before = snapshot(self.home)
        self.command("sync", error="failed")
        self.assertEqual(before, snapshot(self.home))

    def test_sync_refuses_ahead_diverged_and_unreachable(self):
        _, writer = self.origin()
        (self.root / "local").write_text("local commit")
        self.commit(self.root)
        before = self.git(self.root, "rev-parse", "HEAD")
        self.command("sync", error="failed")
        self.assertEqual(before, self.git(self.root, "rev-parse", "HEAD"))
        (writer / "remote").write_text("remote commit")
        self.commit(writer)
        self.git(writer, "push", "-q")
        self.git(self.root, "fetch", "-q")
        self.command("sync", error="failed")
        self.assertEqual(before, self.git(self.root, "rev-parse", "HEAD"))
        self.git(self.root, "reset", "--hard", "-q", "origin/main")
        self.git(self.root, "remote", "set-url", "origin", str(self.work / "missing"))
        before = self.git(self.root, "rev-parse", "HEAD")
        self.command("sync", error="failed")
        self.assertEqual(before, self.git(self.root, "rev-parse", "HEAD"))

    def test_sync_pull_failure_never_applies(self):
        _, writer = self.origin()
        (self.root / "MERGE_MARKER").write_text("local")
        self.commit(self.root)
        # Cached remote still contains local HEAD, but the real remote is rewound.
        self.git(self.root, "push", "-q")
        (writer / "remote-change").write_text("diverge from cached remote")
        self.commit(writer)
        self.git(writer, "push", "--force", "-q")
        before = self.git(self.root, "rev-parse", "HEAD")
        native = self.native_snapshot()
        self.command("sync", error="failed")
        self.assertEqual(before, self.git(self.root, "rev-parse", "HEAD"))
        self.assertFalse((self.root / "skills").exists())
        self.assertEqual(native, self.native_snapshot())


if __name__ == "__main__":
    unittest.main(verbosity=2)

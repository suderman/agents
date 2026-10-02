#!/usr/bin/env python3
"""Credential-free scheduling and delivery checks; never contact a real agent."""

import argparse
import copy
import importlib.util
import json
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "sheepdog", Path(__file__).with_name("sheepdog.py")
)
assert spec and spec.loader
sheepdog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sheepdog)


def agent(kind, status):
    return {
        "agent": kind,
        "workspace_id": "w-test",
        "pane_id": kind,
        "terminal_id": "terminal-" + kind,
        "agent_session": {"value": "session-" + kind},
        "agent_status": status,
        "state_change_seq": 1,
    }


class WatchChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.directory = self.base / "run"
        self.directory.mkdir()
        repo = self.base / "project"
        repo.mkdir()
        self.current = {
            "worker": agent("pi", "working"),
            "supervisor": agent("hermes", "idle"),
        }
        self.state = {
            "status": "active",
            "expires": 1000,
            "next_review": 60,
            "interval": 60,
            "worker_seq": 1,
            "pending": False,
            "review": None,
            "counter": 0,
            "mandate": "/mandate.org",
            "repo": str(repo),
            "task": "/canonical.org",
            "task_heading": "* PROG Assigned task",
            "directory": str(self.directory),
            "supervisor_model": "observed-test-model",
            "model_evidence": "Test session metadata",
            "review_seconds": 300,
            "progress": dict.fromkeys(
                ("accepted", "verification", "publication", "remaining"), "Unknown"
            ),
            "owner_file": str(self.base / "owners/worker.json"),
            "socket": "/socket",
            "socket_identity": [1, 2],
        }
        Path(self.state["owner_file"]).parent.mkdir(mode=0o700)
        Path(self.state["owner_file"]).write_text(
            json.dumps({"run": str(self.directory)})
        )
        for role in self.current:
            self.current[role]["cwd"] = str(repo)
            self.current[role]["foreground_cwd"] = str(repo)
            self.state[role] = {
                "target": role,
                "identity": sheepdog.identity(self.current[role]),
            }
        self.calls = []

    def fake_call(self, run, *args):
        self.calls.append(args)
        if args[:2] == ("agent", "get"):
            return {"agent": copy.deepcopy(self.current[args[2]])}
        if args[:2] == ("agent", "read"):
            return {"text": "worker output continues streaming"}
        return {}

    def tick(self, now):
        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=self.fake_call),
        ):
            return sheepdog.tick(self.directory, self.state, now)

    def prompts(self):
        return [c for c in self.calls if c[:2] == ("agent", "prompt")]

    def test_cli_read_is_plain_text_not_control_json(self):
        response = subprocess.CompletedProcess([], 0, "EXPECTED_SLOW_CHECK 0\n", "")
        with patch.object(sheepdog.subprocess, "run", return_value=response):
            result = sheepdog.call(self.state, "agent", "read", "worker")
        self.assertEqual(result["text"], "EXPECTED_SLOW_CHECK 0\n")

    def test_timer_reviews_busy_streaming_worker(self):
        self.tick(59)
        self.assertFalse(self.prompts())
        for now in range(60, 66):
            self.current["worker"]["state_change_seq"] += 1
            self.tick(now)
        self.assertEqual(len(self.prompts()), 1)
        self.assertEqual(self.state["review"]["worker_status"], "working")

    def test_busy_capture_never_requests_scrolling_history(self):
        def guarded_read(run, *args):
            if args[:2] == ("agent", "read") and "visible" not in args:
                raise RuntimeError(
                    "cannot capture alternate-screen history while working"
                )
            return self.fake_call(run, *args)

        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=guarded_read),
        ):
            sheepdog.tick(self.directory, self.state, 60)
        self.assertEqual(len(self.prompts()), 1)

    def test_worker_state_measurements_are_transition_only(self):
        self.tick(1)
        self.tick(2)
        self.current["worker"]["agent_status"] = "done"
        self.current["worker"]["state_change_seq"] += 1
        self.tick(3)
        events = [
            json.loads(line)
            for line in (self.directory / "events.jsonl").read_text().splitlines()
        ]
        observations = [e for e in events if e["event"] == "worker_state_observed"]
        self.assertEqual([e["status"] for e in observations], ["working", "done"])

    def test_busy_supervisor_coalesces_then_delivers_once(self):
        self.current["supervisor"]["agent_status"] = "working"
        self.tick(60)
        self.tick(120)
        self.assertTrue(self.state["pending"])
        self.assertFalse(self.prompts())
        self.current["supervisor"]["agent_status"] = "done"
        self.tick(121)
        self.tick(122)
        self.assertEqual(len(self.prompts()), 1)

    def test_supervisor_readiness_rechecked_after_capture(self):
        def become_busy(run, *args):
            result = self.fake_call(run, *args)
            if args[:2] == ("agent", "read"):
                self.current["supervisor"]["agent_status"] = "working"
            return result

        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=become_busy),
        ):
            sheepdog.tick(self.directory, self.state, 60)
        self.assertFalse(self.prompts())
        self.assertTrue(self.state["pending"])
        self.assertIsNone(self.state["review"])
        self.tick(61)
        self.assertFalse(self.prompts())
        self.current["supervisor"]["agent_status"] = "idle"
        self.tick(62)
        self.tick(63)
        self.assertEqual(len(self.prompts()), 1)

    def test_blocked_or_unknown_supervisor_gets_no_input(self):
        for status in ("blocked", "unknown"):
            self.current["supervisor"]["agent_status"] = status
            self.tick(61)
        self.assertFalse(self.prompts())

    def test_worker_completion_or_block_triggers_before_timer(self):
        for status in ("done", "blocked", "unknown"):
            with self.subTest(status=status):
                self.state["review"] = None
                self.current["worker"]["agent_status"] = status
                self.current["worker"]["state_change_seq"] += 1
                self.tick(1)
        self.assertEqual(len(self.prompts()), 3)

    def test_replaced_agent_or_session_sends_nothing(self):
        for field, replacement in (
            ("terminal_id", "replacement"),
            ("agent_session", {"value": "new-session"}),
        ):
            original = self.current["worker"][field]
            self.current["worker"][field] = replacement
            with self.assertRaisesRegex(RuntimeError, "identity changed"):
                self.tick(61)
            self.current["worker"][field] = original
        self.assertFalse(self.prompts())

    def test_socket_replacement_stops_before_cli(self):
        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 99]),
            patch.object(sheepdog, "call", side_effect=self.fake_call),
            self.assertRaisesRegex(RuntimeError, "socket changed"),
        ):
            sheepdog.tick(self.directory, self.state, 61)
        self.assertFalse(self.calls)

    def test_timeout_latches_review_and_does_not_resend(self):
        def uncertain(run, *args):
            if args[:2] == ("agent", "prompt"):
                raise subprocess.TimeoutExpired("herdr", 15)
            return self.fake_call(run, *args)

        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=uncertain),
            self.assertRaises(subprocess.TimeoutExpired),
        ):
            sheepdog.tick(self.directory, self.state, 61)
        self.assertIsNotNone(self.state["review"])
        self.tick(62)
        self.assertFalse(self.prompts())

    def test_budget_and_human_stop_do_not_stop_worker(self):
        self.assertFalse(self.tick(1000))
        self.assertEqual(self.state["status"], "expired")
        self.state["status"] = "stopped"
        self.assertFalse(self.tick(1))
        self.assertFalse(self.prompts())
        self.assertFalse(any(c[:2] == ("agent", "send-keys") for c in self.calls))

    def command(self, *args):
        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=self.fake_call),
            patch.object(sheepdog.time, "time", return_value=100),
            patch("sys.argv", ["sheepdog.py", args[0], str(self.directory), *args[1:]]),
        ):
            sheepdog.main()

    def prepare_action(self, allowed=True):
        self.tick(61)
        self.calls.clear()
        self.state["allow_steer"] = allowed
        self.state["allow_abort"] = allowed
        sheepdog.save(self.directory, self.state)
        prompt = self.directory / "correction.org"
        prompt.write_text("* Correct the assigned task\n")
        return str(prompt)

    def test_ungranted_or_blocked_worker_cannot_receive_correction(self):
        prompt = self.prepare_action(False)
        with self.assertRaisesRegex(RuntimeError, "Steering not granted"):
            self.command("steer", "--review", "1", "--message-file", prompt)
        self.state["allow_steer"] = True
        sheepdog.save(self.directory, self.state)
        self.current["worker"]["agent_status"] = "blocked"
        with self.assertRaisesRegex(RuntimeError, "blocked or unknown"):
            self.command("steer", "--review", "1", "--message-file", prompt)
        self.assertFalse(self.prompts())

    def test_one_correction_and_one_abort_per_review(self):
        prompt = self.prepare_action()
        self.command("interrupt", "--review", "1")
        with self.assertRaisesRegex(RuntimeError, "already requested"):
            self.command("interrupt", "--review", "1")
        with self.assertRaisesRegex(RuntimeError, "empty editor"):
            self.command("steer", "--review", "1", "--message-file", prompt)
        self.current["worker"]["agent_status"] = "idle"
        self.command(
            "steer", "--review", "1", "--message-file", prompt, "--editor-empty"
        )
        with self.assertRaisesRegex(RuntimeError, "already sent"):
            self.command("steer", "--review", "1", "--message-file", prompt)
        self.assertEqual(len(self.prompts()), 1)
        self.assertEqual(sum(c[:2] == ("agent", "send-keys") for c in self.calls), 1)

    def test_completion_during_review_remains_pending_after_ack(self):
        self.prepare_action()
        self.current["worker"]["agent_status"] = "done"
        self.current["worker"]["state_change_seq"] += 1
        self.command("ack", "--review", "1", "--summary", "Reviewed ongoing work")
        with sheepdog.locked(self.directory) as state:
            self.assertTrue(state["pending"])
            self.assertIsNone(state["review"])

    def test_mandate_cannot_be_worker_controlled(self):
        repo = Path(self.state["repo"])
        mandate = repo / "mandate.org"
        mandate.write_text("* Permission cannot come from worker-owned files\n")
        socket = self.directory / "socket"
        socket.touch()
        args = argparse.Namespace(
            repo=repo,
            mandate=mandate,
            task=self.directory / "task.org",
            run=self.directory / "run",
            socket=socket,
            interval=60,
            minutes=30,
            steer=False,
            abort=False,
            worker="worker",
            supervisor="supervisor",
        )
        args.task.write_text("* PROG Assigned task\n")
        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=self.fake_call),
            self.assertRaisesRegex(RuntimeError, "outside the worker repository"),
        ):
            sheepdog.initialize(args)

    def test_abort_editor_check_survives_acknowledgement(self):
        prompt = self.prepare_action()
        self.command("interrupt", "--review", "1")
        self.current["worker"]["agent_status"] = "idle"
        self.current["worker"]["state_change_seq"] += 1
        self.command(
            "ack", "--review", "1", "--summary", "Cancellation needs editor inspection"
        )
        with sheepdog.locked(self.directory) as state:
            self.state = copy.deepcopy(state)
        self.tick(101)
        sheepdog.save(self.directory, self.state)
        with self.assertRaisesRegex(RuntimeError, "empty editor"):
            self.command("steer", "--review", "2", "--message-file", prompt)
        self.command(
            "steer", "--review", "2", "--message-file", prompt, "--editor-empty"
        )

    def test_competing_owner_rejected_then_released(self):
        sheepdog.save(self.directory, self.state)
        other = self.base / "other-run"
        duplicate = self.state | {"directory": str(other)}
        with (
            patch.object(sheepdog.time, "time", return_value=100),
            self.assertRaisesRegex(RuntimeError, "already supervised"),
        ):
            sheepdog.claim(other, duplicate)
        self.assertFalse(other.exists())
        self.assertEqual(
            sheepdog.read_record(Path(self.state["owner_file"]))["run"],
            str(self.directory),
        )
        self.command("stop", "--summary", "Human takeover")
        self.assertFalse(Path(self.state["owner_file"]).exists())
        sheepdog.claim(other, duplicate)
        self.assertEqual(
            sheepdog.read_record(Path(self.state["owner_file"]))["run"], str(other)
        )

    def test_stale_expired_or_missing_owner_can_be_reclaimed(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                sheepdog.save(self.directory, self.state)
                if missing:
                    (self.directory / "state.json").unlink()
                other = self.base / f"replacement-{missing}"
                duplicate = self.state | {"directory": str(other), "expires": 2000}
                with patch.object(sheepdog.time, "time", return_value=1001):
                    sheepdog.claim(other, duplicate)
                # The obsolete run cannot release the new owner's lease.
                sheepdog.release(self.state)
                self.assertEqual(
                    sheepdog.read_record(Path(self.state["owner_file"]))["run"],
                    str(other),
                )
                Path(self.state["owner_file"]).write_text(
                    json.dumps({"run": str(self.directory)})
                )

    def test_simultaneous_claims_have_exactly_one_owner(self):
        barrier = threading.Barrier(2)
        owner = self.base / "race/worker.json"

        def attempt(index):
            directory = self.base / f"race-{index}"
            run = self.state | {
                "directory": str(directory),
                "owner_file": str(owner),
                "expires": sheepdog.time.time() + 1000,
            }
            barrier.wait(timeout=5)
            try:
                sheepdog.claim(directory, run)
            except RuntimeError as error:
                return str(error)
            return "owned"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, range(2)))
        self.assertEqual(outcomes.count("owned"), 1)
        self.assertEqual(sum("already supervised" in x for x in outcomes), 1)
        self.assertTrue(Path(sheepdog.read_record(owner)["run"]).is_dir())

    def test_org_group_access_drift_does_not_block_reviews(self):
        org = self.base / "org/work/task"
        org.mkdir(mode=0o700, parents=True)
        task = org / "task.org"
        task.write_text("* PROG Assigned task\n")
        task.chmod(0o600)
        self.state["task"] = str(task)
        self.prepare_action()
        org.chmod(0o770)
        task.chmod(0o660)
        self.next_review()
        self.assertEqual(self.state["status"], "active")
        self.assertEqual(self.state["review"]["id"], 2)
        self.assertEqual(org.stat().st_mode & 0o777, 0o770)
        self.assertEqual(task.stat().st_mode & 0o777, 0o660)
        self.assertFalse(any(c[:2] == ("agent", "send-keys") for c in self.calls))

    def test_runtime_ownership_registry_still_requires_private_mode(self):
        owner = Path(self.state["owner_file"])
        owner.parent.chmod(0o770)
        with (
            self.assertRaisesRegex(RuntimeError, "Ownership directory must be private"),
            sheepdog.ownership_lock(owner),
        ):
            self.fail("Group-accessible runtime registry must not be accepted")
        self.assertEqual(owner.parent.stat().st_mode & 0o777, 0o770)
        self.assertFalse(self.prompts())

    def test_corrupt_owner_fails_closed(self):
        Path(self.state["owner_file"]).write_text("not json")
        with self.assertRaisesRegex(RuntimeError, "Cannot read Sheepdog record"):
            sheepdog.claim(self.base / "other", self.state)
        self.assertFalse(self.prompts())

    def test_review_deadline_stalls_without_replay_or_keys(self):
        self.tick(60)
        self.assertFalse(self.tick(360))
        self.assertEqual(self.state["status"], "stalled")
        self.assertEqual(len(self.prompts()), 1)
        sheepdog.save(self.directory, self.state)
        handoff = (self.directory / "handoff.org").read_text()
        self.assertIn("was not acknowledged", handoff)
        self.assertIn("continues unsupervised", handoff)
        self.assertTrue(Path(self.state["owner_file"]).exists())
        with (
            self.assertRaisesRegex(RuntimeError, "already supervised"),
            patch.object(sheepdog.time, "time", return_value=361),
        ):
            sheepdog.claim(self.base / "other", self.state)

    def test_late_ack_or_steer_cannot_bypass_review_deadline(self):
        self.prepare_action()
        with (
            patch.object(sheepdog.time, "time", return_value=361),
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=self.fake_call),
            self.assertRaisesRegex(RuntimeError, "Review deadline"),
        ):
            sheepdog.review_guard(self.state, 1)
        self.assertEqual(self.state["status"], "stalled")
        self.assertFalse(self.prompts())

    def test_expiry_records_blocked_worker_and_preserves_handoff(self):
        self.current["worker"]["agent_status"] = "blocked"
        self.state["progress"] = {
            "accepted": "Slice one",
            "verification": "Five tests passed",
            "publication": "Local origin commit abc",
            "remaining": "Slice two not started",
        }
        self.tick(1000)
        sheepdog.save(self.directory, self.state)
        text = (self.directory / "handoff.org").read_text()
        for value in self.state["progress"].values():
            self.assertIn(value, text)
        self.assertIn("blocked", text)
        self.assertIn("budget expired", text)
        self.assertFalse(Path(self.state["owner_file"]).exists())
        self.assertFalse(self.prompts())

    def test_repository_departure_detected_but_subdirectory_allowed(self):
        child = Path(self.state["repo"]) / "subdir"
        child.mkdir()
        self.current["worker"]["foreground_cwd"] = str(child)
        self.tick(1)
        for field in ("cwd", "foreground_cwd"):
            previous = self.current["worker"][field]
            self.current["worker"][field] = str(self.base)
            with self.assertRaisesRegex(RuntimeError, "left assigned repository"):
                self.tick(61)
            self.current["worker"][field] = previous
        self.assertFalse(self.prompts())

    def test_review_prompt_names_sheepdog_and_exact_task(self):
        self.tick(60)
        message = self.prompts()[0][-1]
        self.assertIn("Follow sheepdog", message)
        self.assertIn(self.state["task"], message)
        self.assertIn(self.state["task_heading"], message)
        self.assertIn("ACK does not resolve recovery", message)

    def test_launch_records_observed_model_task_and_unique_worker(self):
        org = self.base / "org/work"
        org.mkdir(parents=True)
        org.chmod(0o770)
        task = org / "task.org"
        task.write_text("* PROG Assigned task\n")
        task.chmod(0o660)
        mandate = org / "mandate.org"
        mandate.write_text("* Assigned permissions\n")
        mandate.chmod(0o660)
        socket = self.base / "socket"
        socket.touch()
        args = argparse.Namespace(
            run=self.base / "initialized",
            repo=Path(self.state["repo"]),
            socket=socket,
            task=task,
            mandate=mandate,
            task_heading="* PROG Assigned task",
            supervisor_model="observed-model",
            model_evidence="Current session metadata, session-test, at launch",
            notification_route="",
            review_seconds=300,
            interval=60,
            minutes=30,
            steer=True,
            abort=True,
            worker="worker",
            supervisor="supervisor",
        )
        with (
            patch.dict(
                sheepdog.os.environ, {"XDG_STATE_HOME": str(self.base / "state")}
            ),
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=self.fake_call),
            patch.object(sheepdog.time, "time", return_value=100),
        ):
            with patch("builtins.print") as printed:
                sheepdog.initialize(args)
            bound = sheepdog.read_record(args.run / "state.json")
            self.assertEqual(bound["supervisor_model"], "observed-model")
            self.assertEqual(bound["task"], str(task))
            self.assertIsNone(bound["recovery"])
            self.assertEqual(bound["notification"]["route"], "")
            self.assertEqual(bound["notification"]["status"], "not attempted")
            self.assertIn(
                "No authorized notification route supplied", printed.call_args.args[0]
            )
            args.run = self.base / "competitor"
            with (
                patch.dict(
                    sheepdog.os.environ,
                    {"XDG_STATE_HOME": str(self.base / "different-state")},
                ),
                self.assertRaisesRegex(RuntimeError, "already supervised"),
            ):
                sheepdog.initialize(args)
            self.assertFalse(args.run.exists())
        self.assertFalse(self.prompts())

    def test_ack_and_stop_keep_durable_progress_without_launcher(self):
        self.prepare_action()
        self.command(
            "ack",
            "--review",
            "1",
            "--summary",
            "Accepted slice",
            "--accepted",
            "Slice one",
            "--verification",
            "Tests passed",
            "--publication",
            "Local origin abc",
            "--remaining",
            "Slice two",
        )
        self.command("stop", "--summary", "Human pause", "--outcome", "paused")
        text = (self.directory / "handoff.org").read_text()
        for value in (
            "Slice one",
            "Tests passed",
            "Local origin abc",
            "Slice two",
            "Human pause",
            "paused",
        ):
            self.assertIn(value, text)
        self.assertFalse(Path(self.state["owner_file"]).exists())
        self.assertFalse(self.prompts())

    def reload_state(self):
        self.state = sheepdog.read_record(self.directory / "state.json")

    def next_review(self):
        self.command(
            "ack", "--review", str(self.state["counter"]), "--summary", "Follow up"
        )
        self.reload_state()
        self.tick(161)
        sheepdog.save(self.directory, self.state)

    def test_false_alarm_evidence_restores_interrupted_task(self):
        session = self.base / "worker.jsonl"
        entries = [
            {
                "type": "message",
                "id": "question",
                "parentId": None,
                "timestamp": "2026-10-01T19:59:00Z",
                "message": {"role": "user", "content": "Is browser isolated?"},
            },
            {
                "type": "message",
                "id": "reply",
                "parentId": "question",
                "timestamp": "2026-10-01T20:00:00Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "Isolation confirmed in disposable context.",
                        }
                    ],
                },
            },
        ]
        session.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n")
        self.current["worker"]["agent_session"] = {
            "kind": "path",
            "value": str(session),
        }
        self.state["worker"]["identity"] = sheepdog.identity(self.current["worker"])
        prompt = self.prepare_action()
        self.command(
            "interrupt", "--review", "1", "--reason", "Potential shared browser context"
        )
        evidence = sheepdog.session_evidence(
            self.state, "2026-10-01T19:59:00Z", "Isolation confirmed", 8
        )
        reply = evidence["entries"][0]
        self.assertEqual(reply["parentId"], "question")
        Path(prompt).write_text(
            "* Withdraw false alarm and resume audio validation\n\n" + reply["text"]
        )
        self.current["worker"]["agent_status"] = "idle"
        self.command(
            "steer", "--review", "1", "--editor-empty", "--message-file", prompt
        )
        self.reload_state()
        self.assertEqual(self.state["recovery"]["phase"], "correction_pending")
        self.current["worker"]["agent_status"] = "working"
        self.command(
            "recover",
            "--review",
            "1",
            "--evidence",
            "Session reply confirms isolated context; resume prompt received; audio check started.",
        )
        self.reload_state()
        self.assertIsNone(self.state["recovery"])
        self.assertEqual(self.state["status"], "active")
        self.assertEqual(len(self.prompts()), 1)
        self.assertIn(reply["text"], self.prompts()[0][-1])

    def test_real_correction_persists_across_ack_without_duplicates(self):
        prompt = self.prepare_action()
        Path(prompt).write_text(
            "* Correct browser target\n\nUse the mandate-approved isolated context. Confirm the context, then resume audio checks.\n"
        )
        self.command(
            "interrupt",
            "--review",
            "1",
            "--reason",
            "Confirmed inappropriate browser context; isolated alternative authorized",
        )
        self.reload_state()
        self.next_review()
        with self.assertRaisesRegex(RuntimeError, "recovery"):
            self.command("interrupt", "--review", "2")
        self.current["worker"]["agent_status"] = "idle"
        self.command(
            "steer", "--review", "2", "--editor-empty", "--message-file", prompt
        )
        self.reload_state()
        self.next_review()
        with self.assertRaisesRegex(RuntimeError, "recovery"):
            self.command("steer", "--review", "3", "--message-file", prompt)
        with self.assertRaisesRegex(RuntimeError, "recovery"):
            self.command("stop", "--outcome", "completed")
        self.assertIn(
            "correction_pending", (self.directory / "handoff.org").read_text()
        )
        self.current["worker"]["agent_status"] = "working"
        self.command(
            "recover",
            "--review",
            "3",
            "--evidence",
            "Worker received isolated-context correction; target now isolated; next allowed test running.",
        )
        self.reload_state()
        self.assertIsNone(self.state["recovery"])
        self.assertEqual(sum(c[:2] == ("agent", "send-keys") for c in self.calls), 1)
        self.assertEqual(sum(c[2] == "worker" for c in self.prompts()), 1)

    def test_verbose_output_does_not_hide_pinned_session_reply(self):
        session = self.base / "worker.jsonl"
        entries = [{"type": "session", "version": 3}]
        for index, text in enumerate(
            ["Is browser isolated?", "Isolation confirmed in disposable context."]
            + ["verbose output" * 1000] * 100
        ):
            entries.append(
                {
                    "type": "message",
                    "id": str(index),
                    "parentId": str(index - 1),
                    "timestamp": "2026-10-01T20:00:00Z",
                    "message": {
                        "role": "assistant" if index == 1 else "toolResult",
                        "content": [{"type": "text", "text": text}],
                    },
                }
            )
        session.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        self.current["worker"]["agent_session"] = {
            "kind": "path",
            "value": str(session),
        }
        self.state["worker"]["identity"] = sheepdog.identity(self.current["worker"])
        self.prepare_action()
        result = sheepdog.session_evidence(
            self.state, "2026-10-01T19:59:00Z", "Isolation confirmed", 8
        )
        self.assertEqual(result["matched"], 1)
        self.assertEqual(result["entries"][0]["id"], "1")
        self.assertIn("disposable context", result["entries"][0]["text"])
        with patch.object(sheepdog, "call", side_effect=self.fake_call):
            self.assertNotIn("Isolation confirmed", sheepdog.output(self.state))
        session.unlink()
        with self.assertRaises(OSError):
            sheepdog.session_evidence(
                self.state, "2026-10-01T19:59:00Z", "isolation", 8
            )
        self.assertFalse(self.prompts())

    def test_evidence_is_bounded_and_fails_on_incomplete_history(self):
        session = self.base / "worker.jsonl"
        entries = [
            {
                "type": "message",
                "id": str(index),
                "timestamp": "2026-10-01T20:00:00Z",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "check " * 1000}],
                },
            }
            for index in range(12)
        ]
        session.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n")
        self.current["worker"]["agent_session"] = {
            "kind": "path",
            "value": str(session),
        }
        self.state["worker"]["identity"] = sheepdog.identity(self.current["worker"])
        self.prepare_action()
        with patch("builtins.print") as printed:
            self.command("evidence", "--since", "2026-10-01T19:59:00Z", "--limit", "2")
        result = json.loads(printed.call_args.args[0])
        self.assertEqual(result["matched"], 12)
        self.assertEqual(result["omitted"], 10)
        self.assertEqual(len(result["entries"]), 2)
        self.assertTrue(result["entries"][0]["text_truncated"])
        self.assertEqual(result["entries"][0]["id"], "10")
        self.assertFalse(any(c[:2] == ("agent", "read") for c in self.calls))
        self.assertEqual(
            sheepdog.session_evidence(self.state, "2026-10-01T20:01:00Z", "", 2)[
                "matched"
            ],
            0,
        )
        with session.open("a") as source:
            source.write('{"type":')
        with self.assertRaisesRegex(RuntimeError, "not proof of nonresponse"):
            self.command("evidence", "--since", "2026-10-01T19:59:00Z")
        self.assertFalse(self.prompts())

    def test_recovery_needs_safe_state_and_evidence(self):
        prompt = self.prepare_action()
        self.command("interrupt", "--review", "1")
        with self.assertRaisesRegex(RuntimeError, "awaiting recovery"):
            self.command(
                "recover", "--review", "1", "--evidence", "Still investigating"
            )
        self.current["worker"]["agent_status"] = "idle"
        self.command(
            "steer", "--review", "1", "--editor-empty", "--message-file", prompt
        )
        with self.assertRaisesRegex(RuntimeError, "with evidence"):
            self.command("recover", "--review", "1", "--evidence", " ")
        self.current["worker"]["agent_status"] = "blocked"
        with self.assertRaisesRegex(RuntimeError, "with evidence"):
            self.command(
                "recover", "--review", "1", "--evidence", "No safe recovery yet"
            )
        self.reload_state()
        self.assertIsNotNone(self.state["recovery"])

    def test_uncertain_correction_cannot_be_recovered_or_replayed(self):
        prompt = self.prepare_action()
        original = self.fake_call
        attempts = []

        def uncertain(run, *args):
            if args[:3] == ("agent", "prompt", "worker"):
                attempts.append(args)
                raise subprocess.TimeoutExpired("herdr", 15)
            return original(run, *args)

        with (
            patch.object(self, "fake_call", side_effect=uncertain),
            self.assertRaises(subprocess.TimeoutExpired),
        ):
            self.command("steer", "--review", "1", "--message-file", prompt)
        self.reload_state()
        self.assertEqual(self.state["status"], "paused")
        self.assertEqual(self.state["recovery"]["phase"], "correction_pending")
        with self.assertRaisesRegex(RuntimeError, "No active review"):
            self.command(
                "recover", "--review", "1", "--evidence", "No receipt evidence"
            )
        with self.assertRaisesRegex(RuntimeError, "No active review"):
            self.command("steer", "--review", "1", "--message-file", prompt)
        self.assertEqual(len(attempts), 1)
        self.assertTrue(Path(self.state["owner_file"]).exists())

    def test_notification_without_route_is_not_delivery(self):
        self.prepare_action()
        with self.assertRaisesRegex(RuntimeError, "authorized notification route"):
            self.command(
                "stop",
                "--notification-status",
                "delivered",
                "--notification-evidence",
                "Local handoff written",
            )
        self.command(
            "stop",
            "--outcome",
            "blocked",
            "--notification-status",
            "unavailable",
            "--notification-evidence",
            "No authorized external route supplied; handoff only.",
        )
        self.reload_state()
        self.assertEqual(self.state["notification"]["status"], "unavailable")
        self.assertEqual(self.state["status"], "stopped")

    def test_out_of_scope_escalation_keeps_notification_result(self):
        self.state["notification"] = {
            "route": "Explicitly authorized test route",
            "status": "not attempted",
        }
        for status in ("delivered", "failed", "unavailable"):
            with self.subTest(status=status):
                self.prepare_action()
                self.command(
                    "stop",
                    "--summary",
                    "Need permission to replace browser service; no in-scope remedy remains.",
                    "--outcome",
                    "blocked",
                    "--remaining",
                    "Authorize service replacement or choose another check.",
                    "--notification-status",
                    status,
                    "--notification-evidence",
                    "Authorized route tool result: " + status,
                )
                self.reload_state()
                self.assertEqual(self.state["notification"]["status"], status)
                self.assertIn(status, (self.directory / "handoff.org").read_text())
                self.assertFalse(self.prompts())
                self.state["status"] = "active"
                self.state["review"] = None
                self.state["pending"] = True
                Path(self.state["owner_file"]).write_text(
                    json.dumps({"run": str(self.directory)})
                )
                self.state["counter"] = 0

    def test_stale_review_cannot_authorize_input(self):
        self.tick(61)
        with self.assertRaisesRegex(RuntimeError, "Stale review"):
            sheepdog.review_guard(self.state, 0)


if __name__ == "__main__":
    unittest.main()

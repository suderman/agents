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
from typing import Any
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
        self.state: dict[str, Any] = {
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
            patch.object(sheepdog.time, "time", return_value=now),
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
            patch.object(sheepdog.time, "time", return_value=60),
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
            patch.object(sheepdog.time, "time", return_value=60),
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
        self.state["review_hard_seconds"] = 1800
        self.state["expires"] = 4000

        def uncertain(run, *args):
            if args[:2] == ("agent", "prompt"):
                raise subprocess.TimeoutExpired("herdr", 15)
            return self.fake_call(run, *args)

        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=uncertain),
            patch.object(sheepdog.time, "time", return_value=61),
            self.assertRaises(subprocess.TimeoutExpired),
        ):
            sheepdog.tick(self.directory, self.state, 61)
        self.assertIsNotNone(self.state["review"])
        review = copy.deepcopy(self.state["review"])
        self.tick(2000)
        self.assertEqual(self.state["status"], "paused")
        self.assertEqual(self.state["review"], review)
        self.assertFalse(self.prompts())

    def test_budget_and_human_stop_do_not_stop_worker(self):
        self.assertFalse(self.tick(1000))
        self.assertEqual(self.state["status"], "expired")
        self.state["status"] = "stopped"
        self.assertFalse(self.tick(1))
        self.assertFalse(self.prompts())
        self.assertFalse(any(c[:2] == ("agent", "send-keys") for c in self.calls))

    def command(self, *args, now=100):
        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=self.fake_call),
            patch.object(sheepdog.time, "time", return_value=now),
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

    def test_working_supervisor_keeps_review_past_five_minute_soft_threshold(self):
        self.state["review_hard_seconds"] = 1800
        self.state["expires"] = 4000
        self.tick(60)
        self.current["supervisor"]["agent_status"] = "working"
        self.assertTrue(self.tick(361))
        self.assertEqual(self.state["status"], "active")
        self.assertEqual(self.state["review"]["id"], 1)
        self.assertEqual(len(self.prompts()), 1)

    def test_legacy_review_deadline_stalls_without_replay_or_keys(self):
        self.tick(60)
        self.assertFalse(self.tick(360))
        self.assertEqual(self.state["status"], "stalled")
        self.assertEqual(len(self.prompts()), 1)
        sheepdog.save(self.directory, self.state)
        handoff = (self.directory / "handoff.org").read_text()
        self.assertIn("hard acknowledgement timeout", handoff)
        self.assertIn("continues unsupervised", handoff)
        self.assertTrue(Path(self.state["owner_file"]).exists())
        with (
            self.assertRaisesRegex(RuntimeError, "already supervised"),
            patch.object(sheepdog.time, "time", return_value=361),
        ):
            sheepdog.claim(self.base / "other", self.state)

    def test_legacy_late_ack_or_steer_cannot_bypass_review_deadline(self):
        self.prepare_action()
        with (
            patch.object(sheepdog.time, "time", return_value=361),
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=self.fake_call),
            self.assertRaisesRegex(RuntimeError, "Review hard timeout"),
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
            review_hard_seconds=1800,
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
            self.assertEqual(
                (bound["review_seconds"], bound["review_hard_seconds"]), (300, 1800)
            )
            self.assertIn(
                "Hard timeout: 1800 seconds", (args.run / "handoff.org").read_text()
            )
            init_event = json.loads(
                (args.run / "events.jsonl").read_text().splitlines()[0]
            )
            self.assertEqual(init_event["review_hard_seconds"], 1800)
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

    def test_recovery_needs_safe_state_and_evidence_past_soft_threshold(self):
        prompt = self.fresh_review()
        self.command("interrupt", "--review", "1", now=362)
        with self.assertRaisesRegex(RuntimeError, "awaiting recovery"):
            self.command(
                "recover", "--review", "1", "--evidence", "Still investigating", now=363
            )
        self.current["worker"]["agent_status"] = "idle"
        self.command(
            "steer",
            "--review",
            "1",
            "--editor-empty",
            "--message-file",
            prompt,
            now=364,
        )
        with self.assertRaisesRegex(RuntimeError, "with evidence"):
            self.command("recover", "--review", "1", "--evidence", " ", now=365)
        for status in ("blocked", "unknown"):
            self.current["worker"]["agent_status"] = status
            with (
                self.subTest(status=status),
                self.assertRaisesRegex(RuntimeError, "with evidence"),
            ):
                self.command(
                    "recover",
                    "--review",
                    "1",
                    "--evidence",
                    "No safe recovery yet",
                    now=366,
                )
        self.reload_state()
        self.assertIsNotNone(self.state["recovery"])

    def test_uncertain_correction_cannot_be_recovered_or_replayed_past_soft(self):
        prompt = self.fresh_review()
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
            self.command("steer", "--review", "1", "--message-file", prompt, now=362)
        self.reload_state()
        self.assertEqual(self.state["status"], "paused")
        self.assertEqual(self.state["recovery"]["phase"], "correction_pending")
        with self.assertRaisesRegex(RuntimeError, "No active review"):
            self.command(
                "recover", "--review", "1", "--evidence", "No receipt evidence", now=363
            )
        with self.assertRaisesRegex(RuntimeError, "No active review"):
            self.command("steer", "--review", "1", "--message-file", prompt, now=364)
        with self.assertRaisesRegex(RuntimeError, "No active review"):
            self.command(
                "ack",
                "--review",
                "1",
                "--summary",
                "Cannot bypass delivery latch",
                now=365,
            )
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

    def fresh_review(self):
        self.state["review_hard_seconds"] = 1800
        self.state["expires"] = 4000
        return self.prepare_action()

    def events(self):
        return [
            json.loads(line)
            for line in (self.directory / "events.jsonl").read_text().splitlines()
        ]

    def test_soft_overdue_is_durable_once_without_reminders_or_renewal(self):
        self.fresh_review()
        original = copy.deepcopy(self.state["review"])
        expiry = self.state["expires"]
        self.current["supervisor"]["agent_status"] = "working"
        for now in (361, 500, 900):
            self.assertTrue(self.tick(now))
            sheepdog.save(self.directory, self.state)
            self.reload_state()
        warnings = [e for e in self.events() if e["event"] == "review_overdue"]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["supervisor_status"], "working")
        self.assertEqual(self.state["review"], original | {"overdue_at": 361})
        self.assertEqual(self.state["expires"], expiry)
        self.assertTrue(self.state["pending"])
        self.assertFalse(self.prompts())
        self.assertFalse(any(c[:2] == ("agent", "send-keys") for c in self.calls))
        self.assertIn("overdue", (self.directory / "handoff.org").read_text())

    def test_overdue_latch_is_saved_before_warning_event(self):
        self.fresh_review()
        original = sheepdog.record

        def observe_warning(directory, event, **fields):
            if event == "review_overdue":
                persisted = sheepdog.read_record(directory / "state.json")
                self.assertEqual(persisted["review"].get("overdue_at"), 362)
            return original(directory, event, **fields)

        with patch.object(sheepdog, "record", side_effect=observe_warning):
            self.tick(362)
        self.reload_state()
        self.tick(363)
        self.assertEqual(sum(e["event"] == "review_overdue" for e in self.events()), 1)
        self.assertFalse(self.prompts())

    def test_all_controls_can_complete_after_soft_threshold(self):
        prompt = self.fresh_review()
        self.current["supervisor"]["agent_status"] = "working"
        self.command("interrupt", "--review", "1", now=362)
        self.current["worker"]["agent_status"] = "idle"
        self.command(
            "steer",
            "--review",
            "1",
            "--message-file",
            prompt,
            "--editor-empty",
            now=363,
        )
        self.current["worker"]["agent_status"] = "working"
        self.command(
            "recover",
            "--review",
            "1",
            "--evidence",
            "Correction received and check resumed",
            now=364,
        )
        self.command("ack", "--review", "1", "--summary", "Verified", now=365)
        self.reload_state()
        self.assertEqual(self.state["status"], "active")
        self.assertIsNone(self.state["review"])
        self.assertIsNone(self.state["recovery"])
        self.assertEqual(self.state["expires"], 4000)
        self.assertEqual(self.state["next_review"], 425)
        self.assertEqual(len(self.prompts()), 1)
        self.assertEqual(sum(c[:2] == ("agent", "send-keys") for c in self.calls), 1)
        self.assertEqual(sum(e["event"] == "review_overdue" for e in self.events()), 1)

    def test_ready_supervisor_can_ack_at_last_second_before_hard_cap(self):
        self.fresh_review()
        for status in ("idle", "done"):
            with self.subTest(status=status):
                original = copy.deepcopy(self.state)
                self.current["supervisor"]["agent_status"] = status
                sheepdog.save(self.directory, original)
                self.command(
                    "ack", "--review", "1", "--summary", "Ready late ACK", now=1860
                )
                self.reload_state()
                self.assertIsNone(self.state["review"])
                self.assertEqual(self.state["expires"], 4000)
                self.state = original
        self.assertFalse(self.prompts())

    def test_hard_timeout_stops_regardless_of_supervisor_activity(self):
        self.fresh_review()
        original = copy.deepcopy(self.state)
        for supervisor in ("working", "idle", "done", "blocked", "unknown"):
            for worker in ("working", "blocked", "unknown"):
                with self.subTest(supervisor=supervisor, worker=worker):
                    self.state = copy.deepcopy(original)
                    self.current["supervisor"]["agent_status"] = supervisor
                    self.current["worker"]["agent_status"] = worker
                    self.assertFalse(self.tick(1861))
                    self.assertEqual(self.state["status"], "stalled")
                    self.assertIn(
                        "hard acknowledgement timeout", self.state["stopping_reason"]
                    )
                    self.assertEqual(
                        self.events()[-1]["worker"]["agent_status"], worker
                    )
                    self.assertEqual(
                        self.events()[-1]["supervisor"]["agent_status"], supervisor
                    )
                    self.assertFalse(self.tick(1862))
                    self.assertEqual(self.state["expires"], 4000)
        self.assertFalse(self.prompts())

    def test_controls_reject_hard_timeout_without_watcher_tick(self):
        prompt = self.fresh_review()
        original = copy.deepcopy(self.state)
        for command, extra in (
            ("ack", ["--summary", "Late"]),
            ("steer", ["--message-file", prompt]),
            ("interrupt", []),
            ("recover", ["--evidence", "Late"]),
        ):
            with self.subTest(command=command):
                sheepdog.save(self.directory, copy.deepcopy(original))
                with self.assertRaisesRegex(RuntimeError, "Review hard timeout"):
                    self.command(command, "--review", "1", *extra, now=1861)
                self.reload_state()
                self.assertEqual(self.state["status"], "stalled")
                with self.assertRaisesRegex(RuntimeError, "No active review"):
                    self.command(command, "--review", "1", *extra, now=1862)
        self.assertFalse(self.prompts())
        self.assertFalse(any(c[:2] == ("agent", "send-keys") for c in self.calls))

    def test_overall_expiry_wins_over_both_review_clocks(self):
        self.fresh_review()
        self.state["expires"] = 200
        self.assertFalse(self.tick(200))
        self.assertEqual(self.state["status"], "expired")
        self.assertIn("budget expired", self.state["stopping_reason"])
        self.assertFalse(self.prompts())
        self.assertFalse(any(e["event"] == "review_overdue" for e in self.events()))

    def test_expiry_during_fresh_agent_checks_cannot_accept_ack(self):
        self.fresh_review()
        self.state["expires"] = 500
        sheepdog.save(self.directory, self.state)
        clock = [499]
        original = self.fake_call

        def slow_get(run, *args):
            result = original(run, *args)
            if args[:3] == ("agent", "get", "supervisor"):
                clock[0] = 500
            return result

        with (
            patch.object(self, "fake_call", side_effect=slow_get),
            patch.object(sheepdog.time, "time", side_effect=lambda: clock[0]),
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=slow_get),
            self.assertRaisesRegex(RuntimeError, "Watch budget expired"),
        ):
            sheepdog.review_guard(self.state, 1)
        self.assertEqual(self.state["status"], "expired")

    def test_clocks_start_after_capture_only_for_fresh_bindings(self):
        original_state = copy.deepcopy(self.state)
        original = self.fake_call
        for fresh in (False, True):
            with self.subTest(fresh=fresh):
                self.state = copy.deepcopy(original_state)
                if fresh:
                    self.state["review_hard_seconds"] = 1800
                clock = [60]

                def slow_capture(run, *args, clock=clock):
                    result = original(run, *args)
                    if args[:2] == ("agent", "read"):
                        clock[0] = 120
                    return result

                with (
                    patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
                    patch.object(sheepdog, "call", side_effect=slow_capture),
                    patch.object(
                        sheepdog.time, "time", side_effect=lambda clock=clock: clock[0]
                    ),
                ):
                    self.assertTrue(sheepdog.tick(self.directory, self.state, 60))
                self.assertEqual(self.state["review"]["time"], 120 if fresh else 60)
                self.assertEqual(
                    self.state["review"]["deadline"], 420 if fresh else 360
                )
                if fresh:
                    self.assertEqual(self.state["review"]["hard_deadline"], 1920)

    def test_expiry_during_capture_never_submits_or_leaves_unsent_review(self):
        self.state["review_hard_seconds"] = 1800
        self.state["expires"] = 100
        original = self.fake_call
        clock = [60]

        def slow_capture(run, *args):
            result = original(run, *args)
            if args[:2] == ("agent", "read"):
                clock[0] = 100
                self.current["supervisor"]["agent_status"] = "working"
            return result

        with (
            patch.object(sheepdog, "socket_identity", return_value=[1, 2]),
            patch.object(sheepdog, "call", side_effect=slow_capture),
            patch.object(sheepdog.time, "time", side_effect=lambda: clock[0]),
        ):
            self.assertFalse(sheepdog.tick(self.directory, self.state, 60))
        self.assertEqual(self.state["status"], "expired")
        self.assertIsNone(self.state["review"])
        self.assertFalse(self.prompts())

    def test_default_clocks_and_evidence_cap_without_extending_watch(self):
        self.state["review_seconds"] = 900
        self.state["review_hard_seconds"] = 1800
        self.tick(60)
        review = copy.deepcopy(self.state["review"])
        evidence = json.loads((self.directory / "review.json").read_text())
        self.assertEqual((review["deadline"], review["hard_deadline"]), (960, 1860))
        self.assertEqual(evidence["hard_end"], 1000)
        self.assertEqual(
            (evidence["review_seconds"], evidence["review_hard_seconds"]), (900, 1800)
        )
        self.assertTrue(self.tick(961))
        self.assertFalse(self.tick(1000))
        self.assertEqual(self.state["status"], "expired")
        self.assertEqual(self.state["expires"], 1000)
        self.assertEqual(len(self.prompts()), 1)

    def test_invalid_new_clock_values_cannot_widen_binding(self):
        self.fresh_review()
        original = copy.deepcopy(self.state)
        for hard_seconds, hard_deadline in (
            (1800, float("nan")),
            (1800, 99999),
            (7201, 7262),
            (0, 61),
        ):
            with self.subTest(hard_seconds=hard_seconds, hard_deadline=hard_deadline):
                self.state = copy.deepcopy(original)
                self.state["review_hard_seconds"] = hard_seconds
                self.state["review"]["hard_deadline"] = hard_deadline
                with self.assertRaisesRegex(RuntimeError, "[Rr]eview"):
                    self.tick(362)
        self.assertFalse(self.prompts())

    def test_incomplete_clock_bindings_fail_closed(self):
        self.fresh_review()
        original = copy.deepcopy(self.state)
        for field, location in (
            ("review_hard_seconds", "run"),
            ("hard_deadline", "review"),
        ):
            with self.subTest(field=field):
                self.state = copy.deepcopy(original)
                target = self.state if location == "run" else self.state["review"]
                del target[field]
                with self.assertRaisesRegex(RuntimeError, "Incomplete review clock"):
                    self.tick(362)
        self.assertFalse(self.prompts())

    def test_legacy_deadline_remains_hard_and_never_migrates(self):
        self.prepare_action()
        original = copy.deepcopy(self.state)
        self.assertTrue(self.tick(360))
        self.assertNotIn("hard_deadline", self.state["review"])
        self.assertNotIn("review_hard_seconds", self.state)
        self.assertFalse(self.tick(361))
        for status in ("stalled", "stopped", "paused", "expired"):
            with self.subTest(status=status):
                self.state = copy.deepcopy(original) | {"status": status}
                self.assertFalse(self.tick(362))
                self.assertEqual(self.state["status"], status)
        self.assertFalse(self.prompts())
        self.assertFalse(any(e["event"] == "review_overdue" for e in self.events()))

    def test_clock_limits_and_cli_defaults(self):
        for soft, hard in ((1, 1), (300, 1800), (900, 1800), (3600, 7200)):
            sheepdog.review_limits(soft, hard)
        for soft, hard in (
            (0, 1800),
            (-1, 1800),
            (3601, 7200),
            (300, 0),
            (300, -1),
            (300, 299),
            (900, 7201),
            (300, float("nan")),
            (True, 1800),
        ):
            with (
                self.subTest(soft=soft, hard=hard),
                self.assertRaisesRegex(RuntimeError, "Review"),
            ):
                sheepdog.review_limits(soft, hard)
        argv = [
            "sheepdog.py",
            "init",
            str(self.base / "new"),
            "--socket",
            "/socket",
            "--repo",
            self.state["repo"],
            "--mandate",
            "/mandate.org",
            "--task",
            "/task.org",
            "--worker",
            "worker",
            "--supervisor",
            "supervisor",
            "--task-heading",
            "* PROG Assigned task",
            "--supervisor-model",
            "test",
            "--model-evidence",
            "test session",
        ]
        with (
            patch("sys.argv", argv),
            patch.object(sheepdog, "initialize") as initialize,
        ):
            sheepdog.main()
        args = initialize.call_args.args[0]
        self.assertEqual((args.review_seconds, args.review_hard_seconds), (900, 1800))

    def test_invalid_init_limits_make_no_binding_or_transport_calls(self):
        task = self.base / "task.org"
        mandate = self.base / "mandate.org"
        task.write_text("* PROG Assigned task\n")
        mandate.write_text("* Synthetic mandate\n")
        for soft, hard in ((0, 1800), (3601, 7200), (900, 0), (900, 899), (900, 7201)):
            with self.subTest(soft=soft, hard=hard):
                argv = [
                    "sheepdog.py",
                    "init",
                    str(self.base / "new"),
                    "--socket",
                    str(self.base / "socket"),
                    "--repo",
                    self.state["repo"],
                    "--mandate",
                    str(mandate),
                    "--task",
                    str(task),
                    "--task-heading",
                    "* PROG Assigned task",
                    "--worker",
                    "worker",
                    "--supervisor",
                    "supervisor",
                    "--supervisor-model",
                    "test",
                    "--model-evidence",
                    "test session",
                    "--review-seconds",
                    str(soft),
                    "--review-hard-seconds",
                    str(hard),
                ]
                with (
                    patch("sys.argv", argv),
                    patch.object(sheepdog, "call") as call,
                    self.assertRaisesRegex(RuntimeError, "Review"),
                ):
                    sheepdog.main()
                call.assert_not_called()
                self.assertFalse((self.base / "new").exists())

    def test_soft_commands_keep_all_existing_input_guards(self):
        prompt = self.fresh_review()
        baseline = copy.deepcopy(self.state)
        current = copy.deepcopy(self.current)
        for failure, message in (
            ("permission", "Steering not granted"),
            ("blocked", "blocked or unknown"),
            ("unknown", "blocked or unknown"),
            ("editor", "empty editor"),
            ("recovery", "recovery"),
            ("acted", "already sent"),
            ("worker_identity", "identity changed"),
            ("supervisor_identity", "identity changed"),
            ("socket", "socket changed"),
            ("ownership", "ownership changed"),
            ("cwd", "left assigned repository"),
            ("foreground_cwd", "left assigned repository"),
            ("review_id", "Stale review ID"),
        ):
            with self.subTest(failure=failure):
                self.state = copy.deepcopy(baseline)
                self.current = copy.deepcopy(current)
                Path(self.state["owner_file"]).write_text(
                    json.dumps({"run": str(self.directory)})
                )
                review_id = "1"
                if failure == "permission":
                    self.state["allow_steer"] = False
                elif failure in ("blocked", "unknown"):
                    self.current["worker"]["agent_status"] = failure
                elif failure == "editor":
                    self.state["needs_editor_check"] = True
                elif failure == "recovery":
                    self.state["recovery"] = {"phase": "correction_pending"}
                elif failure == "acted":
                    self.state["review"]["acted"] = True
                elif failure.endswith("identity"):
                    role = failure.split("_")[0]
                    self.current[role]["agent_session"] = {"value": "replacement"}
                elif failure == "socket":
                    self.state["socket_identity"] = [1, 99]
                elif failure == "ownership":
                    Path(self.state["owner_file"]).write_text(
                        json.dumps({"run": "replacement"})
                    )
                elif failure in ("cwd", "foreground_cwd"):
                    self.current["worker"][failure] = str(self.base)
                elif failure == "review_id":
                    review_id = "0"
                sheepdog.save(self.directory, self.state)
                with self.assertRaisesRegex(RuntimeError, message):
                    self.command(
                        "steer",
                        "--review",
                        review_id,
                        "--message-file",
                        prompt,
                        now=362,
                    )
        self.assertFalse(self.prompts())
        self.assertFalse(any(c[:2] == ("agent", "send-keys") for c in self.calls))

    def test_stale_review_cannot_authorize_input(self):
        self.tick(61)
        with self.assertRaisesRegex(RuntimeError, "Stale review"):
            sheepdog.review_guard(self.state, 0)


if __name__ == "__main__":
    unittest.main()

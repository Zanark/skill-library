import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import uuid


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "context-offload" / "scripts" / "prompt_inbox.py"
SPEC = importlib.util.spec_from_file_location("prompt_inbox", SCRIPT)
INBOX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INBOX)


class PromptInboxTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.base = self.root / "base with spaces"
        (self.base / ".agent-context").mkdir(parents=True)
        (self.base / ".agent-context" / "README.md").write_text("Designated disposable base.")
        self.session = str(uuid.uuid4())
        self.path = INBOX.initialize(self.base, self.session)
        self.workers = self.root / "workers"
        self.hooks = self.root / "hooks"
        INBOX.install_hooks(self.hooks, self.workers)
        self.payload = {"sessionId": self.session, "cwd": str(self.base),
                        "stopReason": "end_turn", "stop_hook_active": False,
                        "toolResult": {"resultType": "success", "textResultForLlm": "Disposable test"}}

    def put(self, text="A bounded request", **kwargs):
        message_id = kwargs.pop("message_id", str(uuid.uuid4()))
        INBOX.submit(self.path, text, message_id=message_id, **kwargs)
        return message_id

    def offer(self, event="agentStop", **payload):
        return INBOX.hook(event, {**self.payload, **payload}, self.workers)

    def row(self, message_id):
        with INBOX.transaction(self.path) as database:
            return dict(database.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone())

    def test_queue_defers_until_stop_and_receipts_require_actual_ack(self):
        message_id = self.put()
        self.assertEqual({}, self.offer("postToolUse"))
        output = self.offer()
        self.assertEqual("block", output["decision"])
        self.assertIn("A bounded request", output["reason"])
        self.assertEqual("offered", self.row(message_id)["state"])
        token = self.row(message_id)["token"]
        with self.assertRaises(INBOX.InboxError):
            INBOX.acknowledge(self.path, message_id, token, "completed")
        for state in ("consumed", "completed", "completed"):
            self.assertEqual(state, INBOX.acknowledge(self.path, message_id, token, state)["state"])
        self.assertNotIn("A bounded request", json.dumps(INBOX.snapshot(self.path)))
        self.assertNotIn(token, json.dumps(INBOX.snapshot(self.path)))

    def test_steering_fifo_one_delivery_budget_and_stop_guard(self):
        first = self.put("Ordinary oldest")
        second = self.put("Steer later", mode="steer")
        self.assertEqual({}, self.offer("postToolUse"))
        self.assertEqual({}, self.offer(stop_hook_active=True))
        self.assertEqual({}, self.offer(stop_hook_active=None))
        self.assertEqual({}, self.offer(stopReason="abort"))
        self.offer()
        token = self.row(first)["token"]
        INBOX.acknowledge(self.path, first, token, "failed")
        self.assertEqual({}, self.offer("postToolUse"))
        self.offer("userPromptSubmitted")
        output = self.offer("postToolUse")
        self.assertIn("Steer later", output["additionalContext"])
        self.assertEqual("offered", self.row(second)["state"])

    def test_wrong_session_subagents_and_unregistered_cwd_are_inert(self):
        message_id = self.put(mode="steer")
        for payload in (
            {"sessionId": str(uuid.uuid4())}, {"sessionId": "../escape"},
            {"agentId": "child"}, {"agent_id": "child"}, {"parentAgentId": "parent"},
            {"cwd": str(self.root)}, {"sessionId": None},
        ):
            self.assertEqual({}, self.offer("postToolUse", **payload))
        self.assertEqual("pending", self.row(message_id)["state"])
        output = INBOX.hook("agentStop", {
            "session_id": self.session, "cwd": str(self.base), "stop_reason": "end_turn",
            "stop_hook_active": False,
        }, self.workers)
        self.assertEqual("block", output["decision"])

    def test_concurrent_producers_and_consumers_claim_only_one(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            ids = list(executor.map(lambda index: self.put(f"Request {index}"), range(12)))
            outputs = list(executor.map(lambda _: self.offer(), range(8)))
        self.assertEqual(1, sum(bool(output) for output in outputs))
        self.assertEqual(12, len(set(ids)))
        self.assertEqual(1, sum(self.row(message_id)["state"] == "offered" for message_id in ids))

    def test_idempotent_submit_and_immutable_body_validation(self):
        message_id = self.put("Original")
        content = (self.path / "messages" / f"{message_id}.json").read_bytes()
        self.assertTrue(INBOX.submit(self.path, "Original", message_id=message_id)["duplicate"])
        self.assertEqual(content, (self.path / "messages" / f"{message_id}.json").read_bytes())
        with self.assertRaises(INBOX.InboxError):
            self.put("Different", message_id=message_id)
        (self.path / "messages" / f"{message_id}.json").write_text('{"text":"Tampered"}')
        with self.assertRaisesRegex(INBOX.InboxError, "hash mismatch"):
            self.offer()
        self.assertEqual("pending", self.row(message_id)["state"])

    def test_ttl_retry_preserves_original_expiry(self):
        message_id = self.put("Expiry stays fixed", ttl_seconds=60)
        original = self.row(message_id)["expires"]
        result = INBOX.submit(self.path, "Expiry stays fixed", message_id=message_id, ttl_seconds=60)
        self.assertTrue(result["duplicate"])
        self.assertEqual(original, self.row(message_id)["expires"])
        with self.assertRaises(INBOX.InboxError):
            self.put("Expiry stays fixed", message_id=message_id, ttl_seconds=120)

    def test_failed_or_unknown_tool_results_never_claim_steering_requests(self):
        message_id = self.put(mode="steer")
        for result in ({}, {"resultType": "failure"}, {"resultType": "denied"}):
            self.assertEqual({}, self.offer("postToolUse", toolResult=result))
        self.assertEqual("pending", self.row(message_id)["state"])

    def test_crash_window_deposit_can_be_reconciled_only_by_matching_resubmission(self):
        message_id = self.put("Retained deposit")
        with INBOX.transaction(self.path) as database:
            database.execute("DELETE FROM messages WHERE id=?", (message_id,))
        self.assertEqual([message_id], INBOX.snapshot(self.path)["unindexedDeposits"])
        self.assertEqual({}, self.offer())
        with self.assertRaises(INBOX.InboxError):
            self.put("Other body", message_id=message_id)
        self.put("Retained deposit", message_id=message_id)
        self.assertEqual([], INBOX.snapshot(self.path)["unindexedDeposits"])
        self.assertEqual("block", self.offer()["decision"])

    def test_uncertain_never_auto_replays_and_requires_explicit_recovery(self):
        first = self.put("Do not replay automatically")
        self.put("Next task")
        self.offer()
        token = self.row(first)["token"]
        with INBOX.transaction(self.path) as database:
            database.execute("UPDATE messages SET touched=? WHERE id=?",
                             (time.time() - INBOX.LEASE_SECONDS - 1, first))
        self.assertEqual({}, self.offer())
        self.assertEqual("uncertain", self.row(first)["state"])
        with self.assertRaises(INBOX.InboxError):
            INBOX.acknowledge(self.path, first, token, "consumed")
        INBOX.control_message(self.path, first, "requeue")
        self.offer("userPromptSubmitted")
        self.offer()
        self.assertNotEqual(token, self.row(first)["token"])
        with self.assertRaises(INBOX.InboxError):
            INBOX.acknowledge(self.path, first, token, "consumed")
        self.assertEqual(2, self.row(first)["attempts"])

    def test_consumed_lease_renewal_and_cancellation_dont_fake_completion(self):
        first = self.put()
        self.offer()
        token = self.row(first)["token"]
        now = time.time()
        INBOX.acknowledge(self.path, first, token, "consumed", now=now)
        INBOX.acknowledge(self.path, first, token, "consumed", now=now + 10)
        self.assertEqual(now + 10, self.row(first)["touched"])
        with self.assertRaises(INBOX.InboxError):
            INBOX.control_message(self.path, first, "cancel")
        second = self.put()
        INBOX.control_message(self.path, second, "cancel")
        self.assertEqual("cancelled", self.row(second)["state"])
        self.assertEqual("consumed", self.row(first)["state"])

    def test_expiry_backpressure_and_invalid_inputs(self):
        now = time.time()
        expired = self.put(expires=now + 100, now=now)
        with mock.patch.object(INBOX.time, "time", return_value=now + 101):
            self.assertEqual({}, self.offer())
        self.assertEqual("expired", self.row(expired)["state"])
        for text in ("", " ", "x" * 4097, "bad\x00control"):
            with self.assertRaises(INBOX.InboxError):
                self.put(text)
        with self.assertRaises(INBOX.InboxError):
            self.put(expires=float("inf"))
        with INBOX.transaction(self.path) as database:
            for index in range(INBOX.MAX_PENDING):
                database.execute(
                    "INSERT INTO messages(id,digest,mode,created,state,touched) VALUES (?,?,'queue',0,'pending',0)",
                    (str(uuid.uuid4()), "unused"),
                )
        with self.assertRaisesRegex(INBOX.InboxError, "backlog"):
            self.put()

    def test_disabled_registration_preserves_requests(self):
        message_id = self.put()
        config = INBOX.registration(self.path)
        config["enabled"] = False
        INBOX.atomic_write(self.path / "mailbox.json", INBOX.encode(config))
        self.assertEqual({}, self.offer())
        with self.assertRaisesRegex(INBOX.InboxError, "disabled"):
            self.put()
        self.assertEqual("pending", self.row(message_id)["state"])

    def test_busy_database_surfaces_failure_without_claiming(self):
        message_id = self.put()
        with INBOX.transaction(self.path):
            with self.assertRaises(sqlite3.OperationalError):
                self.offer()
        self.assertEqual("pending", self.row(message_id)["state"])

    def test_cli_stdin_metadata_and_failure_do_not_echo_body(self):
        common = ["--base", str(self.base), "--session", self.session]
        submitted = subprocess.run(
            [sys.executable, str(SCRIPT), "submit", *common], input="Private test body",
            encoding="utf-8", capture_output=True, timeout=5, check=True,
        )
        self.assertNotIn("Private test body", submitted.stdout)
        bad = subprocess.run(
            [sys.executable, str(SCRIPT), "submit", *common, "--text", "Private test body\x01"],
            encoding="utf-8", capture_output=True, timeout=5,
        )
        self.assertNotEqual(0, bad.returncode)
        self.assertNotIn("Private test body", bad.stderr)
        status = subprocess.run(
            [sys.executable, str(SCRIPT), "status", *common],
            encoding="utf-8", capture_output=True, timeout=5, check=True,
        )
        self.assertNotIn("Private test body", status.stdout)
        self.assertEqual(1, json.loads(status.stdout)["counts"]["pending"])

    def test_installed_hook_argv_transports_unicode_json_and_real_cli_ack(self):
        body = "A Unicode request: caf\u00e9 \U0001f600"
        message_id = self.put(body, mode="steer")
        installed = json.loads((self.hooks / "prompt-inbox.json").read_text())
        entry = installed["hooks"]["postToolUse"][0]
        result = subprocess.run(
            [entry["exec"], *entry["args"]], input=json.dumps(self.payload),
            encoding="utf-8", capture_output=True, check=True, timeout=5,
            env={**os.environ, "PYTHONIOENCODING": "ascii"},
        )
        self.assertIn(body, json.loads(result.stdout)["additionalContext"])
        self.assertEqual("", result.stderr)
        token = self.row(message_id)["token"]
        common = ["--base", str(self.base), "--session", self.session, "--id", message_id, "--token", token]
        for state in ("consumed", "completed"):
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "ack", *common, "--state", state],
                encoding="utf-8", capture_output=True, check=True, timeout=5,
            )
            self.assertEqual(state, json.loads(result.stdout)["state"])

    def test_hook_install_is_narrow_idempotent_and_preserves_other_hooks(self):
        existing = self.hooks / "other.json"
        existing.write_text("unchanged")
        before = (self.hooks / "prompt-inbox.json").read_bytes()
        INBOX.install_hooks(self.hooks, self.workers)
        self.assertEqual(before, (self.hooks / "prompt-inbox.json").read_bytes())
        self.assertEqual("unchanged", existing.read_text())
        (self.hooks / "prompt-inbox.json").write_text("{}")
        with self.assertRaises(INBOX.InboxError):
            INBOX.install_hooks(self.hooks, self.workers)

    def test_two_worker_slots_skip_and_kernel_releases_after_process_death(self):
        code = (
            "import importlib.util,sys,time; from pathlib import Path; "
            "s=importlib.util.spec_from_file_location('i',sys.argv[1]); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "c=m.worker_slot(Path(sys.argv[2])); "
            "ok=c.__enter__(); print(ok,flush=True); time.sleep(30); c.__exit__(None,None,None)"
        )
        processes = []
        try:
            for _ in range(2):
                child = subprocess.Popen(
                    [sys.executable, "-c", code, str(SCRIPT), str(self.workers)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )
                processes.append(child)
                self.assertEqual("True", child.stdout.readline().strip())
            with INBOX.worker_slot(self.workers) as acquired:
                self.assertFalse(acquired)
            self.put()
            self.assertEqual({}, self.offer())
            processes[0].kill()
            processes[0].communicate(timeout=5)
            self.assertEqual("block", self.offer()["decision"])
        finally:
            for child in processes:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()

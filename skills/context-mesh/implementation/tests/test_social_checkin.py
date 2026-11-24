import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.social_checkin import active_snapshot, briefing


SESSION = "00000000-0000-4000-8000-000000000001"
NOW = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)


class SocialCheckinTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.nested = self.base / "nested"
        self.nested.mkdir()
        self.social = {
            "personas": [
                {"personaId": "own", "displayName": "Own", "basePath": str(self.base), "sessionId": SESSION,
                 "messages": [{"text": "PRIVATE HISTORICAL BODY"}], "source": "not for export",
                 "socialStanding": {"reputationEvidence": []}},
                {"personaId": "guest", "displayName": "Guest", "basePath": str(self.base), "sessionId": SESSION},
                {"personaId": "peer", "displayName": "Peer", "basePath": str(self.nested),
                 "sessionId": "00000000-0000-4000-8000-000000000002",
                 "socialStanding": {"reputationEvidence": []}},
            ],
            "messages": [], "threads": [], "attention": [],
            "archive": {"messages": [{"text": "ARCHIVE BODY"}]},
        }
        self.index = {
            "generatedAt": NOW.isoformat(),
            "contexts": [{"id": "base", "basePath": str(self.base)},
                         {"id": "nested", "basePath": str(self.nested)}],
            "social": self.social,
            "artifactProvenance": {"text": "TRANSCRIPT BODY"},
        }

    def message(self, key, owner="peer", reply=None, stamp="2026-11-23T10:00:00+00:00", thread=None):
        value = {"id": key, "personaId": owner, "text": key, "timestamp": stamp, "replyTo": reply,
                 "threadId": thread, "isUser": False}
        self.social["messages"].append(value)
        return value

    def read(self):
        return briefing(active_snapshot(self.index), self.base, SESSION, NOW)

    def test_snapshot_excludes_archives_transcripts_source_and_persona_history(self):
        rendered = json.dumps(active_snapshot(self.index))
        for value in ("PRIVATE HISTORICAL BODY", "ARCHIVE BODY", "TRANSCRIPT BODY", "not for export"):
            self.assertNotIn(value, rendered)
        self.assertIn("PRIVATE HISTORICAL BODY", json.dumps(self.index))

    def test_exact_session_longest_base_and_no_ownership_by_display_name(self):
        self.assertEqual(["own", "guest"], [p["personaId"] for p in self.read()["profiles"]])
        with self.assertRaisesRegex(ValueError, "exact base/session"):
            briefing(active_snapshot(self.index), self.nested, SESSION, NOW)
        with self.assertRaises(ValueError):
            briefing(active_snapshot(self.index), self.base, "invalid", NOW)
        with self.assertRaisesRegex(ValueError, "No designated"):
            briefing(active_snapshot(self.index), self.base.parent, SESSION, NOW)

    def test_old_broadcast_is_not_expired_and_full_thread_and_quote_are_returned(self):
        self.message("old-root", stamp="2026-09-01T10:00:00+00:00", thread="thread")
        self.message("old-answer", "own", "old-root", stamp="2026-09-02T10:00:00+00:00", thread="thread")
        self.social["threads"] = [{"id": "thread", "questionMessageId": "old-root", "status": "open"}]
        self.social["attention"] = [{"messageId": "old-root", "personaId": "own", "reason": "broadcast"}]
        result = self.read()
        self.assertEqual({"old-root", "old-answer"}, {m["id"] for m in result["messages"]})
        self.assertEqual(self.social["threads"], result["threads"])
        self.social["attention"].append({"messageId": "missing", "personaId": "own"})
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.read()

    def test_credit_review_is_not_a_vote_and_excludes_same_session_and_already_voted(self):
        self.message("help")
        self.message("thanks", "own", "help")
        self.message("same-session-help", "guest")
        self.message("same-session-thanks", "own", "same-session-help")
        before = copy.deepcopy(self.index)
        result = self.read()
        self.assertEqual(["help"], [c["targetMessageId"] for c in result["peerCreditReview"]])
        self.assertEqual(before, self.index)
        self.social["personas"][2]["socialStanding"]["reputationEvidence"] = [
            {"personaId": "own", "targetMessageId": "help"}
        ]
        self.assertEqual([], self.read()["peerCreditReview"])

    def test_empty_attention_and_unchanged_room_do_not_skip_local_hook_review(self):
        result = self.read()
        self.assertTrue(result["participationReviewRequired"])
        self.assertTrue(result["localConversationHookReviewRequired"])
        self.assertTrue(result["threadKnowledgeReviewRequired"])
        self.assertEqual([], result["attention"])
        self.assertEqual(result["scopeDigest"], self.read()["scopeDigest"])

    def test_recent_window_includes_question_roots_and_ist_today_not_utc_today(self):
        self.message("question", stamp="2026-10-01T10:00:00+00:00", thread="thread")
        self.message("answer", stamp="2026-10-01T11:00:00+00:00", thread="thread")
        self.social["threads"] = [{"id": "thread", "questionMessageId": "question", "status": "open"}]
        result = self.read()
        self.assertEqual({"question"}, {m["id"] for m in result["messages"]})
        self.assertEqual([], result["completeThreadIds"])
        full = briefing(active_snapshot(self.index), self.base, SESSION, NOW, ("thread",))
        self.assertEqual({"question", "answer"}, {m["id"] for m in full["messages"]})
        self.assertEqual(["thread"], full["completeThreadIds"])
        with self.assertRaisesRegex(ValueError, "not in the active room"):
            briefing(active_snapshot(self.index), self.base, SESSION, NOW, ("archived-thread",))
        self.social["threads"] = []
        self.social["messages"] = []
        self.message("today-root", stamp="2026-01-01T10:00:00+00:00", thread="today")
        self.message("old-root", stamp="2026-01-02T10:00:00+00:00", thread="old")
        for number in range(25):
            self.message(f"general-{number:02}", stamp="2026-10-01T10:00:00+00:00")
        self.message("ist-today", stamp="2026-11-22T20:00:00+00:00", thread="today")
        self.message("yesterday", stamp="2026-11-22T18:00:00+00:00", thread="old")
        self.social["threads"] = [
            {"id": "today", "questionMessageId": "today-root", "status": "open"},
            {"id": "old", "questionMessageId": "old-root", "status": "open"},
        ]
        selected = {m["id"] for m in self.read()["messages"]}
        self.assertIn("ist-today", selected)
        self.assertIn("today-root", selected)
        self.assertNotIn("yesterday", selected)

    def test_peer_answer_to_own_question_is_reviewed_but_operator_reply_is_not(self):
        self.message("question", "own")
        self.message("answer", reply="question")
        operator = self.message("operator", reply="question")
        operator["isUser"] = True
        result = self.read()
        self.assertEqual(["answer"], [item["targetMessageId"] for item in result["peerCreditReview"]])
        self.assertEqual("question", result["peerCreditReview"][0]["evidenceMessageId"])
        self.assertTrue(result["activity"][0]["budgetStale"])

    def test_digest_detects_edits_reactions_media_profiles_and_thread_state(self):
        self.message("root", thread="thread")
        self.social["threads"] = [{"id": "thread", "questionMessageId": "root", "status": "open"}]
        original = self.read()["scopeDigest"]
        for key, value in (("text", "edited"), ("reactions", [{"emoji": "+1", "personaId": "own"}]),
                           ("attachments", [{"url": "https://example.com/image.gif"}])):
            message = self.social["messages"][0]
            old = copy.deepcopy(message)
            message[key] = value
            self.assertNotEqual(original, self.read()["scopeDigest"])
            message.clear()
            message.update(old)
        self.social["threads"][0]["status"] = "closed"
        self.assertNotEqual(original, self.read()["scopeDigest"])
        self.social["threads"][0]["status"] = "open"
        self.social["personas"][0]["persona"] = "changed voice"
        self.assertNotEqual(original, self.read()["scopeDigest"])

    def test_catalogue_discovers_old_topics_without_expanding_threads_and_counts_actual_comments(self):
        root = self.message("old-root", "own", stamp="2026-09-01T10:00:00+00:00", thread="old")
        root["questionTitle"] = "How should saved settings behave?"
        self.message("old-answer", "guest", "old-root", stamp="2026-09-02T10:00:00+00:00", thread="old")
        self.social["threads"] = [{"id": "old", "questionMessageId": "old-root", "status": "open"}]
        self.message("closed-root", stamp="2026-09-01T10:00:00+00:00", thread="closed")
        self.social["threads"].append({"id": "closed", "questionMessageId": "closed-root", "status": "closed"})
        for number in range(25):
            self.message(f"general-{number:02}", stamp="2026-10-01T10:00:00+00:00")
        before = copy.deepcopy(self.index)
        result = self.read()
        catalogue = {item["threadId"]: item for item in result["threadCatalogue"]}
        self.assertEqual({"old", "closed"}, catalogue.keys())
        self.assertEqual("How should saved settings behave?", catalogue["old"]["title"])
        self.assertEqual(1, catalogue["old"]["commentCount"])
        self.assertEqual(1, catalogue["old"]["ownCommentCount"])
        self.assertEqual("closed", catalogue["closed"]["status"])
        self.assertFalse({"old-root", "old-answer", "closed-root"} & {m["id"] for m in result["messages"]})
        self.assertEqual([], result["completeThreadIds"])
        self.assertEqual(before, self.index)
        self.social["messages"][1]["text"] = "Corrected older finding, not a new message"
        changed = self.read()
        self.assertNotEqual(result["scopeDigest"], changed["scopeDigest"])
        self.assertNotEqual(catalogue["old"]["contentDigest"], changed["threadCatalogue"][0]["contentDigest"])

    def test_thread_catalogue_fails_visibly_for_unavailable_root_or_unknown_status(self):
        self.social["threads"] = [{"id": "old", "questionMessageId": "missing", "status": "open"}]
        with self.assertRaisesRegex(ValueError, "unavailable root"):
            self.read()
        self.message("missing", thread="old")
        self.social["threads"][0]["status"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unsupported status"):
            self.read()

    def test_cli_delta_is_compact_does_not_write_and_errors_are_nonzero(self):
        path = self.base / "snapshot.json"
        path.write_text(json.dumps(active_snapshot(self.index)), encoding="utf-8")
        script = Path(__file__).resolve().parents[1] / "scripts" / "social_checkin.py"
        argv = [sys.executable, str(script), "--snapshot", str(path), "--cwd", str(self.base), "--session", SESSION]
        first = subprocess.run(argv, capture_output=True, check=True)
        result = json.loads(first.stdout)
        second = subprocess.run(argv + ["--previous", result["scopeDigest"]], capture_output=True, check=True)
        delta = json.loads(second.stdout)
        self.assertTrue(delta["unchanged"])
        self.assertNotIn("profiles", delta)
        self.assertNotIn("messages", delta)
        self.assertTrue(delta["localConversationHookReviewRequired"])
        self.assertTrue(delta["threadKnowledgeReviewRequired"])
        self.assertNotIn("threadCatalogue", delta)
        self.assertEqual(["nested", "snapshot.json"], sorted(p.name for p in self.base.iterdir()))
        path.write_text("{bad", encoding="utf-8")
        failed = subprocess.run(argv, capture_output=True)
        self.assertEqual(2, failed.returncode)
        self.assertIn(b"failed", failed.stderr)


if __name__ == "__main__":
    unittest.main()

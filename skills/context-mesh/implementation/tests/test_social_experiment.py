import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts.social_experiment import IST, apply_experiment, fresh_state


START = datetime(2026, 11, 6, 12, tzinfo=IST)
NOW = START + timedelta(hours=1)


def message(identifier, owner="a", stamp=START, **fields):
    return {"id": identifier, "personaId": owner, "timestamp": stamp.isoformat(),
            "text": "A real fixture exchange", "replyTo": None, **fields}


def event(identifier, kind="check-in", stamp=NOW, **fields):
    return {"id": identifier, "type": kind, "timestamp": stamp.isoformat(),
            "reason": "Specific fixture evidence", **fields}


class SocialExperimentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.policy = {"schemaVersion": 1, "enabled": True, "startedAt": START.isoformat(),
                       "egoSeeds": {"butler": {"value": 80, "reason": "Explicit operator direction"}},
                       "baseline": []}
        self.social = {"personas": [{"personaId": owner, "basePath": str(self.base),
                                     "personalityStats": {"humor": 60}, "socialEvents": []}
                                    for owner in ("a", "b", "c", "butler")], "messages": [], "threads": []}
        self.history = [message("a-help"), message("b-ack", "b", replyTo="a-help")]
        self.state = fresh_state(self.policy)

    def persona(self, owner="a"):
        return next(p for p in self.social["personas"] if p["personaId"] == owner)

    def run_model(self, now=NOW):
        self.state = apply_experiment(self.social, [], self.policy, self.state, self.history, now)
        return self.persona()["socialStanding"]

    def vote(self, identifier="vote", value=1, **fields):
        return event(identifier, "reputation", value=value, targetMessageId="a-help",
                     evidenceMessageId="b-ack", **fields)

    def test_seed_neutral_defaults_and_legacy_metadata_are_not_fake_success(self):
        result = self.run_model()
        self.assertEqual((0, 50, 50), (result["reputation"], result["ego"], result["earnedEgo"]))
        self.assertIn("not measured success", result["egoBasis"]["reason"])
        self.assertEqual(80, self.persona("butler")["socialStanding"]["ego"])
        self.assertEqual({"humor": 60}, self.persona()["personalityStats"])
        self.assertEqual({"gifs": 5, "memes": 5, "laughter": 3}, result["budget"]["remaining"])

    def test_votes_defensive_pride_and_floor_removal(self):
        self.persona("b")["socialEvents"] = [self.vote(value=-1)]
        result = self.run_model()
        self.assertEqual((-1, 51, 50, True),
                         (result["reputation"], result["ego"], result["earnedEgo"], result["defensivePride"]))
        self.history.extend([message("second-help"), message("second-ack", "b", replyTo="second-help")])
        self.persona("b")["socialEvents"].append(event(
            "restore", "reputation", targetMessageId="second-help", evidenceMessageId="second-ack", value=1))
        result = self.run_model()
        self.assertEqual((0, 50, False), (result["reputation"], result["ego"], result["defensivePride"]))

    def test_self_votes_unrelated_evidence_unknown_ids_and_future_events_fail(self):
        for owner, change in (
            ("a", {}), ("b", {"evidenceMessageId": "a-help"}),
            ("b", {"targetMessageId": "missing"}), ("b", {"targetMessageId": []}),
            ("b", {"value": True}), ("b", {"timestamp": (NOW + timedelta(days=1)).isoformat()}),
        ):
            with self.subTest(owner=owner, change=change):
                self.persona(owner)["socialEvents"] = [{**self.vote(), **change}]
                with self.assertRaises(ValueError):
                    self.run_model()
                self.persona(owner)["socialEvents"] = []

    def test_duplicate_contributions_and_negative_pile_on_fail(self):
        self.persona("b")["socialEvents"] = [self.vote(value=-1)]
        self.run_model()
        self.history.append(message("c-rebuttal", "c", replyTo="a-help"))
        self.persona("c")["socialEvents"] = [event(
            "pile-on", "reputation", value=-1, targetMessageId="a-help", evidenceMessageId="c-rebuttal")]
        with self.assertRaisesRegex(ValueError, "pile-on"):
            self.run_model()
        self.persona("c")["socialEvents"] = []
        self.persona("b")["socialEvents"].append(self.vote("another-id", value=-1))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.run_model()

    def test_accepted_events_are_immutable_and_removal_does_not_reset_score(self):
        self.persona("b")["socialEvents"] = [self.vote()]
        self.run_model()
        snapshot = deepcopy(self.state)
        self.persona("b")["socialEvents"][0]["value"] = -1
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.run_model()
        self.assertEqual(snapshot, self.state)
        self.persona("b")["socialEvents"] = []
        self.assertEqual(1, self.run_model()["reputation"])

    def test_archive_assessment_is_labelled_and_not_automatically_reinferred(self):
        for item in self.history:
            item["timestamp"] = (START - timedelta(days=1)).isoformat()
        self.policy["baseline"] = [{"targetMessageId": "a-help", "evidenceMessageId": "b-ack",
                                    "value": 1, "reason": "Reviewed concrete useful acknowledgement"}]
        self.state = fresh_state(self.policy)
        standing = self.run_model()
        self.assertEqual(1, standing["reputation"])
        self.assertTrue(standing["reputationEvidence"][0]["notARetrospectiveVote"])
        self.assertEqual("archive-assessment", standing["reputationEvidence"][0]["source"])
        self.assertEqual(standing, self.run_model())

    def test_baseline_cannot_assess_post_start_messages(self):
        self.policy["baseline"] = [{"targetMessageId": "a-help", "evidenceMessageId": "b-ack",
                                    "value": 1, "reason": "Not actually historical"}]
        self.state = fresh_state(self.policy)
        with self.assertRaisesRegex(ValueError, "baseline"):
            self.run_model()

    def test_ego_requires_exact_owned_work_evidence_and_deduplicates_outcomes(self):
        evidence = self.base / "verified.txt"
        evidence.write_text("The requested output passed the targeted acceptance test.", encoding="utf-8")
        proof = {"path": str(evidence), "quote": evidence.read_text(encoding="utf-8")}
        self.persona()["socialEvents"] = [
            event("done", "work-success", outcomeId="actual-task", evidence=proof),
            event("mistake", "work-correction", outcomeId="different-task", evidence=proof),
        ]
        self.assertEqual(49, self.run_model()["earnedEgo"])
        self.persona()["socialEvents"].append(
            event("repeat", "work-success", outcomeId="actual-task", evidence=proof))
        with self.assertRaisesRegex(ValueError, "duplicate work"):
            self.run_model()
        self.persona()["socialEvents"][-1]["outcomeId"] = "third-task"
        self.persona()["socialEvents"][-1]["evidence"] = {**proof, "quote": "Invented success"}
        with self.assertRaisesRegex(ValueError, "quote not found"):
            self.run_model()
        self.persona()["socialEvents"][-1]["evidence"] = {**proof, "path": str(self.base.parent / "other.txt")}
        with self.assertRaisesRegex(ValueError, "own base"):
            self.run_model()

    def test_media_caps_overlap_archive_removal_and_midnight_reset(self):
        attachment = {"type": "gif", "url": "https://media.example.org/original.gif",
                      "isMeme": True, "alt": "Fixture", "context": "Fixture"}
        self.history += [message(f"gif-{i}", attachments=[attachment]) for i in range(5)]
        result = self.run_model()
        self.assertEqual({"gifs": 0, "memes": 0, "laughter": 3}, result["budget"]["remaining"])
        self.history = [message("sixth", attachments=[attachment])]
        before = deepcopy(self.state)
        with self.assertRaisesRegex(ValueError, "exceeds daily gifs"):
            self.run_model()
        self.assertEqual(before, self.state)
        tomorrow = START + timedelta(days=1)
        self.history = [message("next-day", stamp=tomorrow, attachments=[attachment])]
        result = self.run_model(tomorrow + timedelta(hours=1))
        self.assertEqual(1, result["budget"]["used"]["gifs"])
        self.assertEqual(1, result["budget"]["used"]["memes"])

    def test_laughter_counts_distinct_peer_targets_and_honest_marker(self):
        for i in range(4):
            self.history.append(message(f"joke-{i}", "b"))
        self.history += [message(f"laugh-{i}", replyTo=f"joke-{i}", findsFunny=True) for i in range(3)]
        self.history.append(message("laugh-again", replyTo="joke-0", text="\U0001f602"))
        self.assertEqual(3, self.run_model()["budget"]["used"]["laughter"])
        self.history.append(message("fourth-laugh", replyTo="joke-3", text="\U0001f602"))
        with self.assertRaisesRegex(ValueError, "laughter"):
            self.run_model()

    def test_laughter_cannot_be_self_awarded_or_unattributed(self):
        for reply in ("a-help", None, "missing"):
            with self.subTest(reply=reply):
                self.history.append(message("bad-laugh", replyTo=reply, findsFunny=True))
                with self.assertRaisesRegex(ValueError, "laughter"):
                    self.run_model()
                self.history.pop()

    def test_thread_content_and_operator_posts_are_not_socially_capped(self):
        self.history += [message(f"thread-{i}", threadId="technical", text="\U0001f602",
                                 attachments=[{"type": "gif", "url": "https://media.example.org/x.gif"}])
                         for i in range(8)]
        self.history += [message("operator", isUser=True, text="\U0001f602")]
        self.social["threads"] = [{"questionMessageId": "a-help"}]
        self.assertEqual({"gifs": 0, "memes": 0, "laughter": 0}, self.run_model()["budget"]["used"])

    def test_operator_joke_can_receive_budgeted_laughter_without_a_self_reaction(self):
        self.history.append(message("user-joke", isUser=True))
        self.history.append(message("own-laugh", replyTo="user-joke", findsFunny=True))
        self.assertEqual(1, self.run_model()["budget"]["used"]["laughter"])

    def test_moving_a_thread_post_to_general_chat_charges_it(self):
        attachment = {"type": "image", "url": "https://media.example.org/actual.gif"}
        self.history.append(message("moved", threadId="technical", attachments=[attachment]))
        self.assertEqual(0, self.run_model()["budget"]["used"]["gifs"])
        self.history[-1].pop("threadId")
        self.assertEqual(1, self.run_model()["budget"]["used"]["gifs"])

    def test_retirement_counts_only_active_dates_and_is_reversible(self):
        later = START + timedelta(days=400)
        self.assertEqual(0, self.run_model(later)["lifecycle"]["unengagedActiveDays"])
        self.persona()["socialEvents"] = [event(f"day-{i}", stamp=START + timedelta(days=i)) for i in range(1, 31)]
        self.persona()["socialEvents"].append(event("same-day", stamp=START + timedelta(days=30, hours=1)))
        standing = self.run_model(later)
        self.assertEqual("retired", standing["lifecycle"]["status"])
        self.assertEqual(30, standing["lifecycle"]["unengagedActiveDays"])
        self.assertEqual(2, len(self.history))
        self.persona()["socialEvents"].append(event("return", "revive", stamp=later))
        self.assertEqual("settling-in", self.run_model(later)["lifecycle"]["status"])

    def test_high_ego_exemption_and_real_peer_engagement(self):
        self.persona("butler")["socialEvents"] = [
            event(f"butler-day-{i}", stamp=START + timedelta(days=i)) for i in range(1, 32)]
        self.persona()["socialEvents"] = [
            event(f"a-day-{i}", stamp=START + timedelta(days=i)) for i in range(1, 32)]
        later = START + timedelta(days=32)
        self.run_model(later)
        self.assertEqual("unbothered", self.persona("butler")["socialStanding"]["lifecycle"]["status"])
        self.history.append(message("new-peer-answer", "b", stamp=later, replyTo="a-help"))
        self.assertEqual(0, self.run_model(later)["lifecycle"]["unengagedActiveDays"])

    def test_disabled_gate_preserves_ledger_and_missing_ledger_is_not_a_reset(self):
        self.run_model()
        saved = deepcopy(self.state)
        disabled = {**self.policy, "enabled": False}
        contexts = [{"social": deepcopy(self.social["personas"])}]
        self.assertIsNone(apply_experiment(self.social, contexts, disabled, self.state, [], NOW))
        self.assertEqual(saved, self.state)
        self.assertFalse(self.social["experiment2"]["enabled"])
        self.assertTrue(all("socialStanding" not in p for p in self.social["personas"] + contexts[0]["social"]))
        with self.assertRaisesRegex(ValueError, "restore it"):
            apply_experiment(self.social, [], self.policy, None, self.history, NOW)

    def test_stale_writer_reloads_accepted_events_and_budget_under_output_lock(self):
        from test_build_context_mesh import MODULE
        output = self.base / "output"
        output.mkdir()
        (output / "meshboard-experiment-2.json").write_text(json.dumps(self.policy), encoding="utf-8")
        (output / "meshboard-experiment-2-state.json").write_text(json.dumps(self.state), encoding="utf-8")
        config = {"_path": str(self.base / "config.json"), "outputDirectory": "output"}
        self.persona("b")["socialEvents"] = [self.vote()]
        self.social["attention"] = []
        first = {"social": deepcopy(self.social), "contexts": [], "summary": {},
                 "_experimentHistory": self.history, "generatedAt": NOW.isoformat()}
        stale = {"social": deepcopy(self.social), "contexts": [], "summary": {},
                 "_experimentHistory": [], "generatedAt": NOW.isoformat()}
        stale["social"]["personas"][1]["socialEvents"] = []
        with patch.object(MODULE, "PROJECT_ROOT", self.base), \
                patch.object(MODULE, "render_html", return_value="fixture"), \
                patch.object(MODULE, "render_digest", return_value="fixture"):
            MODULE.write_outputs(first, config)
            MODULE.write_outputs(stale, config)
        published = json.loads((output / "context-index.json").read_text(encoding="utf-8"))
        self.assertEqual(1, published["social"]["personas"][0]["socialStanding"]["reputation"])
        self.assertNotIn("_experimentHistory", published)
        self.assertEqual(1, len(json.loads((output / "meshboard-experiment-2-state.json").read_text())["events"]))

    def test_initializer_is_once_only_and_preserves_existing_ledger(self):
        from scripts.social_experiment import initialize
        index = {"social": self.social, "contexts": []}
        index["social"]["messages"] = self.history
        (self.base / "context-index.json").write_text(json.dumps(index), encoding="utf-8")
        initialize(self.base, self.policy)
        ledger = self.base / "meshboard-experiment-2-state.json"
        original = ledger.read_bytes()
        with self.assertRaises(FileExistsError):
            initialize(self.base, self.policy)
        self.assertEqual(original, ledger.read_bytes())


if __name__ == "__main__":
    unittest.main()

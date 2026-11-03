import copy
import unittest

from scripts.social_personality import STARTERS, TRAITS, derive_social_personality


class SocialPersonalityTests(unittest.TestCase):
    def test_authored_cast_is_distinct_without_claiming_to_be_observed(self):
        profiles = [derive_social_personality({"personaId": key}, []) for key in STARTERS]
        self.assertEqual(len(profiles), len({profile["natureSummary"] for profile in profiles}))
        for profile in profiles:
            self.assertEqual("meshboard-only", profile["meshboardPersonality"]["scope"])
            self.assertEqual("authored fictional starter", profile["meshboardPersonality"]["origin"])
            self.assertEqual(set(TRAITS), set(profile["personalityStats"]))
            self.assertNotEqual({100}, set(profile["personalityStats"].values()))
        alfred = profiles[0]["personalityStats"]
        goblin = profiles[1]["personalityStats"]
        self.assertGreater(alfred["seriousness"], goblin["seriousness"] + 40)
        self.assertGreater(goblin["humor"], alfred["humor"])

    def test_recent_conversation_changes_traits_without_saturating_every_dimension(self):
        persona = {"personaId": "new"}
        def events(kinds):
            return [{"id": str(i), "timestamp": f"{i:04}", "kind": kind} for i, kind in enumerate(kinds)]
        earlier = derive_social_personality(persona, events(["shitpost"] * 10 + ["chat"] * 10))
        recent = derive_social_personality(persona, events(["chat"] * 10 + ["shitpost"] * 10))
        self.assertGreater(recent["personalityStats"]["humor"], earlier["personalityStats"]["humor"])
        self.assertLess(recent["personalityStats"]["seriousness"], earlier["personalityStats"]["seriousness"])
        self.assertGreater(recent["meshboardPersonality"]["evolution"]["conversationWeight"], 0.7)
        self.assertEqual(50, recent["personalityStats"]["helpfulness"])

    def test_work_and_operator_posts_do_not_train_the_social_character(self):
        persona = {"personaId": "new", "persona": "risk help curious " * 5000,
                   "personalityStats": dict.fromkeys(TRAITS, 100)}
        messages = [{"id": str(i), "kind": "work", "text": "research must work retry " * 100} for i in range(50)]
        messages += [{"id": "operator", "isUser": True, "kind": "shitpost"},
                     {"id": "reference", "threadId": "technical", "kind": "reply"}]
        result = derive_social_personality(persona, messages)
        self.assertEqual(dict.fromkeys(TRAITS, 50), result["personalityStats"])
        self.assertEqual(0, result["meshboardPersonality"]["evolution"]["messageCount"])

    def test_real_thread_answers_influence_helpfulness_but_reference_monologues_do_not(self):
        question = {"id": "question", "personaId": "b", "kind": "help", "threadId": "t"}
        answer = {"id": "answer", "kind": "reply", "replyTo": "question", "threadId": "t"}
        result = derive_social_personality({"personaId": "a"}, [answer], [question, {**answer, "personaId": "a"}])
        self.assertGreater(result["personalityStats"]["helpfulness"], 50)
        self.assertEqual(1, result["meshboardPersonality"]["evolution"]["messageCount"])

    def test_reflection_requires_real_relevant_evidence_and_updates_nature(self):
        messages = [{"id": "mine", "kind": "chat", "personaId": "a"}]
        conversation = messages + [{"id": "peer", "personaId": "b", "replyTo": "mine", "kind": "reply"}]
        persona = {"personaId": "a", "meshboardPersonality": {
            "temperament": "reserved · watchful",
            "reflections": [{"text": "A peer answered and I became more willing to join in.",
                             "messageIds": ["mine", "peer"], "traitAdjustments": {"personaRelationships": 12},
                             "natureSummary": "reserved · warming-up"}]}}
        original = copy.deepcopy(persona)
        result = derive_social_personality(persona, messages, conversation)
        self.assertEqual("reserved · warming-up", result["natureSummary"])
        self.assertEqual(62, result["personalityStats"]["personaRelationships"])
        self.assertEqual(1, result["meshboardPersonality"]["evolution"]["peerCount"])
        self.assertEqual(original, persona)
        self.assertEqual(result, derive_social_personality({**persona, **result}, messages, conversation))
        for evidence in (["missing"], ["unrelated"]):
            persona["meshboardPersonality"]["reflections"][0]["messageIds"] = evidence
            with self.assertRaisesRegex(ValueError, "missing or unrelated"):
                derive_social_personality(persona, messages, conversation + [{"id": "unrelated", "personaId": "b"}])

    def test_invalid_profiles_fail_explicitly_and_work_scope_is_rejected(self):
        for value in (None, [], {"scope": "work"}, {"startingTraits": {"humor": True}},
                      {"startingTraits": {"humor": float("nan")}},
                      {"startingTraits": {"humor": 101}}, {"humorStyle": ""},
                      {"origin": {}}, {"workInstructions": "change work behavior"},
                      {"reflections": [{"text": "Invented", "messageIds": []}]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                derive_social_personality({"personaId": "a", "meshboardPersonality": value}, [])


if __name__ == "__main__":
    unittest.main()

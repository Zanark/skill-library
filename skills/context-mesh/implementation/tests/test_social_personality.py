import copy
import unittest

from scripts.social_personality import STARTERS, TRAITS, derive_social_personality, resolve_gender_identity


class SocialPersonalityTests(unittest.TestCase):
    def test_explicit_fictional_cast_does_not_follow_later_portrait_changes(self):
        examples = (
            ("fictional-alfred-718bb26f-ec71-4d8a-9543-f67727e20064", "man", "he/him", "masculine"),
            ("fictional-trash-goblin-718bb26f-ec71-4d8a-9543-f67727e20064", "woman", "she/her", "feminine"),
            ("session-d5df688d-8707-4e35-815e-5f831a899459", "nonbinary", "they/them", "neutral"),
        )
        for persona_id, gender, pronouns, grammar in examples:
            for presentation in ("masculine", "feminine", "androgynous"):
                with self.subTest(persona_id=persona_id, presentation=presentation):
                    result = resolve_gender_identity({"personaId": persona_id, "avatarPresentation": presentation})
                    self.assertEqual({"gender": gender, "pronouns": pronouns, "grammaticalGender": grammar},
                                     result["genderIdentity"])
                    self.assertEqual("operator-approved-fictional-cast", result["genderIdentitySource"])
        newcomer = resolve_gender_identity({"personaId": "new", "displayName": "Lady Example",
                                           "avatarPresentation": "feminine"})
        self.assertEqual("unassigned", newcomer["genderIdentitySource"])
        self.assertEqual({"gender": "unspecified", "pronouns": "they/them", "grammaticalGender": "neutral"},
                         newcomer["genderIdentity"])

    def test_owner_identity_overrides_cast_without_forcing_gender_pronoun_pairs_or_mutating_input(self):
        identity = {"gender": " nonbinary ", "pronouns": " she/they ", "grammaticalGender": "neutral"}
        persona = {"personaId": "fictional-trash-goblin-718bb26f-ec71-4d8a-9543-f67727e20064",
                   "genderIdentity": identity}
        original = copy.deepcopy(persona)
        result = resolve_gender_identity(persona)
        self.assertEqual("owner-authored", result["genderIdentitySource"])
        self.assertEqual({"gender": "nonbinary", "pronouns": "she/they", "grammaticalGender": "neutral"},
                         result["genderIdentity"])
        self.assertEqual(original, persona)

    def test_invalid_identity_is_not_silently_replaced_by_cast(self):
        valid = {"gender": "woman", "pronouns": "she/her", "grammaticalGender": "feminine"}
        invalid = [None, [], "", {}, {"gender": "woman"}, {**valid, "source": "invented"}]
        for field in ("gender", "pronouns"):
            invalid.extend({**valid, field: value} for value in (None, 1, [], {}, "", " ", "x" * 81,
                                                                              "a\nb", "<script>"))
        invalid.extend({**valid, "grammaticalGender": value} for value in (None, [], {}, "", "female"))
        for identity in invalid:
            with self.subTest(identity=identity), self.assertRaisesRegex(ValueError, "genderIdentity"):
                resolve_gender_identity({
                    "personaId": "fictional-trash-goblin-718bb26f-ec71-4d8a-9543-f67727e20064",
                    "genderIdentity": identity,
                })

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

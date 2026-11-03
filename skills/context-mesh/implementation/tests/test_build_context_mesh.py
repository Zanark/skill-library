import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_context_mesh.py"
ARTIFACT_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "artifact_provenance.py"
SPEC = importlib.util.spec_from_file_location("build_context_mesh", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
ARTIFACT_SPEC = importlib.util.spec_from_file_location("artifact_provenance_tests", ARTIFACT_SCRIPT)
ARTIFACT = importlib.util.module_from_spec(ARTIFACT_SPEC)
assert ARTIFACT_SPEC.loader
sys.modules[ARTIFACT_SPEC.name] = ARTIFACT
ARTIFACT_SPEC.loader.exec_module(ARTIFACT)


class ContextMeshTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.color_registry = Path(directory.name) / "persona-colors.sqlite3"

    def test_split_sections_and_select(self):
        text = "# State\n\n## Current focus\n- Build the mesh\n\n## Open questions\n- None"
        sections = MODULE.split_sections(text)
        self.assertEqual(["State", "Current focus", "Open questions"], [s["title"] for s in sections])
        self.assertEqual(["Build the mesh"], MODULE.select_sections(text, ("current focus",)))

    def test_journal_events_are_newest_first(self):
        text = "# Journal\n\n## 2026-08-20\n- Older\n\n## 2026-08-25 — New\n- Newer"
        events = MODULE.journal_events(text)
        self.assertEqual("2026-08-25", events[0]["date"])
        self.assertEqual("New", events[0]["title"])
        self.assertIn("Newer", events[0]["summary"])

    def test_discovery_reads_only_context_stores(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "Base" / ".agent-context"
            store.mkdir(parents=True)
            for name in MODULE.STORE_FILES:
                (store / name).write_text(f"# {name}\n", encoding="utf-8")
            stores = MODULE.discover_stores([root])
            self.assertEqual(1, len(stores))
            self.assertEqual(store, stores[0].store_path)

    def test_discovery_ignores_incomplete_store(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "Partial" / ".agent-context"
            store.mkdir(parents=True)
            (store / "STATE.md").write_text("# State\n", encoding="utf-8")
            self.assertEqual([], MODULE.discover_stores([root]))

    def test_graph_has_no_dangling_edges(self):
        contexts = [
            {
                "id": "ctx-a",
                "name": "A",
                "basePath": r"C:\contexts\A",
                "freshness": {"label": "fresh"},
                "focus": ["Focus"],
                "memory": [{"section": "Facts", "text": "A durable memory item"}],
                "_corpus": r"related context: c:\contexts\b",
            },
            {
                "id": "ctx-b",
                "name": "B",
                "basePath": r"C:\contexts\B",
                "freshness": {"label": "fresh"},
                "focus": ["Focus"],
                "memory": [],
                "_corpus": "",
            },
        ]
        graph = MODULE.build_graph(contexts, [], 0)
        node_ids = {node["id"] for node in graph["nodes"]}
        context_colors = {
            node["outlineColor"]
            for node in graph["nodes"]
            if node["type"] == "context"
        }
        self.assertTrue(all(edge["source"] in node_ids and edge["target"] in node_ids for edge in graph["edges"]))
        self.assertTrue(any(edge["type"] == "cross-reference" for edge in graph["edges"]))
        self.assertTrue(all(edge.get("reason") for edge in graph["edges"]))
        self.assertTrue(all("evidence" in edge for edge in graph["edges"]))
        self.assertEqual(2, len(context_colors))

    def test_path_prefix_does_not_create_relationship(self):
        contexts = [
            {
                "id": "ctx-runner",
                "name": "Runner",
                "basePath": r"C:\contexts\Runner",
                "freshness": {"label": "fresh"},
                "focus": [],
                "memory": [],
                "_corpus": "",
            },
            {
                "id": "ctx-runner2",
                "name": "Runner2",
                "basePath": r"C:\contexts\Runner2",
                "freshness": {"label": "fresh"},
                "focus": [],
                "memory": [],
                "_corpus": r"only c:\contexts\runner2 is referenced",
            },
        ]
        graph = MODULE.build_graph(contexts, [], 0)
        self.assertFalse(any(edge["type"] == "cross-reference" for edge in graph["edges"]))

    def test_parent_path_does_not_match_nested_context_path(self):
        self.assertFalse(
            MODULE.corpus_mentions_path(
                r"see c:\contexts\KnowledgeLedger\ServiceFabric",
                r"C:\contexts\KnowledgeLedger",
            )
        )
        self.assertTrue(
            MODULE.corpus_mentions_path(
                r"see c:\contexts\KnowledgeLedger\ for the root context",
                r"C:\contexts\KnowledgeLedger",
            )
        )

    def test_inspiration_reference_is_low_confidence_with_exact_excerpt(self):
        contexts = [
            {
                "id": "ctx-a",
                "name": "A",
                "basePath": r"C:\contexts\A",
                "freshness": {"label": "fresh"},
                "focus": [],
                "memory": [],
                "_corpus": r"use c:\contexts\b as documentation style inspiration",
                "_files": {
                    "MEMORY.md": (
                        "# Preferences\n"
                        "Use `C:\\contexts\\B` as documentation style inspiration only.\n"
                    )
                },
            },
            {
                "id": "ctx-b",
                "name": "B",
                "basePath": r"C:\contexts\B",
                "freshness": {"label": "fresh"},
                "focus": [],
                "memory": [],
                "_corpus": "",
                "_files": {},
            },
        ]
        graph = MODULE.build_graph(contexts, [], 0)
        edge = next(edge for edge in graph["edges"] if edge["type"] == "cross-reference")
        self.assertEqual("low", edge["confidence"])
        self.assertEqual("incidental-reference", edge["relationshipClass"])
        self.assertIn("MEMORY.md:1-2", edge["evidence"][0])
        self.assertIn("inspiration", edge["evidence"][0])

    def test_social_personas_are_loaded_and_secrets_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "Base" / ".agent-context"
            store.mkdir(parents=True)
            for name in MODULE.STORE_FILES:
                (store / name).write_text(f"# {name}\n", encoding="utf-8")
            social = store / "social"
            social.mkdir()
            (social / "persona.json").write_text(
                __import__("json").dumps(
                    {
                        "personaId": "p1",
                        "displayName": "Persona One",
                        "messages": [
                            {
                                "text": "token=hidden keep working",
                                "kind": "work",
                                "reactions": [
                                    {"emoji": "😂", "personaId": "p1"},
                                    {"emoji": "✅", "personaId": "p1"},
                                    {"emoji": "👏", "personaId": "p2"},
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            discovered = MODULE.discover_stores([root])
            personas = MODULE.load_social_personas(discovered[0])
            self.assertEqual("p1", personas[0]["personaId"])
            self.assertIn("[REDACTED]", personas[0]["messages"][0]["text"])
            self.assertEqual(
                [{"emoji": "✅", "personaId": "p1"}, {"emoji": "👏", "personaId": "p2"}],
                personas[0]["messages"][0]["reactions"],
            )
            self.assertTrue(all(0 <= value <= 100 for value in personas[0]["personalityStats"].values()))
            self.assertNotIn("witness", personas[0]["personalityStats"])
            self.assertTrue(personas[0]["natureSummary"])
            self.assertLessEqual(len(personas[0]["natureSummary"].split("·")), 2)

    def test_owner_authored_avatar_presentation_is_optional_validated_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store_path = root / ".agent-context"
            social = store_path / "social"
            social.mkdir(parents=True)
            for name in MODULE.STORE_FILES:
                (store_path / name).write_text(f"# {name}\n", encoding="utf-8")
            source = social / "persona.json"
            payload = {"personaId": "p1", "displayName": "One", "profileImageData": "abc"}
            store = MODULE.discover_stores([root])[0]
            source.write_text(json.dumps(payload), encoding="utf-8")
            self.assertNotIn("avatarPresentation", MODULE.load_social_personas(store)[0])
            for presentation in ("feminine", "masculine", "androgynous"):
                with self.subTest(presentation=presentation):
                    source.write_text(json.dumps({**payload, "avatarPresentation": presentation}), encoding="utf-8")
                    original = source.read_bytes()
                    loaded = MODULE.load_social_personas(store)
                    board = MODULE.build_social_board(
                        [{"id": store.context_id, "name": store.name, "social": loaded}],
                        {"edges": []}, self.color_registry,
                    )
                    self.assertEqual(presentation, board["personas"][0]["avatarPresentation"])
                    self.assertEqual("abc", board["personas"][0]["profileImageData"])
                    self.assertEqual(original, source.read_bytes())
            for invalid in ("female", "", None, 1, [], {}):
                with self.subTest(invalid=invalid):
                    source.write_text(json.dumps({**payload, "avatarPresentation": invalid}), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "avatarPresentation"):
                        MODULE.load_social_personas(store)

    def test_avatar_presentation_conflicts_between_replicas_are_reported(self):
        persona = {"personaId": "p1", "displayName": "One", "contextId": "ctx-a", "messages": [],
                   "avatarPresentation": "feminine"}
        for alternate in ("masculine", None):
            with self.subTest(alternate=alternate):
                replica = {**persona, "contextId": "ctx-b"}
                if alternate is None:
                    del replica["avatarPresentation"]
                else:
                    replica["avatarPresentation"] = alternate
                contexts = [{"id": "ctx-a", "name": "A", "social": [persona]},
                            {"id": "ctx-b", "name": "B", "social": [replica]}]
                with self.assertRaisesRegex(ValueError, "Conflicting copies of social persona p1"):
                    MODULE.build_social_board(contexts, {"edges": []}, self.color_registry)

    def test_work_store_volume_cannot_flatten_a_social_character(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            social = root / ".agent-context" / "social"
            social.mkdir(parents=True)
            source = social / "persona.json"
            original = json.dumps({
                "personaId": "fictional-trash-goblin-718bb26f-ec71-4d8a-9543-f67727e20064",
                "displayName": "Goblin", "persona": "Working role remains unchanged.", "messages": [],
            })
            source.write_text(original, encoding="utf-8")
            quiet = MODULE.Store("ctx-a", "A", root, social.parent, {"STATE.md": "Ordinary notes."})
            noisy = MODULE.Store("ctx-a", "A", root, social.parent, {
                name: "must verified help support work investigate why refresh progress " * 5000
                for name in MODULE.STORE_FILES
            })
            before = MODULE.load_social_personas(quiet)[0]
            after = MODULE.load_social_personas(noisy)[0]
            self.assertEqual(before["personalityStats"], after["personalityStats"])
            self.assertEqual(before["meshboardPersonality"], after["meshboardPersonality"])
            self.assertLess(after["personalityStats"]["seriousness"], 30)
            self.assertEqual(original, source.read_text(encoding="utf-8"))
            self.assertEqual("Working role remains unchanged.", after["persona"])

    def test_social_relationships_distinguish_siblings_friends_and_mutuals(self):
        contexts = [
            {"id": "ctx-a", "name": "A", "social": [{"personaId": "a1", "displayName": "A1", "contextId": "ctx-a", "messages": []}]},
            {"id": "ctx-b", "name": "B", "social": [{"personaId": "b1", "displayName": "B1", "contextId": "ctx-b", "messages": []}]},
            {"id": "ctx-c", "name": "C", "social": [{"personaId": "c1", "displayName": "C1", "contextId": "ctx-c", "messages": []}]},
            {"id": "ctx-d", "name": "D", "social": [{"personaId": "d1", "displayName": "D1", "contextId": "ctx-d", "messages": []}]},
        ]
        graph = {"edges": [{"source": "ctx-a", "target": "ctx-c", "type": "cross-reference", "confidence": "high"}, {"source": "ctx-b", "target": "ctx-c", "type": "cross-reference", "confidence": "high"}]}
        relationships = MODULE.build_social_board(contexts, graph, self.color_registry)["relationships"]
        by_pair = {(item["left"], item["right"]): item for item in relationships}
        self.assertEqual("mutual-friend", by_pair[("a1", "b1")]["relation"])
        self.assertEqual(["C"], by_pair[("a1", "b1")]["mutualContexts"])
        self.assertEqual("friend", by_pair[("a1", "c1")]["relation"])
        self.assertEqual("stranger", by_pair[("a1", "d1")]["relation"])

    def broadcast_board(self, messages_by_persona, threads=None):
        names = {"a": "Asker", "b": "Meshboard Builder", "c": "Guest (fictional)"}
        contexts = [{"id": "ctx-a", "name": "A", "social": [
            {"personaId": persona_id, "displayName": name, "contextId": "ctx-a", "contextName": "A",
             "messages": messages_by_persona.get(persona_id, []), "threads": (threads or []) if persona_id == "a" else []}
            for persona_id, name in names.items()
        ]}]
        return MODULE.build_social_board(contexts, {"edges": []}, self.color_registry)

    def test_converted_thread_projects_existing_reply_chain_without_source_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            social = root / ".agent-context" / "social"
            social.mkdir(parents=True)
            payload = {
                "personaId": "a", "displayName": "Asker",
                "messages": [{"id": "question", "text": "Which animal?", "threadId": "animals"}],
                "threads": [{"id": "animals", "questionMessageId": "question",
                             "replyMessageIds": ["nested", "answer"]}],
            }
            path = social / "a.json"
            original = json.dumps(payload)
            path.write_text(original, encoding="utf-8")
            store = MODULE.Store("ctx-a", "A", root, social.parent, {})
            persona = MODULE.load_social_personas(store)[0]
            peer_messages = [
                {"id": "nested", "text": "Good choice.", "replyTo": "answer", "timestamp": "2020-01-01"},
                {"id": "answer", "text": "Owl.", "replyTo": "question", "timestamp": "2020-01-02"},
                {"id": "unrelated", "text": "Another conversation."},
            ]
            peer_snapshot = json.dumps(peer_messages)
            board = self.broadcast_board({"a": persona["messages"], "b": peer_messages}, persona["threads"])
            messages = {message["id"]: message for message in board["messages"]}
            for message_id in ("question", "answer", "nested"):
                self.assertEqual("animals", messages[message_id]["threadId"])
                self.assertEqual("open", messages[message_id]["threadStatus"])
            self.assertIsNone(messages["unrelated"].get("threadId"))
            self.assertEqual(peer_snapshot, json.dumps(peer_messages))
            self.assertEqual(original, path.read_text(encoding="utf-8"))
            for invalid in ("answer", [None]):
                payload["threads"][0]["replyMessageIds"] = invalid
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "replyMessageIds"):
                    MODULE.load_social_personas(store)

    def test_converted_thread_rejects_unrelated_cyclic_and_conflicting_replies(self):
        for reply in (
            {"id": "answer", "text": "Unrelated"},
            {"id": "answer", "text": "Cycle", "replyTo": "answer"},
            {"id": "answer", "text": "Elsewhere", "replyTo": "question", "threadId": "other"},
        ):
            with self.subTest(reply=reply), self.assertRaisesRegex(ValueError, "replyMessageIds"):
                self.broadcast_board({
                    "a": [{"id": "question", "text": "Which animal?", "threadId": "animals"}],
                    "b": [reply],
                }, [{"id": "animals", "questionMessageId": "question", "ownerPersonaId": "a",
                     "status": "open", "replyMessageIds": ["answer"]}])

    def test_broadcast_requires_each_persona_and_deduplicates_direct_mentions(self):
        board = self.broadcast_board({
            "a": [{"id": "ping", "text": "@MeShBoArD, thoughts?", "mentions": ["b", "b"], "timestamp": "2020-01-01"}],
            "b": [{"id": "answer", "text": "My answer", "replyTo": "ping"}],
        })
        ping = next(message for message in board["messages"] if message["id"] == "ping")
        self.assertEqual(["b", "c"], ping["broadcastRecipients"])
        self.assertEqual(["b"], ping["broadcastResponded"])
        self.assertEqual(["c"], ping["broadcastPending"])
        self.assertEqual([{"messageId": "ping", "personaId": "c", "reason": "broadcast"}], board["attention"])

    def test_broadcast_accepts_emoji_reply_and_legacy_reaction_but_not_unrelated_posts(self):
        for reply, reactions in [
            ([{"id": "emoji", "text": "\U0001f44d", "replyTo": "ping"}], []),
            ([], [{"emoji": "\U0001f44d", "personaId": "b"}]),
        ]:
            with self.subTest(reply=reply):
                board = self.broadcast_board({
                    "a": [{"id": "ping", "text": "Everyone", "mentions": ["@MESHBOARD"], "reactions": reactions}],
                    "b": reply, "c": [{"id": "unrelated", "text": "Something else"}],
                })
                self.assertEqual(["c"], next(message for message in board["messages"] if message["id"] == "ping")["broadcastPending"])

    def test_broadcast_token_boundaries_and_full_persona_names(self):
        for text, expected in [
            ("@meshboard", True), ("Hello (@MESHBOARD)!", True),
            ("@Meshboard Builder, hello", False), ("name@meshboard.example", False),
            ("@meshboarder", False), ("@meshboard-team", False), ("@@meshboard", False),
        ]:
            with self.subTest(text=text):
                board = self.broadcast_board({"a": [{"id": "ping", "text": text}]})
                self.assertEqual(expected, board["messages"][0]["isBroadcast"])
                self.assertEqual(2 if expected else 0, len(board["attention"]))
        direct = self.broadcast_board({"a": [{"id": "direct", "text": "@Meshboard Builder, hello", "mentions": ["b"]}]})
        self.assertEqual([{"messageId": "direct", "personaId": "b"}], direct["attention"])

    def test_operator_broadcast_includes_source_persona_and_user_reply_does_not_clear_it(self):
        board = self.broadcast_board({
            "a": [{"id": "ping", "text": "@meshboard hello", "isUser": True},
                  {"id": "user-answer", "text": "Operator speaking", "isUser": True, "replyTo": "ping"}],
            "b": [{"id": "answer", "text": "Here", "replyTo": "ping"}],
        })
        ping = next(message for message in board["messages"] if message["id"] == "ping")
        self.assertEqual(["a", "b", "c"], ping["broadcastRecipients"])
        self.assertEqual(["a", "c"], ping["broadcastPending"])

    def test_closed_thread_broadcast_acknowledgement_does_not_reopen_thread(self):
        thread = {"id": "t1", "questionMessageId": "ping", "ownerPersonaId": "a", "status": "closed"}
        board = self.broadcast_board({
            "a": [{"id": "ping", "text": "@meshboard thoughts?", "threadId": "t1"}],
            "b": [{"id": "ack", "text": "I saw the room question.", "broadcastReplyTo": "ping"}],
        }, [thread])
        self.assertEqual("closed", board["threads"][0]["status"])
        self.assertEqual(["c"], next(message for message in board["messages"] if message["id"] == "ping")["broadcastPending"])
        root_without_thread_id = self.broadcast_board({
            "a": [{"id": "ping", "text": "@meshboard thoughts?"}],
            "b": [{"id": "ack", "text": "I saw the room question.", "broadcastReplyTo": "ping"}],
        }, [thread])
        self.assertEqual(["c"], next(message for message in root_without_thread_id["messages"] if message["id"] == "ping")["broadcastPending"])
        for target, extra in [
            ("missing", {}), ("ping", {"threadId": "t1"}), ("ping", {"replyTo": "ping"}),
        ]:
            with self.subTest(target=target, extra=extra), self.assertRaisesRegex(ValueError, "broadcastReplyTo"):
                self.broadcast_board({
                    "a": [{"id": "ping", "text": "@meshboard thoughts?", "threadId": "t1"}],
                    "b": [{"id": "ack", "text": "Here", "broadcastReplyTo": target, **extra}],
                }, [thread])
        with self.assertRaisesRegex(ValueError, "broadcastReplyTo"):
            self.broadcast_board({
                "a": [{"id": "ping", "text": "@meshboard hello"}],
                "b": [{"id": "ack", "text": "Here", "broadcastReplyTo": "ping"}],
            })

    def test_long_broadcast_and_acknowledgement_survive_loading_without_source_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            social = root / ".agent-context" / "social"
            social.mkdir(parents=True)
            payload = {"personaId": "a", "displayName": "Asker", "messages": [
                {"id": "long", "text": " \t\r\n" + "Long message " * 110 + "@meshboard\r\n  \t"},
                {"id": "ack", "text": "Acknowledged", "broadcastReplyTo": "earlier"},
                {"id": "blank", "text": " \t\r\n"},
            ]}
            source = social / "a.json"
            original = json.dumps(payload)
            source.write_text(original, encoding="utf-8")
            store = MODULE.Store("ctx-a", "A", root, social.parent, {})
            messages = MODULE.load_social_personas(store)[0]["messages"]
            self.assertEqual(2, len(messages))
            self.assertEqual(payload["messages"][0]["text"], messages[0]["text"])
            self.assertEqual("earlier", messages[1]["broadcastReplyTo"])
            board = self.broadcast_board({"a": [messages[0]]})
            self.assertTrue(board["messages"][0]["isBroadcast"])
            self.assertEqual(original, source.read_text(encoding="utf-8"))
            payload["messages"][1]["broadcastReplyTo"] = []
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "broadcastReplyTo must be"):
                MODULE.load_social_personas(store)

    def test_remote_attachments_preserve_media_only_messages_and_relevance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            social = root / ".agent-context" / "social"
            social.mkdir(parents=True)
            attachment = {
                "type": "gif",
                "url": "https://media.giphy.com/media/example/200.gif?cid=public",
                "alt": "A person working through a surprising calculation",
                "context": "Responds to the calculator joke in the quoted message",
                "sourceUrl": "https://giphy.com/gifs/example",
            }
            payload = {"personaId": "p1", "messages": [
                {"id": "media-only", "text": "", "replyTo": "question", "threadId": "t1",
                 "attachments": [attachment], "reactions": [{"emoji": "👍", "personaId": "p2"}]},
                {"id": "legacy", "text": "Still readable"},
            ]}
            original = json.dumps(payload)
            source = social / "p1.json"
            source.write_text(original, encoding="utf-8")
            store = MODULE.Store("ctx-a", "A", root, social.parent, {})
            messages = MODULE.load_social_personas(store)[0]["messages"]
            self.assertEqual(2, len(messages))
            self.assertEqual([attachment], messages[0]["attachments"])
            self.assertEqual("", messages[0]["text"])
            self.assertEqual("question", messages[0]["replyTo"])
            self.assertEqual("t1", messages[0]["threadId"])
            self.assertEqual([{"emoji": "👍", "personaId": "p2"}], messages[0]["reactions"])
            self.assertNotIn("attachments", messages[1])
            self.assertEqual(original, source.read_text(encoding="utf-8"))
            self.assertEqual(["p1.json"], [file.name for file in social.iterdir()])

    def test_remote_attachments_reject_bad_urls_and_missing_relevance(self):
        attachment = {"type": "gif", "url": "https://media.giphy.com/media/example/giphy.gif",
                      "alt": "Confused calculation", "context": "Related to the calculation being discussed"}
        invalid_urls = [
            "http://media.giphy.com/a.gif", "javascript:alert(1)", "data:image/gif;base64,abc",
            "file:///C:/private/image.gif", "//media.giphy.com/a.gif",
            "https://user:pass@media.giphy.com/a.gif", "https://127.0.0.1/a.gif",
            "https://127.1/a.gif", "https://[::1]/a.gif", "https://2130706433/a.gif",
            "https://localhost/a.gif", "https://host.local/a.gif", "https://host.internal/a.gif",
            "https://media.giphy.com:8443/a.gif", "https://media.giphy.com:bad/a.gif",
            "https://media.giphy.com/a.gif#fragment", "https://media.giphy.com/a.gif?token=hidden",
            "https://media.giphy.com/a.gif?%74oken%3Dhidden", "https://media.giphy.com\\@localhost/a.gif",
            "https://media.giphy.com/\na.gif", "https://media.giphy.com/a b.gif",
        ]
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                MODULE.normalize_social_attachments([{**attachment, "url": url}])
        for invalid in [None, {}, "url", [{"type": "video"}],
                        [{**attachment, "alt": ""}], [{**attachment, "context": " "}],
                        [{**attachment, "sourceUrl": "javascript:alert(1)"}]]:
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                MODULE.normalize_social_attachments(invalid)
        for kind in ("image", "gif", "sticker"):
            normalized = MODULE.normalize_social_attachments([{**attachment, "type": kind}])[0]
            self.assertEqual(kind, normalized["type"])
            self.assertEqual(attachment["url"], normalized["sourceUrl"])

    def test_invalid_remote_attachment_stops_loading_instead_of_disappearing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            social = root / ".agent-context" / "social"
            social.mkdir(parents=True)
            (social / "p1.json").write_text(json.dumps({
                "personaId": "p1", "messages": [{"text": "", "attachments": [{"type": "gif"}]}],
            }), encoding="utf-8")
            store = MODULE.Store("ctx-a", "A", root, social.parent, {})
            with self.assertRaisesRegex(ValueError, r"p1.json message 1: attachment alt"):
                MODULE.load_social_personas(store)

    def test_output_directory_cannot_escape_project(self):
        config = {
            "_path": str(MODULE.DEFAULT_CONFIG),
            "outputDirectory": str(Path(tempfile.gettempdir()) / "escaped-output"),
        }
        with self.assertRaises(RuntimeError):
            MODULE.resolve_output_dir(config)

    def test_social_copied_personas_are_not_duplicated(self):
        persona = {"personaId": "p1", "displayName": "One", "contextId": "ctx-a", "contextName": "A", "messages": [{"id": "m1", "text": "Hi"}]}
        contexts = [
            {"id": "ctx-a", "name": "A", "social": [persona]},
            {"id": "ctx-b", "name": "B", "social": [{**persona, "contextId": "ctx-b"}]},
        ]
        board = MODULE.build_social_board(contexts, {"edges": []}, self.color_registry)
        self.assertEqual(1, board["personaCount"])
        self.assertEqual(1, board["messageCount"])
        self.assertEqual([], board["relationships"])

    def test_social_conflicting_persona_copies_are_reported(self):
        persona = {"personaId": "p1", "displayName": "One", "contextId": "ctx-a", "messages": []}
        contexts = [
            {"id": "ctx-a", "name": "A", "social": [persona]},
            {"id": "ctx-b", "name": "B", "social": [{**persona, "messages": [{"id": "m1", "text": "Different"}]}]},
        ]
        with self.assertRaisesRegex(ValueError, "Conflicting copies of social persona p1"):
            MODULE.build_social_board(contexts, {"edges": []}, self.color_registry)

    def test_persona_colors_are_central_unique_and_stable(self):
        personas = [
            {"personaId": name, "displayName": name, "contextId": "ctx-a", "profileImageData": "a" * 64, "profileColor": "#ffffff", "messages": []}
            for name in ("b", "c")
        ]
        contexts = [{"id": "ctx-a", "name": "A", "social": personas}]
        board = MODULE.build_social_board(contexts, {"edges": []}, self.color_registry)
        original = {persona["personaId"]: persona["profileColor"] for persona in board["personas"]}
        self.assertEqual(2, len(set(original.values())))
        self.assertNotIn("#ffffff", original.values())
        later = MODULE.register_persona_colors(["c", "a"], self.color_registry)
        self.assertEqual(original["c"], later["c"])
        self.assertEqual(original["b"], later["b"])
        self.assertEqual(3, len(set(later.values())))
        restored = MODULE.register_persona_colors(["b", "c", "a"], self.color_registry)
        self.assertEqual(later, restored)
        self.assertEqual(str(self.color_registry), board["colorRegistryPath"])

    def test_persona_color_registry_serializes_concurrent_registration(self):
        MODULE.register_persona_colors([], self.color_registry)
        script = (
            "import sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(SCRIPT.parent)!r}); "
            "from build_context_mesh import register_persona_colors; "
            "print('ready', flush=True); "
            "register_persona_colors(sys.argv[2:], Path(sys.argv[1]))"
        )
        processes = []
        try:
            with closing(sqlite3.connect(self.color_registry)) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                for names in (["one", "shared"], ["two", "shared"]):
                    process = subprocess.Popen(
                        [sys.executable, "-c", script, str(self.color_registry), *names],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    processes.append(process)
                    self.assertEqual("ready", process.stdout.readline().strip())
            for process in processes:
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(0, process.returncode, stdout + stderr)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        colors = MODULE.register_persona_colors(["one", "two", "shared"], self.color_registry)
        self.assertEqual({"one", "two", "shared"}, set(colors))
        self.assertEqual(3, len(set(colors.values())))

    def test_invalid_registered_color_fails_without_reassigning(self):
        MODULE.register_persona_colors(["one"], self.color_registry)
        with closing(sqlite3.connect(self.color_registry)) as connection, connection:
            connection.execute("UPDATE persona_colors SET color = 'invalid' WHERE persona_id = 'one'")
        with self.assertRaisesRegex(ValueError, "Invalid persona color"):
            MODULE.register_persona_colors(["one", "two"], self.color_registry)
        with closing(sqlite3.connect(self.color_registry)) as connection:
            self.assertEqual(
                [("one", "invalid")],
                connection.execute("SELECT persona_id, color FROM persona_colors").fetchall(),
            )

    def test_dashboard_assets_and_vendor_bundle_are_available(self):
        css = MODULE.read_required_asset(MODULE.PROJECT_ROOT / "assets" / "dashboard.css")
        script = MODULE.read_required_asset(MODULE.PROJECT_ROOT / "assets" / "dashboard.js")
        vendor = MODULE.browser_vendor_bundle()
        self.assertIn("#graph canvas", css)
        self.assertIn("ForceGraph()", script)
        self.assertIn("forceCollide", vendor)
        self.assertIn("ForceGraph", vendor)

    def test_json_for_script_escapes_html_script_terminators(self):
        payload = MODULE.json_for_script({"value": "</SCRIPT>\u2028\u2029"})
        self.assertNotIn("<", payload)
        self.assertIn("\\u003c/SCRIPT>", payload)
        self.assertIn("\\u2028", payload)
        self.assertIn("\\u2029", payload)

    def test_artifact_copy_suffix_maps_to_canonical_name(self):
        self.assertEqual(
            "sfmc-migration-resource-report.html",
            ARTIFACT.logical_name(r"C:\Users\me\Downloads\SFMC-Migration-Resource-Report 3.html"),
        )
        self.assertEqual(
            "sfmc-migration-resource-report.html",
            ARTIFACT.logical_name("SFMC-Migration-Resource-Report (3).html"),
        )

    def test_artifact_extraction_and_secret_redaction(self):
        candidates = ARTIFACT.extract_candidates(
            r'Generated "C:\reports\Resource Report 2.html" from input.csv'
        )
        self.assertIn(r"C:\reports\Resource Report 2.html", candidates)
        self.assertEqual(
            "token=[redacted] generated report.html",
            ARTIFACT.truncate("token=do-not-keep generated report.html"),
        )

    def test_artifact_cache_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session-1"
            session.mkdir()
            (session / "workspace.yaml").write_text(
                "name: TestChat\ncwd: C:\\work\n",
                encoding="utf-8",
            )
            event = {
                "type": "assistant.message",
                "timestamp": "2026-08-20T12:00:00Z",
                "data": {"content": r"Saved C:\work\result.html"},
            }
            (session / "events.jsonl").write_text(
                __import__("json").dumps(event, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            cache = root / "cache.json"
            first, cache_payload = ARTIFACT.build_artifact_index(root, cache, 3650, 100)
            cache.write_text(__import__("json").dumps(cache_payload), encoding="utf-8")
            second, _ = ARTIFACT.build_artifact_index(root, cache, 3650, 100)
            self.assertEqual(1, first["scannedSessions"])
            self.assertEqual(1, second["reusedSessions"])

    def test_artifact_limit_keeps_origin_before_later_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("origin", "later", "inspection", "unrelated"):
                session = root / name
                session.mkdir()
                (session / "events.jsonl").write_text("", encoding="utf-8")
            from unittest.mock import patch
            def scan(session):
                timestamp, action = {
                    "origin": ("2026-08-01T12:00:00Z", "generated"),
                    "later": ("2026-10-01T12:00:00Z", "generated"),
                    "inspection": ("2026-11-01T12:00:00Z", "inspected"),
                    "unrelated": ("2026-09-01T12:00:00Z", "generated"),
                }[session.name]
                logical_name = "other.html" if session.name == "unrelated" else "report.html"
                return [{"logicalName": logical_name, "sessionId": session.name, "firstSeen": timestamp, "lastSeen": timestamp, "action": action}]
            with patch.object(ARTIFACT, "scan_session", side_effect=scan):
                index, _ = ARTIFACT.build_artifact_index(root, root / "cache.json", 3650, 2)
            self.assertEqual(["origin", "later"], [record["sessionId"] for record in index["records"]])


    def test_archive_preserves_history_and_character_but_projects_empty_room(self):
        from copy import deepcopy
        board = self.broadcast_board({
            "a": [{"id": "question", "text": "@meshboard Which animal?", "threadId": "animals"}],
            "b": [{"id": "answer", "text": "Owl.", "threadId": "animals", "replyTo": "question"}],
        }, [{"id": "animals", "questionMessageId": "question", "ownerPersonaId": "a", "status": "open"}])
        author = next(persona for persona in board["personas"] if persona["personaId"] == "a")
        author["meshboardPersonality"]["reflections"] = [{
            "text": "The answer gave this character a more relaxed conversational direction.",
            "messageIds": ["question", "answer"], "traitAdjustments": {"humor": 7},
            "natureSummary": "relaxed and inquisitive",
        }]
        author.update(MODULE.derive_social_personality(author, author["messages"], board["messages"]))
        before = deepcopy(board)
        contexts = [{"social": deepcopy(board["personas"])}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = MODULE.freeze_social_archive({"social": board}, root)
            snapshot = (root / MODULE.SOCIAL_ARCHIVE_JSON).read_bytes()
            MODULE.project_active_social(board, contexts, archive, root)
            self.assertEqual([], board["messages"])
            self.assertEqual([], board["threads"])
            self.assertEqual([], board["attention"])
            self.assertEqual(0, board["messageCount"])
            self.assertEqual(before, MODULE.load_social_archive(root)["social"])
            for old, current in zip(before["personas"], board["personas"]):
                self.assertEqual({k:v for k,v in old.items() if k not in ("messages", "threads")},
                                 {k:v for k,v in current.items() if k not in ("messages", "threads")})
                self.assertEqual([], current["messages"])
                self.assertEqual([], current["threads"])
            self.assertTrue(all(not p["messages"] and not p["threads"] for p in contexts[0]["social"]))
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                MODULE.freeze_social_archive({"social": board}, root)
            self.assertEqual(snapshot, (root / MODULE.SOCIAL_ARCHIVE_JSON).read_bytes())

    def test_new_messages_and_broadcast_obligations_remain_active(self):
        from copy import deepcopy
        old = {"a": [{"id": "old", "text": "@meshboard Old question"}]}
        archive = {"archivedAt": "2026-11-03T02:06:15+05:30",
                   "social": deepcopy(self.broadcast_board(old))}
        new = {**old, "b": [{"id": "new", "text": "@meshboard New question"}]}
        board = self.broadcast_board(new)
        character = deepcopy(board["personas"])
        MODULE.project_active_social(board, [], archive, self.color_registry.parent)
        self.assertEqual(["new"], [m["id"] for m in board["messages"]])
        self.assertEqual({"a", "c"}, {item["personaId"] for item in board["attention"]})
        self.assertTrue(all(item["messageId"] == "new" for item in board["attention"]))
        for expected, current in zip(character, board["personas"]):
            for key in ("meshboardPersonality", "personalityStats", "natureSummary"):
                self.assertEqual(expected[key], current[key])

    def test_late_replies_are_archived_without_restarting_conversations(self):
        from copy import deepcopy
        old = {"a": [{"id": "old", "text": "@meshboard Old question", "threadId": "t"}]}
        threads = [{"id": "t", "questionMessageId": "old", "ownerPersonaId": "a", "status": "closed"}]
        for field, value in [("replyTo", "old"), ("threadId", "t"), ("broadcastReplyTo", "old")]:
            with self.subTest(field=field):
                archived_board = self.broadcast_board(old, threads)
                archive = {"archivedAt": "2026-11-03T02:06:15+05:30", "social": deepcopy(archived_board)}
                board = self.broadcast_board({**old, "b": [
                    {"id": "new", "text": "Late answer", field: value},
                    {"id": "fresh", "text": "New conversation"},
                ], "c": [{"id": "nested", "text": "Follow-up", "replyTo": "new"}]}, threads)
                characters = deepcopy(board["personas"])
                contexts = [{"social": deepcopy(board["personas"])}]
                arrivals = MODULE.project_active_social(board, contexts, archive, self.color_registry.parent)
                self.assertEqual({"new", "nested"}, {message["id"] for message in arrivals})
                self.assertEqual(["fresh"], [message["id"] for message in board["messages"]])
                self.assertEqual([], board["threads"])
                self.assertEqual([], board["attention"])
                self.assertTrue(all(message["id"] == "fresh" for persona in contexts[0]["social"]
                                    for message in persona["messages"]))
                self.assertEqual(archived_board["messages"], archive["social"]["messages"][:1])
                self.assertEqual(3, archive["social"]["messageCount"])
                self.assertEqual(2, board["archive"]["lateReplyCount"])
                for before, after in zip(characters, board["personas"]):
                    self.assertEqual({k:v for k,v in before.items() if k not in ("messages", "threads")},
                                     {k:v for k,v in after.items() if k not in ("messages", "threads")})
                self.assertEqual([], MODULE.project_active_social(board, contexts, archive, self.color_registry.parent))

    def test_archived_reply_new_thread_and_its_answers_stay_archived(self):
        from copy import deepcopy
        old = {"a": [{"id": "old", "text": "Old question"}]}
        archive = {"archivedAt": "2026-11-03T02:06:15+05:30", "social": deepcopy(self.broadcast_board(old))}
        threads = [{"id": "follow-up", "questionMessageId": "new", "ownerPersonaId": "a", "status": "open"}]
        board = self.broadcast_board({"a": old["a"] + [
            {"id": "new", "text": "Related question", "replyTo": "old", "threadId": "follow-up"}],
            "b": [{"id": "answer", "text": "Answer", "threadId": "follow-up"}]}, threads)
        MODULE.project_active_social(board, [], archive, self.color_registry.parent)
        self.assertEqual([], board["messages"])
        self.assertEqual([], board["threads"])
        self.assertEqual(["follow-up"], [thread["id"] for thread in archive["social"]["threads"]])
        self.assertEqual({"old", "new", "answer"}, {message["id"] for message in archive["social"]["messages"]})

    def test_archive_publication_merges_stale_builds_and_repairs_viewer(self):
        from copy import deepcopy
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            original = self.broadcast_board({"a": [{"id": "old", "text": "Original"}]})
            archive = MODULE.freeze_social_archive({"social": original}, output)
            pending = []
            for author, message_id in [("b", "first"), ("c", "second")]:
                board = self.broadcast_board({"a": [{"id": "old", "text": "Original"}],
                                              author: [{"id": message_id, "text": message_id, "replyTo": "old"}]})
                proposed = deepcopy(archive)
                MODULE.project_active_social(board, [], proposed, output)
                pending.append({"social": board, "contexts": [], "summary": {}, "_socialArchive": proposed})
            config = {"_path": str(root / "config.json"), "outputDirectory": "output"}
            with patch.object(MODULE, "PROJECT_ROOT", root), \
                    patch.object(MODULE, "render_html", side_effect=lambda index: json.dumps(index)), \
                    patch.object(MODULE, "render_digest", return_value="digest"):
                for index in pending:
                    MODULE.write_outputs(index, config)
                saved = MODULE.load_social_archive(output)
                self.assertEqual(["old", "first", "second"], [m["id"] for m in saved["social"]["messages"]])
                self.assertEqual(original["messages"], saved["social"]["messages"][:1])
                self.assertEqual(["second"], [m["id"] for m in pending[-1]["_archivedReplies"]])
                payload = (output / MODULE.SOCIAL_ARCHIVE_JSON).read_bytes()
                viewer = (output / MODULE.SOCIAL_ARCHIVE_HTML).read_bytes()
                active_payload = (output / "context-index.json").read_text(encoding="utf-8")
                self.assertNotIn("Original", active_payload)
                self.assertNotIn("_socialArchive", active_payload)
                (output / MODULE.SOCIAL_ARCHIVE_HTML).write_text("stale viewer", encoding="utf-8")
                MODULE.write_outputs(pending[-1], config)
                self.assertEqual(payload, (output / MODULE.SOCIAL_ARCHIVE_JSON).read_bytes())
                self.assertEqual(viewer, (output / MODULE.SOCIAL_ARCHIVE_HTML).read_bytes())
                self.assertEqual([], pending[-1]["_archivedReplies"])
                self.assertNotIn("_archivedReplies", (output / "context-index.json").read_text(encoding="utf-8"))

    def test_archive_invalid_data_fails_and_atomic_creation_never_replaces(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(MODULE.load_social_archive(root))
            path = root / MODULE.SOCIAL_ARCHIVE_JSON
            for payload in ({}, [], {"schemaVersion": 1, "archivedAt": "invalid", "social": {}}):
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    MODULE.load_social_archive(root)
            with self.assertRaises(FileExistsError):
                MODULE.atomic_create(path, "replacement")
            self.assertNotEqual("replacement", path.read_text(encoding="utf-8"))
            self.assertEqual([path], list(root.iterdir()))
            path.unlink()
            (root / MODULE.SOCIAL_ARCHIVE_HTML).write_text("Preserved viewer", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "archive JSON is missing"):
                MODULE.load_social_archive(root)


if __name__ == "__main__":
    unittest.main()

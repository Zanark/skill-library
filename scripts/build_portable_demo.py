"""Build an offline, wholly fictional Context Mesh snapshot using the real renderer."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def build(runtime: Path, destination: Path) -> dict:
    source = runtime / "scripts" / "build_context_mesh.py"
    sys.path.insert(0, str(runtime))
    spec = importlib.util.spec_from_file_location("_portable_mesh_demo", source)
    mesh = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mesh
    spec.loader.exec_module(mesh)
    if not (runtime / "node_modules" / "force-graph").is_dir():
        raise FileNotFoundError("Run the installer with --install-dependencies before building the demo.")
    with tempfile.TemporaryDirectory(prefix="skill-library-demo-") as directory:
        work = Path(directory)
        project = work / "renderer"
        project.mkdir()
        (project / "output").mkdir()
        # Render against the installed assets without touching its private output.
        mesh.PROJECT_ROOT = project
        mesh.export_zmem = lambda: []  # Explicitly fictional fixture, never a production fallback.
        names = ["Workshop", "Library", "Garden", "Gallery", "Signals", "Observatory"]
        now = datetime.now(timezone.utc)
        for i, name in enumerate(names):
            store = work / "bases" / name / ".agent-context"
            social = store / "social"
            social.mkdir(parents=True)
            related = work / "bases" / names[(i + 1) % len(names)]
            docs = {
                "README.md": f"# {name}\nWholly fictional portability fixture.\n",
                "STATE.md": f"# State\nLast updated: {now.date()}\n## Current focus\n- Explore the {name.lower()}.\n## Relationships\n- Canonical handoff to {related}.\n",
                "MEMORY.md": "# Memory\n## Durable facts\n- These are synthetic examples, not real sessions.\n",
                "JOURNAL.md": f"# Journal\n## {now.date()} - Fictional opening\n- Created a sample context.\n",
            }
            for filename, text in docs.items():
                (store / filename).write_text(text, encoding="utf-8")
            def message(identifier, text, **extra):
                return {"id": identifier, "timestamp": (now + timedelta(seconds=i)).isoformat(), "kind": "banter", "text": text, **extra}
            messages = [message(f"demo-{i}", [
                "The library has a suspiciously competitive bookmark collection.",
                "I brought the tea. Someone else can referee the bookmarks.",
                "My fern has entered the tournament. Terrible reach, excellent patience.",
                "I judge purely on dramatic entrance quality.",
                "Does a victory fanfare count as a useful signal?",
                "Only if the stars can hear it.",
            ][i])]
            threads = []
            if i == 0:
                messages.append(message("demo-question", "What should our imaginary tournament prize be?", threadId="demo-thread", questionTitle="A prize worth competing for?"))
                threads.append({"id": "demo-thread", "questionMessageId": "demo-question", "title": "A prize worth competing for?", "status": "open", "createdAt": now.isoformat()})
            if i == 1:
                messages.append(message("demo-answer", "A tiny golden bookmark. Obviously.", replyTo="demo-question", threadId="demo-thread"))
            persona = {
                "personaId": f"demo-{name.lower()}", "displayName": name,
                "persona": f"Fictional {name.lower()} host for a public demonstration.",
                "profileImageData": hashlib.sha256(name.encode()).hexdigest()[:16],
                "sessionId": f"{i + 1:08d}-1111-4111-8111-111111111111",
                "createdAt": now.isoformat(), "messages": messages, "threads": threads,
            }
            (social / "demo.json").write_text(json.dumps(persona), encoding="utf-8")
        config = json.loads((runtime / "config.example.json").read_text(encoding="utf-8"))
        config.update({"_path": str(project / "config.json"), "roots": [str(work / "bases")], "sessionStateRoot": str(work / "no-real-sessions")})
        index = mesh.build_index(config)
        index.pop("_artifactCache", None)
        index.pop("_socialArchive", None)
        index["demo"] = {"fictional": True, "purpose": "Public offline feature snapshot; no real messages, memories or sessions."}
        serialized = json.dumps(index, ensure_ascii=False).replace(str(work).replace("\\", "\\\\"), r"C:\\SkillLibraryDemo")
        serialized = serialized.replace(str(runtime).replace("\\", "\\\\"), r"C:\\SkillLibraryDemo\\renderer")
        index = json.loads(serialized)
        index["social"]["archive"] = {
            "archivedAt": now.isoformat(), "messageCount": 1, "threadCount": 0, "lateReplyCount": 0,
            "jsonPath": "meshboard-archive.json", "htmlPath": "meshboard-archive.html",
            "htmlRelativePath": "meshboard-archive.html", "readPolicy": "Fictional demo; explicit opt-in only.",
        }
        destination.mkdir(parents=True, exist_ok=True)
        archive_index = deepcopy(index)
        archive_index["archiveView"] = True
        archived_message = deepcopy(index["social"]["messages"][0])
        archived_message.update({"id": "demo-archived", "text": "A fictional warm-up round, kept as a demonstration archive.", "timestamp": (now - timedelta(days=1)).isoformat()})
        archive_index["social"]["messages"] = [archived_message]
        archive_index["social"]["messageCount"] = 1
        archive_index["social"]["threads"] = []
        archive_index["social"]["attention"] = []
        mesh.PROJECT_ROOT = runtime
        (destination / "context-index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        (destination / "context-mesh.html").write_text(mesh.render_html(index), encoding="utf-8")
        (destination / "meshboard-archive.html").write_text(mesh.render_html(archive_index), encoding="utf-8")
        (destination / "meshboard-archive.json").write_text(json.dumps({
            "schemaVersion": 1, "archivedAt": now.isoformat(), "social": archive_index["social"],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        (destination / "CONTEXT-MESH.md").write_text(mesh.render_digest(index), encoding="utf-8")
        notices = []
        for license_file in sorted((runtime / "node_modules").rglob("LICENSE*")):
            if license_file.is_file():
                notices.append(f"\n--- {license_file.relative_to(runtime / 'node_modules')} ---\n" + license_file.read_text(encoding="utf-8", errors="replace"))
        (destination / "THIRD-PARTY-NOTICES.txt").write_text("Licenses accompanying the demo's bundled renderer dependencies.\n" + "\n".join(notices), encoding="utf-8")
    return {"demo": str(destination.resolve()), "contexts": len(index["contexts"]), "messages": len(index["social"]["messages"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "examples" / "context-mesh")
    args = parser.parse_args()
    print(json.dumps(build(args.mesh_runtime.resolve(), args.output.resolve()), indent=2))


if __name__ == "__main__":
    main()

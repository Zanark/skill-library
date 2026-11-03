"""Install portable Windows runtimes and path-rebased skills without changing agent permissions."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIMES = {
    "context-mesh": "context-mesh",
    "clipfarm-leetcode": "clipfarm",
    "documentation-mesh": "documentation-mesh",
    "speak": "speak",
}
SKIP = {"node_modules", ".venv", "__pycache__", ".pytest_cache", "obj", "bin"}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def copy_payload(source: Path, destination: Path) -> None:
    for base, directories, files in os.walk(source):
        directories[:] = sorted(d for d in directories if d not in SKIP and not d.endswith(".egg-info"))
        for name in sorted(files):
            path = Path(base) / name
            target = destination / path.relative_to(source)
            if target.exists():
                if target.read_bytes() != path.read_bytes():
                    raise FileExistsError(f"Different runtime file exists; choose a new runtime root: {target}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def rebase(text: str, runtime: Path, repository: Path = ROOT) -> str:
    mappings = {
        r"C:\devdesk\Copilot\CopilotSessions\context-network": runtime / "context-mesh",
        r"C:\devdesk\homedesk\ClipFarm": runtime / "clipfarm",
        "__CLIPFARM_ROOT__": runtime / "clipfarm",
        r"C:\devdesk\Copilot\CopilotSessions\documentation-mesh-plugin": runtime / "documentation-mesh",
        r"C:\devdesk\tools\copilot-speak": runtime / "speak",
        r"C:\devdesk\homedesk\skill-library": repository,
        r"C:\Users\mishrad\CareerKB": runtime / "private-state" / "career-kb",
        r"C:\unprotectedDownloads\Connects": runtime / "private-state" / "career-sources",
        r"C:\notedesk\zettelkasten\1 Project": runtime / "private-state" / "sprint-notes",
    }
    for old, new in mappings.items():
        text = re.sub(re.escape(old.replace("\\", "\\\\")), lambda _: str(new).replace("\\", "\\\\"), text, flags=re.I)
        text = re.sub(re.escape(old), lambda _: str(new), text, flags=re.I)
    return text


def install(runtime: Path, skills: Path, *, dependencies=False, replace_skills=False) -> dict:
    runtime = runtime.resolve()
    skills = skills.resolve()
    for skill, directory in RUNTIMES.items():
        source = ROOT / "skills" / skill / "implementation"
        if not source.is_dir():
            raise FileNotFoundError(f"Missing packaged implementation: {source}")
        copy_payload(source, runtime / directory)
    docs_runtime = runtime / "documentation-mesh" / "runtime" / "windows-x64"
    version = json.loads((docs_runtime / "version-manifest.json").read_text(encoding="utf-8-sig"))
    executable = docs_runtime / version["executable"]
    with executable.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != version["sha256"]:
            raise ValueError("The bundled Documentation Mesh runtime failed its checksum.")
    inventory = json.loads((ROOT / "source-inventory.json").read_text(encoding="utf-8"))
    pending = []
    for entry in inventory:
        source = ROOT / "skills" / entry["name"] / "SKILL.md"
        content = rebase(source.read_text(encoding="utf-8"), runtime)
        if entry["name"] == "documentation-mesh":
            before, heading, after = content.partition("## Runtime resolution\n")
            _, next_heading, remaining = after.partition("\n## ")
            if not heading or not next_heading:
                raise ValueError("Documentation Mesh skill is missing its runtime-resolution section.")
            binding = (
                "## Runtime resolution\n\n"
                "This standalone installation uses the verified pinned executable below, "
                "not a PATH command or a plugin-relative fallback. Run its version check first:\n\n"
                f'```powershell\n& "{executable}" --version\n```\n'
            )
            content = before + binding + "\n## " + remaining
            content = re.sub(r"(?m)^documentation-mesh(?=\s)", lambda _: f'& "{executable}"', content)
        target = skills / entry["name"] / "SKILL.md"
        if target.exists() and target.read_text(encoding="utf-8") != content:
            if not replace_skills:
                raise FileExistsError(f"Existing skill differs; inspect it or explicitly use --replace-skills: {target}")
        pending.append((target, content))
    for target, content in pending:
        if target.exists() and target.read_text(encoding="utf-8") != content:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup = runtime / "skill-backups" / stamp / target.parent.name / "SKILL.md"
            backup.parent.mkdir(parents=True)
            shutil.copy2(target, backup)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    config = runtime / "context-mesh" / "config.json"
    if not config.exists():
        example = ROOT / "skills" / "context-mesh" / "implementation" / "config.example.json"
        settings = json.loads(example.read_text(encoding="utf-8"))
        settings["roots"] = [str(ROOT), str(runtime / "contexts")]
        settings["sessionStateRoot"] = str(runtime / "historical-sessions")
        write_json(config, settings)
    write_json(runtime / "mcp.speak.template.json", {
        "mcpServers": {"copilot-speak": {
            "command": "node", "args": [str(runtime / "speak" / "mcp-server" / "index.mjs")],
        }},
    })
    if dependencies:
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm:
            raise FileNotFoundError("Install Node.js 18+ with npm before using --install-dependencies.")
        for directory in (runtime / "context-mesh", runtime / "speak" / "mcp-server"):
            subprocess.run([npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=directory, check=True)
        clipfarm = runtime / "clipfarm"
        python = clipfarm / ".venv" / "Scripts" / "python.exe"
        if not python.exists():
            subprocess.run([sys.executable, "-m", "venv", str(clipfarm / ".venv")], check=True)
        subprocess.run([
            str(python), "-m", "pip", "install", "-r", str(clipfarm / "constraints-windows-py313.txt"),
            "-e", str(clipfarm) + "[workflow,dev]",
        ], check=True)
    result = {
        "runtimeRoot": str(runtime), "skillsDirectory": str(skills), "installedSkills": len(pending),
        "dependencyRestoreRequested": dependencies,
        "privateState": "Not activated; restore separately into a new isolated directory.",
        "externalServices": "Authenticate ADO/IcM/WorkIQ/Agency independently. Internal zmem is private-only.",
        "agentConfiguration": "No permissions, trust settings, auth or global MCP registration modified.",
    }
    write_json(runtime / "installation.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SkillLibrary")
    parser.add_argument("--skills-directory", type=Path, default=Path.home() / ".copilot" / "skills")
    parser.add_argument("--install-dependencies", action="store_true", help="Explicitly allow npm/pip dependency restoration.")
    parser.add_argument("--replace-skills", action="store_true", help="Back up and replace differing installed skill instructions.")
    args = parser.parse_args()
    if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"} or sys.version_info < (3, 13):
        parser.error("This runtime snapshot requires Windows x64 and Python 3.13+.")
    print(json.dumps(install(
        args.runtime_root, args.skills_directory,
        dependencies=args.install_dependencies, replace_skills=args.replace_skills,
    ), indent=2))


if __name__ == "__main__":
    main()

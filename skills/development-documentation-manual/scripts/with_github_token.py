"""Run a trusted command with the manual's local GitHub credential, without printing it."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

SKILL_ROOT = Path(__file__).resolve().parents[1]


def parse_token(text: str) -> str:
    token = None
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if key.strip() != "TODO_SYNC_GITHUB_TOKEN" or not separator or token is not None:
            raise ValueError(f"Invalid local credential configuration at line {number}.")
        value = value.strip()
        if value[:1] in {"'", '"'}:
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"Invalid local credential configuration at line {number}.")
            value = value[1:-1]
        if not value or not all(character.isascii() and (character.isalnum() or character == "_") for character in value):
            raise ValueError(f"Empty or invalid local credential at line {number}.")
        token = value
    if token is None:
        raise ValueError("Local credential configuration has no TODO_SYNC_GITHUB_TOKEN.")
    return token


def load_token(skill_root: Path = SKILL_ROOT) -> str:
    path = skill_root / ".env"
    if path.exists():
        repository = skill_root.parents[1]
        relative = str(path.relative_to(repository))
        tracked = subprocess.run(
            ["git", "-C", str(repository), "ls-files", "--", relative],
            check=True, capture_output=True,
        )
        ignored = subprocess.run(
            ["git", "-C", str(repository), "check-ignore", "--quiet", "--", relative],
            capture_output=True,
        )
        if tracked.stdout or ignored.returncode != 0:
            raise ValueError("Local credential file must be Git-ignored and untracked.")
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            raise ValueError("Unable to read the local credential file.") from None
        return parse_token(text)
    token = os.environ.get("TODO_SYNC_GITHUB_TOKEN", "").strip()
    if not token and os.name == "nt":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                token, _ = winreg.QueryValueEx(key, "TODO_SYNC_GITHUB_TOKEN")
        except FileNotFoundError:
            token = ""
    if not isinstance(token, str) or not token.strip():
        raise ValueError("TODO sync credential is not configured.")
    return token.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Trusted command after --.")
    args = parser.parse_args(argv)
    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("Provide a trusted command after --.")
    try:
        token = load_token()
        environment = os.environ.copy()
        environment["TODO_SYNC_GITHUB_TOKEN"] = token
        environment["GH_TOKEN"] = token
        environment.pop("GH_DEBUG", None)
        return subprocess.run(command, env=environment).returncode
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, ValueError) else "Credential loading or command launch failed."
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

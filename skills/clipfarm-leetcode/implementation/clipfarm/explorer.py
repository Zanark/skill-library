"""Browser session-folder links and legacy Windows protocol compatibility."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

SESSION_NAME = re.compile(r"session_[0-9]{8}_[0-9]{6}_[0-9]{6}")
SESSION_URI = re.compile(r"clipfarm://open-session/(session_[0-9]{8}_[0-9]{6}_[0-9]{6})/?")
PROTOCOL_OWNER = "ClipFarm.SessionExplorer.v1"
PROTOCOL_KEY = r"Software\Classes\clipfarm"
EXPLORER_CSS = """
.session-explorer{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0}
.session-explorer a{display:inline-block;background:#cd5c5c;color:#002b36;border:1px solid #cd5c5c;border-radius:5px;padding:10px 15px;font:600 14px system-ui;text-decoration:none}
.session-explorer a:hover{filter:brightness(1.08)}
.session-explorer a:focus-visible{outline:2px solid #eee8d5;outline-offset:4px}
.session-explorer span{font:13px/1.5 system-ui;color:#b4c4c4}
"""
EXPORT_FOLDER_CSS = """
.export-folder{min-width:0;margin:14px 0 20px;padding:12px 14px;background:#123b49;border:1px solid #78a9ff;border-left-width:4px;border-radius:7px}
.export-folder-label{display:block;margin-bottom:5px;color:#b9d2ff;font:700 12px/1.5 system-ui;letter-spacing:.06em;text-transform:uppercase}
.export-folder a{display:block;color:#fff4cf;text-decoration:underline;text-underline-offset:3px}
.export-folder code{font:600 16px/1.55 Consolas,monospace;overflow-wrap:anywhere;white-space:normal}
.export-folder-location{display:block;margin-top:7px;color:#c0d2d6;font:12px/1.5 system-ui}
.export-folder-location code{font-size:12px;font-weight:400}
.export-folder a:focus-visible{outline:2px solid #fff4cf;outline-offset:4px}
"""


def export_folder_sort_key(folder: Path) -> tuple[str, str]:
    """Sort by the actual folder name, with a deterministic tie-break across roots."""
    return folder.name.casefold(), str(folder).casefold()


def export_folder_field(folder: Path, gallery_directory: Path) -> str:
    """Identify the exported media's directory, not the clip title or internal ID."""
    if not folder.name:
        raise ValueError("An export folder must have a directory name.")
    relative = Path(os.path.relpath(folder, gallery_directory))
    href = quote(relative.as_posix(), safe="/") + "/"
    name = html.escape(folder.name, quote=True)
    location = (
        '<span class="export-folder-location">Relative location: '
        f'<code>{html.escape(str(relative))}</code></span>'
        if relative != Path(".") and relative.parent != Path(".") else ""
    )
    return (
        f'<div class="export-folder" data-export-folder="{name}">'
        '<span class="export-folder-label">Export folder</span>'
        f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
        'title="Open this reel folder in a new browser tab">'
        f'<code>{name}</code></a>{location}</div>'
    )


def _css_hash(css: str) -> str:
    # HTML parsing normalizes source line endings before CSP checks inline styles.
    normalized = css.replace("\r\n", "\n").replace("\r", "\n")
    return "sha256-" + base64.b64encode(hashlib.sha256(normalized.encode("utf-8")).digest()).decode("ascii")


class _Policies(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "meta" and (attributes.get("http-equiv") or "").lower() == "content-security-policy":
            self.values.append((self.get_starttag_text(), attributes.get("content") or ""))


def add_explorer_button(document: str, session_name: str) -> str:
    """Add a new-tab directory link; upgrade exact legacy headers without other edits."""
    if not SESSION_NAME.fullmatch(session_name):
        raise ValueError("Explorer links require a timestamped ClipFarm session name.")
    markup = (
        '<div class="session-explorer"><a id="open-session-explorer" '
        f'data-session-name="{session_name}" href="./" target="_blank" rel="noopener noreferrer" '
        'title="Open this session directory in a new browser tab">'
        'Open session folder</a><span>Opens this folder in a new browser tab.</span></div>'
    )
    legacy_markup = (
        '<div class="session-explorer"><a id="open-session-explorer" '
        f'href="clipfarm://open-session/{session_name}" '
        'title="Open this session folder using the local ClipFarm Windows handler">'
        'Open in Explorer</a><span>Windows may ask you to allow the local handler.</span></div>'
    )
    controls = re.findall(
        r"""\bid\s*=\s*(?:"open-session-explorer"|'open-session-explorer'|open-session-explorer(?=[\s>]))""",
        document, re.IGNORECASE,
    )
    if controls:
        if len(controls) == 1:
            if markup in document:
                return document
            if legacy_markup in document:
                return document.replace(legacy_markup, markup, 1)
        raise ValueError("An existing session-folder control conflicts with this session.")
    heading = re.search(r"</h1\s*>", document, re.IGNORECASE)
    if heading is None:
        raise ValueError("The session gallery has no heading for the Explorer button.")
    document = document[:heading.end()] + markup + document[heading.end():]
    return append_gallery_css(document, EXPLORER_CSS)


def append_gallery_css(document: str, css: str) -> str:
    """Extend the existing stylesheet without relaxing its CSP or touching scripts."""
    styles = list(re.finditer(r"<style(?:\s[^>]*)?>(.*?)</style\s*>", document, re.IGNORECASE | re.DOTALL))
    if len(styles) != 1:
        raise ValueError("Expected one inline session stylesheet; existing gallery was preserved.")
    style = styles[0]
    old_css = style.group(1)
    new_css = old_css + css
    policies = _Policies()
    policies.feed(document)
    for raw, policy in policies.values:
        directives = {}
        for directive in policy.split(";"):
            fields = directive.strip().split()
            if fields:
                directives.setdefault(fields[0].lower(), fields[1:])
        if not any(name in directives for name in ("style-src-elem", "style-src", "default-src")):
            continue
        sources = directives.get("style-src-elem", directives.get("style-src", directives.get("default-src", [])))
        old_hash = _css_hash(old_css)
        if f"'{old_hash}'" in sources:
            updated = re.sub(
                r"(?:^|(?<=;))\s*style-src(?:-elem)?\s+[^;]*",
                lambda match: match.group(0).replace(old_hash, _css_hash(new_css)),
                policy, flags=re.IGNORECASE,
            )
            if updated == policy:
                raise ValueError("The gallery needs an explicit style-src policy; it was preserved.")
            updated_tag, count = re.subn(
                r"(\bcontent\s*=\s*)([\"'])(.*?)\2",
                lambda match: match.group(1) + match.group(2) + html.escape(updated, quote=True) + match.group(2),
                raw, count=1, flags=re.IGNORECASE | re.DOTALL,
            )
            if count != 1:
                raise ValueError("Could not update the stylesheet CSP hash; gallery was preserved.")
            document = document.replace(raw, updated_tag, 1)
        elif "'unsafe-inline'" not in sources or any(
            source.startswith(("'sha", "'nonce-")) for source in sources
        ):
            raise ValueError("The existing CSP does not authorize the stylesheet; gallery was preserved.")
    # A CSP replacement can change offsets; locate the unchanged stylesheet again.
    style = re.search(r"<style(?:\s[^>]*)?>(.*?)</style\s*>", document, re.IGNORECASE | re.DOTALL)
    if style is None or style.group(1) != old_css:
        raise ValueError("Could not update the session stylesheet; gallery was preserved.")
    document = document[:style.start(1)] + new_css + document[style.end(1):]
    return document


def _results_root(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("Use an absolute local results directory.")
    root = path.resolve(strict=True)
    if not root.is_dir() or str(root).startswith(("\\\\", "//")):
        raise ValueError("The results root must be an existing local directory, not a network share.")
    return root


def session_folder(uri: str, results_dir: Path) -> Path:
    match = SESSION_URI.fullmatch(uri)
    if match is None:
        raise ValueError("Only clipfarm://open-session/<timestamped-session-name> links are supported.")
    root = _results_root(results_dir)
    candidate = root / match.group(1)
    folder = candidate.resolve(strict=True)
    if folder != candidate or folder.parent != root or not folder.is_dir():
        raise ValueError("The session must be a direct results child, without a redirected path.")
    if not (folder / "index.html").is_file():
        raise ValueError("The session has no index.html gallery.")
    return folder


def open_session(uri: str, results_dir: Path) -> Path:
    if sys.platform != "win32":
        raise ValueError("Open in Explorer requires Windows.")
    folder = session_folder(uri, results_dir)
    os.startfile(str(folder), "explore")
    return folder


def install_protocol(results_dir: Path) -> str:
    if sys.platform != "win32":
        raise ValueError("The Explorer integration can only be installed on Windows.")
    import winreg

    root = _results_root(results_dir)
    executable = Path(sys.executable).with_name("pythonw.exe")
    if not executable.is_file():
        raise ValueError("The current Python installation has no pythonw.exe for the Windows handler.")
    try:
        existing = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "clipfarm")
    except FileNotFoundError:
        existing = None
    if existing is not None:
        with existing:
            try:
                owner = winreg.QueryValueEx(existing, "ClipFarmOwner")[0]
            except FileNotFoundError:
                owner = None
        if owner != PROTOCOL_OWNER:
            raise ValueError("The clipfarm: protocol belongs to another application; it was not changed.")
    command = subprocess.list2cmdline([
        str(executable), "-m", "clipfarm", "explorer", "open",
        "--results-dir", str(root), "--from-browser", "--",
    ]) + ' "%1"'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, PROTOCOL_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:ClipFarm session folder")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        winreg.SetValueEx(key, "ClipFarmOwner", 0, winreg.REG_SZ, PROTOCOL_OWNER)
        winreg.SetValueEx(key, "ClipFarmResultsRoot", 0, winreg.REG_SZ, str(root))
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, PROTOCOL_KEY + r"\shell\open\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
    return command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy Windows Explorer protocol; current galleries use browser folder links")
    commands = parser.add_subparsers(dest="command", required=True)
    install = commands.add_parser("install", help="Register the per-user clipfarm: session-folder handler")
    install.add_argument("--results-dir", type=Path, required=True, help="Absolute local results root")
    opening = commands.add_parser("open", help="Open one validated session link in Windows File Explorer")
    opening.add_argument("--results-dir", type=Path, required=True)
    opening.add_argument("--from-browser", action="store_true", help=argparse.SUPPRESS)
    opening.add_argument("uri")
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            install_protocol(args.results_dir)
            print(f"Registered the current user's clipfarm: handler for {args.results_dir}.")
        else:
            folder = open_session(args.uri, args.results_dir)
            if not args.from_browser:
                print(f"Requested Windows File Explorer for {folder}.")
    except (OSError, ValueError) as exc:
        message = f"ClipFarm could not open or configure Explorer: {exc}"
        if getattr(args, "from_browser", False) and sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, "ClipFarm - Explorer", 0x10)
        if sys.stderr is not None:
            print(message, file=sys.stderr)
        return 1
    return 0

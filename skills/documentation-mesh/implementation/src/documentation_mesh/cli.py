from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import VERSION
from .core import build, load_json, runtime_root, validate_index


def copy_template(name: str, target: Path) -> None:
    source = runtime_root() / "templates" / name
    if not source.is_file():
        raise RuntimeError(f"Bundled template is missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def initialize(source: Path, workspace: Path, force: bool = False) -> Path:
    source = source.resolve()
    workspace = workspace.resolve()
    if not source.is_dir():
        raise RuntimeError(f"Source directory does not exist: {source}")
    markdown_count = sum(1 for path in source.rglob("*") if path.is_file() and path.suffix.lower() in {".md", ".mdx"})
    if not markdown_count:
        raise RuntimeError(f"No Markdown or MDX files found under {source}")
    if workspace == source or workspace.is_relative_to(source):
        raise RuntimeError("Generated workspace must remain outside the source collection")
    config_path = workspace / "config.json"
    if config_path.exists() and not force:
        return config_path
    workspace.mkdir(parents=True, exist_ok=True)
    template = load_json(runtime_root() / "templates" / "config.default.json")
    template["sourceRoots"] = [str(source)]
    template["workspaceLocation"] = str(workspace)
    template["runtimeVersion"] = VERSION
    template["pluginVersion"] = VERSION
    config_path.write_text(json.dumps(template, indent=2), encoding="utf-8")
    copy_template("workspace-readme.md", workspace / "README.md")
    return config_path


def open_report(path: Path) -> None:
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"Report does not exist: {path}")
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="documentation-mesh", description="Build an offline documentation intelligence mesh.")
    value.add_argument("--version", action="version", version=f"documentation-mesh {VERSION}")
    subcommands = value.add_subparsers(dest="command", required=True)
    init = subcommands.add_parser("init", help="Initialize a generated workspace")
    init.add_argument("--source", type=Path, required=True)
    init.add_argument("--workspace", type=Path, required=True)
    init.add_argument("--force", action="store_true")
    build_parser = subcommands.add_parser("build", help="Build or refresh a workspace")
    build_parser.add_argument("--config", type=Path, required=True)
    build_parser.add_argument("--validate", action="store_true")
    build_parser.add_argument("--open", action="store_true")
    validate_parser = subcommands.add_parser("validate", help="Validate a generated index")
    validate_parser.add_argument("--index", type=Path, required=True)
    open_parser = subcommands.add_parser("open", help="Open an offline report")
    open_parser.add_argument("--html", type=Path, required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "init":
            config_path = initialize(arguments.source, arguments.workspace, arguments.force)
            print(json.dumps({"config": str(config_path), "workspace": str(config_path.parent)}, indent=2))
        elif arguments.command == "build":
            index, paths = build(arguments.config.resolve(), validate=arguments.validate)
            print(json.dumps({"statistics": index["statistics"], "outputs": {key: str(value) for key, value in paths.items()}}, indent=2))
            if arguments.open:
                open_report(paths["html"])
        elif arguments.command == "validate":
            index = load_json(arguments.index.resolve())
            validate_index(index)
            print(json.dumps({"valid": True, "index": str(arguments.index.resolve())}, indent=2))
        elif arguments.command == "open":
            open_report(arguments.html)
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(f"documentation-mesh: {error}", file=sys.stderr)
        return 1

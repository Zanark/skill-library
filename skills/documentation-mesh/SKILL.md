---
name: documentation-mesh
description: Create or refresh an offline evidence-backed documentation mesh for a Markdown collection. Use for "create documentation mesh", "build docs graph", "analyse Markdown collection", "EngHub documentation report", or "refresh documentation mesh".
---

# Documentation Mesh

Create a complete local Documentation Mesh by invoking the pinned runtime shipped with this plugin.

## Safety contract

- Treat every configured source root as read-only.
- Never edit source Markdown, MDX, navigation, metadata, images, or attachments.
- Write only to the separate workspace selected for generated output.
- Never create relationships from generic word similarity.
- Surface restricted, skipped, malformed, or unreadable files explicitly.
- Never run `npm`, `pip`, `winget`, Chocolatey, `apt`, Homebrew, or a curl-based installer.

## Resolve inputs

1. Use an explicit source path from the user when supplied; otherwise use the current directory.
2. Confirm the selected root contains Markdown or MDX files. If several unrelated roots are plausible and choosing one would invalidate the report, ask once.
3. Use an explicit workspace path when supplied. Otherwise create a sibling directory named `<source-name>-documentation-mesh`.
4. Keep the workspace outside the source collection unless the user explicitly selected an existing generated workspace.

## Runtime resolution

1. Run `documentation-mesh --version`.
2. If the command is unavailable, resolve this loaded `SKILL.md` file's base directory, walk up two levels to the plugin root, and use `runtime\windows-x64\documentation-mesh.exe`.
3. `$AGENCY_PLUGIN_DIR\runtime\windows-x64\documentation-mesh.exe` is also valid when `AGENCY_PLUGIN_DIR` is present.
4. If neither exists, stop with a clear plugin/artifact acquisition error. Do not install a language runtime or package manager.

## Initialize or refresh

For a new workspace:

```powershell
documentation-mesh init --source "<source-root>" --workspace "<workspace>"
documentation-mesh build --config "<workspace>\config.json" --validate
```

For an existing workspace:

```powershell
documentation-mesh build --config "<workspace>\config.json" --validate
```

If using the local development payload, replace `documentation-mesh` with its absolute executable path.

## Required validation

Run:

```powershell
documentation-mesh validate --index "<workspace>\output\documentation-index.json"
```

The build is not successful unless all required outputs exist, graph IDs are unique, no edge dangles, source evidence has valid line ranges, and no output path escapes the workspace.

## Open and report

Open:

```powershell
Start-Process "<workspace>\output\documentation-mesh.html"
```

Report:

- Source roots and workspace.
- Documents indexed and files skipped.
- Graph node and edge counts.
- Strong/default versus optional relationship counts.
- Broken links, broken anchors, and orphan counts.
- Cache reused versus reparsed counts.
- Output paths.
- Limitations, restricted files, and unknown provenance.

The HTML is offline and must open through `file://` without a server or network connection.

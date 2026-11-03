# Documentation Mesh Agency Plugin

Documentation Mesh is a Copilot-only Agency plugin that builds a reusable, read-only intelligence layer over Markdown and MDX collections. It generates an offline searchable catalogue, evidence-backed force graph, documentation-health analysis, Git timeline, provenance search, deterministic JSON index, compact startup digest, and incremental cache.

## Version and support

- Plugin/runtime version: `0.1.0`
- Engine: GitHub Copilot through Agency
- Platform: Windows x64
- License: MIT
- Source collections are read-only.
- Generated workspaces must remain outside source roots.

Linux and macOS payloads are not included in this release. The Python source remains the portable development and behavioral-reference implementation. The distributed runtime is a dependency-free .NET console application published as a Windows x64 self-contained single-file executable.

## Installation

Agency itself is a host prerequisite and is not bundled.

### Ephemeral local plugin

Extract the ZIP first; the ZIP is not directly loadable.

```powershell
agency copilot --plugin local:C:\path\to\documentation-mesh-plugin
```

### Persistent local plugin

```powershell
agency plugin install local:C:\path\to\documentation-mesh-plugin --engine copilot
agency copilot
```

### Marketplace

After marketplace publication:

```powershell
agency plugin install market:documentation-mesh@<marketplace> --engine copilot
agency copilot
```

Then ask:

```text
Use the documentation-mesh skill and create a documentation mesh report for this directory.
```

Trigger phrases also include:

- `create documentation mesh`
- `build docs graph`
- `analyse Markdown collection`
- `EngHub documentation report`
- `refresh documentation mesh`

## Runtime delivery

Local development and the distributable ZIP include:

```text
runtime\windows-x64\documentation-mesh.exe
```

End users do not install Python, npm packages, graph libraries, or build tools.

`packaging\agency.artifact.template.json` contains the pinned Universal Package declaration for marketplace publication. It is deliberately not active in `agency.json` because no authorized feed was provided and a fake feed would break local plugin loading. Before marketplace publication, replace the feed placeholders, publish the exact checked payload, and copy the pinned `artifacts` block into `agency.json`.

Agency artifact downloads still require Agency, a supported OS, access to the plugin and artifact source, and authentication when the pinned package is not already cached. Artifact support is currently a local CLI capability.

## Consumer workflow

Initialize a new generated workspace:

```powershell
documentation-mesh init `
  --source "C:\path\to\markdown-collection" `
  --workspace "C:\path\to\generated-documentation-mesh"

documentation-mesh build `
  --config "C:\path\to\generated-documentation-mesh\config.json" `
  --validate
```

Refresh:

```powershell
documentation-mesh build `
  --config "C:\path\to\generated-documentation-mesh\config.json" `
  --validate
```

Validate independently:

```powershell
documentation-mesh validate `
  --index "C:\path\to\generated-documentation-mesh\output\documentation-index.json"
```

Open:

```powershell
Start-Process "C:\path\to\generated-documentation-mesh\output\documentation-mesh.html"
```

## Generated workspace

```text
workspace\
  config.json
  README.md
  output\
    documentation-mesh.html
    documentation-index.json
    DOCUMENTATION-MESH.md
    build-cache.json
```

The JSON index is the source of truth. The Markdown digest is intentionally compact and suitable for future Agency/Copilot session hydration.

## Architecture

1. **Discovery** resolves configured roots, applies include/exclude globs, rejects path escape, and records skipped files.
2. **Incremental parser** reuses unchanged cached documents by canonical path, size, and modification timestamp.
3. **Markdown analysis** extracts frontmatter, headings, anchors, Markdown/reference/HTML/wiki links, images, Mermaid fences, commands, code paths, work items, PRs, and incidents. Links inside code fences are excluded.
4. **Relationship builder** emits strong explicit document links, structural DocFX TOC membership, and exact referenced entities. Generic word similarity never creates a default edge.
5. **Git provenance** reads repository history once per source root to derive creation, update, contributors, commits, and rename evidence where available.
6. **Health analysis** detects broken targets and anchors, orphans, missing ownership, missing connectivity, malformed syntax, exact duplicates, and conservative near duplicates.
7. **Output publisher** validates IDs, evidence ranges, relationship classes, confidence levels, and dangling edges before atomically replacing outputs.
8. **Offline dashboard** embeds pinned force-graph/D3 assets and escaped JSON. It uses no CDN, server, external font, or network API.

## Relationship evidence policy

Default edges require persisted high-confidence evidence:

- Direct internal Markdown, reference-style, HTML, or wiki link.
- Explicit see-also, prerequisite, next-step, replacement, or deprecation link context.

Structural edges are high confidence but hidden from the core graph:

- DocFX/YAML navigation section containment.
- TOC membership.

Expanded entity edges require exact persisted references to code paths, commands, work items, PRs, or incidents.

Every edge contains:

- Stable source, target, and edge IDs.
- Relationship type and class.
- Confidence.
- Human-readable reason.
- Source file, line range, and concise excerpt.
- Directionality.
- Extraction method.
- Default-visibility decision.
- Caveat where applicable.

Weak and incidental semantic similarity is not generated by version `0.1.0`.

## Date provenance

Dates use:

1. First and last Git commits when Git history is available.
2. Filesystem modification time as a clearly labelled low-confidence fallback.
3. Unknown dates appear last in timeline animation.

No creation date is invented.

## Dashboard

The dashboard opens directly through `file://` and contains:

- **Catalogue:** search, family/status/owner filters, orphan/broken/diagram/code filters, collapsible evidence cards.
- **Knowledge graph:** live Canvas force simulation, pan, zoom, fit, drag, pin, unpin, family anchors, local depth, detail/evidence/status controls, physics sliders, edge evidence inspector, and one-shot timeline animation.
- **Health:** evidence-backed issue filters and links back to document cards.
- **Timeline:** Git-backed creation/update chronology.
- **Provenance:** path, title, author, and commit search.

## Configuration

`config.json` supports:

- Source roots.
- Include/exclude globs.
- Generated and archived globs.
- Output/cache paths.
- Git and optional session-provenance toggles.
- History and freshness thresholds.
- Optional entity-node limit.
- Default evidence/detail levels.
- Browser executable override.
- Workspace and plugin/runtime versions.
- Workspace initialization policy.

See `schemas\config.schema.json`.

## Security and privacy

- Source files are never modified.
- External URLs are parsed but never followed.
- Markdown code is never executed.
- Secret-like assignments are redacted from evidence excerpts.
- Embedded JSON escapes HTML/script terminators and Unicode line separators.
- Complete source bodies and complete local transcripts are not embedded.
- Outputs remain local and are never published automatically.

## Development

Development prerequisites:

```powershell
npm ci --ignore-scripts --no-audit --no-fund
```

The Python reference implementation uses only the standard library. Run its unit and plugin-contract tests:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests\unit
python -m unittest discover -s tests\plugin_contract
```

Build the self-contained executable:

```powershell
.\packaging\build-runtime.ps1
```

This requires the .NET 8 SDK. The script deletes any existing blocked Python-built executable before publishing `src\DocumentationMesh.Runtime` as a self-contained, single-file `win-x64` application. End users do not need .NET installed.

Run the packaged consumer contract, including a validated cache refresh:

```powershell
.\tests\consumer-contract.ps1
```

Create the versioned ZIP and checksums:

```powershell
.\packaging\create-zip.ps1
```

Browser smoke test:

```powershell
$env:DOCUMENTATION_MESH_HTML = "C:\path\to\workspace\output\documentation-mesh.html"
npm run test:browser
```

## Cache behavior

The cache stores parsed document records with canonical path, size, and modification timestamp. Unchanged inputs are reused; changed inputs are reparsed. Output ordering is deterministic by canonical ID/path. Git history and aggregate health are recomputed so cross-document changes cannot leave stale relationships.

## Known limitations

- Windows x64 is the only packaged platform in `0.1.0`.
- Marketplace artifact publication is blocked pending an authorized feed; the local bundled payload is complete.
- Session-state artifact provenance is represented in the schema/UI but is disabled in this version; Git provenance is implemented.
- YAML frontmatter and TOC parsing intentionally support common documentation shapes rather than the complete YAML specification.
- Mermaid validation detects malformed fences but does not execute Mermaid.
- Near-duplicate detection uses conservative SimHash and may miss heavily rewritten duplicates.
- External-link availability is not checked because generation never follows external URLs.

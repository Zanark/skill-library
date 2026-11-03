# Documentation Mesh Workspace

This workspace contains generated, local-only Documentation Mesh outputs for a read-only Markdown collection.

## Commands

```powershell
documentation-mesh build --config .\config.json --validate
documentation-mesh validate --index .\output\documentation-index.json
Start-Process .\output\documentation-mesh.html
```

## Outputs

- `output\documentation-mesh.html`
- `output\documentation-index.json`
- `output\DOCUMENTATION-MESH.md`
- `output\build-cache.json`

Do not place authored source documentation in this workspace.

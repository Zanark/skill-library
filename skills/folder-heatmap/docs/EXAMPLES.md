# Examples and edge cases

These are illustrative local commands, not evidence that these paths exist on
another machine. Follow the actual scope and `SKILL.md` before scanning.

## Generate and refresh

```powershell
python "C:\devdesk\homedesk\skill-library\skills\folder-heatmap\scripts\folder_heatmap.py" --root "C:\devdesk\homedesk" --output "$env:TEMP\homedesk-space-review" --open
```

After moving files, repeat the same command. Open or reload that exact output,
not an old screenshot. A browser refresh alone does not run Python.

## Current directory without opening a browser

```powershell
python "C:\devdesk\homedesk\skill-library\skills\folder-heatmap\scripts\folder_heatmap.py"
```

The command prints the newly generated absolute output path. Its default
temporary output must not fall under the scanned root.

## Useful checks

- A zero-byte folder appears in the table even without a visible heatmap tile.
- An unreadable child appears in errors; totals exclude unreadable content.
- A directory junction is listed as skipped, never traversed.
- A 1 MiB file sorts above a 900 KiB file by Size, regardless of label text.
- All-folder percent sorting uses each row's own parent, not the current view.
- Sorting by file path does not expand the retained top-20 direct-file list.
- Search results are sorted before the 1,000-row cap.

## Anti-examples

Do not use this report to claim exact freed disk space, identify duplicate
content, approve deletion of `.git` or dependency folders, or bypass a path
denied by organizational policy. Do not write reports under the scanned tree:
the CLI rejects that placement to avoid self-counting refreshes.

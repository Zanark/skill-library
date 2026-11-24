# Folder heatmap

A reusable, local-first version of the directory-space review tool: an
interactive treemap, sortable tables, folder navigation, search and largest
direct files, with JSON and CSV exports. Scanning uses only Python's standard
library and reads file metadata, not content.

**Contract:** [SKILL.md](SKILL.md). **Code:**
[scripts\folder_heatmap.py](scripts/folder_heatmap.py).

## Run

Requires Python 3.10+ and a modern browser. No package installation or server.
The installed personal skill references this checkout, like the library's
repository-backed documentation manual; retain the checkout.

```powershell
python "C:\devdesk\homedesk\skill-library\skills\folder-heatmap\scripts\folder_heatmap.py" --root "C:\devdesk\homedesk" --output "$env:TEMP\homedesk-space-review" --open
```

Omit `--root` to scan the command's current directory. Omit `--output` for a new
timestamped directory under the system temporary directory's `folder-heatmap`
folder. Explicit output must be outside the scan root. If scanning a location
that includes the temporary directory, specify another output location.
Omit `--open` for generation only.

Repeat the same command after moving files; it rescans and replaces only the
three named reports. Refresh the browser tab if it still displays the old page.

## Review

Click folder tiles or table names to drill down; Home and Up navigate.
Both tables start with Size descending. A new header's first click sorts
ascending, and its next click descending. Clicking the initially active Size
header once switches it to ascending. Direction labels and accessible
`aria-sort` expose the active state. Numeric sorting uses raw bytes/counts/
percentages, not unit strings. Sort choice survives filtering and navigation
within that loaded page.

Folder search can target the current folder or every scanned folder. Sorting
happens before the 1,000-row display limit. All-folder rows overlap because
parent totals include descendants; never add them together.
The direct-file table contains only the 20 largest files directly in the
selected folder, not every file in its subtree.

## Limits and safety

Sizes are logical file bytes (GiB = 1,073,741,824 bytes), not allocated space or
guaranteed savings. Hard-linked paths count separately. Hidden folders and
builds count; links, junctions and other reparse points do not. Access errors
produce a visibly partial report and exit 2. Invalid inputs and execution or
browser failures exit 1. This is a non-atomic snapshot; concurrent file changes
can affect totals. Nothing is deleted, uploaded, installed or classified as
safe to delete by the generator. HTML has no remote dependencies or requests.

Outputs include absolute folder/file names, so keep reports out of public
repositories and uploads unless separately authorized. An organization-denied
path remains excluded: this script is not an alternative access route.

## Contents

- [Architecture](docs/ARCHITECTURE.md)
- [Workflow](docs/WORKFLOW.md)
- [CLI and output reference](docs/REFERENCE.md)
- [Examples and edge cases](docs/EXAMPLES.md)
- [Operations and testing](docs/OPERATIONS-AND-TESTING.md)

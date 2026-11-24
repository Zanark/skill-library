# CLI and output reference

The normative contract is `SKILL.md`; the CLI is implemented by `main` in
`scripts\folder_heatmap.py`.

| Argument | Behavior |
|---|---|
| `--root PATH` | Scan directory; defaults to the actual command cwd |
| `--output PATH` | External report directory; defaults to a unique timestamp under the system temporary directory |
| `--open` | Open completed HTML using the system default browser |
| `--help` | Show local usage without scanning |

Exit codes: **0** no recorded scan errors; **2** partial scan with explicit
read errors; **1** invalid input or execution/output/browser failure.
Skipped links alone do not mark a scan partial, since they are deliberately
excluded. Root links/reparse points are rejected.

| File | Contents |
|---|---|
| `index.html` | Offline interactive treemap and both sortable tables |
| `snapshot.json` | Root, start/end timestamps, flat directory nodes, errors and skipped paths |
| `folder-sizes.csv` | All directory paths, total bytes/GiB, recursive file counts and direct bytes/counts |

Each node has `name`, `parent` (-1 for root), `children` (node IDs), `size`
(recursive bytes), `files` (recursive count), `direct`, `directFiles` and
`largest` (up to 20 `[bytes, name]` pairs). All bytes are logical sizes.
The exported CSV is raw path data; import it as text rather than enabling
spreadsheet formulas for untrusted filenames.

The JSON summary on stdout gives `report`, `status`, bytes/GiB, folder/file
counts, error/skip counts, largest immediate folders and largest root files.
Progress messages may precede the summary on long scans.

Header behavior: default Size descending; first click on an inactive column
ascending; repeated clicks toggle. The initially descending Size column's first
click is ascending. The folder table supports name, bytes, percent of parent
and count; direct files support path/name and bytes.

# Operations and testing

`SKILL.md` is normative. Maintain its contract, the generator, supporting docs
and source inventory hash together.

## Verification commands

From `C:\devdesk\homedesk\skill-library`:

```powershell
python -m unittest discover -s tests -p "test_folder_heatmap*.py"
.\scripts\Validate-SkillLibrary.ps1
python .\scripts\verify_portable_payload.py --build
python .\scripts\verify_portable_payload.py
```

The scanner and exports need only Python. Browser tests use Playwright and
an installed Edge browser when available; missing optional tools skip browser
qualification rather than claiming it passed. No runtime package is needed
to generate or use a report.

Focused cases cover recursive/direct reconciliation, hidden/empty folders,
top-20 retention, link exclusions, partial error reporting, invalid/root/output
boundaries, embedded filename escaping and exported paths. Browser cases cover
every header in both directions, default descending, numeric unit differences,
parent-relative percentages, filtering, navigation, keyboard interaction,
row-limit ordering and mobile overflow. Fixtures contain only synthetic names.

## Installation

For this checkout, install the entry with the documented Copilot CLI command:

```powershell
copilot skill add "C:\devdesk\homedesk\skill-library\skills\folder-heatmap\SKILL.md"
copilot skill list --json
```

This materializes the prompt under the user's personal skill directory; bundled
code stays in the referenced checkout. The library's multi-skill installer also
installs the inventory entry and rebases its checkout path. Do not run that
whole installer merely to install this one skill.
Discovery in the current already-running host is not guaranteed by a successful
disk installation; verify CLI listing and use a new host if it is not exposed.

## Maintenance and failures

Read-only scan coverage does not justify elevation. Review error details and
keep incomplete totals explicit. Output failures are nonzero and can leave
partial files. Browser-opening failure preserves generated artifacts but is
still reported as failure. A busy filesystem remains non-atomic.

After intentional source changes, update the exact `SKILL.md` SHA-256 entry
in `source-inventory.json` and regenerate the public payload catalogue with
the existing verifier. Do not add generated local reports to the public payload.

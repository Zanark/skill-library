# Workflow

Follow `SKILL.md` Execution and Report contract as the source of authority.

1. Resolve the requested directory and applicable access restrictions.
2. Choose output outside that directory. Use host session artifacts when known;
   never invent a session identity or write reports into source by default.
3. Run the bundled Python generator; only add `--open` when opening is desired.
4. Inspect the printed status and error count. Exit 2 still produces a report,
   but means partial coverage. Read errors in the HTML or JSON.
5. Review the treemap, descend into folders and use clickable headers for
   ascending/descending comparisons. Percent of parent is relative to each
   result's own parent in all-folder search.
6. Deliver the complete absolute report path and actual coverage. A measured
   dependency/cache/build folder is not automatically disposable.
7. For a refresh, repeat the scan against the same root/output, then reload
   the page. A changed scan is not an atomic filesystem comparison.

Only the selected output directory receives generator writes: `index.html`,
`snapshot.json` and `folder-sizes.csv`. Existing versions of those three files
are replaced; unrelated files are not cleaned up. A failed write is reported
explicitly and may leave an incomplete output set; do not present it as complete.
No scanner action grants deletion, elevation, publishing or upload permission.

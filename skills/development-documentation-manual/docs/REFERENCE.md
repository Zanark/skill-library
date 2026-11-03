# Reference: routes, schemas and vocabulary

## Mode routing

| Request/artifact | Read manual section | Required evidence emphasis | Dedicated procedure |
|---|---|---|---|
| New workstream/planning package | 2-4 | Eight fields, stable IDs, actual dependencies | Local TODO contract |
| Bug/feature implementation | 4-6 | Real affected path plus focused tests | Repository build/test commands |
| Development journal | 5 | Causal narrative, dated actual events | Local ledger rules |
| Architecture/engineering book | 6 | Source-backed ownership and behavior | Local documentation builder |
| Beginner curriculum | 7 | Prerequisites, distinct examples, demonstrated learning | Teaching contract |
| Exhaustive source explanation | 8 | Explicit scope, full range coverage and reviewed meaning | Source-atlas tooling |
| PDF/HTML edition | 9 | Native PDF and actual layout/navigation | Edition-specific pipeline |
| GUI visual reference | 10 | Surface/theme/scroll coverage and honest fixtures | Capture/reader tools |
| Image/art selection | 10 | Bounded inspected items and persisted decisions | Strictest local view budget |
| Retrospective documentary | 11 | Frozen corpus, source IDs, omissions and historical truth | Documentary contract |
| Coding/system-design clips | 11 | Full source understanding, time maps, output ASR/motion | clipfarm-leetcode |
| Audio companion | 7, 11 | Frozen textbook identity and actual chapter ranges | Companion builder |
| Music/3D/design ports | 11 | Native source, derivation, version and review | Project production runbook |
| Offline report | 12 | Collection scope/time, partial/failure states | Authorized collector/report workflow |
| Investigation/runbook | 12 | Observations, hypotheses, roles and rollback boundary | Authorized operational workflow |
| Session resumption | 13 | Owned persisted state and freshness | context-offload/context-mesh |
| Documentation graph | 13 | Index scope, confidence and source evidence | documentation-mesh |
| Release/migration | 14 | Exact allowlist, hashes, rights and separate approvals | Existing packaging tools |
| Enrich this manual | 15 | New source-backed technique or counterexample | EVOLUTION.md |

## Status is a dimension, not one universal boolean

| Dimension | Example states |
|---|---|
| Workstream execution | NOT_STARTED, IN_PROGRESS, BLOCKED, DONE |
| Procedure definition | Draft, reviewed, complete, superseded |
| Technical result | Not run, failed, partially verified, verified |
| Environment | Synthetic fixture, local, target-qualified, unknown |
| Human decision | Not requested, pending, approved, rejected |
| Artifact lifecycle | Editable, generated preview, frozen edition, packaged |
| Remote delivery | Local only, submitted, running, completed, verified target |

Use the local vocabulary rather than retrofitting these words into an existing
parser. Do preserve the distinction between the dimensions.

## Evidence verbs

| Verb | Minimum honest meaning |
|---|---|
| Discovered | Found a path/metadata entry |
| Read | Examined the specified text/range |
| Inspected | Observed the actual item at the stated level |
| Generated | Tool produced an actual output artifact |
| Validated | Named checks ran against identified inputs/output |
| Verified | Defined outcome was supported by relevant observation |
| Approved | Authorized human explicitly accepted a specified revision |
| Published | Identified content became available at the intended remote target |

Always qualify the object and scope. "Validated" without naming the gate can
hide that only JSON parsing was checked.

## Recommended source receipt fields

`Source ID`, `project label`, `source role`, `repository-relative path`,
`reviewed range/section`, `revision or hash if needed`, `review date`,
`technique supported`, `authority class`, `privacy/rights boundary`,
`limitations`, `supersedes/superseded by`.

Private receipts may retain full local paths where appropriate. Public receipts
must not expose private paths, identifiers or source bodies unnecessarily.
No placeholder receipt constitutes review evidence.

## Minimal change-impact receipt

| Changed source | Dependent document/artifact | Required update | Evidence |
|---|---|---|---|
| An actual API symbol | Usage guide/example | Correct invocation and failure behavior | Source and focused test |
| An actual widget | GUI surface inventory | New state/theme/scroll capture | Native fixture and image review |
| A frozen chapter | Companion page map | New edition concordance | Actual rendered page ranges |

Do not copy these illustrative rows as completed work.

## Common anti-patterns

- One flat TODO checklist replacing the index/workstream/ledger distinction.
- A directory count presented as exhaustive semantic review.
- Test logs copied without source revision or actual execution.
- A source hash refreshed while its explanation remains stale.
- Decorative figures with undefined arrows or unreadable labels.
- Hundreds of screenshots with no surface coverage map.
- A "refresh" button that implies new collection but reloads old embedded data.
- A design specification described as an implemented pipeline.
- A generated draft described as a sent message.
- A frozen edition silently overwritten by a prettier later layout.
- Private architecture made "public" merely by renaming entities.
- Per-project page budgets/view limits generalized into universal mandates.
- A master procedure's DONE state reused as proof that a new run passed.

## Terms

**Canonical source:** the editable authority from which a derivative is built.
**Edition:** a specific frozen reading artifact and its source/manifest identity.
**Concordance:** mapping of stable IDs between editions, page ranges or companions.
**Coverage:** accounting for a declared set; not automatically quality.
**Qualification:** observation in the actual target environment.
**Provenance:** evidence of origin/derivation; stronger than a filename association.
**Receipt:** an attributable record of an actual input/action/output/check.
**Worktree:** a distinct checkout that may share repository history; not a new
product simply because Context Mesh registers it as another base.

# Source register and coverage limits

First edition reviewed on **2026-11-03**. Paths in the tables are relative to the
named source project, not relative links into this public repository. They are
discovery pointers, not redistributed source bodies. Availability and rights
must be checked by the next reader.

The author read these canonical instructions/contracts and representative
documents during the audit. Ranges identify bounded reads where applicable.
Full-file entries mean the document text was read, not that every referenced
implementation, output or historical claim was independently revalidated.

## Public-safe project references

| ID | Project | Source and reviewed scope | Supports |
|---|---|---|---|
| TR-01 | TrickRoom | `docs\06-development-workflow.md`, full | TODO schema, implementation loop, journals |
| TR-02 | TrickRoom | `JOURNAL.md`, lines 1-50 | Actual diagnostic narrative; GUI path versus direct method |
| TR-03 | TrickRoom | `docs\book\README.md`, full | AST citations, print pipeline and edition review |
| CF-01 | ClipFarm | `TODO\01_PRODUCT_DECISIONS.todo`, lines 1-90 | Bounded decisions, evidence and approvals |
| CF-02 | ClipFarm | `TODO\08_DEVELOPMENT_LEDGER.todo`, lines 1-100 | Development history and handoff distinctions |
| CF-03 | ClipFarm | `TODO\WORKFLOWS\06_ANIMATED_EXPLAINERS.todo`, lines 1-120; Skill Library `skills\clipfarm-leetcode\SKILL.md`, lines 230-390 | Procedure versus execution; reviewed production |
| PF-01 | phantom-fudge | `docs\DEVELOPMENT-WORKFLOW.md`, full | Coupled code/TODO/documentation change loop |
| PF-02 | phantom-fudge | `docs\DOCUMENTATION-MAINTENANCE.md`, full | Change-to-document map and maintenance order |
| PF-03 | phantom-fudge | `docs\source-atlas\README.md`, full | Whole-source explanation and reviewed coverage |
| ET-01 | EntropyTag | `AGENTS.md`, full | Small-first scope and promotion gate |
| ET-02 | EntropyTag | `TODO\16_DOCUMENTATION_FOUNDATION.todo`, full | Planning package and documentation acceptance |
| ET-03 | EntropyTag | `docs\ledger\README.md`, full | Action/effect/reason/mechanism/evidence narrative |
| SC-01 | SpriteCanvas | `AGENTS.md`, full | Contributor workflow and local contracts |
| SC-02 | SpriteCanvas | `docs\README.md`, lines 1-125 | Handbook structure, source citations, fixtures and diagrams |
| KC-01 | KardboardCode-VTuber | `AGENTS.md`, full; `docs\README.md`, lines 1-120 | Local workflow, handbook and front-page boundaries |
| KC-02 | KardboardCode-VTuber | `docs\book\README.md`, full | Chapter discovery, ordered edition and PDF checks |
| KC-03 | KardboardCode-VTuber | `YTScript\README.md`, full | Timed production script and production package |
| KC-04 | KardboardCode-VTuber | `YTScript\DevelopmentJourney\README.md`, full | Frozen retrospective corpus and narrative/evidence audit |
| KC-05 | KardboardCode-VTuber | `TODO\23_COMPLETE_GUI_VISUAL_REFERENCE.todo`, full | Surface coverage, native screenshots and standalone reader |
| BB-01 | B-Bakery | `AGENTS.md`, complete instruction text | Front-page, privacy and image-review boundaries |
| BB-02 | B-Bakery | `docs\image-review-workflow.md`, lines 1-150 | Bounded sheets, persisted item decisions and stop budget |
| BB-03 | B-Bakery | `README.md`, complete six-image front-page structure inspected during portfolio comparison | Explicit visual README exception |
| CH-01 | CareerHQ | `docs\AGENT_CONTRACT.md`, lines 1-150; `docs\OPERATION-SOURCES.md`, lines 1-135 | Attributable sources and operational boundaries; no personal records copied |
| KF-01 | Career Forensics skill in Skill Library | `skills\career-forensics\SKILL.md`, lines 45-130; protocol only, no private KB ingested | Append-only evidence, source deduplication, corrections/deltas and demonstrated recall |
| LA-01 | LinkedIn-EasyApply-Automaton | `docs\developer_guide.md`, lines 1-110 | Existing alternative project/tracking organization |
| DS-01 | DeepSeaFoam | `docs\PUBLISHING.md`, lines 1-100 | Packaging/publication separation |
| DS-02 | DeepSeaFoam | `docs\MAPPINGS.md`, lines 1-100 | Semantic roles, generated ports and compatibility limits |
| PW-01 | portfolioWebsiteGitHub | `README.md`, lines 1-150 | Preview/public build distinction, explicit branch-selected deployment and artifact provenance |
| PW-02 | portfolioWebsiteGitHub | `RESEARCH.md`, lines 1-130 | Research rationale, finding/applicability limits and dated amendments; historical source consultation not rerun by this audit |
| SL-01 | SubwooferLullabies | `docs\website.md`, lines 1-155 | Canonical versus site copies, production provenance |
| SW-01 | SongsWorkspace / Almost Us | `production\BLENDER-WORKFLOW.md`, lines 1-160 | Native 3D production, derivation, reproducibility limits |
| KL-01 | KnowledgeLedger | `CURRICULUM.md`, full | Teaching sequence and learning evidence |
| KL-02 | KnowledgeLedger / technical book base | `book\README.md`, full | Chaptered learning and rendering patterns; private technical detail not reproduced |
| KL-03 | KnowledgeLedger / platform book base | `book\README.md`, full | Engineering-book composition and pipeline; process only |
| SA-01 | ServiceAgnostic-KnowledgeLedger | `book\AUTHORING-CONTRACT.md`, full | Stable IDs, teaching budgets and source boundaries |
| SA-02 | ServiceAgnostic-KnowledgeLedger | `book\VISUAL-AND-PRODUCTION.md`, lines 1-155 | Design proposals and print/figure gates; explicitly design-only document |
| SA-03 | ServiceAgnostic-KnowledgeLedger | `book\PRODUCTION.md`, lines 1-125 | Later implemented local pipeline, previews and honest environment limits |
| SA-04 | ServiceAgnostic-KnowledgeLedger | `book\podcast-companion\AUTHORING.md`, full | Frozen-edition audio direction and chapter ranges |
| BM-01 | BookMaker | Private continuity `MEMORY.md`, lines 15-85; only generalized publishing procedure retained | Independent illustrated edition, native PDF and source/derivative boundaries |
| DM-01 | Documentation Mesh skill in Skill Library | `README.md`, full; `docs\REFERENCE.md`, lines 1-100 | Read-only documentation intelligence and evidence |
| CTX-01 | Installed context-offload skill | Governing skill read for hydration/offload; source referenced, not recopied | Owned four-file continuity, freshness and identity |
| CTX-02 | Context Mesh | Startup digest fully read; structured index and active metadata inspected | Portfolio/base discovery, graph provenance and write boundary |
| LIB-01 | Skill Library | Root `README.md`, `docs\PROVENANCE.md`, `docs\DOCUMENTATION-STANDARD.md`, `docs\MAINTENANCE-PLAYBOOK.md`, full | Registration, provenance and documentation policy |
| LIB-02 | Skill Library | `scripts\Validate-SkillLibrary.ps1`, `scripts\install_skill_library.py`, full | Required support docs, hashes, links and installed support-path rebasing |
| LIB-03 | Skill Library | `scripts\verify_portable_payload.py`, full; `docs\PORTABILITY.md`, lines 1-155; `tests\test_portability.py`, lines 1-290 | Portable checksum generation, no-overwrite behavior and state separation |
| OP-01 | Restricted operational/context desks, grouped | Workflow-related continuity excerpts across registered desks and prior comparison's relevant collector/report guidance | Generic read-only collection, report times, constraints, investigations and draft-versus-sent distinctions only |

## Subsequent tracking enrichment receipts

| ID | Source and reviewed scope | Authority and limits |
|---|---|---|
| GH-01 | Owner's explicit 2026-11-06 request in the BowserBoyAdvance working session: cross-repository TODO-to-issue descriptions, completion state, URL backlinks and Project membership; follow-up requests incorporation into this manual | User-directed workflow requirement, not evidence that a synchronizer exists; paraphrased process only, no raw transcript or credentials |
| GH-02 | Official GitHub PAT limitations, classic scopes, Projects API/Actions and CLI environment references listed in GITHUB-TRACKING.md; consulted 2026-11-06, plus installed Copilot environment help | Credential/API guidance at that date, not permanent platform guarantees; read-only access checks do not prove mutation success; no migration performed by this enrichment |
| GH-03 | Owner's explicit 2026-11-06 follow-up: include workflow-scope use in this manual and make credentials available by default across sessions without repeated assignment | User-directed local discovery and authorized workflow-maintenance requirement; not blanket deployment/dispatch permission or remote secret provisioning; no credential/account details retained |
| GH-04 | Official GitHub classic-scope reference and Microsoft Export-Clixml reference consulted 2026-11-06; current-user persistence mechanism exercised locally with secret-free read-back and GitHub access verification | Platform guidance and bounded local credential provisioning only; no claim that all existing parent processes inherited changes or any hosted runner received credentials |
| GH-05 | Owner's explicit 2026-11-06 follow-up selects a local gitignored .env in this manual's support folder, owner-entered plaintext token, cross-session access through the skill and exclusion from the public library; reviewed root .gitignore, validator, public/support packagers and installer boundaries | User-authorized local credential convention; file contents are never a documentation source. Implemented runner and exclusion gates require focused fixture checks; ignore rules cannot prevent forced/bypassed publication or other local readers |

## Concurrent-use enrichment receipt

| ID | Source and reviewed scope | Authority and limits |
|---|---|---|
| CU-01 | Owner's 2026-11-09 request to use desktop apps/websites during agent editing, followed by explicit approval of the proposed concurrent-use manual addition; reviewed manual 4.1-4.5 and 14.1-14.5, execution workflow, reference and operations gates | User-directed documentation contract. Lane/state/resource isolation, coexistence acceptance and promotion/recovery are adopted guidance, not observed implementation across projects. Process-only paraphrase; no private application data, runtime inventory or raw transcript retained. Compatible addition, no supersession of local authority or GitHub/credential rules. |

## Commit-cadence enrichment receipt

| ID | Source and reviewed scope | Authority and limits |
|---|---|---|
| CM-01 | Owner's explicit 2026-11-10 request for more frequent but substantial, non-spam commits across projects, always through Zanark using the already provisioned credential; reviewed manual 4.5, workflow and existing nonprinting credential runner | User-directed cross-project workflow requirement. Local author/committer attribution, API login and Git transport are distinct; documentation changes do not authorize unrelated commits, pushes or global authentication changes. No token, email or private source retained. |

## Original portfolio coverage accounting

The mesh had **33 entries**, not 33 independent products. The bounded structural
inventory found **1,077** text artifacts at the time of discovery; manual support
files written afterward are not part of that number.

| Entry group | Entries | Treatment |
|---|---:|---|
| Canonical hobby/application/content/library bases | 14 | Structural inventory and workflow continuity inspected; representative governing docs reviewed, sources above |
| Dedicated pedagogy/publishing bases | 5 | Curriculum/book contracts and continuity reviewed; only public-safe process retained |
| General assistant/runner/operational/continuity-only desks | 11 | Structural inventory and relevant workflow continuity excerpts; not a product/code audit |
| Additional application/library worktrees | 2 | Inventoried; treated as related copies, not new techniques merely because separately registered |
| Embedded media-production provenance origin | 1 | Recognized as historical replica; not a separate canonical product |
| Total | 33 | No claim of exhaustive semantic review |

The private inventory preserves actual local base mappings, discovered paths,
hashes and headings. It is intentionally not copied into the public repository.
The coverage grouping does not imply that private bases are public sources.

## Explicit omissions and limitations

- The bounded walk excluded dependency trees, caches, raw/private media,
  archived social conversations and generated-output-heavy areas. It was not a
  filesystem-wide census.
- Not every one of the 1,077 files was semantically read. Representative canonical
  contracts establish documentation modes, not paragraph-by-paragraph completeness.
- Referenced runtime code, old screenshots, historical PDFs, audio and videos were
  not re-executed/reviewed merely because their instructions were read.
- Some source documentation records historical validation. This manual does not
  convert those records into new test results.
- Worktrees, context-only bases and provenance replicas were not counted as new
  products or proof of a separate workflow.
- Operational techniques are generalized; no private service architecture,
  incidents, personal histories, raw conversations or production commands are
  imported.
- Source paths/line numbers may drift. Re-read current files and local
  instructions before applying a technique; use hashes/revisions for frozen claims.
- A new project's novel mode or contrary local contract must be added through
  EVOLUTION rather than silently forcing it into an existing category.

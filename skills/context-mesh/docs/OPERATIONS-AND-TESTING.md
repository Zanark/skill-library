# Operations and Testing

## 1. Operational goals

Context Mesh operations must:

- Resolve the correct current base.
- Preserve current-base-only writes and sibling read-only access.
- Generate all three portfolio artifacts.
- Represent stale data honestly.
- Rank artifact provenance by evidence.
- Expose evidence for graph connections.
- Avoid secret leakage and transcript embedding.
- Work offline without external dashboard dependencies.

These goals are grounded in the access, refresh, dashboard, and honesty contracts
(`../SKILL.md:L23-L32`, `../SKILL.md:L50-L83`, `../SKILL.md:L91-L100`).

## 2. Standard generation runbook

1. Confirm source context stores and zmem export are readable.
2. Run:

   ```powershell
   python C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py --check
   ```

3. Confirm the command reports at least one context.
4. Confirm these files exist and are readable:

   ```text
   output\CONTEXT-MESH.md
   output\context-index.json
   output\context-mesh.html
   ```

5. Read the digest completely.
6. Validate one known current base, one relationship, one freshness state, and one artifact query.

Steps 2–5 are normative (`../SKILL.md:L36-L39`, `../SKILL.md:L50-L59`). Step 1 and the semantic checks in
step 6 are recommendations.

## 3. Startup validation matrix

| Test ID | Input | Expected result | Source |
|---|---|---|---|
| R-01 | Working directory exactly equals a base path | That base resolves | `../SKILL.md:L25-L26` |
| R-02 | Working directory is below one base | Ancestor base resolves | `../SKILL.md:L25-L26` |
| R-03 | Parent and nested bases both match | Longest path resolves | `../SKILL.md:L25-L26` |
| R-04 | No base matches | Registration delegated to `context-offload` | `../SKILL.md:L44-L45` |
| R-05 | New base initialization | Existing stores unchanged; only new store created | `../SKILL.md:L29-L30` |
| H-01 | Marker missing | Stale; full offload required | `../SKILL.md:L46-L48` |
| H-02 | Marker invalid | Stale; full offload required | `../SKILL.md:L46-L48` |
| H-03 | Marker age 11:59:59 | Not stale by the 12-hour threshold | `../SKILL.md:L46-L48` |
| H-04 | Marker age 12:00:00 | Stale; full offload required | `../SKILL.md:L46-L48` |
| H-05 | Long session reaches next 12-hour boundary | Full offload repeats | `../SKILL.md:L46-L48` |
| S-01 | Related sibling exists | It may be read as reference | `../SKILL.md:L42-L43` |
| S-02 | Related sibling exists | It is not modified | `../SKILL.md:L27-L28` |

## 4. Generation validation matrix

| Test ID | Condition | Expected result | Source |
|---|---|---|---|
| G-01 | Valid inputs | Build reports at least one context | `../SKILL.md:L58-L59` |
| G-02 | Valid inputs | All three outputs produced | `../SKILL.md:L58-L59` |
| G-03 | Zero contexts | Build considered failed | `../SKILL.md:L58-L59` |
| G-04 | One output missing | Build considered failed | `../SKILL.md:L58-L59` |
| G-05 | Generator error | Failure reported plainly | `../SKILL.md:L58-L59` |
| G-06 | Generator error | No success-shaped fallback | `../SKILL.md:L58-L59` |
| G-07 | Run from any registered base | Reads stores; writes only mesh output | `../SKILL.md:L31-L31` |

## 5. Dashboard functional matrix

| Area | Test | Expected result | Source |
|---|---|---|---|
| Offline | Disconnect network and open HTML | Core dashboard remains usable | `../SKILL.md:L61-L64` |
| Cards | Inspect a context | Freshness, identity, focus, threads, next steps, questions, memory, timeline visible | `../SKILL.md:L65-L65` |
| Search | Search known context text | Relevant cards/nodes are filtered | `../SKILL.md:L66-L66` |
| Freshness | Select stale filter | Stale contexts remain distinguishable | `../SKILL.md:L66-L66`, `../SKILL.md:L98-L98` |
| Artifact path | Search exact full path | Evidence-bearing results shown | `../SKILL.md:L67-L69` |
| Artifact filename | Search filename | Evidence-bearing results shown | `../SKILL.md:L67-L69` |
| Copy suffix | Search browser-copy filename | Suffix normalization finds candidate | `../SKILL.md:L67-L69` |
| Result metadata | Inspect artifact result | Chat, session, cwd, timestamps, paths, excerpt, nearby prompt shown | `../SKILL.md:L67-L69` |
| Default graph | Load dashboard | Only contexts and high-confidence/explicit handoffs shown by default | `../SKILL.md:L70-L71` |
| Detail | Enable context-memory/zmem | Optional nodes become available | `../SKILL.md:L72-L73` |
| Evidence filter | Enable incidental evidence | Lower-confidence references become inspectable | `../SKILL.md:L72-L73` |
| Edge inspector | Select connection | Confidence, class, exact excerpt shown | `../SKILL.md:L74-L75` |
| Timeline | Play animation | One-shot sequence runs | `../SKILL.md:L76-L78` |
| Timeline controls | Stop and replay | Both controls work | `../SKILL.md:L76-L78` |
| Colors | Fit and zoom graph | Contexts retain stable distinct circumference identity | `../SKILL.md:L79-L80` |
| Stroke | Zoom graph | Circumference stroke remains zoom-independent | `../SKILL.md:L79-L80` |
| Layout | Inspect connected family | Family occupies a central anchor | `../SKILL.md:L81-L83` |
| Layout | Inspect isolated nodes | They sit farther out | `../SKILL.md:L81-L83` |
| Pin | Drag and pin context | Family anchor moves and viewport centers | `../SKILL.md:L81-L83` |
| Reset | Use unpin-all | Custom anchors reset | `../SKILL.md:L81-L83` |

## 6. Provenance validation matrix

| Test ID | Evidence | Expected label/rank | Source |
|---|---|---|---|
| P-01 | Explicit “created/generated/modified” excerpt | Eligible for “Likely origin” | `../SKILL.md:L93-L95` |
| P-02 | Later “opened/inspected” excerpt | Ranked below creation evidence | `../SKILL.md:L67-L69` |
| P-03 | Filename only | Not certain origin | `../SKILL.md:L93-L95` |
| P-04 | Path/name co-occurrence only | Not a strong graph edge | `../SKILL.md:L74-L75` |
| P-05 | Explicit handoff | Eligible for conservative default graph | `../SKILL.md:L70-L71` |
| P-06 | Context with journal dates | Earliest dated journal evidence used | `../SKILL.md:L76-L78` |
| P-07 | zmem node | Creation timestamp used | `../SKILL.md:L76-L78` |
| P-08 | Unknown date | Labelled unknown/inherited; no invented precision | `../SKILL.md:L76-L78` |

## 7. Privacy and security matrix

| Test ID | Input | Expected result | Source |
|---|---|---|---|
| SEC-01 | `TOKEN=value` in local session state | Value redacted in excerpt | `../SKILL.md:L96-L97` |
| SEC-02 | Long transcript | Only concise excerpt indexed; no complete transcript | `../SKILL.md:L96-L97` |
| SEC-03 | Credential in source | Excluded from generated summary | `../SKILL.md:L100-L100` |
| SEC-04 | Sensitive incident payload | Excluded from generated summary | `../SKILL.md:L100-L100` |
| SEC-05 | Undocumented internal memory | Not scraped | `../SKILL.md:L99-L99` |
| SEC-06 | Sibling store under current base session | Read-only | `../SKILL.md:L27-L30` |
| SEC-07 | Access contract description | Described as instructional, not OS enforcement | `../SKILL.md:L32-L32` |

## 8. Failure modes and recovery

### 8.1 Digest missing or unreadable

**Impact:** required startup hydration cannot begin.

**Recovery recommendation:** run the checked generator, require the normal success gates, then read the
regenerated digest completely. Do not continue from an assumed portfolio state. The underlying requirements
are `../SKILL.md:L36-L39` and `../SKILL.md:L50-L59`.

### 8.2 Invalid JSON index

**Impact:** base resolution and graph consumers cannot operate reliably.

**Recovery recommendation:** report the invalid index, regenerate with `--check`, validate JSON parsing, and
restart longest-match resolution. Do not guess the active base.

### 8.3 Zero-context generation

**Impact:** generated artifacts do not satisfy the build contract.

**Recovery:** report failure plainly and investigate source discovery; do not publish a success-shaped empty
portfolio (`../SKILL.md:L58-L59`).

### 8.4 Partial output generation

**Impact:** digest, index, and dashboard disagree.

**Recovery:** treat the run as failed because all three files are mandatory; repair and regenerate
(`../SKILL.md:L58-L59`).

### 8.5 Wrong base resolved

**Impact:** the wrong persona may write the wrong store.

**Recovery recommendation:** stop writes, verify path normalization and longest-match sorting, rerun
resolution, and inspect whether a sibling store was changed. The access rule is normative
(`../SKILL.md:L25-L30`).

### 8.6 Sibling store modified

**Impact:** ownership boundary violated.

**Recovery recommendation:** stop further writes, restore the sibling from verified history, apply the
intended change only to the current base if appropriate, and document the correction. The read-only boundary
is normative (`../SKILL.md:L27-L30`).

### 8.7 False artifact origin

**Impact:** provenance is overstated.

**Recovery:** remove “Likely origin” unless creation, generation, or modification evidence exists; show the
actual evidence class and uncertainty (`../SKILL.md:L93-L95`).

### 8.8 False graph relationship

**Impact:** incidental text becomes an asserted architectural or handoff connection.

**Recovery:** lower confidence or remove from the default graph, preserve exact evidence, and expose it only
through the appropriate evidence filter when warranted (`../SKILL.md:L70-L75`).

### 8.9 Stale state shown as current

**Impact:** operational status is fabricated by omission of age.

**Recovery:** restore stale labelling, require `context-offload` reconciliation, and avoid inferring fresh
status (`../SKILL.md:L46-L48`, `../SKILL.md:L98-L98`).

### 8.10 Secret leakage

**Impact:** sensitive data enters generated artifacts.

**Recovery recommendation:** stop publication, remove the secret from outputs, correct redaction logic, rotate
credentials through the appropriate secure process when exposure occurred, and regenerate. Exclusion and
redaction are normative (`../SKILL.md:L96-L100`); credential rotation is operational advice.

## 9. Maintenance and change-impact matrix

| Source change | Review impact |
|---|---|
| Role/ownership (`L7-L13`) | Architecture, README, cross-skill interaction, ownership tests |
| Fixed paths (`L15-L21`) | Commands, runbooks, examples, path assertions |
| Access contract (`L23-L32`) | Resolver, sibling tests, registration tests, security wording |
| Hydration (`L34-L48`) | Startup state machine, freshness matrix, examples |
| Refresh (`L50-L59`) | Build command, output gates, failure recovery |
| Dashboard behavior (`L61-L89`) | Functional tests, UI reference, examples |
| Data honesty (`L91-L100`) | Provenance ranking, redaction tests, privacy controls |

This is a **recommended** documentation-maintenance map.

## 10. Cross-skill regression suite

Run these scenarios whenever either skill changes:

1. Registered fresh base hydrates correctly.
2. Registered stale base delegates a full offload.
3. Nested base chooses the longest path.
4. Unregistered base creates only its own four-file store.
5. Store milestone triggers all three regenerated outputs.
6. zmem offload appears through optional detail and triggers refresh.
7. Sibling references remain read-only.
8. Artifact creation evidence outranks later inspection.
9. Filename-only evidence never becomes certain origin.
10. Stale cards remain stale.
11. Journal and zmem dates retain their distinct provenance.
12. Secret assignments are redacted and full transcripts excluded.

Each scenario directly covers requirements in `../SKILL.md:L23-L100`.

## 11. Documentation regression checklist

- [ ] All citations still point to the intended source lines.
- [ ] The fixed project, generator, and output paths match the source.
- [ ] Longest-match semantics remain explicit.
- [ ] Current-base and sibling boundaries remain explicit.
- [ ] The boundary is never described as OS-enforced.
- [ ] The 12-hour condition says “at least 12 hours.”
- [ ] The refresh gate requires at least one context and all three outputs.
- [ ] Dashboard behavior is not expanded beyond the source without a recommendation label.
- [ ] “Likely origin” remains evidence-gated.
- [ ] Timeline dates retain honest provenance.
- [ ] Session excerpts remain concise and redacted.
- [ ] No internal-memory scraping is implied.
- [ ] Cross-skill ownership remains: offload owns state/persona; mesh owns portfolio indexing.

## 12. Recommended review cadence

**Recommendation.** Review and rerun the cross-skill suite after changes to either `SKILL.md`, the generator,
the output schema, base registration behavior, zmem export format, or dashboard provenance logic. The source
defines the required behavior but not a maintenance calendar.


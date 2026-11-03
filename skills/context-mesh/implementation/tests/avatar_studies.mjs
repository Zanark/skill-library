import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { performance } from "node:perf_hooks";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const root = path.resolve(import.meta.dirname, "..");
const source = fs.readFileSync(path.join(root, "assets", "dashboard.js"), "utf8");
const start = source.indexOf("function avatarRecipe(seed) {");
const end = source.indexOf("\nfunction socialDateLabel(", start);
assert.ok(start >= 0 && end > start, "Cannot locate frozen baseline renderers");
const studies = fs.readFileSync(path.join(root, "assets", "avatar-studies.js"), "utf8");
const sandbox = { btoa: text => Buffer.from(text, "latin1").toString("base64") };
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end) + "\n" + studies, sandbox);
const hash = text => createHash("sha256").update(text).digest("hex");
assert.equal(hash(sandbox.avatarDataUri("0".repeat(64))),
  "5695c656d2e3c7d01f335b182cf3d58aa8520a8d07585832cc1d2b2cad284124", "Frozen face-v1 changed");
const args = process.argv.slice(2);
assert.ok(args.length === 0 || (args.length === 2 && args[0] === "--index"),
  "Usage: node tests\\avatar_studies.mjs [--index <context-index.json>]");
const hairNames = ["Short", "Sweep", "Curls", "Bob", "Long", "Quiff", "Bun", "Sparse"];
const versions = [
  { id: 1, name: "01 / Original reference", tag: "Frozen reference", idea: "Flat cartoon. Original large circular eyes and single earring retained for an honest starting point.", review: "Historical reference, no longer the live renderer." },
  { id: 2, name: "02 / Earlier glossy study", tag: "Previous experiment", idea: "More gradients and detail, but larger sparkling eyes amplified the anime-like appearance.", review: "Rejected direction for this request: surface detail did not fix the proportions." },
  { id: 3, name: "03 / Human-eyed editorial", tag: "Iteration 1", idea: "Narrow almond apertures, clipped irises, small catchlights, quieter lips and paired earrings. Flat shapes isolate the geometry change.", review: "Reviewed: eye geometry is much quieter; silhouettes stay readable. Face and polo still look stiff and generic." },
  { id: 4, name: "04 / Soft sculpted", tag: "Iteration 1", idea: "Keep the new eyes; add coherent warm light, cheek planes, restrained hair strands and cloth volume.", review: "Reviewed: a useful restrained middle ground. The outlines and identical collar still read as a polished cartoon." },
  { id: 5, name: "05 / Illustrated studio", tag: "Iteration 1", idea: "Remove the heavy face outline, refine jaw/nose/eyelid planes and avoid shiny white eyes.", review: "Reviewed: less anime-like, but plastic chin/nose highlights, weak pale brows and rigid poses need work." },
  { id: 6, name: "06 / Graphic ink", tag: "Iteration 2", idea: "Angular jaw, stronger brows, head tilt, three clothing cuts and matching hoops. Deliberate flat shadow planes instead of glossy volume.", review: "Reviewed: clearer graphic personality, but intentionally hard cheek/nose planes can look severe. A stylistic alternative, not realism." },
  { id: 7, name: "07 / Painted atelier", tag: "Iteration 2", idea: "Quieter highlights, shared directional light, a softer nose/chin, controlled organic hair and subtle fixed-seed grain.", review: "Reviewed: warmer and less rigid. Close-up reveals grooved hair highlights, a forehead band and texture that adds little at 46px." },
  { id: 8, name: "08 / Refined portrait", tag: "Iteration 3", idea: "Tighter portrait crop, quieter irises, mirrored lid geometry, softer nose, less washed-out skin and fine hair groups. Remove grain and displacement.", review: "Reviewed across the cast, six skin palettes and eight hair families: clearer small faces, no shiny nose stripe, visible paired studs. My balanced recommendation, not an automatic selection." },
  { id: 9, name: "08B / Individual wardrobes", tag: "Selected / live renderer", idea: "Visibly larger almond eyes, fuller shoulders/chest and individually authored outfits. Different cuts, fabrics, layers and palettes, not a shared blazer with badges.", review: "User authorized live deployment. Original 08 is preserved. Clothing presentation is fictional art direction, not an inferred gender. Gothita keeps the romantic goth treatment; newly discovered unmapped personas use the role wardrobe." },
];
const render = (seed, version, persona = {}, appearance = {}) => version === 1 ? sandbox.avatarDataUri(seed) :
  version === 2 ? sandbox.avatarDataUriV2(seed) : sandbox.avatarStudyDataUri(seed, version, persona, appearance);
for (const version of versions) {
  for (const bad of ["", "not-hex", null, undefined, 7]) {
    assert.throws(() => render(bad, version.id), { name: "TypeError" });
  }
  assert.equal(render("a0f", version.id), render("A0F", version.id), "Case changes a portrait");
  assert.notEqual(render("0".repeat(64), version.id), render("0".repeat(63) + "1", version.id));
}
assert.throws(() => sandbox.avatarStudyDataUri("abc", 999), { name: "RangeError" });
const goblinId = "fictional-trash-goblin-718bb26f-ec71-4d8a-9543-f67727e20064";
const gothDirection = { theme: "goth", presentation: "feminine", flair: "bold" };
const winkDirection = { expression: "friendly-wink" };
const facialHairStyles = ["stubble", "goatee", "boxed-beard", "chevron", "handlebar", "full-beard"];
const butlerDirection = { theme: "butler", presentation: "masculine", flair: "restrained" };
const alfredContext = "ctx-ded91077c7ca";
const futureAlfred = { personaId: "session-future-alfred", contextId: alfredContext, profileImageData: "abc" };
const feminineAlfred = { ...futureAlfred, avatarPresentation: "feminine" };
assert.equal(sandbox.personaAvatarDataUri(feminineAlfred),
  render("abc", 9, feminineAlfred, { ...butlerDirection, presentation: "feminine" }),
  "An owner-authored feminine presentation lost the existing context theme");
assert.ok(Buffer.from(sandbox.personaAvatarDataUri(feminineAlfred).split(",")[1], "base64")
  .toString("utf8").includes('data-feature="lipstick"'), "Explicit feminine character has no lipstick");
assert.throws(() => sandbox.personaAvatarDataUri({ ...futureAlfred, avatarPresentation: "unknown" }), { name: "TypeError" });
assert.equal(sandbox.personaAvatarDataUri(futureAlfred), render("abc", 9, futureAlfred, butlerDirection),
  "A future Alfred session lost its context-level portrait direction");
assert.equal(sandbox.personaAvatarDataUri({ ...futureAlfred, contextId: "ctx-unmapped" }),
  render("abc", 9, futureAlfred), "Butler styling leaked into another context");
for (const feature of ["mature-features", "moustache", "bow-tie", "watch-chain"]) {
  assert.ok(Buffer.from(sandbox.personaAvatarDataUri(futureAlfred).split(",")[1], "base64")
    .toString("utf8").includes(`data-feature="${feature}"`), `Missing Alfred detail: ${feature}`);
}
const outfitDescriptions = {
  "cable-knit": "Plum cable-knit / boat neck / geometric pendant",
  "cardboard-harness": "Forest work shirt / corrugated KC box harness / box headphones",
  mandarin: "Jade stand-collar shirt / offset brass buttons",
  suspenders: "Ivory shirt / burgundy suspenders / slim tie",
  "chore-jacket": "Ochre canvas chore jacket / charcoal tee / patch pockets",
  "map-shirt": "Petrol camp-collar shirt / original contour-line print",
  "mockneck-drape": "Charcoal mockneck / oxblood asymmetric drape / silver clasp",
  "linen-wrap": "Cream linen wrap / teal inset / copper belt",
  "tweed-cravat": "Olive herringbone waistcoat / plum cravat",
  "zip-hoodie": "Slate asymmetric zip hoodie / cobalt lining",
  "bib-overalls": "Forest-green bib overalls / rust raglan tee",
  "shawl-cardigan": "Terracotta shawl-knit cardigan / cream Henley",
  "embroidered-smock": "Ink-blue smock / square embroidered yoke / copper cross-stitch",
  "moto-jacket": "Aubergine leather moto jacket / diagonal zip / mustard tee",
  "satin-bomber": "Raspberry satin bomber / cream raglan sleeves / teal ribbing",
  "breton-sling": "Cream-and-navy Breton stripes / ochre cross-body pouch",
};
let current = [];
if (args.length) {
  const index = JSON.parse(fs.readFileSync(path.resolve(args[1]), "utf8"));
  assert.ok(Array.isArray(index.social?.personas) && index.social.personas.length);
  current = index.social.personas.map(persona => {
    assert.equal(typeof persona.displayName, "string");
    sandbox.avatarRecipe(persona.profileImageData);
    assert.equal(sandbox.personaAvatarDataUri(persona),
      render(persona.profileImageData, 9, persona, sandbox.avatarPortraitDirection(persona)),
      "Live portrait differs from the reviewed study");
    return { label: persona.displayName, seed: persona.profileImageData, group: "Current personas",
      appearance: sandbox.avatarPortraitDirection(persona),
      metadata: { personaId: persona.personaId, displayName: persona.displayName, persona: persona.persona,
        avatarPresentation: persona.avatarPresentation, personalityStats: persona.personalityStats } };
  });
  const castOutfits = current.map(persona => {
    const direction = persona.appearance;
    const outfit = direction.theme || direction.outfit;
    assert.ok(outfit && outfit !== "role", `${persona.label} still has an uncast fallback outfit`);
    return outfit;
  });
  assert.equal(new Set(castOutfits).size, current.length, "Current characters share an outfit construction");
  const bearded = current.filter(persona => facialHairStyles.includes(persona.appearance.facialHair));
  assert.ok(bearded.length >= 6, "The current cast did not gain facial-hair variety");
  assert.equal(new Set(bearded.map(persona => persona.appearance.facialHair)).size, facialHairStyles.length,
    "The current cast repeats one facial-hair style instead of using the authored variety");
}
const seeds = Array.from({ length: 512 }, (_, index) => hash(`portrait-study-${index}`));
let preservedChecks = 0;
const selectedPath = path.join(root, "output", "avatar-studies", "round-3", "fingerprints.json");
if (fs.existsSync(selectedPath)) {
  for (const { seed, fingerprint } of JSON.parse(fs.readFileSync(selectedPath, "utf8"))) {
    assert.equal(hash(render(seed, 8)), fingerprint, "The selected original 08 changed");
    preservedChecks++;
  }
}
const wardrobeRoles = [
  ["creative", "Fictional adult comedy guest"],
  ["research", "Research-minded Thread Scout"],
  ["operations", "Daily-ops driver"],
  ["architect", "Skills-library maintainer"],
  ["analyst", "Migration resource-report engineer"],
  ["maker", "Full-body VTubing engineer"],
  ["general", "Engineering partner"],
];
const presentations = ["feminine", "masculine", "androgynous"];
const flairOptions = ["restrained", "bold"];
const styleKeys = presentations.flatMap(presentation => flairOptions.map(flair => `${presentation}:${flair}`));
for (const [family, persona] of wardrobeRoles) {
  for (const presentation of presentations) {
    const seed = seeds[0], metadata = { persona };
    const style = sandbox.avatarWardrobeProfile(seed, metadata, { presentation });
    assert.equal(style.family, family);
    assert.equal(style.presentation, presentation);
    assert.notEqual(render(seed, 9, metadata, { presentation, flair: "bold" }),
      render(seed, 9, metadata, { presentation, flair: "restrained" }), "Flair control has no effect");
  }
}
assert.throws(() => render("abc", 9, {}, { presentation: "unknown" }), { name: "TypeError" });
assert.throws(() => render("abc", 9, {}, { flair: "unknown" }), { name: "TypeError" });
assert.throws(() => render("abc", 9, {}, { expression: "closed" }), { name: "TypeError" });
assert.throws(() => render("abc", 9, {}, { expression: "wink" }), { name: "TypeError" });
assert.throws(() => render("abc", 9, {}, { facialHair: "unknown" }), { name: "TypeError" });
assert.throws(() => render("abc", 9, {}, { theme: "unknown" }), { name: "TypeError" });
assert.throws(() => render("abc", 9, {}, { outfit: "unknown" }), { name: "TypeError" });
assert.throws(() => render("abc", 9, {}, { theme: "goth", outfit: "zip-hoodie" }), { name: "TypeError" });
assert.throws(() => render("abc", 9, {}, { theme: "butler", outfit: "zip-hoodie" }), { name: "TypeError" });
for (const outfit of Object.keys(outfitDescriptions)) {
  for (const presentation of presentations) {
    assert.notEqual(render(seeds[0], 9, {}, { outfit, presentation, flair: "bold" }),
      render(seeds[0], 9, {}, { outfit, presentation, flair: "restrained" }), `${outfit} ignores flair`);
  }
}
assert.throws(() => render("abc", 9, null), { name: "TypeError" });
assert.throws(() => render("abc", 9, { personalityStats: [] }), { name: "TypeError" });
for (const bad of [NaN, Infinity, -1, 101, "high"]) {
  assert.throws(() => render("abc", 9, { personalityStats: { humor: bad } }), { name: "TypeError" });
}
const characteristicNames = ["seriousness", "humor", "curiosity", "persistence", "helpfulness"];
for (const name of characteristicNames) {
  assert.notEqual(render(seeds[0], 9, { personalityStats: { [name]: 0 } }),
    render(seeds[0], 9, { personalityStats: { [name]: 100 } }), `${name} does not affect wardrobe`);
}
assert.equal(render(seeds[0], 9, { gender: "female" }), render(seeds[0], 9, { gender: "male" }),
  "Wardrobe inferred a gender from unauthored metadata");
const frozenPath = path.join(root, "output", "avatar-studies", "round-1", "fingerprints.json");
if (fs.existsSync(frozenPath)) {
  for (const { seed, versions: saved } of JSON.parse(fs.readFileSync(frozenPath, "utf8"))) {
    for (const [version, fingerprint] of Object.entries(saved)) {
      assert.equal(hash(render(seed, Number(version))), fingerprint, "An already-reviewed early study changed");
      preservedChecks++;
    }
  }
}
const fixtures = [];
const addFixture = (label, predicate) => {
  const seed = seeds.find(candidate => predicate(sandbox.avatarRecipe(candidate)));
  assert.ok(seed, `No fixture for ${label}`);
  fixtures.push({ label, seed, group: "Synthetic coverage (not registered personas)" });
};
for (let index = 0; index < 8; index++) {
  addFixture(`${hairNames[index]} + paired earrings`, recipe => recipe.hairStyle === index && recipe.accessory === 3);
}
for (let index = 0; index < 6; index++) {
  addFixture(`Skin palette ${index + 1}`, recipe =>
    recipe.skin === ["#f8d7b4", "#eebc91", "#d99b72", "#bc805d", "#955d43", "#704536"][index] && recipe.eyeStyle === 0);
}
for (let index = 0; index < 4; index++) addFixture(`Eye expression ${index}`, recipe => recipe.eyeStyle === index);
for (let index = 0; index < 5; index++) addFixture(`Mouth expression ${index}`, recipe => recipe.mouthStyle === index);
for (let index = 0; index < 5; index++) {
  fixtures.push({ label: `Lipstick / mouth expression ${index}`,
    seed: seeds.find(seed => sandbox.avatarRecipe(seed).mouthStyle === index),
    group: "Synthetic lipstick coverage", appearance: { presentation: "feminine" } });
}
for (let index = 0; index < 5; index++) addFixture(`Accessory ${index}`, recipe => recipe.accessory === index);
for (const [family, persona] of wardrobeRoles) {
  fixtures.push({ label: `${family} wardrobe`, seed: seeds[0], group: "Synthetic wardrobe coverage",
    metadata: { persona, personalityStats: Object.fromEntries(characteristicNames.map(name => [name, 85])) } });
}
fixtures.push({ label: "Romantic goth (synthetic adult)", seed: seeds[0],
  group: "Synthetic art direction", metadata: { persona: "Fictional adult comedy guest" }, appearance: gothDirection });
fixtures.push({ label: "Classic older butler", seed: seeds[0],
  group: "Synthetic art direction", metadata: { persona: "Fictional adult assistant" }, appearance: butlerDirection });
fixtures.push({ label: "Friendly wink / formerly both-closed seed",
  seed: seeds.find(seed => sandbox.avatarRecipe(seed).eyeStyle === 2),
  group: "Synthetic art direction", appearance: winkDirection });
for (const facialHair of facialHairStyles) {
  fixtures.push({ label: `Facial hair / ${facialHair.replaceAll("-", " ")}`, seed: seeds[0],
    group: "Synthetic facial-hair coverage", appearance: { facialHair } });
}
for (const [outfit, description] of Object.entries(outfitDescriptions)) {
  fixtures.push({ label: description, seed: seeds[0], group: "Synthetic individual outfits", appearance: { outfit } });
}
const personas = [...current, ...fixtures];
const records = personas.map(persona => ({
  ...persona,
  traits: sandbox.avatarRecipe(persona.seed),
  wardrobe: sandbox.avatarWardrobeProfile(persona.seed, persona.metadata, persona.appearance),
  images: Object.fromEntries(versions.map(version => [version.id, render(persona.seed, version.id, persona.metadata, persona.appearance)])),
  wardrobeImages: Object.fromEntries(styleKeys.map(key => {
    const [presentation, flair] = key.split(":");
    return [key, render(persona.seed, 9, persona.metadata, { ...persona.appearance, presentation, flair })];
  })),
}));
const previousStudyPath = path.join(root, "output", "avatar-studies", "round-4", "avatar-studies.js");
let previousRenderer;
if (fs.existsSync(previousStudyPath)) {
  const previous = { btoa: sandbox.btoa };
  vm.createContext(previous);
  vm.runInContext(source.slice(start, end) + "\n" + fs.readFileSync(previousStudyPath, "utf8"), previous);
  previousRenderer = previous.avatarStudyDataUri;
}
const metrics = [];
for (const version of versions) {
  const timings = [];
  const bytes = [];
  for (const seed of seeds) {
    const time = performance.now();
    const uri = render(seed, version.id);
    timings.push(performance.now() - time);
    assert.equal(uri, render(seed, version.id));
    const svg = Buffer.from(uri.split(",")[1], "base64").toString("utf8");
    assert.match(svg, /^[\x00-\x7f]*$/);
    assert.doesNotMatch(svg, /\b(?:NaN|undefined|Infinity)\b/);
    bytes.push(Buffer.byteLength(svg));
  }
  timings.sort((left, right) => left - right);
  metrics.push({ version: version.id, svgBytesMean: Math.round(bytes.reduce((a, b) => a + b) / bytes.length),
    svgBytesMax: Math.max(...bytes), generationMedianMs: +timings[256].toFixed(3),
    generationP95Ms: +timings[486].toFixed(3) });
}
const json = value => JSON.stringify(value).replace(/</g, "\\u003c");
const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MeshBoard / Portrait workshop</title><style>
*{box-sizing:border-box} :root{color-scheme:dark;--page:#11141c;--panel:#1b202c;--text:#efece3;--muted:#aeb5c5;--line:#364153;--accent:#e5b775}
body.light{color-scheme:light;--page:#f4efe5;--panel:#fffdf6;--text:#272c35;--muted:#646975;--line:#d8d1c5;--accent:#845b24}
body{margin:0;padding:28px;font:14px/1.6 system-ui,sans-serif;background:var(--page);color:var(--text)}
header{max-width:1550px;margin:auto}h1{font-size:clamp(28px,4vw,48px);letter-spacing:-.04em;margin:0}h2{font-size:23px;margin:0 0 9px}h3{font-size:16px;margin:0}p{margin:6px 0;color:var(--muted)}
.eyebrow{letter-spacing:.18em;text-transform:uppercase;color:var(--accent);font-size:11px}.notice{border-left:3px solid var(--accent);padding:4px 14px;margin:18px 0}
.toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:22px 0}label{display:flex;flex-wrap:wrap;gap:8px;align-items:center;min-width:0;max-width:100%}select{min-width:0;max-width:100%}
button,select{font:inherit;border:1px solid var(--line);border-radius:8px;padding:8px 11px;background:var(--panel);color:var(--text)}
button{cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
main{max-width:1550px;margin:auto}.comparisons{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:16px;align-items:start}
.study{border:1px solid var(--line);border-radius:16px;padding:16px;background:var(--panel);min-width:0}
.study .tag{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)}figure{margin:14px 0}
.portrait{width:220px;max-width:100%;height:auto;aspect-ratio:1;display:block;margin:auto;border-radius:20px}
.mini{display:flex;align-items:center;justify-content:center;gap:12px;margin:14px 0}.mini img{width:46px;height:46px;border-radius:10px}.mini span{font-size:11px;color:var(--muted)}
.review{font-size:12px;border-top:1px solid var(--line);padding-top:10px;margin-top:12px}.idea{font-size:12px;min-height:77px}
.roster{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr));gap:12px}.roster .portrait{width:160px}.roster h3{font-size:13px}
.cast{grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr))}.cast .portrait{width:200px}
.inspect-character{display:block;width:100%;padding:0;border:0;background:transparent;margin:12px 0}
section{margin:34px 0}.detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,512px),1fr));gap:18px}
.detail-grid img{width:512px;max-width:100%;height:auto;display:block;border-radius:20px}.details{color:var(--muted);font-size:12px}
table{border-collapse:collapse;font-size:12px;width:100%}td,th{padding:9px;text-align:left;border-bottom:1px solid var(--line)}.table-wrap{overflow-x:auto}
.legend{font-size:12px}a{color:var(--accent)}details{border:1px solid var(--line);border-radius:12px;padding:14px;margin:20px 0}
@media(max-width:600px){body{padding:14px}.toolbar{align-items:stretch;flex-direction:column}select{max-width:100%}.idea{min-height:0}}
</style></head><body><header>
<p class="eyebrow">MeshBoard / Procedural SVG portrait workshop</p><h1>From symbols to faces.</h1>
<p>Same saved seeds. Different original drawing decisions. Compare the whole journey, not just the newest image.</p>
<div class="notice"><strong>Shared-renderer comparison gallery.</strong> The live 08B uses these same drawings after deliberate deployment; historical versions remain references. Persona sources and color assignments are unchanged.
Every new earring-bearing candidate has a matching pair; the two historical references intentionally retain their original single earring.</div>
<div class="toolbar"><label>Character <select id="persona"></select></label><button id="theme" type="button" aria-pressed="false">&#9728; / &#9790; Theme</button>
<button id="earrings" type="button">Inspect paired-earring fixture</button></div>
<div class="toolbar"><label>08B clothing <select id="presentation"><option value="auto">Seeded fictional presentation</option><option value="feminine">Feminine tailoring</option><option value="masculine">Masculine tailoring</option><option value="androgynous">Androgynous tailoring</option></select></label>
<label>08B styling <select id="flair"><option value="auto">Character default</option><option value="restrained">Restrained styling</option><option value="bold">Bolder styling</option></select></label></div>
<p id="identity" class="legend"></p></header><main>
<section id="individual-wardrobes"><h2>Individuals, not a uniform.</h2><p>Every current character has a separately authored outfit: different silhouette, neckline, fabric, layering and palette. Click a portrait to compare the shared 08B drawing with original 08.</p><div id="individual-cast" class="roster cast"></div></section>
<section><h2>Your chosen 08, refined.</h2><p>Original on the left; 08B on the right. Clothing controls affect only 08B.</p><div id="refinement-comparison" class="comparisons"></div></section>
<section aria-label="All drawing versions"><div id="comparisons" class="comparisons"></div></section>
<section><h2>The actual review journey</h2>
<p><strong>Loop 1 - fix construction before decoration.</strong> Compared 03 / 04 / 05 across the current cast and skin palettes. Narrower eyes helped; the rigid front-facing pose, repeated polo and plastic highlights remained.</p>
<p><strong>Loop 2 - test opposite art directions.</strong> Created graphic 06 and textured 07, then reviewed the cast, jewelry under every hair family and large close-ups. Graphic planes were intentionally severe; texture barely helped small icons, and hair highlights looked grooved.</p>
<p><strong>Loop 3 - edit, do not just add.</strong> Created 08 with a closer crop, finer hair, balanced lids and quieter skin/nose. Removed the grain/displacement experiment. Reviewed the cast, six skin tones, all earring hairstyles and both gallery themes.</p>
<p>03 stays the crisp flat alternative; 06 stays the bold graphic alternative; 08 is my balanced recommendation. None is deployed or silently chosen for you.</p></section>
<section><h2>Your 08 refinements</h2><p>08B keeps the shading and paired studs, with larger almond eyes and a fuller shoulder/chest crop. The wider framing and raised head expose roughly twice the chest area; the face necessarily occupies less of the square.</p>
<p><strong>Construction correction:</strong> shared tapered necks connect jaw to shoulders; the hoodie folds sit beside an open neckline instead of filling the neck with blue fabric. High collars/choker sit lower. A restrained black silhouette edge separates the figure from its background without thickening the interior drawing.</p>
<p><strong>Eye-size correction:</strong> the wider crop offset the initial increase. The latest 08B now has eyes about 11% wider and irises about 10% larger than original 08 at the same display size, not merely in drawing coordinates. Almond lids and tiny catchlights remain.</p>
<p>The earlier role families still looked like one crew in matching jackets. The full seventeen-person cast now has fifteen independent garment designs, Gothita's goth dress and Alfred's dinner jacket. The newest additions are an embroidered smock, leather moto jacket, satin bomber and striped shirt with a cross-body pouch. These are different garment constructions, not just color swaps or new badges.</p>
<p>Presentation is fictional styling, never inferred from hair, names or real-user demographics. Current-character outfits are explicitly mapped by persona ID in the preview, using each persona as creative inspiration, not a literal workplace uniform or psychological finding. Unmapped/synthetic characters retain the earlier role/stat rules; those seven families remain available for honest comparison. The preview does not edit persona files.</p></section>
<section><h2>Gothita / romantic goth</h2><p>An explicit user-directed adult character design: long black hair with a pointed fringe, smoky winged eyes, oxblood-red lipstick, silver crescent earrings, a lace choker and an off-shoulder black brocade-style dress. The reference informs styling, not a copied face. Old seeds and the existing live artwork stay untouched by the display-name change.</p></section>
${previousRenderer ? '<p><a href="round-4/index.html">Preserved earlier 08B: before gothic art direction and screen-size eye correction.</a></p>' : ""}
${fs.existsSync(path.join(root, "output", "avatar-studies", "round-5", "index.html")) ? '<p><a href="round-5/index.html">Preserved goth / larger-eyes revision: before the cast received individual clothes.</a></p>' : ""}
${fs.existsSync(path.join(root, "output", "avatar-studies", "round-6", "index.html")) ? '<p><a href="round-6/index.html">Preserved individual costumes before neck/collar corrections and the subtle black silhouette edge.</a></p>' : ""}
<section><h2>At actual chat size</h2><p>No enlarged pixel trick: these images are all 46px wide.</p><div id="chat-strip" class="comparisons"></div></section>
<section><div class="toolbar"><h2>Whole-cast and feature stress test</h2><label>Drawing <select id="roster-version"></select></label><label>Coverage <select id="coverage"><option value="current">Current cast</option><option value="earrings">Eight hair families + earrings</option><option value="skin">Six skin palettes</option><option value="expressions">Eyes, mouths and accessories</option><option value="wardrobe">Earlier seven role wardrobes</option><option value="individual">Same face / individual outfits</option></select></label></div>
<p>Coverage characters are deterministic synthetic fixtures, not invented session participants.</p><div id="roster" class="roster"></div></section>
<section><h2>Large inspection</h2><p>512px reveals construction quality; it is not the normal profile size.</p><div id="detail" class="detail-grid"></div></section>
<details><summary>What was measured, and what was not</summary><p>Local Node generation times, 512 deterministic seeds per version; raw SVG sizes exclude Base64. These are one-machine samples, not cross-device rendering or memory guarantees. Browser checks also decode real images and reject external resources. Visual preference remains yours.</p><div class="table-wrap"><table><thead><tr><th>Version</th><th>Mean SVG</th><th>Largest sample</th><th>Generation median</th><th>P95</th></tr></thead><tbody>${metrics.map(m => `<tr><td>${m.version}</td><td>${m.svgBytesMean} B</td><td>${m.svgBytesMax} B</td><td>${m.generationMedianMs} ms</td><td>${m.generationP95Ms} ms</td></tr>`).join("")}</tbody></table></div></details>
<p class="details">Offline original vector artwork. No model-generated portrait, photograph, external font, downloaded texture or hosted avatar service. SVG shading can suggest volume; it is not a 3D face or a promise of photorealism.</p>
</main><script>
const personas=${json(records)}, versions=${json(versions)}, hairNames=${json(hairNames)}, outfitDescriptions=${json(outfitDescriptions)};
const esc=text=>String(text).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const personaSelect=document.getElementById("persona"), rosterSelect=document.getElementById("roster-version");
for(const group of [...new Set(personas.map(p=>p.group))]){
 const opt=document.createElement("optgroup");opt.label=group;
 personas.forEach((p,i)=>{if(p.group===group){const o=document.createElement("option");o.value=i;o.textContent=p.label;opt.append(o)}});
 personaSelect.append(opt);
}
versions.forEach(v=>{const o=document.createElement("option");o.value=v.id;o.textContent=v.name;rosterSelect.append(o)});
rosterSelect.value=versions.at(-1).id;
function styleFor(p){return {presentation:document.getElementById("presentation").value==="auto"?p.wardrobe.presentation:document.getElementById("presentation").value,flair:document.getElementById("flair").value==="auto"?p.wardrobe.flair:document.getElementById("flair").value}}
function image(p,v,cls="portrait"){const s=styleFor(p),uri=Number(v)===9?p.wardrobeImages[s.presentation+":"+s.flair]:p.images[v];return '<img class="'+cls+'" src="'+uri+'" alt="'+esc(p.label+' - '+versions.find(s=>s.id===Number(v)).name)+'">'}
function wardrobeLabel(p){const s=styleFor(p);return (p.wardrobe.theme==="goth"?"Romantic goth":p.wardrobe.theme==="butler"?"Dinner jacket / wing collar / bow tie":outfitDescriptions[p.wardrobe.outfit]||p.wardrobe.family)+" / "+s.presentation+" / "+s.flair+(p.wardrobe.facialHair!=="none"?" / "+p.wardrobe.facialHair.replaceAll("-"," "):"")}
function renderCast(){
 const cast=personas.filter(p=>p.group==="Current personas");
 document.getElementById("individual-cast").innerHTML=cast.map(p=>'<article class="study"><h3>'+esc(p.label)+'</h3><button type="button" class="inspect-character" data-character="'+personas.indexOf(p)+'" aria-label="'+esc("Inspect "+p.label)+'">'+image(p,9)+'</button><p class="details">'+esc(wardrobeLabel(p))+'</p></article>').join("");
}
document.getElementById("individual-cast").addEventListener("click",event=>{const target=event.target.closest("[data-character]");if(target){personaSelect.value=target.dataset.character;renderFocus();document.getElementById("refinement-comparison").scrollIntoView({block:"start"})}});
function renderFocus(){
 const p=personas[Number(personaSelect.value)];
 document.getElementById("identity").textContent=p.label+" / original recipe: "+hairNames[p.traits.hairStyle]+" / accessory "+p.traits.accessory+" / eye expression "+p.traits.eyeStyle+" / 08B: "+wardrobeLabel(p)+(p.wardrobe.theme==="goth"?" / explicit hair, makeup and expression art direction":"")+" / saved seed unchanged";
 document.getElementById("refinement-comparison").innerHTML=versions.filter(v=>v.id>=8).map(v=>'<article class="study"><h3>'+esc(v.name)+'</h3><figure>'+image(p,v.id)+'</figure><div class="mini">'+image(p,v.id,"chat")+'<span>46px</span></div><p>'+esc(v.id===9?wardrobeLabel(p):"Original 08 / unchanged")+'</p></article>').join("");
 document.getElementById("comparisons").innerHTML=versions.map(v=>'<article class="study" data-version="'+v.id+'"><span class="tag">'+esc(v.tag)+'</span><h3>'+esc(v.name)+'</h3><figure>'+image(p,v.id)+'<figcaption class="mini">'+image(p,v.id,"chat")+'<span>220px above / 46px here</span></figcaption></figure><p class="idea">'+esc(v.idea)+'</p><p class="review">'+esc(v.review)+'</p></article>').join("");
 document.getElementById("chat-strip").innerHTML=versions.map(v=>'<article class="study"><h3>'+esc(v.name)+'</h3><div class="mini">'+image(p,v.id,"chat")+'<span>Actual 46px</span></div></article>').join("");
 document.getElementById("detail").innerHTML=versions.filter(v=>v.id>=3).map(v=>'<figure><h3>'+esc(v.name)+'</h3>'+image(p,v.id)+'</figure>').join("");
}
function renderRoster(){
 const coverage=document.getElementById("coverage").value;
 let selected=coverage==="current"?personas.filter(p=>p.group==="Current personas"):coverage==="earrings"?personas.filter(p=>p.label.includes("+ paired earrings")):coverage==="skin"?personas.filter(p=>p.label.startsWith("Skin palette")):coverage==="wardrobe"?personas.filter(p=>p.group==="Synthetic wardrobe coverage"):coverage==="individual"?personas.filter(p=>p.group==="Synthetic individual outfits"):personas.filter(p=>/^(Eye expression|Mouth expression|Accessory)/.test(p.label));
 if(!selected.length)selected=personas.filter(p=>p.label.includes("+ paired earrings"));
 document.getElementById("roster").innerHTML=selected.map(p=>'<article class="study"><h3>'+esc(p.label)+'</h3><figure>'+image(p,rosterSelect.value)+'</figure><div class="mini">'+image(p,rosterSelect.value,"chat")+'<span>46px</span></div>'+(Number(rosterSelect.value)===9?'<p class="details">'+esc(wardrobeLabel(p))+'</p>':'')+'</article>').join("");
}
personaSelect.addEventListener("change",renderFocus);
rosterSelect.addEventListener("change",renderRoster);
document.getElementById("coverage").addEventListener("change",renderRoster);
for(const id of ["presentation","flair"])document.getElementById(id).addEventListener("change",()=>{renderFocus();renderRoster();renderCast()});
document.getElementById("earrings").addEventListener("click",()=>{personaSelect.value=personas.findIndex(p=>p.label==="${hairNames[0]} + paired earrings");renderFocus()});
document.getElementById("theme").addEventListener("click",e=>{const light=document.body.classList.toggle("light");e.currentTarget.setAttribute("aria-pressed",String(light))});
if(location.hash==="#trash-goblin"){const i=personas.findIndex(p=>p.metadata?.personaId==="${goblinId}");if(i>=0)personaSelect.value=i}
renderFocus();renderRoster();renderCast();
</script></body></html>`;
const output = path.join(root, "output", "avatar-studies");
fs.mkdirSync(output, { recursive: true });
const htmlPath = path.join(output, "index.html");
fs.writeFileSync(htmlPath, html);
fs.writeFileSync(path.join(output, "metrics.json"), JSON.stringify(metrics, null, 2) + "\n");
const executablePath = [process.env.EDGE_PATH, "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"].filter(Boolean).find(file => fs.existsSync(file));
assert.ok(executablePath, "Microsoft Edge not found; set EDGE_PATH");
const browser = await chromium.launch({ executablePath, headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1720, height: 1100 } });
  const errors = [], external = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => { if (/^https?:/.test(request.url())) external.push(request.url()); });
  await page.goto(pathToFileURL(htmlPath).href);
  const checks = seeds.flatMap(seed => versions.filter(v => v.id >= 3).map(version =>
    ({ svg: Buffer.from(render(seed, version.id).split(",")[1], "base64").toString("utf8"),
      lipstick: version.id === 9 && sandbox.avatarWardrobeProfile(seed).presentation === "feminine",
      earrings: sandbox.avatarRecipe(seed).accessory === 3 })));
  for (const record of records) for (const [style, uri] of Object.entries(record.wardrobeImages)) {
    checks.push({ svg: Buffer.from(uri.split(",")[1], "base64").toString("utf8"),
      lipstick: style.startsWith("feminine:") || record.wardrobe.theme === "goth",
      expression: record.wardrobe.expression,
      earrings: record.wardrobe.theme !== "butler" && (record.wardrobe.theme === "goth" || record.traits.accessory === 3) });
  }
  for (const seed of seeds) checks.push({
    svg: Buffer.from(render(seed, 9, {}, winkDirection).split(",")[1], "base64").toString("utf8"),
    lipstick: sandbox.avatarWardrobeProfile(seed).presentation === "feminine",
    expression: "friendly-wink", earrings: sandbox.avatarRecipe(seed).accessory === 3,
  });
  for (const seed of seeds) checks.push({
    svg: Buffer.from(render(seed, 9, {}, gothDirection).split(",")[1], "base64").toString("utf8"), earrings: true, lipstick: true,
  });
  const result = await page.evaluate(async checks => {
    const parser = new DOMParser(), failures = [];
    const lipstickShades = new Set();
    for (const { svg, earrings, lipstick = false, expression = "open" } of checks) {
      const doc = parser.parseFromString(svg, "image/svg+xml");
      if (doc.querySelector("parsererror,script,foreignObject,text,image,animate,animateTransform,feImage")) failures.push("Invalid/non-vector/animated SVG");
      if (!doc.querySelector('[data-feature="eyes"]')?.children.length) failures.push("No eyes");
      if (!doc.querySelector('[data-feature="mouth"]')?.children.length) failures.push("No mouth");
      const makeup = doc.querySelector('[data-feature="mouth"] [data-feature="lipstick"]');
      if (Boolean(makeup) !== lipstick) failures.push("Lipstick presentation mismatch");
      if (makeup) {
        const shade = makeup.getAttribute("data-shade");
        const channels = /^#[0-9a-f]{6}$/.test(shade) ? shade.slice(1).match(/../g).map(value => parseInt(value, 16)) : [];
        if (channels.length !== 3 || channels[0] <= channels[1] || channels[0] <= channels[2] ||
            !makeup.querySelector(`path[fill="${shade}"]`)) failures.push("Lipstick is not visibly painted red/pink");
        lipstickShades.add(shade);
      }
      if (doc.querySelectorAll("[data-earring]").length !== (earrings ? 2 : 0)) failures.push("Earring pair mismatch");
      const ids = [...doc.querySelectorAll("[id]")].map(node => node.id);
      if (new Set(ids).size !== ids.length) failures.push("Duplicate SVG ID");
      if (["study-v8", "study-v9"].includes(doc.documentElement.getAttribute("data-avatar-version")) &&
          doc.querySelector("filter")) failures.push("Refined study regained experimental filters");
      if (doc.documentElement.getAttribute("data-avatar-version") === "study-v9") {
        const closed = doc.querySelectorAll('[data-feature="eyes"] > [data-eye="closed"]');
        const open = doc.querySelectorAll('[data-feature="eyes"] > [data-eye="open"]');
        const expectedClosed = expression === "friendly-wink" ? 1 : 0;
        if (closed.length !== expectedClosed || open.length !== 2 - expectedClosed) failures.push("Live eye policy violated");
        if (expectedClosed) {
          if (!closed[0].matches('[data-expression="wink"]') ||
              !closed[0].querySelector('[data-feature="wink-cheek"]') ||
              !doc.querySelector('[data-feature="mouth"][data-expression="smile"]')) failures.push("Wink lost its friendly expression");
          const lid = closed[0].querySelector('[data-feature="wink-lid"]');
          const coordinates = lid?.getAttribute("d").match(/-?\d+(?:\.\d+)?/g).map(Number);
          if (!coordinates || coordinates[3] >= Math.min(coordinates[1], coordinates[5])) failures.push("Wink lid looks sleepy instead of lifted");
        }
        if (!doc.querySelector('[data-feature="wardrobe"] [data-feature="torso"]')) failures.push("Missing torso/wardrobe");
        if (!doc.querySelector('[data-feature="neck-anatomy"] [data-feature="neck"]')) failures.push("Missing shared neck construction");
        if (doc.documentElement.getAttribute("viewBox") !== "0 0 128 128") failures.push("Torso crop regressed");
        if (doc.querySelector('[data-feature="head"]').getAttribute("stroke-width") !== ".65") failures.push("Missing light contour");
        if (!doc.querySelector('[data-feature="silhouette-outline"]') ||
            doc.getElementById("portrait-figure")?.querySelector('[data-feature="silhouette-outline"]')) failures.push("Missing or recursive outer silhouette");
      }
      for (const node of doc.querySelectorAll("*")) for (const attribute of node.attributes) {
        for (const match of attribute.value.matchAll(/url\(#([^)]+)\)/g)) {
          if (!doc.getElementById(match[1])) failures.push("Unresolved paint or clip reference");
        }
        if (/^(href|src)$/i.test(attribute.name) && !attribute.value.startsWith("#")) failures.push("External SVG reference");
      }
    }
    await Promise.all([...document.images].map(image => image.decode()));
    if (lipstickShades.size < 3) failures.push("Lipstick lost its varied red/pink shades");
    return { failures, loaded: [...document.images].every(image => image.complete && image.naturalWidth > 0),
      small: [...document.querySelectorAll(".mini img")].every(image => image.getBoundingClientRect().width === 46) };
  }, checks);
  assert.deepEqual([...new Set(result.failures)], []);
  assert.ok(result.loaded && result.small, "Images failed decoding or 46px presentation");
  const facialHairChecks = await page.evaluate(async checks => {
    const parser = new DOMParser(), serializer = new XMLSerializer(), canvas = document.createElement("canvas");
    canvas.width = canvas.height = 46;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const raster = async uri => {
      const image = new Image();
      image.src = uri;
      await image.decode();
      context.clearRect(0, 0, 46, 46);
      context.drawImage(image, 0, 0, 46, 46);
      return context.getImageData(0, 0, 46, 46).data;
    };
    const geometry = new Set(), changedCounts = [];
    for (const { before, after, style, mouthStyle } of checks) {
      const baseline = parser.parseFromString(atob(before.split(",")[1]), "image/svg+xml");
      const styled = parser.parseFromString(atob(after.split(",")[1]), "image/svg+xml");
      const hair = styled.querySelector('[data-feature="facial-hair"]');
      if (!hair || hair.getAttribute("data-style") !== style) throw new Error("Missing authored facial hair");
      if (mouthStyle === 0) geometry.add([...hair.querySelectorAll("path")].map(path => path.getAttribute("d")).join("|"));
      hair.remove();
      if (serializer.serializeToString(styled) !== serializer.serializeToString(baseline)) {
        throw new Error("Facial hair changed the underlying face, expression, clothes or accessories");
      }
      const [oldPixels, newPixels] = await Promise.all([raster(before), raster(after)]);
      let changed = 0;
      for (let offset = 0; offset < oldPixels.length; offset += 4) {
        if ([0, 1, 2, 3].some(channel => oldPixels[offset + channel] !== newPixels[offset + channel])) changed++;
      }
      if (changed < 3) throw new Error("Facial hair is invisible at chat size");
      changedCounts.push(changed);
    }
    if (geometry.size < 6) throw new Error("Facial-hair styles share the same geometry");
    return changedCounts;
  }, facialHairStyles.flatMap(style => Array.from({ length: 5 }, (_, mouthStyle) => {
    const seed = seeds.find(candidate => sandbox.avatarRecipe(candidate).mouthStyle === mouthStyle);
    return { style, mouthStyle, before: render(seed, 9), after: render(seed, 9, {}, { facialHair: style }) };
  })));
  const openSeed = seeds.find(seed => sandbox.avatarRecipe(seed).eyeStyle === 0);
  const geometry = await page.evaluate(uris => {
    return uris.map(uri => {
      const doc = new DOMParser().parseFromString(atob(uri.split(",")[1]), "image/svg+xml");
      const svg = document.importNode(doc.documentElement, true);
      svg.style.cssText = "position:fixed;left:-1000px;top:0;visibility:hidden";
      document.body.append(svg);
      const eye = svg.querySelector('[data-eye="open"] > path').getBBox();
      const torso = (svg.querySelector('[data-feature="torso"]') || svg.querySelector("svg > g > path")).getBBox();
      const view = svg.viewBox.baseVal;
      const result = { eyeWidth: eye.width, eyeHeight: eye.height,
        eyeWidthFraction: eye.width / view.width, eyeHeightFraction: eye.height / view.height,
        irisFraction: 2 * Number(svg.querySelector('[data-eye="open"] circle').getAttribute("r")) / view.width,
        visibleTorsoFraction: (view.y + view.height - torso.y) / view.height,
        face: svg.querySelector('[data-feature="head"]').parentElement.innerHTML };
      svg.remove();
      return result;
    });
  }, [render(openSeed, 8), render(openSeed, 9, {}, { presentation: "feminine" }),
    render(openSeed, 9, { persona: "Fictional adult comedy guest" }, { presentation: "feminine", flair: "bold" })]);
  assert.ok(geometry[1].eyeWidth > geometry[0].eyeWidth * 1.15, "Eye aperture did not widen");
  assert.ok(geometry[1].eyeHeight > geometry[0].eyeHeight * 1.15, "Eye aperture did not open");
  assert.ok(geometry[1].eyeWidthFraction > geometry[0].eyeWidthFraction * 1.1, "Wider crop cancelled actual visible eye enlargement");
  assert.ok(geometry[1].eyeHeightFraction > geometry[0].eyeHeightFraction * 1.15, "Eye height is not larger at the same display size");
  assert.ok(geometry[1].irisFraction > geometry[0].irisFraction * 1.08, "Iris enlargement was cancelled by the crop");
  assert.ok(geometry[1].visibleTorsoFraction > geometry[0].visibleTorsoFraction * 1.9, "Torso framing barely changed");
  assert.equal(geometry[1].face, geometry[2].face, "Changing costume changed the face identity");
  if (previousRenderer) {
    const unchanged = records.filter(p => ["Current personas", "Synthetic wardrobe coverage"].includes(p.group)).map(p => ({
      previous: previousRenderer(p.seed, 9, p.metadata),
      current: render(p.seed, 9, p.metadata, p.appearance),
      goth: p.wardrobe.theme === "goth",
      butler: p.wardrobe.theme === "butler",
      individual: p.wardrobe.outfit !== "role",
    }));
    await page.evaluate(checks => {
      const parser = new DOMParser();
      for (const { previous, current, goth, butler, individual } of checks) {
        const parse = uri => parser.parseFromString(atob(uri.split(",")[1]), "image/svg+xml");
        const before = parse(previous), after = parse(current);
        if (butler) {
          if (!after.querySelector('[data-theme="butler"]') || !after.querySelector('[data-feature="moustache"]') ||
              !after.querySelector('[data-feature="mature-features"]')) throw new Error("Missing authored older-butler treatment");
        } else if (before.querySelector('[data-feature="head"]').getAttribute("d") !== after.querySelector('[data-feature="head"]').getAttribute("d") ||
            before.getElementById("skin").outerHTML !== after.getElementById("skin").outerHTML) throw new Error("Unrequested head or skin change");
        for (const doc of [before, after]) {
          (doc.querySelector('[data-feature="neck-anatomy"]') || doc.querySelector('[data-feature="neck"]'))?.remove();
        }
        const garment = doc => doc.querySelector('[data-feature="wardrobe"]').outerHTML.replace(/>\s+</g, "><");
        const sameClothes = garment(before) === garment(after);
        if (!goth && !butler && sameClothes === individual) {
          throw new Error(individual ? "Individual outfit still uses the old uniform" : "Generic wardrobe changed unintentionally");
        }
      }
    }, unchanged);
  }
  assert.ok(await page.locator("#comparisons .portrait").evaluateAll(images =>
    images.every(image => image.getBoundingClientRect().width === 220)), "Large comparison is not actually 220px");
  assert.ok(await page.locator("#detail .portrait").evaluateAll(images =>
    images.every(image => image.getBoundingClientRect().width === 512)), "Large inspection is not actually 512px");
  const imageUris = [...new Set(records.flatMap(record => [...Object.values(record.images), ...Object.values(record.wardrobeImages)]))];
  await page.evaluate(async uris => {
    for (let offset = 0; offset < uris.length; offset += 16) {
      await Promise.all(uris.slice(offset, offset + 16).map(async uri => {
        const image = new Image();
        image.src = uri;
        await image.decode();
        if (!image.naturalWidth) throw new Error("Coverage image failed native decode");
      }));
    }
  }, imageUris);
  const visibleNecks = await page.evaluate(async uris => {
    const parser = new DOMParser(), canvas = document.createElement("canvas");
    canvas.width = canvas.height = 512;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const lengths = [];
    for (const uri of uris) {
      const doc = parser.parseFromString(atob(uri.split(",")[1]), "image/svg+xml");
      const neck = doc.querySelector('[data-feature="neck"]');
      neck.setAttribute("fill", "#ff00ff");
      neck.setAttribute("stroke", "none");
      const image = new Image();
      image.src = "data:image/svg+xml;base64," + btoa(new XMLSerializer().serializeToString(doc));
      await image.decode();
      context.clearRect(0, 0, 512, 512);
      context.drawImage(image, 0, 0, 512, 512);
      const pixels = context.getImageData(256, 0, 1, 512).data;
      let longest = 0, length = 0;
      for (let y = 0; y < 512; y++) {
        const offset = y * 4;
        length = pixels[offset] > 245 && pixels[offset + 1] < 15 && pixels[offset + 2] > 245 ? length + 1 : 0;
        longest = Math.max(longest, length);
      }
      lengths.push(longest / 4);
    }
    return lengths;
  }, records.map(record => record.images[9]));
  assert.deepEqual(visibleNecks.flatMap((visible, index) =>
    visible < 4 ? [{ character: records[index].label, visibleNeckUnits: visible }] : []), [],
  "Collars hide the rendered neck; check actual layer visibility, not just the presence of a neck path");
  const outlinedRecords = current.length ? records.filter(p => p.group === "Current personas") : records.slice(0, 1);
  const silhouetteChecks = await page.evaluate(async uris => {
    const parser = new DOMParser(), serializer = new XMLSerializer(), canvas = document.createElement("canvas");
    canvas.width = canvas.height = 512;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const raster = async doc => {
      const image = new Image();
      image.src = "data:image/svg+xml;base64," + btoa(serializer.serializeToString(doc));
      await image.decode();
      context.clearRect(0, 0, 512, 512);
      context.drawImage(image, 0, 0, 512, 512);
      return context.getImageData(0, 0, 512, 512).data;
    };
    const changedCounts = [];
    for (const uri of uris) {
      const doc = parser.parseFromString(atob(uri.split(",")[1]), "image/svg+xml");
      const without = doc.cloneNode(true);
      without.querySelector('[data-feature="silhouette-outline"]').remove();
      const alphaOnly = without.cloneNode(true), figure = alphaOnly.getElementById("portrait-figure");
      for (const child of [...figure.parentElement.children]) if (child !== figure) child.remove();
      const [after, before, foreground] = await Promise.all([raster(doc), raster(without), raster(alphaOnly)]);
      let changed = 0;
      for (let y = 0; y < 512; y++) for (let x = 0; x < 512; x++) {
        const offset = (y * 512 + x) * 4;
        if (after[offset] === before[offset] && after[offset + 1] === before[offset + 1] &&
            after[offset + 2] === before[offset + 2] && after[offset + 3] === before[offset + 3]) continue;
        changed++;
        let nearFigure = false, nearTransparency = false;
        for (let dy = -4; dy <= 4 && !(nearFigure && nearTransparency); dy++) for (let dx = -4; dx <= 4; dx++) {
          if (x + dx < 0 || x + dx >= 512 || y + dy < 0 || y + dy >= 512) continue;
          const alpha = foreground[((y + dy) * 512 + x + dx) * 4 + 3];
          nearFigure ||= alpha > 0;
          nearTransparency ||= alpha < 255;
        }
        if (!nearFigure) throw new Error("Outline changed background away from the character");
        if (!nearTransparency) throw new Error("Outline changed interior artwork away from the silhouette");
      }
      if (changed < 20) throw new Error("Black silhouette edge did not actually render");
      changedCounts.push(changed);
    }
    return changedCounts;
  }, outlinedRecords.map(record => record.images[9]));
  const individualRecords = records.filter(p => p.group === "Synthetic individual outfits");
  await page.evaluate(uris => {
    const parser = new DOMParser(), geometry = new Set(), faces = new Set();
    for (const uri of uris) {
      const doc = parser.parseFromString(atob(uri.split(",")[1]), "image/svg+xml");
      const wardrobe = doc.querySelector('[data-feature="wardrobe"]');
      geometry.add([...wardrobe.querySelectorAll("path")].map(node => node.getAttribute("d")).join("|"));
      faces.add(doc.querySelector('[data-feature="head"]').parentElement.outerHTML);
    }
    if (geometry.size !== uris.length) throw new Error("Individual clothes only differ by color");
    if (faces.size !== 1) throw new Error("Individual outfits changed the shared synthetic face");
  }, individualRecords.map(record => record.images[9]));
  await page.evaluate(uris => {
    const parser = new DOMParser();
    const geometry = uris.map(uri => {
      const doc = parser.parseFromString(atob(uri.split(",")[1]), "image/svg+xml");
      return [...doc.querySelectorAll('[data-feature="wardrobe"] path')]
        .map(node => node.getAttribute("d")).join("|");
    });
    if (new Set(geometry).size !== uris.length) throw new Error("Current cast repeats garment geometry");
  }, records.filter(record => record.group === "Current personas").map(record => record.images[9]));
  assert.equal(await page.locator("#individual-cast article").count(), current.length);
  if (current.length) {
    await page.locator("#individual-cast button").first().click();
    assert.match(await page.locator("#identity").textContent(), new RegExp(current[0].label));
    await page.locator("#individual-wardrobes").screenshot({ path: path.join(output, "individual-cast.png") });
  }
  await page.click("#earrings");
  await page.evaluate(async () => Promise.all([...document.images].map(image => image.decode())));
  await page.locator("#comparisons").screenshot({ path: path.join(output, "iteration-overview.png") });
  await page.locator("#refinement-comparison").screenshot({ path: path.join(output, "08-vs-08b.png") });
  await page.locator("#detail").screenshot({ path: path.join(output, "iteration-detail.png") });
  await page.locator("#detail figure").last().screenshot({ path: path.join(output, "refined-512.png") });
  for (const [coverage, expected] of [["earrings", 8], ["skin", 6], ["expressions", 14]]) {
    await page.selectOption("#coverage", coverage);
    assert.equal(await page.locator("#roster article").count(), expected);
  }
  await page.selectOption("#coverage", "current");
  for (const version of versions.filter(v => v.id >= 3)) {
    await page.selectOption("#roster-version", String(version.id));
    await page.evaluate(async () => Promise.all([...document.images].map(image => image.decode())));
    await page.locator("#roster").screenshot({ path: path.join(output, `cast-v${version.id}.png`) });
  }
  await page.selectOption("#coverage", "wardrobe");
  assert.equal(await page.locator("#roster article").count(), 7);
  const originalImage = await page.locator('#comparisons [data-version="8"] .portrait').getAttribute("src");
  for (const presentation of presentations) {
    await page.selectOption("#presentation", presentation);
    for (const flair of flairOptions) {
      await page.selectOption("#flair", flair);
      assert.equal(await page.locator('#comparisons [data-version="8"] .portrait').getAttribute("src"), originalImage);
      assert.ok(await page.locator("#roster .details").evaluateAll((nodes, presentation) =>
        nodes.every(node => node.textContent.includes(presentation)), presentation));
      await page.evaluate(async () => Promise.all([...document.images].map(image => image.decode())));
      await page.locator("#roster").screenshot({ path: path.join(output, `wardrobe-${presentation}-${flair}.png`) });
    }
  }
  await page.selectOption("#presentation", "auto");
  await page.selectOption("#flair", "auto");
  await page.selectOption("#coverage", "individual");
  assert.equal(await page.locator("#roster article").count(), Object.keys(outfitDescriptions).length);
  await page.evaluate(async () => Promise.all([...document.images].map(image => image.decode())));
  await page.locator("#roster").screenshot({ path: path.join(output, "individual-outfits-synthetic.png") });
  const gothIndex = records.findIndex(p => p.metadata?.personaId === goblinId);
  const syntheticGothIndex = records.findIndex(p => p.group === "Synthetic art direction");
  for (const [index, name] of [[syntheticGothIndex, "goth-synthetic"], [gothIndex, "trash-goblin-goth"]]) {
    if (index < 0) continue;
    await page.selectOption("#persona", String(index));
    await page.evaluate(async () => Promise.all([...document.images].map(image => image.decode())));
    assert.match(await page.locator("#identity").textContent(), /Romantic goth/);
    await page.locator("#refinement-comparison").screenshot({ path: path.join(output, `${name}-comparison.png`) });
    await page.locator("#detail figure").last().screenshot({ path: path.join(output, `${name}-512.png`) });
    await page.evaluate(uri => {
      const doc = new DOMParser().parseFromString(atob(uri.split(",")[1]), "image/svg+xml");
      if (doc.querySelectorAll('[data-eye="open"]').length !== 2 ||
          doc.querySelectorAll("[data-earring]").length !== 2 ||
          !doc.querySelector('[data-feature="dark-lipstick"]') ||
          !doc.querySelector('[data-feature="choker"]') ||
          !doc.querySelector('[data-feature="lace-neckline"]') ||
          doc.querySelectorAll('[data-feature="smoky-eye"]').length !== 2) throw new Error("Missing gothic art direction");
    }, records[index].images[9]);
  }
  const rigIndex = records.findIndex(p => p.metadata?.personaId === "session-96f84287-724b-45f0-ada4-1168c5240762");
  if (rigIndex >= 0) {
    await page.selectOption("#persona", String(rigIndex));
    await page.evaluate(async () => Promise.all([...document.images].map(image => image.decode())));
    await page.locator("#detail figure").last().screenshot({ path: path.join(output, "rig-neck-512.png") });
  }
  await page.selectOption("#coverage", "earrings");
  await page.locator("#roster").screenshot({ path: path.join(output, "earring-coverage.png") });
  await page.selectOption("#coverage", "skin");
  await page.locator("#roster").screenshot({ path: path.join(output, "skin-coverage.png") });
  await page.click("#theme");
  assert.equal(await page.locator("#theme").getAttribute("aria-pressed"), "true");
  await page.locator("#comparisons").screenshot({ path: path.join(output, "light-comparison.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "Mobile gallery overflow");
  await page.emulateMedia({ reducedMotion: "reduce" });
  assert.equal(await page.evaluate(() => document.getAnimations().length), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, [], "Offline gallery made an external request");
  fs.writeFileSync(path.join(output, "validation.json"), JSON.stringify({
    seedsPerVersion: seeds.length, checkedSvgDocuments: checks.length, pairedEarringChecks: true,
    actualPersonas: current.length, syntheticCoverage: fixtures.length, versions: versions.map(v => v.id),
    mobileWidth: 390, externalRequests: external.length, errors, nativeDecodedImages: imageUris.length,
    preservedEarlyPortraitChecks: preservedChecks, metrics,
    individuallyDesignedOutfits: individualRecords.length + 1,
    neckVisibilityChecks: visibleNecks.length,
    minimumVisibleNeckUnits: Math.min(...visibleNecks),
    silhouetteBoundaryChecks: silhouetteChecks.length,
    facialHairExpressionChecks: facialHairChecks.length,
    minimumFacialHairChangedPixelsAt46px: Math.min(...facialHairChecks),
  }, null, 2) + "\n");
  console.log(JSON.stringify({ gallery: htmlPath, actualPersonas: current.length,
    versions: versions.length, checkedSvgDocuments: checks.length, metrics }, null, 2));
} finally {
  await browser.close();
}

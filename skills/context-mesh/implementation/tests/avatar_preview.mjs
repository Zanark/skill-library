import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const root = path.resolve(import.meta.dirname, "..");
const source = fs.readFileSync(path.join(root, "assets", "dashboard.js"), "utf8");
const start = source.indexOf("function avatarRecipe(seed) {");
const end = source.indexOf("\nfunction socialDateLabel(", start);
assert.ok(start >= 0 && end > start, "Cannot locate the standalone avatar renderer block");
const renderer = source.slice(start, end);
const sandbox = { btoa: text => Buffer.from(text, "latin1").toString("base64") };
vm.createContext(sandbox);
vm.runInContext(renderer, sandbox);

const compatibilityCases = [
  ["0".repeat(64), "5695c656d2e3c7d01f335b182cf3d58aa8520a8d07585832cc1d2b2cad284124"],
  ["f".repeat(64), "0c8502f0cac402961a4d78b30833af71de585907d7c2e3914155c1cd57359857"],
  ["0".repeat(32), "e5cbed7411b677e04408c31bfcfa3bd99ee5c2bdd0747bffb1d6f4adb5e835f6"],
  ["0".repeat(63) + "1", "97bbe8827cc3fbb4a3097b1760a46d2e228dbb306091c26703c08ed09c72404b"],
];
for (const [seed, fingerprint] of compatibilityCases) {
  assert.equal(createHash("sha256").update(sandbox.avatarDataUri(seed)).digest("hex"), fingerprint,
    "The candidate changed a previously saved face-v1 rendering");
  assert.equal(sandbox.avatarDataUriV2(seed), sandbox.avatarDataUriV2(seed.toUpperCase()),
    "The candidate does not preserve repeatability or legacy seed support");
}
for (const name of ["avatarDataUri", "avatarDataUriV2"]) {
  for (const seed of ["", "xyz", "f-g", null, undefined, 12]) {
    assert.throws(() => sandbox[name](seed), { name: "TypeError", message: /non-empty hexadecimal/ });
  }
  assert.equal(sandbox[name]("abcdef"), sandbox[name]("ABCDEF"), "Seed case changes identity");
  assert.notEqual(sandbox[name]("0".repeat(64)), sandbox[name]("0".repeat(63) + "1"),
    "The seed tail is ignored");
}

const hash = text => createHash("sha256").update(text).digest("hex");
const hairNames = ["Short", "Side-swept", "Curls", "Bob", "Long", "Spikes", "Bun", "Sparse side hair"];
const styleSamples = new Map();
const sampleSeeds = Array.from({ length: 256 }, (_, index) => hash(`face-v2-preview-${index}`));
for (const seed of sampleSeeds) {
  const style = sandbox.avatarRecipe(seed).hairStyle;
  if (!styleSamples.has(style)) styleSamples.set(style, { label: hairNames[style], seed });
  for (const name of ["avatarDataUri", "avatarDataUriV2"]) {
    const uri = sandbox[name](seed);
    assert.equal(uri, sandbox[name](seed), "A seed does not reproduce the same portrait");
    const svg = Buffer.from(uri.split(",")[1], "base64").toString("utf8");
    assert.match(svg, /^[\x00-\x7f]*$/, "The btoa encoder requires ASCII templates");
    assert.doesNotMatch(svg, /\b(?:NaN|undefined|Infinity)\b/);
  }
}
assert.equal(styleSamples.size, 8, "The preview does not exercise all hairstyles");

const argumentsList = process.argv.slice(2);
assert.ok(argumentsList.length === 0 || (argumentsList.length === 2 && argumentsList[0] === "--index"),
  "Usage: node tests\\avatar_preview.mjs [--index <context-index.json>]");
let current = [];
if (argumentsList.length) {
  const index = JSON.parse(fs.readFileSync(path.resolve(argumentsList[1]), "utf8"));
  assert.ok(Array.isArray(index.social?.personas) && index.social.personas.length,
    "The supplied index contains no social personas");
  current = index.social.personas.map(persona => {
    assert.equal(typeof persona.displayName, "string", "A persona is missing its display name");
    sandbox.avatarRecipe(persona.profileImageData);
    return { label: persona.displayName, seed: persona.profileImageData };
  });
}
const escape = text => String(text).replace(/[&<>"']/g, character =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
const card = (persona, index, prefix) => {
  const recipe = sandbox.avatarRecipe(persona.seed);
  return `<article class="card" id="${prefix}-${index}">
    <h3>${escape(persona.label)}</h3>
    <p class="traits">${hairNames[recipe.hairStyle]} &middot; same seed, palette and expression choices</p>
    <div class="pair">${[["face-v1", sandbox.avatarDataUri], ["face-v2 candidate", sandbox.avatarDataUriV2]].map(([label, render]) =>
      `<figure><figcaption>${label}</figcaption><img class="portrait" src="${render(persona.seed)}" alt="${escape(persona.label)} ${label} at 220 pixels"><div class="small"><img src="${render(persona.seed)}" alt="${escape(persona.label)} ${label} at 46 pixels"><span>46px</span></div></figure>`).join("")}</div>
  </article>`;
};
const styles = [...styleSamples.entries()].sort(([left], [right]) => left - right).map(([, persona]) => persona);
const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MeshBoard procedural avatar comparison</title>
<style>
*{box-sizing:border-box} :root{color-scheme:dark;--page:#151521;--card:#252536;--text:#f2effa;--muted:#bcb6d0;--line:#49415e}
body.light{color-scheme:light;--page:#f4f1fa;--card:#fff;--text:#282138;--muted:#655b76;--line:#d6cce5}
body{margin:0;padding:28px;font:15px/1.5 system-ui,sans-serif;background:var(--page);color:var(--text)}
header{display:flex;align-items:start;gap:24px;justify-content:space-between;margin-bottom:26px}
h1{font-size:30px;margin:0 0 8px}h2{font-size:22px;margin:28px 0 14px}p{margin:6px 0;color:var(--muted)}
button{padding:10px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text);cursor:pointer}
.notice{color:#d8b8ff}body.light .notice{color:#73448e}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,470px),1fr));gap:16px}
.card{padding:16px;border:1px solid var(--line);border-radius:18px;background:var(--card);box-shadow:0 6px 24px #00000014}
h3{font-size:17px;margin:0}.traits{font-size:12px;margin:3px 0 13px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}
figure{margin:0;min-width:0;display:flex;align-items:center;flex-direction:column;gap:9px}
figcaption{font-size:13px;font-weight:650}.portrait{width:220px;max-width:100%;height:auto;aspect-ratio:1;border-radius:18px}
.small{display:flex;align-items:center;gap:9px;color:var(--muted);font-size:12px}.small img{width:46px;height:46px;border-radius:10px}
@media(max-width:540px){body{padding:14px}h1{font-size:23px}header{flex-direction:column;gap:8px}.pair{gap:10px}}
</style></head><body>
<header><div><h1>Same characters. Richer procedural artwork.</h1><p>Original on the left; face-v2 candidate on the right. Large portraits are 220px, with actual 46px chat-size samples underneath.</p>
<p class="notice">Preview only. The live dashboard still uses face-v1. No persona files, seeds or color assignments are changed.</p></div>
<button id="theme" type="button" aria-pressed="false">&#9728; / &#9790; Theme</button></header>
${current.length ? `<h2>Current MeshBoard personas</h2><section id="current-avatars" class="grid">${current.map((persona, index) => card(persona, index, "current")).join("")}</section>` : ""}
<h2>All eight hairstyle families</h2><p>Deterministic synthetic seeds, not additional registered personas.</p>
<section id="style-avatars" class="grid">${styles.map((persona, index) => card(persona, index, "style")).join("")}</section>
<script>${renderer}
document.getElementById("theme").addEventListener("click",event=>{const light=document.body.classList.toggle("light");event.currentTarget.setAttribute("aria-pressed",String(light))});
</script></body></html>`;

const output = path.join(root, "output");
fs.mkdirSync(output, { recursive: true });
const htmlPath = path.join(output, "avatar-face-v2-preview.html");
fs.writeFileSync(htmlPath, html);
const edgePath = [process.env.EDGE_PATH, "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"].filter(Boolean).find(candidate => fs.existsSync(candidate));
assert.ok(edgePath, "Microsoft Edge was not found; set EDGE_PATH to its executable");
const browser = await chromium.launch({ executablePath: edgePath, headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1720, height: 1100 } });
  const errors = [];
  const network = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
  await page.goto(pathToFileURL(htmlPath).href);
  const result = await page.evaluate(async seeds => {
    await Promise.all([...document.images].map(image => image.decode()));
    const parser = new DOMParser();
    const failures = [];
    for (const seed of seeds) {
      const svg = atob(avatarDataUriV2(seed).split(",")[1]);
      const xml = parser.parseFromString(svg, "image/svg+xml");
      if (xml.querySelector("parsererror,text,script,image,foreignObject") ||
          xml.documentElement.getAttribute("data-avatar-version") !== "face-v2-preview" ||
          !xml.querySelector('[data-feature="eyes"]')?.children.length ||
          !xml.querySelector('[data-feature="mouth"]')?.children.length) failures.push(seed);
      for (const element of xml.querySelectorAll("*")) {
        for (const attribute of element.attributes) {
          for (const reference of attribute.value.matchAll(/url\(#([^)]+)\)/g)) {
            if (!xml.getElementById(reference[1])) failures.push(`Unresolved ${reference[1]}`);
          }
        }
      }
    }
    return {
      failures,
      loaded: [...document.images].every(image => image.complete && image.naturalWidth > 0),
      large: [...document.querySelectorAll(".portrait")].every(image => image.getBoundingClientRect().width === 220),
      small: [...document.querySelectorAll(".small img")].every(image => image.getBoundingClientRect().width === 46),
    };
  }, [...sampleSeeds, ...current.map(persona => persona.seed)]);
  assert.deepEqual(result.failures, []);
  assert.ok(result.loaded && result.large && result.small, "Portraits failed to decode or use the intended sizes");
  if (current.length) await page.locator("#current-avatars").screenshot({ path: path.join(output, "avatar-face-v2-current.png") });
  await page.locator("#style-avatars").screenshot({ path: path.join(output, "avatar-face-v2-styles.png") });
  await page.locator(".card").first().screenshot({ path: path.join(output, "avatar-face-v2-detail.png") });
  await page.click("#theme");
  assert.equal(await page.locator("#theme").getAttribute("aria-pressed"), "true");
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, "Mobile preview overflows");
  assert.deepEqual(network, [], "The preview requested an external resource");
  assert.deepEqual(errors, [], "Preview JavaScript failed");
  console.log(JSON.stringify({ legacyFingerprints: compatibilityCases.length, candidateSeeds: sampleSeeds.length,
    actualPersonas: current.length, hairstyleFamilies: styles.length, networkRequests: network.length, preview: htmlPath }, null, 2));
} finally {
  await browser.close();
}

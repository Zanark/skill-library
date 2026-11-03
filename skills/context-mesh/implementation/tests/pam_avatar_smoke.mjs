import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import vm from "node:vm";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const root = path.resolve(import.meta.dirname, "..");
const [dashboardPath, baselinePath, screenshotPath] = process.argv.slice(2);
assert.ok(dashboardPath && baselinePath, "Pass dashboard HTML and the pre-change avatar-studies.js");
const dashboard = fs.readFileSync(dashboardPath, "utf8").replaceAll("\r\n", "\n");
const source = fs.readFileSync(path.join(root, "assets", "dashboard.js"), "utf8");
const start = source.indexOf("function avatarRecipe(seed) {");
const end = source.indexOf("\nfunction socialDateLabel(", start);
assert.ok(start >= 0 && end > start);
const candidate = fs.readFileSync(path.join(root, "assets", "avatar-studies.js"), "utf8").replaceAll("\r\n", "\n");
const baseline = fs.readFileSync(baselinePath, "utf8").replaceAll("\r\n", "\n");
const renderer = artwork => {
  const sandbox = { btoa: text => Buffer.from(text, "latin1").toString("base64") };
  vm.createContext(sandbox);
  vm.runInContext(source.slice(start, end) + "\n" + artwork, sandbox);
  return sandbox;
};
const before = renderer(baseline);
const after = renderer(candidate);
const index = JSON.parse(fs.readFileSync(path.join(path.dirname(dashboardPath), "context-index.json"), "utf8"));
const pam = index.social.personas.find(persona => persona.displayName === "PAM");
assert.ok(pam);
const uri = after.personaAvatarDataUri(pam);
const svg = Buffer.from(uri.split(",")[1], "base64").toString("utf8");
assert.match(svg, /^[\x00-\x7f]*$/);
assert.doesNotMatch(svg, /<image\b|https?:\/\/(?!www\.w3\.org)|\b(?:NaN|undefined|Infinity)\b/);
for (const feature of ["teal-blazer", "ivory-blouse", "gold-pendant", "pam-name-badge",
  "open-blouse-neckline", "kiss-lips", "kiss-heart", "lipstick"]) {
  assert.ok(svg.includes(`data-feature="${feature}"`), feature);
}
assert.doesNotMatch(svg, /chin-rest-pose|wristwatch|gold-ring/);
assert.ok(svg.includes(">EXECUTIVE ASSISTANT</text>"));
assert.equal((svg.match(/data-eye="open"/g) || []).length, 1);
assert.equal((svg.match(/data-eye="closed"/g) || []).length, 1);
assert.equal((svg.match(/data-earring=/g) || []).length, 2);
assert.equal(uri, after.personaAvatarDataUri({ ...pam, profileImageData: pam.profileImageData.toUpperCase() }));
assert.notEqual(uri, before.personaAvatarDataUri(pam));
assert.equal(after.personaAvatarDataUri({ ...pam, personaId: "future-pam-session" }), uri);
assert.notEqual(after.personaAvatarDataUri({ ...pam, personaId: "unrelated", contextId: "unrelated" }), uri);
for (const persona of index.social.personas.filter(item => item.contextId !== pam.contextId)) {
  assert.equal(after.personaAvatarDataUri(persona), before.personaAvatarDataUri(persona),
    `Changed ${persona.displayName}'s portrait`);
}
for (const version of [3, 4, 5, 6, 7, 8]) {
  assert.equal(after.avatarStudyDataUri(pam.profileImageData, version),
    before.avatarStudyDataUri(pam.profileImageData, version), `Historical study ${version} changed`);
}
assert.throws(() => after.avatarStudyDataUri("abc", 9, {}, { theme: "pam", outfit: "zip-hoodie" }),
  { name: "TypeError" });

const activeArtwork = fs.readFileSync(path.resolve(path.dirname(dashboardPath), "..", "assets", "avatar-studies.js"),
  "utf8").replaceAll("\r\n", "\n");
assert.ok(dashboard.includes(activeArtwork), "Rebuild the dashboard before testing");
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pam-avatar-test-"));
const edge = [process.env.EDGE_PATH, "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"].find(file => file && fs.existsSync(file));
assert.ok(edge, "Microsoft Edge is required");
let browser;
try {
  const htmlPath = path.join(temporary, "dashboard.html");
  fs.writeFileSync(htmlPath, dashboard.replace(activeArtwork, () => candidate));
  browser = await chromium.launch({ executablePath: edge, headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route(/^https?:/, route => route.abort());
  await page.goto(pathToFileURL(htmlPath).href);
  await page.click('[data-view="social-view"]');
  const roster = page.locator(`.social-persona[data-persona-id="${pam.personaId}"]`);
  const portrait = roster.locator(".social-roster-avatar");
  await portrait.evaluate(image => image.decode());
  assert.equal(await portrait.getAttribute("src"), uri);
  assert.equal(await portrait.evaluate(image => image.naturalWidth), 128);
  assert.equal(await portrait.evaluate(image => image.getBoundingClientRect().width), 46);
  await roster.locator(".social-roster-profile-trigger").click();
  await page.locator("#social-profile-card:not([hidden])").waitFor();
  assert.equal(await page.locator(".social-profile-avatar").getAttribute("src"), uri);
  assert.equal(await page.locator(".social-profile-avatar").evaluate(image => image.getBoundingClientRect().width), 368);
  if (screenshotPath) await page.locator("#social-profile-card").screenshot({ path: screenshotPath });
  await page.keyboard.press("Escape");
  const chat = page.locator(`.social-profile-trigger[data-persona-id="${pam.personaId}"] .social-avatar`).first();
  assert.equal(await chat.getAttribute("src"), uri);
  await chat.click();
  assert.equal(await page.locator(".social-profile-avatar").evaluate(image => image.getBoundingClientRect().width), 220);
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 430, height: 900 });
  await roster.locator(".social-roster-profile-trigger").click();
  assert.equal(await page.locator(".social-profile-avatar").getAttribute("src"), uri);
  assert.ok(await page.locator(".social-profile-avatar").evaluate(image => {
    const box = image.getBoundingClientRect();
    return box.left >= 0 && box.right <= innerWidth;
  }));
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ result: "passed", unchangedPeerPortraits: index.social.personas.length - 1,
    historicalStudies: 6, sizes: [46, 220, 368], offline: true }));
} finally {
  if (browser) await browser.close();
  fs.rmSync(temporary, { recursive: true, force: true });
}

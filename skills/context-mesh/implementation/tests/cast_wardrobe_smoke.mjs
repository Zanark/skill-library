import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import vm from "node:vm";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const root = path.resolve(import.meta.dirname, "..");
const [dashboardPath, baselinePath, outputPath] = process.argv.slice(2);
assert.ok(dashboardPath && baselinePath,
  "Pass the generated dashboard, pre-change avatar-studies.js and optional screenshot directory");
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
const before = renderer(baseline), after = renderer(candidate);
const index = JSON.parse(fs.readFileSync(path.join(path.dirname(dashboardPath), "context-index.json"), "utf8"));
const cast = index.social.personas;
assert.ok(cast.length);
const preserved = new Set(["pam", "butler", "goth"]);
const checks = cast.map(persona => {
  const direction = after.avatarPortraitDirection(persona);
  const untouched = preserved.has(direction.theme);
  const oldUri = before.personaAvatarDataUri(persona), uri = after.personaAvatarDataUri(persona);
  if (untouched) assert.equal(uri, oldUri, `Changed preserved ${persona.displayName}`);
  else assert.notEqual(uri, oldUri, `${persona.displayName} was not refreshed`);
  assert.equal(uri, after.personaAvatarDataUri({ ...persona, profileImageData: persona.profileImageData.toUpperCase() }));
  for (const version of [3, 4, 5, 6, 7, 8]) {
    assert.equal(after.avatarStudyDataUri(persona.profileImageData, version),
      before.avatarStudyDataUri(persona.profileImageData, version), `Historical ${version} changed`);
  }
  const svg = Buffer.from(uri.split(",")[1], "base64").toString("utf8");
  assert.doesNotMatch(svg, /\b(?:NaN|undefined|Infinity)\b|<image\b|<filter\b/);
  return { name: persona.displayName, id: persona.personaId, oldUri, uri, untouched,
    synthetic: untouched ? null : after.avatarStudyDataUri("abc", 9, {}, { outfit: direction.outfit, presentation: "androgynous" }) };
});
assert.equal(checks.filter(check => check.untouched).length, 3, "The three exempt designs must remain present");
const edge = [process.env.EDGE_PATH, "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"].find(file => file && fs.existsSync(file));
assert.ok(edge, "Microsoft Edge is required");
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "cast-wardrobe-"));
let browser;
try {
  const html = fs.readFileSync(dashboardPath, "utf8").replaceAll("\r\n", "\n");
  const active = fs.readFileSync(path.resolve(path.dirname(dashboardPath), "..", "assets", "avatar-studies.js"), "utf8")
    .replaceAll("\r\n", "\n");
  assert.ok(html.includes(active), "Generated dashboard is stale");
  const candidatePath = path.join(temporary, "dashboard.html");
  fs.writeFileSync(candidatePath, html.replace(active, () => candidate));
  browser = await chromium.launch({ executablePath: edge, headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const errors = [], external = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route(/^https?:/, route => { external.push(route.request().url()); return route.abort(); });
  await page.goto(pathToFileURL(candidatePath).href);
  await page.evaluate(async checks => {
    const parser = new DOMParser(), geometry = new Set(), backdrops = new Set(), faces = new Set();
    const parse = uri => parser.parseFromString(atob(uri.split(",")[1]), "image/svg+xml");
    const wardrobe = doc => doc.querySelector('[data-feature="wardrobe"]').outerHTML;
    for (const check of checks) {
      const before = parse(check.oldUri), after = parse(check.uri);
      if (after.querySelector("parsererror,script,foreignObject,image,filter")) throw new Error(check.name + ": invalid SVG");
      for (const node of after.querySelectorAll("*")) for (const attribute of node.attributes) {
        for (const match of attribute.value.matchAll(/url\(#([^)]+)\)/g)) {
          if (!after.getElementById(match[1])) throw new Error(check.name + ": missing SVG definition");
        }
      }
      for (const uri of [check.uri, check.oldUri]) {
        const image = new Image();
        image.src = uri;
        await image.decode();
        if (image.naturalWidth !== 128) throw new Error(check.name + ": invalid native size");
      }
      if (check.untouched) continue;
      const face = doc => doc.querySelector('[data-feature="head"]').parentElement.outerHTML;
      if (face(before) !== face(after)) throw new Error(check.name + ": changed face, hair or expression");
      if (wardrobe(before) === wardrobe(after)) throw new Error(check.name + ": unchanged clothes");
      const prop = after.querySelector('[data-feature="name-backdrop"]');
      if (!prop?.children.length) throw new Error(check.name + ": missing name prop");
      backdrops.add([...prop.querySelectorAll("path")].map(node => node.getAttribute("d")).join("|"));
      const synthetic = parse(check.synthetic);
      faces.add(face(synthetic));
      geometry.add([...synthetic.querySelectorAll('[data-feature="wardrobe"] path')]
        .map(node => node.getAttribute("d")).join("|"));
    }
    const refreshed = checks.filter(check => !check.untouched).length;
    if (geometry.size !== refreshed || backdrops.size !== refreshed) throw new Error("Repeated garment or prop construction");
    if (faces.size !== 1) throw new Error("A garment changed the common synthetic face");
  }, checks);
  await page.click('[data-view="social-view"]');
  for (const check of checks) {
    const roster = page.locator(`.social-persona[data-persona-id="${check.id}"]`);
    const avatar = roster.locator(".social-roster-avatar");
    await avatar.evaluate(image => image.decode());
    assert.equal(await avatar.getAttribute("src"), check.uri, `${check.name}: roster`);
    assert.equal(await avatar.evaluate(image => image.getBoundingClientRect().width), 46);
    await roster.locator(".social-roster-profile-trigger").click();
    await page.locator("#social-profile-card:not([hidden])").waitFor();
    assert.equal(await page.locator(".social-profile-avatar").getAttribute("src"), check.uri, `${check.name}: profile`);
    await page.keyboard.press("Escape");
  }
  const visibleChat = page.locator(".social-profile-trigger .social-avatar");
  assert.ok(await visibleChat.count(), "No actual chat avatar checked");
  for (const image of await visibleChat.all()) {
    const id = await image.evaluate(node => node.closest("[data-persona-id]").dataset.personaId);
    const check = checks.find(check => check.id === id);
    assert.ok(check, "Chat author missing from cast");
    assert.equal(await image.getAttribute("src"), check.uri, `${check.name}: chat`);
  }
  if (outputPath) {
    fs.mkdirSync(outputPath, { recursive: true });
    await page.screenshot({ path: path.join(outputPath, "live-roster.png") });
    await page.setViewportSize({ width: 430, height: 900 });
    await page.locator(".social-roster-profile-trigger").first().click();
    assert.ok(await page.locator(".social-profile-avatar").evaluate(image => {
      const box = image.getBoundingClientRect();
      return box.left >= 0 && box.right <= innerWidth;
    }));
    await page.locator("#social-profile-card").screenshot({ path: path.join(outputPath, "mobile-profile.png") });
  }
  assert.deepEqual(errors, []);
  assert.ok(external.every(url => html.includes(url)), "The outfit renderer added an external resource");
  console.log(JSON.stringify({ result: "passed", cast: cast.length,
    redesigned: checks.filter(check => !check.untouched).length, preserved: 3,
    historicalVersionsPerPersona: 6, chatAvatars: await visibleChat.count(),
    existingMediaRequestsBlocked: external.length, networkAllowed: false }));
} finally {
  if (browser) await browser.close();
  fs.rmSync(temporary, { recursive: true, force: true });
}

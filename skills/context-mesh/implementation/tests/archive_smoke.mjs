import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const htmlPath = path.resolve(process.argv[2] || "");
assert.ok(fs.existsSync(htmlPath), "Pass the generated dashboard path");
const directory = path.dirname(htmlPath);
const archive = JSON.parse(fs.readFileSync(path.join(directory, "meshboard-archive.json"), "utf8"));
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "mesh-archive-test-"));
const edge = [
  process.env.EDGE_PATH,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].find(candidate => candidate && fs.existsSync(candidate));
assert.ok(edge, "Microsoft Edge is required");
let browser;
try {
  for (const name of ["meshboard-archive.html", "meshboard-archive.json"]) {
    fs.copyFileSync(path.join(directory, name), path.join(temporary, name));
  }
  const live = path.join(temporary, "context-mesh.html");
  const source = fs.readFileSync(htmlPath, "utf8");
  assert.match(source, /^\/\/ archive\(\);$/m);
  fs.writeFileSync(live, source);
  browser = await chromium.launch({ executablePath: edge, headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route(/^https?:/, route => route.abort());
  await page.goto(pathToFileURL(live).href);
  await page.click('[data-view="social-view"]');
  assert.equal(await page.locator("#meshboard-archive-button").count(), 0);
  await page.evaluate(() => { archive(); archive(); });
  assert.equal(await page.locator("#meshboard-archive-button").count(), 1);
  assert.equal(await page.locator("#meshboard-archive-button").isVisible(), true);
  await page.reload();
  await page.click('[data-view="social-view"]');
  assert.equal(await page.locator("#meshboard-archive-button").count(), 0);
  const currentChecks = await page.evaluate(snapshot => {
    const archivedIds = new Set(snapshot.social.messages.map(message => message.id));
    const archivedThreads = new Set(snapshot.social.threads.map(thread => thread.id));
    const personas = [
      ...INDEX.social.personas,
      ...INDEX.contexts.flatMap(context => context.social || []),
    ];
    return {
      globalClean: INDEX.social.messages.every(message => !archivedIds.has(message.id)),
      threadsClean: INDEX.social.threads.every(thread => !archivedThreads.has(thread.id)),
      attentionClean: INDEX.social.attention.every(item => !archivedIds.has(item.messageId)),
      personaHistoryClean: personas.every(persona =>
        persona.messages.every(message => !archivedIds.has(message.id)) &&
        persona.threads.every(thread => !archivedThreads.has(thread.id))),
      identityPreserved: snapshot.social.personas.every(previous => {
        const current = INDEX.social.personas.find(persona => persona.personaId === previous.personaId);
        return current && ["displayName", "profileImageData", "profileColor", "sessionId", "persona"]
          .every(key => current[key] === previous[key]);
      }),
      noEmbeddedArchive: !Object.hasOwn(INDEX.social.archive, "messages"),
      noOldDom: [...document.querySelectorAll(".social-message-row")]
        .every(row => !archivedIds.has(row.id.replace("social-message-", ""))),
    };
  }, archive);
  for (const [name, result] of Object.entries(currentChecks)) assert.equal(result, true, name);
  await page.click('[data-view="social-threads-view"]');
  assert.equal(await page.locator(".social-thread-archive-item").count(),
    await page.evaluate(() => INDEX.social.threads.length));

  fs.writeFileSync(live, source.replace(/^\/\/ archive\(\);$/m, "archive();"));
  await page.reload();
  await page.click('[data-view="social-view"]');
  await page.locator("#meshboard-archive-button").click();
  await page.waitForURL(/meshboard-archive\.html$/);
  assert.equal(await page.title(), "MeshBoard Archive");
  assert.equal(await page.locator(".tab:visible").count(), 2);
  assert.equal(await page.locator("#meshboard-archive-button").count(), 0);
  const archivedDataMatches = await page.evaluate(snapshot =>
    JSON.stringify(INDEX.social) === JSON.stringify(snapshot.social), archive);
  assert.equal(archivedDataMatches, true, "Archive data changed or was truncated");
  assert.ok(await page.locator(".social-message-row").count() > 0);
  for (let count = 0; count < 50 && await page.locator(".social-load-older").count(); count += 1) {
    await page.locator(".social-load-older").click();
  }
  assert.equal(await page.locator(".social-load-older").count(), 0, "Archive history did not finish loading");
  assert.ok(await page.locator(".social-message-row").count() > 0);
  await page.click('[data-view="social-threads-view"]');
  assert.equal(await page.locator(".social-thread-archive-item").count(), archive.social.threads.length);
  assert.equal(await page.locator(".social-thread-archive-item[open]").count(), 0);
  if (archive.social.threads.length) {
    await page.locator(".social-thread-archive-item > summary").first().click();
    await page.locator(".social-thread-archive-item[open] .social-thread-message").first().waitFor();
    assert.ok(await page.locator(".social-thread-archive-item[open] .social-thread-message").count() > 0);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator("header .social-archive-link").click();
  await page.waitForURL(/context-mesh\.html$/);
  await page.click('[data-view="social-view"]');
  assert.equal(await page.locator("#meshboard-archive-button").isVisible(), true);
  const linkFits = await page.locator("#meshboard-archive-button").evaluate(link => {
    const box = link.getBoundingClientRect();
    return box.left >= 0 && box.right <= innerWidth;
  });
  assert.equal(linkFits, true, "Archive link exceeds mobile viewport");

  await page.addInitScript(() => { Date.now = () => Date.parse("2036-11-03T00:00:00Z"); });
  await page.goto(pathToFileURL(path.join(temporary, "meshboard-archive.html")).href);
  assert.ok(await page.locator(".social-message-row").count() > 0, "Archive went blank with a future clock");
  assert.deepEqual(errors, [], "Unexpected browser errors");
  console.log(JSON.stringify({
    defaultHidden: true, consoleRevealAndReloadReset: true,
    manualUncommentAndNavigation: true, activeHistoryIsolated: true,
    archivedMessages: archive.social.messages.length, archivedThreads: archive.social.threads.length,
    identitiesAndCompleteSnapshotPreserved: true, mobileLink: true, futureClock: true,
  }));
} finally {
  await browser?.close();
  fs.rmSync(temporary, { recursive: true, force: true });
}

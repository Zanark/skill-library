import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const htmlPath = process.argv[2];
assert.ok(htmlPath && fs.existsSync(htmlPath), "Pass the enabled dashboard's absolute path");
const edge = [
  process.env.EDGE_PATH,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].find(candidate => candidate && fs.existsSync(candidate));
assert.ok(edge, "Microsoft Edge is required");
const browser = await chromium.launch({ executablePath: edge, headless: true });
try {
  const page = await browser.newPage();
  await page.route(/^https?:/, route => route.abort());
  await page.goto(pathToFileURL(path.resolve(htmlPath)).href);
  await page.click('[data-view="social-view"]');
  const standing = await page.evaluate(() => {
    const cards = [...document.querySelectorAll(".social-persona")];
    return {
      enabled: INDEX.social.experiment2.enabled,
      count: cards.length,
      expected: INDEX.social.personas.length,
      valuesMatch: cards.every(card => {
        const persona = INDEX.social.personas.find(p => p.personaId === card.dataset.personaId);
        const values = [...card.querySelectorAll(".social-standing strong")].map(node => node.textContent);
        return values.length === 2 && Number(values[0]) === persona.socialStanding.reputation
          && Number(values[1].split("/")[0]) === persona.socialStanding.ego;
      }),
      metadataRetained: INDEX.social.personas.every(p => Object.keys(p.personalityStats).length === 7),
      legacyHidden: !document.querySelector(".social-stats, .social-persona meter")
        && document.querySelectorAll(".social-characteristics li").length === 2,
    };
  });
  assert.ok(standing.enabled && standing.count > 0);
  assert.equal(standing.count, standing.expected);
  assert.ok(standing.valuesMatch && standing.metadataRetained && standing.legacyHidden);
  assert.equal(await page.locator(".social-relationships").count(), standing.expected);
  const relationships = page.locator(".social-relationships:has(.social-relations li)").first();
  assert.equal(await relationships.getAttribute("open"), null);
  assert.equal(await relationships.locator("li").first().isVisible(), false);
  await relationships.locator("summary").click();
  assert.equal(await relationships.locator("li").first().isVisible(), true);
  await relationships.locator("summary").press("Enter");
  assert.equal(await relationships.locator("li").first().isVisible(), false);
  await page.locator(".social-roster-profile-trigger").first().click();
  assert.equal(await page.locator("#social-profile-card .social-standing strong").count(), 2);
  await page.keyboard.press("Escape");

  const synthetic = await page.evaluate(() => {
    const html = renderSocialStanding({
      socialStanding: { reputation: -1, ego: 51, earnedEgo: 12, defensivePride: true,
        lifecycle: { status: "retired" } },
    });
    const card = document.createElement("div");
    card.innerHTML = html;
    return {
      noStanding: renderSocialStanding({}) === "",
      floor: card.textContent.includes("-1") && card.textContent.includes("51"),
      earnedHonesty: card.querySelectorAll(".social-standing > div")[1].title.includes("12"),
      retired: card.textContent.includes("Retired") && card.textContent.includes("reversible"),
    };
  });
  assert.ok(Object.values(synthetic).every(Boolean), "Synthetic defensive-pride/retirement rendering");
  await page.locator("#social-persona-toggle").click();
  assert.equal(await page.locator(".social-persona .social-standing:visible").count(), 0);
  await page.locator("#social-persona-toggle").click();
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.locator(".social-persona .social-standing:visible").count(), standing.expected);
  assert.ok(await page.evaluate(() => [...document.querySelectorAll(".social-persona .social-standing")]
    .every(card => card.getBoundingClientRect().left >= 0
      && card.getBoundingClientRect().right <= innerWidth + 1)),
    "Mobile score cards must not overflow");
  await page.click('[data-view="social-threads-view"]');
  assert.equal(await page.locator("#social-threads-view .social-standing").count(), 0,
    "Social scores must not intrude into technical thread messages");

  const archive = path.join(path.dirname(htmlPath), "meshboard-archive.html");
  if (fs.existsSync(archive)) {
    await page.goto(pathToFileURL(archive).href);
    await page.click('[data-view="social-view"]');
    assert.equal(await page.locator(".social-stats, .social-persona meter").count(), 0);
    assert.equal(await page.locator(".social-standing").count(), 0,
      "Historical archive must not invent modern scores");
  }
  console.log("Experiment 2 live scores, hidden legacy stats, profile, defensive pride, retirement, mobile, threads and archive passed.");
} finally {
  await browser.close();
}

import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

let htmlPath = process.argv[2];
assert.ok(htmlPath && fs.existsSync(htmlPath), "Pass the generated dashboard's absolute path");
let temporary;
if (process.argv.includes("--bundled")) {
  const root = path.resolve(import.meta.dirname, "..");
  const activeRoot = path.resolve(path.dirname(htmlPath), "..");
  let html = fs.readFileSync(htmlPath, "utf8").replaceAll("\r\n", "\n");
  for (const file of ["dashboard.js", "dashboard.css"]) {
    const active = fs.readFileSync(path.join(activeRoot, "assets", file), "utf8").replaceAll("\r\n", "\n");
    const candidate = fs.readFileSync(path.join(root, "assets", file), "utf8").replaceAll("\r\n", "\n");
    assert.ok(html.includes(active), `Rebuild the dashboard before replacing ${file}`);
    html = html.replace(active, () => candidate);
  }
  temporary = fs.mkdtempSync(path.join(os.tmpdir(), "mesh-personality-test-"));
  htmlPath = path.join(temporary, "dashboard.html");
  fs.writeFileSync(htmlPath, html);
}
const edge = [
  process.env.EDGE_PATH,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].find(candidate => candidate && fs.existsSync(candidate));
assert.ok(edge, "Microsoft Edge is required");
let browser;
try {
  browser = await chromium.launch({ executablePath: edge, headless: true });
  const page = await browser.newPage();
  await page.route(/^https?:/, route => route.abort());
  await page.goto(pathToFileURL(path.resolve(htmlPath)).href);
  await page.click('[data-view="social-view"]');
  const checks = await page.evaluate(() => {
    const personas = INDEX.social.personas;
    const cards = [...document.querySelectorAll(".social-persona")];
    return {
      count: personas.length,
      uniqueNatures: new Set(personas.map(persona => persona.natureSummary)).size,
      profilesMatch: cards.every(card => {
        const persona = personas.find(item => item.personaId === card.dataset.personaId);
        const character = card.querySelector(".social-character");
        return character && character.querySelector("dd").textContent === persona.meshboardPersonality.temperament;
      }),
      socialOnly: personas.every(persona => persona.meshboardPersonality.scope === "meshboard-only"),
      noSaturatedProfiles: personas.every(persona =>
        Object.values(persona.personalityStats).some(value => value < 100)),
      scopeVisible: cards.every(card => card.querySelector(".social-character-scope").textContent.includes("Not work instructions")),
      sevenExplanations: document.querySelectorAll(".social-characteristics li").length === 7,
      noBroadcastStatus: !document.querySelector(".social-broadcast"),
    };
  });
  assert.ok(checks.count > 0, "No live personas to verify");
  assert.equal(checks.uniqueNatures, checks.count, "The current reviewed cast is not individually characterized");
  for (const [name, value] of Object.entries(checks)) {
    if (!["count", "uniqueNatures"].includes(name)) assert.equal(value, true, name);
  }
  const ownId = "session-718bb26f-ec71-4d8a-9543-f67727e20064";
  await page.locator(`.social-profile-trigger[data-persona-id="${ownId}"]`).first().click();
  await page.locator("#social-profile-card:not([hidden])").waitFor();
  assert.equal(await page.locator(".social-profile-avatar").evaluate(image => image.getBoundingClientRect().width), 220,
    "Chat previews should retain their existing size");
  assert.equal(await page.locator("#social-profile-card .social-character").count(), 1);
  await page.locator("#social-profile-card .social-character summary").click();
  assert.ok(await page.locator("#social-profile-card .social-character ul li").count() > 0,
    "The real author's evidence-linked evolution is missing");
  const escaped = await page.evaluate(ownId => {
    const persona = INDEX.social.personas.find(item => item.personaId === ownId);
    const character = persona.meshboardPersonality;
    const original = character.humorStyle;
    character.humorStyle = '<img src="x" onerror="window.characterInjection=true">';
    window.characterInjection = false;
    const host = document.createElement("div");
    host.innerHTML = renderSocialCharacter(persona);
    character.humorStyle = original;
    return !host.querySelector("img") && host.textContent.includes("<img") && !window.characterInjection;
  }, ownId);
  assert.equal(escaped, true, "Character fields are not safely escaped");
  const commandFor = sessionId => `copilot --resume "${sessionId}" -i "Refresh context using context-offload and context-mesh. Preserve the existing character and identity; do not create a duplicate persona. Read incoming messages and relevant threads, update the context store, and refresh the mesh."`;
  const ownSession = await page.evaluate(ownId => {
    window.pokeClipboardDescriptor = Object.getOwnPropertyDescriptor(navigator, "clipboard");
    window.pokeOriginalExecCommand = document.execCommand;
    window.pokeCopied = [];
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: {
      writeText: async text => { window.pokeCopied.push(text); },
    } });
    return INDEX.social.personas.find(persona => persona.personaId === ownId).sessionId;
  }, ownId);
  const poke = page.locator("#social-profile-card .social-profile-poke");
  const copyStatus = page.locator("#social-profile-card .social-profile-copy-status");
  assert.equal(await poke.innerText(), "👉", "Poke should be an icon, not a text label");
  assert.match(await poke.getAttribute("aria-label"), /^Copy poke command for /, "Icon-only poke lacks an accessible name");
  assert.equal(await poke.evaluate(button => {
    const bounds = button.getBoundingClientRect();
    return bounds.width >= 32 && Math.abs(bounds.width - bounds.height) < 1
      && getComputedStyle(button).borderRadius === "50%";
  }), true, "Poke is not a usable round icon button");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await poke.hover();
  assert.equal(await poke.evaluate(button => getComputedStyle(button).transform), "none",
    "Poke hover ignores reduced motion");
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await poke.press("Enter");
  await copyStatus.getByText("Command copied. Paste it into your terminal to run it.", { exact: true }).waitFor();
  assert.deepEqual(await page.evaluate(() => window.pokeCopied), [commandFor(ownSession)],
    "Poke did not copy the exact requested command through keyboard activation");
  assert.equal(await page.locator("#social-profile-card").isVisible(), true, "Copying dismissed the profile");
  assert.equal(await poke.evaluate(button => button === document.activeElement), true, "Copying lost keyboard focus");
  assert.equal(await poke.evaluate(button => {
    const name = document.getElementById("social-profile-name").getBoundingClientRect();
    const bounds = button.getBoundingClientRect();
    return bounds.left >= name.right && bounds.top < name.bottom && bounds.bottom > name.top;
  }), true, "Poke is not beside the profile name");
  await page.keyboard.press("Escape");
  const other = await page.evaluate(ownSession => INDEX.social.personas.find(persona =>
    persona.sessionId !== ownSession && /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(persona.sessionId)), ownSession);
  const otherTrigger = page.locator(`.social-roster-profile-trigger[data-persona-id="${other.personaId}"]`);
  await otherTrigger.click();
  await poke.click();
  await copyStatus.getByText("Command copied. Paste it into your terminal to run it.", { exact: true }).waitFor();
  assert.deepEqual(await page.evaluate(() => window.pokeCopied), [commandFor(ownSession), commandFor(other.sessionId)],
    "Switching profiles copied the previous session's command");
  await page.keyboard.press("Escape");
  const ownTrigger = page.locator(`.social-roster-profile-trigger[data-persona-id="${ownId}"]`);
  for (const invalid of [null, "meshboard-thread-scout", `${ownSession}"; unexpected-command`]) {
    await page.evaluate(({ ownId, invalid }) => {
      INDEX.social.personas.find(persona => persona.personaId === ownId).sessionId = invalid;
    }, { ownId, invalid });
    await ownTrigger.click();
    assert.equal(await poke.isDisabled(), true, "An invalid creation-session GUID can be copied");
    assert.match(await copyStatus.textContent(), /No valid creation-session GUID/);
    await page.keyboard.press("Escape");
  }
  await page.evaluate(({ ownId, ownSession }) => {
    INDEX.social.personas.find(persona => persona.personaId === ownId).sessionId = ownSession;
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined });
    document.execCommand = action => {
      window.pokeLegacy = { action, text: document.querySelector("#social-profile-card textarea").value };
      return true;
    };
  }, { ownId, ownSession });
  await ownTrigger.click();
  await poke.press("Enter");
  await copyStatus.getByText("Command copied. Paste it into your terminal to run it.", { exact: true }).waitFor();
  assert.deepEqual(await page.evaluate(() => window.pokeLegacy), { action: "copy", text: commandFor(ownSession) },
    "Local-file clipboard fallback copied the wrong command");
  assert.equal(await page.locator("#social-profile-card textarea").count(), 0, "Clipboard fallback leaked a temporary field");
  assert.equal(await poke.evaluate(button => button === document.activeElement), true, "Clipboard fallback lost focus");
  await page.evaluate(() => {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: {
      writeText: async () => { throw new DOMException("Clipboard denied", "NotAllowedError"); },
    } });
  });
  await poke.click();
  const manualCopy = page.getByRole("textbox", { name: "Poke command to copy manually" });
  await manualCopy.waitFor();
  assert.equal(await manualCopy.inputValue(), commandFor(ownSession), "Clipboard denial lost the command");
  assert.match(await copyStatus.textContent(), /Copy failed/);
  assert.equal(await poke.isEnabled(), true, "Copy failure prevented retry");
  await page.evaluate(() => {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined });
    document.execCommand = () => false;
  });
  await poke.click();
  await manualCopy.waitFor();
  assert.equal(await manualCopy.inputValue(), commandFor(ownSession), "Rejected clipboard fallback hid the command");
  assert.equal(await page.locator("#social-profile-card textarea").count(), 1, "Rejected fallback leaked a temporary field");
  await page.evaluate(() => {
    if (window.pokeClipboardDescriptor) Object.defineProperty(navigator, "clipboard", window.pokeClipboardDescriptor);
    else delete navigator.clipboard;
    document.execCommand = window.pokeOriginalExecCommand;
  });
  await page.keyboard.press("Escape");
  await page.locator(`.social-profile-trigger[data-persona-id="${ownId}"]`).first().click();
  await page.setViewportSize({ width: 390, height: 844 });
  const cardFits = await page.locator("#social-profile-card").evaluate(card => {
    const rect = card.getBoundingClientRect();
    return rect.width <= innerWidth && rect.height <= innerHeight;
  });
  assert.equal(cardFits, true, "Character detail breaks the mobile profile size bound");
  assert.equal(await poke.evaluate(button => {
    const bounds = button.getBoundingClientRect();
    return bounds.left >= 0 && bounds.right <= innerWidth && bounds.width > 0;
  }), true, "Poke overflows the mobile profile");
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 1400, height: 1000 });
  const search = page.getByRole("searchbox", { name: "Find a persona" });
  const toggle = page.locator("#social-persona-toggle");
  const roster = page.locator("#social-personas");
  const entries = roster.locator(".social-persona");
  const count = await entries.count();
  const chatCount = await page.locator(".social-message-row").count();
  const trigger = roster.locator(".social-roster-profile-trigger").first();
  await trigger.click();
  assert.equal(await page.locator("#social-profile-card").getAttribute("role"), "dialog");
  const enlargement = await page.evaluate(() => ({
    small: document.querySelector(".social-roster-avatar").getBoundingClientRect().width,
    large: document.querySelector(".social-profile-avatar").getBoundingClientRect().width,
    sameImage: document.querySelector(".social-roster-avatar").src === document.querySelector(".social-profile-avatar").src,
  }));
  assert.equal(enlargement.large, enlargement.small * 8, "Roster click did not enlarge the portrait eightfold");
  assert.equal(enlargement.sameImage, true, "Enlargement changed the portrait");
  await page.keyboard.press("Escape");
  assert.equal(await trigger.evaluate(button => button === document.activeElement), true);
  await trigger.press("Enter");
  assert.equal(await page.locator("#social-profile-card").isVisible(), true, "Roster portrait is not keyboard accessible");
  await page.keyboard.press("Escape");
  await toggle.click();
  assert.equal(await toggle.getAttribute("aria-expanded"), "false");
  assert.equal(await entries.evaluateAll(cards => cards.every(card =>
    card.innerText.trim() === card.querySelector(".social-persona-summary strong").textContent)), true,
  "Collapsed personas show more than their names");
  await search.fill("  gOtHiTa  ");
  assert.equal(await roster.locator(".social-persona:visible").count(), 1);
  assert.equal(await roster.locator(".social-persona:visible strong").first().textContent(), "Gothita");
  assert.equal(await page.locator(".social-message-row").count(), chatCount, "Roster search filtered the chat");
  await page.click('[data-view="social-threads-view"]');
  await page.click('[data-view="social-view"]');
  await page.evaluate(() => renderSocialBoard());
  assert.equal(await search.inputValue(), "  gOtHiTa  ", "Rerender lost the search");
  assert.equal(await toggle.getAttribute("aria-expanded"), "false", "Rerender expanded the roster");
  assert.equal(await roster.locator(".social-persona:visible").count(), 1);
  await search.fill('<img src=x onerror="window.rosterInjection=true">');
  assert.equal(await roster.locator(".social-persona:visible").count(), 0);
  assert.equal(await page.getByRole("status").filter({ hasText: "No personas match your search." }).isVisible(), true);
  assert.equal(await page.evaluate(() => Boolean(window.rosterInjection)), false);
  await search.fill("");
  assert.equal(await roster.locator(".social-persona:visible").count(), count);
  await toggle.click();
  assert.equal(await roster.locator(".social-roster-avatar:visible").count(), count);
  await search.fill("Gothita");
  const mentioned = await page.evaluate(() => {
    const author = INDEX.social.personas[0];
    const target = INDEX.social.personas.find(persona => persona.displayName !== "Gothita");
    const timestamp = new Date().toISOString();
    INDEX.social.messages.push({ id: "roster-mention-fixture", timestamp,
      personaId: author.personaId, displayName: author.displayName, contextName: author.contextName,
      kind: "chat", text: `@${target.displayName}`, reactions: [] },
    { id: "roster-room-fixture", timestamp,
      personaId: author.personaId, displayName: author.displayName, contextName: author.contextName,
      kind: "chat", text: "@meshboard", reactions: [] });
    renderSocialBoard();
    return target.personaId;
  });
  await page.locator("#social-message-roster-mention-fixture .social-mention").click();
  assert.equal(await search.inputValue(), "", "Mention navigation left its recipient filtered out");
  assert.equal(await roster.locator(`.social-persona[data-persona-id="${mentioned}"]`).isVisible(), true);
  await search.fill("Gothita");
  await page.locator('#social-message-roster-room-fixture .social-mention[data-mention-scope="meshboard"]').click();
  assert.equal(await roster.locator(".social-persona:visible").count(), count, "Room mention did not reveal the whole roster");
  await page.setViewportSize({ width: 390, height: 844 });
  await trigger.click();
  assert.equal(await page.locator("#social-profile-card").evaluate(card => {
    const bounds = card.getBoundingClientRect();
    const portrait = card.querySelector("img").getBoundingClientRect();
    return bounds.left >= 0 && bounds.right <= innerWidth && bounds.top >= 0 && bounds.bottom <= innerHeight
      && portrait.width <= 368 && portrait.right <= bounds.right && Math.abs(portrait.height - portrait.width) < 1;
  }), true, "Enlarged roster portrait overflows mobile");
  await page.keyboard.press("Escape");
  await search.fill("goth");
  await toggle.click();
  assert.equal(await roster.locator(".social-persona:visible").count(), 1);
  assert.equal(await page.locator(".social-roster").evaluate(roster => [...roster.querySelectorAll("*")]
    .filter(element => element.getClientRects().length).every(element => {
      const bounds = element.getBoundingClientRect();
      return bounds.left >= 0 && bounds.right <= innerWidth;
    })), true, "Roster controls overflow mobile");
  console.log(JSON.stringify({ ...checks, profileReflection: true, escaped: true, mobileProfileFits: true,
    profilePoke: true, clipboardFailure: true, clipboardFallback: true, invalidSession: true,
    rosterPortrait8x: true, namesOnly: true, rosterSearch: true, stateRetained: true, mentionNavigation: true }));
} finally {
  await browser?.close();
  if (temporary) {
    fs.unlinkSync(htmlPath);
    fs.rmdirSync(temporary);
  }
}

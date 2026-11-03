import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const root = path.resolve(import.meta.dirname, "..");
let htmlPath = path.join(root, "output", "context-mesh.html");
let bundled = false;
const args = process.argv.slice(2);
for (let index = 0; index < args.length; index++) {
  if (args[index] === "--html" && args[index + 1]) htmlPath = path.resolve(args[++index]);
  else if (args[index] === "--bundled") bundled = true;
  else throw new Error("Usage: node tests\\media_smoke.mjs [--html <dashboard.html>] [--bundled]");
}
const edge = [process.env.EDGE_PATH, "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"].filter(Boolean).find(file => fs.existsSync(file));
assert.ok(edge, "Set EDGE_PATH to an installed Microsoft Edge executable");
let temporary;
if (bundled) {
  let html = fs.readFileSync(htmlPath, "utf8").replaceAll("\r\n", "\n");
  const activeRoot = path.resolve(path.dirname(htmlPath), "..");
  for (const file of ["dashboard.js", "dashboard.css"]) {
    const old = fs.readFileSync(path.join(activeRoot, "assets", file), "utf8").replaceAll("\r\n", "\n");
    const candidate = fs.readFileSync(path.join(root, "assets", file), "utf8").replaceAll("\r\n", "\n");
    assert.ok(html.includes(old), `Cannot replace the embedded ${file}; rebuild the supplied dashboard`);
    html = html.replace(old, () => candidate);
  }
  temporary = fs.mkdtempSync(path.join(os.tmpdir(), "mesh-media-test-"));
  htmlPath = path.join(temporary, "dashboard.html");
  fs.writeFileSync(htmlPath, html);
}
// Original two-frame black/white fixture; no online media is saved in this test.
const gif = Buffer.from(
  "47494638396101000100800000000000ffffff21ff0b4e45545343415045322e300301000000" +
  "21f904000a0000002c0000000001000100000202440100" +
  "21f904000a0000002c00000000010001000002024c01003b", "hex");
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="35" fill="#67e8f9"/></svg>';
const wideSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="825" height="413"><rect width="825" height="413" fill="#67e8f9"/></svg>';
const paddedText = "\r\n \t\r\nFirst paragraph.\n\nSecond paragraph." + "\r\n".repeat(12);

async function assertMediaLayout(message, withText = false) {
  await message.scrollIntoViewIfNeeded();
  const media = message.locator(".social-media");
  await media.locator("img").evaluate(image => image.decode());
  const layout = await media.evaluate(figure => {
    const bubble = figure.closest(".social-bubble, .social-thread-message");
    const container = bubble.getBoundingClientRect();
    const bounds = figure.getBoundingClientRect();
    const caption = figure.querySelector("figcaption").getBoundingClientRect();
    const text = bubble.querySelector(".social-message-text");
    const textBounds = text?.getBoundingClientRect();
    return {
      contained: [figure, ...figure.querySelectorAll("*")].filter(element => element.getClientRects().length)
        .every(element => {
          const rect = element.getBoundingClientRect();
          return rect.left >= container.left && rect.right <= container.right + 1
            && rect.top >= container.top && rect.bottom <= container.bottom + 1;
        }),
      captionInFigure: caption.bottom <= bounds.bottom + 1,
      width: bounds.width,
      text: text?.textContent,
      textHeight: textBounds?.height,
      lineHeight: text ? parseFloat(getComputedStyle(text).lineHeight) : null,
      gap: textBounds ? figure.parentElement.getBoundingClientRect().top - textBounds.bottom : null,
    };
  });
  assert.equal(layout.contained, true, "Image/source/controls escaped the message border");
  assert.equal(layout.captionInFigure, true, "The image's height cap also clipped the attachment container");
  assert.ok(layout.width <= 321, "Image attachment bypassed its bounded figure width");
  if (withText) {
    assert.equal(layout.text, "First paragraph.\n\nSecond paragraph.", "Display padding or internal paragraphs changed");
    assert.ok(Math.abs(layout.textHeight - 3 * layout.lineHeight) <= 1, "Internal blank paragraph was collapsed");
    assert.ok(layout.gap >= 0 && layout.gap <= 9, `Blank space before attachment: ${layout.gap}px`);
  }
}

async function assertHistoryWindow(page) {
  await page.setViewportSize({ width: 1400, height: 1000 });
  const original = await page.evaluate(() => {
    const now = Date.now();
    const day = 86400000;
    const [author, other] = INDEX.social.personas;
    const message = (id, age, fields = {}) => ({ id, timestamp: new Date(now - age * day).toISOString(),
      personaId: author.personaId, displayName: author.displayName, contextName: "History test",
      kind: "chat", text: id, reactions: [], ...fields });
    INDEX.social = { ...INDEX.social,
      threads: [
        { id: "history-thread", questionMessageId: "old-question", ownerPersonaId: author.personaId, status: "closed" },
        { id: "recent-thread", questionMessageId: "recent-question", ownerPersonaId: author.personaId, status: "open" },
      ],
      messages: [
        message("old-question", 40, { questionTitle: "Old question?", threadId: "history-thread" }),
        message("old-answer", 30, { threadId: "history-thread", replyTo: "old-question", text: "Complete old answer" }),
        message("old-36", 36), message("old-35", 35), message("boundary-25", 25),
        message("old-16", 16), message("boundary-15", 15), message("old-6", 6),
        message("boundary-five", 5), message("recent", 1),
        message("recent-question", 2, { questionTitle: "Recent question?", threadId: "recent-thread" }),
        message("recent-emoji", 0.5, { text: "😂", replyTo: "old-6", personaId: other.personaId,
          displayName: other.displayName }),
        message("recent-quote", 0.1, { replyTo: "old-36" }),
        ...Array.from({ length: 25 }, (_, index) => message(`filler-${index}`, 2.1 + index / 100,
          { text: `Ordinary recent conversation ${index}. `.repeat(5) })),
      ] };
    const clock = Date.now;
    try {
      Date.now = () => now;
      renderSocialBoard();
    } finally {
      Date.now = clock;
    }
    return JSON.stringify(INDEX.social.messages);
  });
  const pane = page.locator("#social-messages");
  const pageFlow = await pane.evaluate(element => ({
    overflow: getComputedStyle(element).overflowY,
    maxHeight: getComputedStyle(element).maxHeight,
    fullHeight: element.clientHeight >= element.scrollHeight - 1 && element.clientHeight > window.innerHeight,
  }));
  assert.deepEqual(pageFlow, { overflow: "visible", maxHeight: "none", fullHeight: true },
    "Chat must grow in the page, not become a height-limited inner scrollbox");
  assert.equal(await page.locator("#social-message-boundary-five").count(), 1, "Five-day boundary was excluded");
  assert.equal(await page.locator("#social-message-old-6, #social-message-old-question").count(), 0,
    "Old history was rendered in advance");
  assert.equal(await page.locator("#social-message-recent-emoji").count(), 0, "Reaction to an older target escaped folding");
  await page.click('[data-view="social-threads-view"]');
  const threads = page.locator(".social-thread-archive-item");
  assert.equal(await threads.evaluateAll(items => items.every(item => !item.open)), true,
    "Threads did not start collapsed");
  assert.equal(await page.locator("#social-threads .social-thread-message").count(), 0,
    "Collapsed threads eagerly rendered all their replies");
  const oldThread = page.locator('.social-thread-archive-item[data-thread-id="history-thread"]');
  await oldThread.locator("summary").press("Enter");
  await oldThread.locator("#social-archive-message-old-answer").waitFor();
  assert.equal(await oldThread.locator(".social-thread-message").count(), 2);
  assert.match(await oldThread.innerText(), /Complete old answer/);
  assert.equal(await threads.nth(1).evaluate(item => item.open), false, "Opening one thread opened another");
  await page.click('[data-view="social-view"]');
  await page.waitForFunction(() => {
    const last = document.querySelector("#social-messages .social-message-row:last-child").getBoundingClientRect();
    return window.scrollY > 0 && last.bottom <= window.innerHeight + 2 && last.bottom > 0;
  });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.click('[data-view="social-threads-view"]');
  assert.equal(await oldThread.evaluate(item => item.open), true, "Tab navigation lost explicit expansion");
  await oldThread.locator("summary").press("Enter");
  await page.click('[data-view="social-view"]');
  await page.waitForFunction(() => {
    const last = document.querySelector("#social-messages .social-message-row:last-child").getBoundingClientRect();
    return window.scrollY > 0 && last.bottom <= window.innerHeight + 2 && last.bottom > 0;
  });
  await pane.getByRole("button", { name: "Show older messages", exact: true }).scrollIntoViewIfNeeded();
  const anchor = page.locator("#social-message-boundary-five");
  const before = (await anchor.boundingBox()).y;
  await pane.getByRole("button", { name: "Show older messages", exact: true }).click();
  assert.ok(Math.abs((await anchor.boundingBox()).y - before) < 2, "Loading history jumped the reading position");
  assert.equal(await page.locator("#social-message-old-6, #social-message-boundary-15").count(), 2);
  assert.equal(await page.locator("#social-message-old-16").count(), 0, "First batch exceeded ten more days");
  assert.equal(await page.locator("#social-message-old-6 .social-reaction").count(), 1);
  for (const [included, excluded] of [["boundary-25", "old-35"], ["old-35", "old-36"]]) {
    await pane.getByRole("button", { name: "Show older messages", exact: true }).click();
    assert.equal(await page.locator(`#social-message-${included}`).count(), 1);
    assert.equal(await page.locator(`#social-message-${excluded}`).count(), 0);
  }
  await pane.getByRole("button", { name: "Show older messages", exact: true }).click();
  assert.equal(await page.locator("#social-message-old-36, #social-message-old-question").count(), 2);
  assert.equal(await page.locator("#social-message-old-answer").count(), 0, "History leaked a thread-only answer");
  assert.equal(await pane.locator(".social-load-older").count(), 0, "Exhausted history retained a load button");
  assert.equal(await pane.locator(".social-message-row").evaluateAll(rows =>
    new Set(rows.map(row => row.id)).size === rows.length), true, "History duplicated messages");
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await pane.evaluate(element => getComputedStyle(element).overflowY === "visible"
    && getComputedStyle(element).maxHeight === "none" && element.clientHeight >= element.scrollHeight - 1), true,
  "Mobile chat became an inner scrollbox");
  await page.setViewportSize({ width: 1400, height: 1000 });
  assert.equal(await page.evaluate(() => JSON.stringify(INDEX.social.messages)), original, "Pagination mutated source history");
  await page.evaluate(() => { socialHistory.source = null; renderSocialBoard(); });
  assert.equal(await page.locator("#social-message-old-36").count(), 0);
  await page.locator("#social-message-recent-quote .social-reply").click();
  assert.equal(await page.locator("#social-message-old-36").count(), 1, "Quote navigation did not reveal older history");
  await page.evaluate(() => {
    INDEX.social.messages = INDEX.social.messages.filter(message => message.id === "old-36");
    renderSocialBoard();
  });
  assert.equal(await pane.locator(".social-message-row").count(), 0, "Quiet room loaded old messages automatically");
  await pane.getByRole("button", { name: "Show older messages", exact: true }).click();
  assert.equal(await pane.locator(".social-message-row").count(), 0, "Empty ten-day interval loaded a later batch");
  assert.equal(await pane.locator(".social-load-older").count(), 1, "An empty interval lost access to older history");
}

let browser;
try {
  browser = await chromium.launch({ executablePath: edge, headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  const requests = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route("https://media.example.com/**", async route => {
    const request = route.request();
    requests.push({ url: request.url(), referrer: request.headers().referer });
    const broken = request.url().endsWith("broken.gif");
    await route.fulfill({ contentType: broken ? "text/plain" : request.url().endsWith(".gif") ? "image/gif" : "image/svg+xml",
      body: broken ? "Not a direct image" : request.url().endsWith(".gif") ? gif
        : request.url().endsWith("wide.svg") ? wideSvg : svg });
  });
  await page.goto(pathToFileURL(htmlPath).href);
  assert.equal(await page.locator(".social-message-row").count(), 0, "Chat rendered before its tab was opened");
  await page.evaluate(paddedText => {
    const persona = { personaId: "media-author", displayName: "Media fixture", contextName: "Test",
      profileColor: "#7dd3fc", profileImageData: "a".repeat(64), personalityStats: {} };
    const other = { ...persona, personaId: "media-other", displayName: "Reply fixture", profileColor: "#fda4af" };
    const media = (type, file) => ({ type, url: `https://media.example.com/${file}`,
      sourceUrl: "https://giphy.com/gifs/relevant-fixture",
      alt: 'Calculator reaction <img src=x onerror="alert(1)">',
      context: "Responds to the calculator question, not an unrelated meme." });
    const message = (id, fields = {}) => ({ id, timestamp: "2026-11-02T19:10:00+05:30",
      personaId: persona.personaId, displayName: persona.displayName, contextName: "Test", kind: "reply",
      text: "", reactions: [], ...fields });
    INDEX.social = {
      personas: [persona, other], personaCount: 2, relationships: [],
      threads: [{ id: "media-thread", questionMessageId: "question", ownerPersonaId: persona.personaId, status: "open" }],
      messages: [
        message("question", { text: "Why is the calculator confused?", questionTitle: "Calculator?",
          threadId: "media-thread" }),
        message("gif", { attachments: [media("gif", "animated.gif")], replyTo: "question" }),
        message("image", { attachments: [media("image", "image.svg")], isUser: true }),
        message("padded-image", { text: paddedText, attachments: [media("image", "wide.svg")] }),
        message("sticker", { text: "😂", replyTo: "question", attachments: [media("sticker", "sticker.svg")] }),
        message("reply", { text: "I know that look", replyTo: "gif" }),
        message("reaction", { text: "😂", replyTo: "gif", personaId: other.personaId, displayName: other.displayName }),
        message("thread-gif", { attachments: [media("gif", "thread.gif")], threadId: "media-thread", replyTo: "question" }),
        message("thread-image", { text: paddedText, attachments: [media("image", "wide.svg")],
          threadId: "media-thread", replyTo: "question" }),
        message("broken", { attachments: [media("gif", "broken.gif")] }),
        message("blocked", { text: "Unsafe URL must stay blocked",
          attachments: [{ ...media("gif", "animated.gif"), url: "javascript:alert(1)" }] }),
      ],
    };
    renderSocialBoard();
  }, paddedText);
  await page.click('[data-view="social-view"]');
  const animation = page.locator("#social-message-gif .social-media");
  await animation.scrollIntoViewIfNeeded();
  await page.waitForFunction(() => document.querySelector("#social-message-gif .social-media")?.dataset.mediaState === "loaded");
  assert.equal(await animation.locator("img").getAttribute("src"), "https://media.example.com/animated.gif");
  assert.equal(await animation.locator("img").getAttribute("referrerpolicy"), "no-referrer");
  assert.equal(await animation.locator("a").getAttribute("rel"), "noopener noreferrer");
  assert.equal(await page.locator("#social-message-gif .social-reaction[data-count='1']").count(), 1);
  assert.equal(await page.locator("#social-message-reaction").count(), 0, "Plain emoji reply was not folded");
  assert.equal(await page.locator("#social-message-sticker .social-media").count(), 1, "Emoji caption swallowed the sticker");
  assert.equal(await page.locator("#social-message-sticker .social-bubble.emoji-only").count(), 0);
  assert.equal(await animation.locator("img").getAttribute("alt"), 'Calculator reaction <img src=x onerror="alert(1)">');
  assert.equal(await page.locator(".social-media-description, .social-media-context").count(), 0, "Agent metadata became a caption");
  assert.doesNotMatch(await page.locator("body").innerText(), /Calculator reaction|Why this fits|Responds to the calculator question|Hide GIF/);
  assert.match(await page.locator("#social-message-reply .social-reply").textContent(), /\[GIF attachment\]/);
  assert.equal(await animation.locator(".social-media-controls").isVisible(), false, "Successful media retained visible controls");
  assert.equal(await page.evaluate(() => INDEX.social.messages.find(message => message.id === "gif").attachments[0].context),
    "Responds to the calculator question, not an unrelated meme.", "Agent relevance metadata was discarded");
  assert.equal(await page.locator("#social-message-image").evaluate(element => element.classList.contains("right")), true);
  await assertMediaLayout(page.locator("#social-message-image"));
  await assertMediaLayout(page.locator("#social-message-padded-image"), true);
  assert.deepEqual(await page.evaluate(() => INDEX.social.messages
    .filter(message => ["padded-image", "thread-image"].includes(message.id)).map(message => message.text)),
  [paddedText, paddedText], "Display trimming mutated the original indexed messages");
  const frames = new Set();
  for (let index = 0; index < 8 && frames.size < 2; index++) {
    frames.add((await animation.locator("img").screenshot({ animations: "allow" })).toString("base64"));
    await page.waitForTimeout(70);
  }
  assert.equal(frames.size, 2, "The GIF decoded but did not visibly animate");
  await page.evaluate(() => renderSocialBoard());
  await page.waitForFunction(() => document.querySelector("#social-message-gif .social-media")?.dataset.mediaState === "loaded");
  assert.equal(await animation.locator("button").isVisible(), false, "Rerender restored a Hide button");
  await page.locator("#social-message-broken").scrollIntoViewIfNeeded();
  await page.waitForFunction(() => document.querySelector("#social-message-broken .social-media")?.dataset.mediaState === "error");
  assert.match(await page.locator("#social-message-broken .social-media-status").textContent(), /unavailable.*source link/);
  assert.equal(await page.locator("#social-message-broken .social-media-toggle").textContent(), "Retry GIF");
  assert.equal(await page.locator("#social-message-broken a").count(), 1);
  await page.evaluate(() => renderSocialBoard());
  assert.equal(await page.locator("#social-message-broken .social-media").getAttribute("data-media-state"), "error");
  assert.equal(await page.locator("#social-message-broken .social-media-toggle").isVisible(), true);
  await page.route("https://media.example.com/broken.gif", route => route.fulfill({ contentType: "image/gif", body: gif }));
  await page.locator("#social-message-broken .social-media-toggle").click();
  await page.waitForFunction(() => document.querySelector("#social-message-broken .social-media")?.dataset.mediaState === "loaded");
  assert.equal(await page.locator("#social-message-broken .social-media-controls").isVisible(), false);
  assert.equal(await page.locator("#social-message-blocked img.social-media-image").count(), 0);
  assert.match(await page.locator("#social-message-blocked .social-media-error").textContent(), /blocked/);
  assert.equal(await page.locator("#social-message-thread-gif").count(), 0, "Thread attachment escaped into main chat");
  await page.setViewportSize({ width: 390, height: 844 });
  await animation.scrollIntoViewIfNeeded();
  assert.equal(await animation.locator("img").evaluate(image => {
    const bounds = image.getBoundingClientRect();
    return bounds.left >= 0 && bounds.right <= innerWidth;
  }), true, "Inline chat GIF overflowed mobile");
  await assertMediaLayout(page.locator("#social-message-image"));
  await assertMediaLayout(page.locator("#social-message-padded-image"), true);
  await page.setViewportSize({ width: 1400, height: 1000 });
  await page.locator("#social-message-question .social-thread-link").click();
  assert.equal(await page.locator("#social-thread-message-thread-gif .social-media").count(), 1);
  await assertMediaLayout(page.locator("#social-thread-message-thread-image"), true);
  await page.click('[data-view="social-threads-view"]');
  await page.locator('.social-thread-archive-item[data-thread-id="media-thread"] > summary').click();
  const threadMedia = page.locator("#social-archive-message-thread-gif .social-media");
  await threadMedia.scrollIntoViewIfNeeded();
  await page.waitForFunction(() => document.querySelector("#social-archive-message-thread-gif .social-media")?.dataset.mediaState === "loaded");
  assert.equal(await threadMedia.locator(".social-media-controls").isVisible(), false);
  await assertMediaLayout(page.locator("#social-archive-message-thread-image"), true);
  assert.doesNotMatch(await page.locator("#social-threads-view").innerText(), /Calculator reaction|Why this fits|Responds to the calculator question|Hide GIF/);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.evaluate(() => { socialMediaVisibility.clear(); renderSocialThreads(); });
  assert.equal(await threadMedia.getAttribute("data-media-state"), "hidden", "Reduced motion autoplayed a GIF");
  assert.equal(await threadMedia.locator("img").getAttribute("src"), null);
  assert.equal(await threadMedia.locator("button").textContent(), "Show GIF");
  await threadMedia.locator("button").click();
  await page.waitForFunction(() => document.querySelector("#social-archive-message-thread-gif .social-media")?.dataset.mediaState === "loaded");
  assert.equal(await threadMedia.locator("button").isVisible(), false);
  await page.evaluate(() => renderSocialThreads());
  await page.waitForFunction(() => document.querySelector("#social-archive-message-thread-gif .social-media")?.dataset.mediaState === "loaded");
  assert.equal(await threadMedia.locator("button").isVisible(), false, "Rerender lost reduced-motion opt-in");
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, "Media overflowed mobile");
  assert.equal(await threadMedia.locator("img").evaluate(image => image.getBoundingClientRect().right <= innerWidth), true);
  await assertMediaLayout(page.locator("#social-archive-message-thread-image"), true);
  await page.click('[data-view="social-view"]');
  await page.locator("#social-message-question .social-thread-link").click();
  await assertMediaLayout(page.locator("#social-thread-message-thread-image"), true);
  await assertHistoryWindow(page);
  assert.ok(requests.length > 0 && requests.every(request => !request.referrer), "Media leaked a referrer or never loaded");
  assert.deepEqual(errors, []);
  console.log("Media/history smoke passed: media and layout, five-day initial window, ten-day history batches, stable reading position, latest-message navigation, old quotes, source preservation and lazy collapsed threads.");
} finally {
  await browser?.close();
  if (temporary) {
    fs.unlinkSync(htmlPath);
    fs.rmdirSync(temporary);
  }
}

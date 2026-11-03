import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const projectRoot = path.resolve(import.meta.dirname, "..");
const htmlPath = path.join(projectRoot, "output", "context-mesh.html");
const screenshotPath = process.env.CONTEXT_MESH_SCREENSHOT;
const edgeCandidates = [
  process.env.EDGE_PATH,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);
const edgePath = edgeCandidates.find(candidate => fs.existsSync(candidate));

assert.ok(fs.existsSync(htmlPath), `Missing generated dashboard: ${htmlPath}`);
assert.ok(edgePath, "Microsoft Edge executable was not found");

const errors = [];
const browser = await chromium.launch({
  executablePath: edgePath,
  headless: true,
  args: ["--allow-file-access-from-files"],
});

async function loadAllChatHistory(page) {
  while (await page.locator(".social-load-older").count()) {
    await page.locator(".social-load-older").click();
  }
}

async function assertThreadArchive(page) {
  await page.click('[data-view="social-threads-view"]');
  await page.waitForSelector("#social-threads-view.active");
  assert.equal(await page.locator('[data-view="social-view"] + .tab').textContent(), "MeshBoard-Threads");
  assert.equal(await page.locator(".social-thread-archive-item").evaluateAll(items => items.every(item => !item.open)), true,
    "Threads should initially be collapsed");
  assert.equal(await page.locator("#social-threads .social-thread-message").count(), 0,
    "Collapsed archive eagerly rendered replies");
  for (const heading of await page.locator(".social-thread-archive-item > summary").all()) {
    await heading.click();
  }
  await page.waitForFunction(() => [...document.querySelectorAll(".social-thread-archive-item")]
    .every(item => item.open && item.querySelector(".social-thread-list").dataset.loaded === "true"));
  const contents = await page.evaluate(() => {
    const messages = socialDisplayMessages(INDEX.social).messages;
    const questions = new Map(messages.map(message => [message.id, message]));
    const threads = [...INDEX.social.threads].sort((a, b) =>
      String(questions.get(a.questionMessageId).timestamp || "").localeCompare(String(questions.get(b.questionMessageId).timestamp || "")) || a.id.localeCompare(b.id));
    return {
      expected: threads.map(thread => ({
        id: thread.id,
        title: questions.get(thread.questionMessageId).questionTitle || "Thread",
        status: thread.status === "closed" ? "Closed permanently" : "Open",
        messages: messages.filter(message => message.threadId === thread.id || message.id === thread.questionMessageId)
          .map(message => ({id: message.id, persona: message.personaId, text: message.text.trim().replaceAll("\r\n", "\n")})),
      })),
      actual: [...document.querySelectorAll(".social-thread-archive-item")].map(thread => ({
        id: thread.dataset.threadId,
        title: thread.querySelector(".social-thread-header h3").textContent,
        status: thread.querySelector(".social-thread-state").textContent,
        messages: [...thread.querySelectorAll(".social-thread-message")].map(message => ({
          id: message.dataset.messageId, persona: message.dataset.personaId,
          text: message.querySelector(".social-message-text")?.textContent || "",
        })),
      })),
      expanded: [...document.querySelectorAll("#social-threads .social-thread-list")].every(list =>
        getComputedStyle(list).maxHeight === "none" && getComputedStyle(list).overflowY === "visible"),
    };
  });
  assert.deepEqual(contents.actual, contents.expected, "Archive omits, truncates, duplicates, misattributes, or misorders saved thread content");
  assert.ok(contents.expanded, "Archive limits full reply-list height");
  const thread = page.locator("details.social-thread-archive-item").first();
  if (await thread.count()) {
    assert.equal(await thread.evaluate(element => element.open), true, "Explicit thread expansion was lost");
    const heading = thread.locator("summary.social-thread-header");
    const replies = thread.locator(".social-thread-list");
    await heading.click();
    assert.equal(await replies.isVisible(), false, "Collapsing a thread did not hide replies");
    assert.equal(await heading.isVisible(), true, "Collapsed thread lost its heading");
    if (await page.locator("details.social-thread-archive-item").count() > 1) {
      assert.equal(await page.locator("details.social-thread-archive-item").nth(1).evaluate(element => element.open), true,
        "Collapsing one thread also collapsed another");
    }
    await page.click('[data-view="social-view"]');
    await page.click('[data-view="social-threads-view"]');
    assert.equal(await thread.evaluate(element => element.open), false, "Tab navigation lost collapsed state");
    await heading.focus();
    await page.keyboard.press("Enter");
    assert.equal(await replies.isVisible(), true, "Keyboard expansion did not restore replies");
    await page.keyboard.press("Space");
    assert.equal(await replies.isVisible(), false, "Keyboard collapse did not hide replies");
    await heading.click();
    assert.equal(await replies.isVisible(), true, "Reopening a thread lost replies");
  }
}

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  page.on("pageerror", error => errors.push(`pageerror: ${error.message}`));
  page.on("console", message => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });

  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
  await page.click('[data-view="social-view"]');
  await page.waitForSelector("#social-view.active");
  assert.equal(await page.locator("#social-view .social-hero h2").textContent(), "MeshBoard");
  assert.match(
    await page.locator("#social-status").textContent(),
    /read-only file-backed board/,
    "MeshBoard is not marked read-only",
  );
  assert.ok(await page.locator(".social-characteristics").count() === 1, "Characteristic explanations are missing");
  assert.equal(await page.locator(".social-characteristics li").count(), 7, "Unexpected active characteristic count");
  await loadAllChatHistory(page);
  assert.ok(await page.locator(".social-message-row").filter({ hasText: "status meeting has been banished" }).count() > 0, "Social banter is missing");
  assert.ok(await page.locator(".social-avatar").count() > 0, "MeshBoard has no generated avatars");
  const avatarMarkup = await page.locator(".social-avatar").first().getAttribute("src");
  assert.ok(avatarMarkup && !atob(avatarMarkup.split(",")[1]).includes("<text"), "Avatar contains text");
  const faceChecks = await page.evaluate(async () => {
    const parser = new DOMParser();
    const inspect = persona => {
      const uri = personaAvatarDataUri(persona);
      const document = parser.parseFromString(atob(uri.split(",")[1]), "image/svg+xml");
      const features = [...document.querySelectorAll("[data-feature]")].map(feature => {
        const clone = feature.cloneNode(true);
        for (const element of [clone, ...clone.querySelectorAll("*")]) {
          element.removeAttribute("fill");
          element.removeAttribute("stroke");
        }
        return clone.outerHTML;
      }).join("");
      return {
        uri, features, valid: !document.querySelector("parsererror"),
        version: document.documentElement.getAttribute("data-avatar-version"),
        outlined: Boolean(document.querySelector('[data-feature="silhouette-outline"]')),
        reviewed: uri === avatarStudyDataUri(persona.profileImageData, 9, persona,
          avatarPortraitDirection(persona)),
        eyes: document.querySelector('[data-feature="eyes"]')?.children.length,
        openEyes: document.querySelectorAll('[data-feature="eyes"] > [data-eye="open"]').length,
        closedEyes: document.querySelectorAll('[data-feature="eyes"] > [data-eye="closed"]').length,
        friendlyWink: avatarPortraitDirection(persona).expression === "friendly-wink",
        winkDetails: Boolean(document.querySelector('[data-eye="closed"][data-expression="wink"] [data-feature="wink-lid"]') &&
          document.querySelector('[data-feature="wink-cheek"]') &&
          document.querySelector('[data-feature="mouth"][data-expression="smile"]')),
        mouth: document.querySelector('[data-feature="mouth"]')?.children.length,
        unsafe: Boolean(document.querySelector("text,script,image,foreignObject")),
      };
    };
    const actual = INDEX.social.personas.map(inspect);
    const samples = ["0".repeat(32), "f".repeat(32), "0".repeat(64), "f".repeat(64),
      ...Array.from({length: 128}, (_, index) => index.toString(16).padStart(64, "0"))]
      .map(profileImageData => inspect({profileImageData}));
    const rendered = [...document.querySelectorAll(".social-avatar,.social-roster-avatar")];
    rendered.forEach(image => { image.loading = "eager"; });
    await Promise.all(rendered.map(image => image.decode()));
    return {
      actual, samples,
      stable: actual.every((face, index) => face.uri === personaAvatarDataUri(INDEX.social.personas[index])),
      caseStable: personaAvatarDataUri({profileImageData: "abcdef".repeat(10)}) === personaAvatarDataUri({profileImageData: "ABCDEF".repeat(10)}),
      tailMatters: personaAvatarDataUri({profileImageData: "0".repeat(64)}) !== personaAvatarDataUri({profileImageData: "0".repeat(63) + "1"}),
      loaded: rendered.every(image => image.naturalWidth > 0),
      consistent: [...document.querySelectorAll(".social-message-row .social-avatar")].every(image => {
        const id = image.closest(".social-message-row").dataset.personaId;
        const roster = document.querySelector(`.social-persona[data-persona-id="${CSS.escape(id)}"] .social-roster-avatar`);
        return roster?.src === image.src;
      }),
    };
  });
  assert.ok(faceChecks.stable && faceChecks.caseStable, "A saved seed does not reproduce the same face");
  assert.ok(faceChecks.tailMatters, "Avatar ignores seed characters beyond the original identicon prefix");
  assert.ok(faceChecks.loaded && faceChecks.consistent, "Faces fail to load or differ between chat and roster");
  for (const face of [...faceChecks.actual, ...faceChecks.samples]) {
    assert.ok(face.valid && face.eyes >= 2 && face.mouth > 0 && !face.unsafe, "Avatar is not a self-contained face with eyes and a mouth");
    assert.ok(face.version === "study-v9" && face.outlined && face.reviewed, "Live avatar is not the reviewed 08B portrait with its silhouette");
    assert.equal(face.closedEyes, face.friendlyWink ? 1 : 0, "Closed eyes are not restricted to an authored friendly wink");
    assert.equal(face.openEyes, face.friendlyWink ? 1 : 2, "A portrait has no open eye");
    if (face.friendlyWink) assert.ok(face.winkDetails, "Friendly wink lacks its lifted lid, cheek or smile");
  }
  assert.equal(new Set(faceChecks.actual.map(face => face.features)).size, faceChecks.actual.length,
    "Existing personas differ only in color, not facial features/hair/accessories");
  assert.ok(await page.locator(".social-message-row.left").count() > 0, "Agent messages are not left aligned");
  if (await page.locator(".social-thread-link").count()) {
    assert.ok(await page.locator(".social-question-title").count() > 0, "MeshBoard thread fixture has no question heading");
    await page.locator(".social-thread-link").first().click();
    assert.equal(await page.locator("#social-thread-panel").getAttribute("aria-hidden"), "false");
    assert.ok(await page.locator(".social-thread-message").count() > 0, "Thread panel has no messages");
    assert.ok(await page.locator(".social-thread-message[style*='--persona-color']").count() > 0, "Thread message has no registered border color");
    assert.ok(await page.locator(".social-bubble.threaded").count() > 0, "Threaded bubble has no animated-border target");
  } else {
    assert.equal(await page.locator(".social-thread-panel").getAttribute("aria-hidden"), "true");
  }

  const liveColors = await page.evaluate(() => ({
    colors: INDEX.social.personas.map(persona => persona.profileColor),
    backgrounds: [...document.querySelectorAll(".social-bubble:not(.emoji-only)")].map(bubble => getComputedStyle(bubble).backgroundColor),
    messages: [...document.querySelectorAll(".social-bubble:not(.emoji-only)")].map(bubble => {
      const style = getComputedStyle(bubble);
      return { personaId: bubble.closest(".social-message-row").dataset.personaId, border: style.borderColor };
    }),
    registry: INDEX.social.colorRegistryPath,
  }));
  assert.equal(new Set(liveColors.colors).size, liveColors.colors.length, "Persona colors collide");
  assert.equal(new Set(liveColors.backgrounds).size, 1, "Message backgrounds vary by persona");
  assert.ok(liveColors.registry.endsWith("persona-colors.sqlite3"), "Central registry is missing");
  const colorToRgb = color => `rgb(${[1, 3, 5].map(offset => parseInt(color.slice(offset, offset + 2), 16)).join(", ")})`;
  const registeredColors = await page.evaluate(() => Object.fromEntries(INDEX.social.personas.map(persona => [persona.personaId, persona.profileColor])));
  for (const message of liveColors.messages) {
    assert.equal(message.border, colorToRgb(registeredColors[message.personaId]), "Message border differs from registry");
  }
  const emojiClassification = await page.evaluate(() => ({
    positive: ["😂", "😂 😂", "👍🏽", "👨‍👩‍👧‍👦", "🇮🇳", "1️⃣", "🏳️‍🌈", "❤️"].map(isEmojiOnly),
    negative: ["", " ", "hello 😂", "1", "123", "#", "*", "\u200d", "\ufe0f", "🏽", "🇮"].map(isEmojiOnly),
  }));
  assert.ok(emojiClassification.positive.every(Boolean), "Valid emoji-only sequence was not recognized");
  assert.ok(emojiClassification.negative.every(value => !value), "Plain text or incomplete emoji was treated as emoji-only");
  const liveEmoji = page.locator("#social-message-session-718bb26f-ec71-4d8a-9543-f67727e20064-social-3");
  assert.equal(await liveEmoji.count(), 0, "Actual emoji reaction still occupies a separate message");
  const liveReaction = await page.evaluate(() => {
    const message = INDEX.social.messages.find(item => item.id === "session-718bb26f-ec71-4d8a-9543-f67727e20064-social-3");
    return {target: message.replyTo, author: message.displayName};
  });
  assert.ok((await page.locator(`#social-message-${liveReaction.target} .social-reaction[data-emoji="😂"]`).getAttribute("title")).includes(liveReaction.author),
    "Actual emoji acknowledgement was not attached to its source with authorship");

  const firstProfile = page.locator(".social-profile-trigger").first();
  const secondProfile = page.locator(".social-profile-trigger").nth(1);
  const profileCard = page.locator("#social-profile-card");
  const expectedProfile = async trigger => page.evaluate(
    id => INDEX.social.personas.find(persona => persona.personaId === id),
    await trigger.getAttribute("data-persona-id"),
  );
  await firstProfile.hover();
  await page.waitForTimeout(700);
  assert.equal(await profileCard.isVisible(), false, "Profile appeared before the one-second delay");
  await profileCard.waitFor({state: "visible"});
  assert.equal(await profileCard.getAttribute("role"), "tooltip");
  const firstPersona = await expectedProfile(firstProfile);
  assert.equal(await profileCard.locator("h3").textContent(), firstPersona.displayName);
  assert.equal(await profileCard.locator(".social-profile-description").textContent(), firstPersona.persona);
  assert.equal(await profileCard.locator(".social-profile-avatar").getAttribute("src"),
    await firstProfile.locator("img").getAttribute("src"), "Profile card shows a different face than chat");
  const previewSize = () => profileCard.locator(".social-profile-avatar").evaluate(image => ({
    width: image.getBoundingClientRect().width, height: image.getBoundingClientRect().height,
  }));
  assert.deepEqual(await previewSize(), {width: 220, height: 220}, "Hover portrait is not five times its original size");
  assert.equal(await firstProfile.locator("img").evaluate(image => image.getBoundingClientRect().width), 46,
    "Preview enlargement changed chat avatar size");
  assert.equal(await page.locator(".social-roster-avatar").first().evaluate(image => image.getBoundingClientRect().width), 46,
    "Preview enlargement changed roster avatar size");
  await page.mouse.move(0, 0);
  await profileCard.waitFor({state: "hidden"});
  await firstProfile.hover();
  await page.waitForTimeout(200);
  await page.mouse.move(0, 0);
  await page.waitForTimeout(1100);
  assert.equal(await profileCard.isVisible(), false, "Cancelled hover opened a stale preview");
  await firstProfile.click();
  assert.equal(await profileCard.getAttribute("role"), "dialog");
  assert.deepEqual(await previewSize(), {width: 220, height: 220}, "Click-opened portrait is not enlarged");
  await page.mouse.move(0, 0);
  assert.equal(await profileCard.isVisible(), true, "Click-opened profile closed on mouse leave");
  await secondProfile.click();
  assert.equal(await profileCard.locator("h3").textContent(), (await expectedProfile(secondProfile)).displayName);
  await page.keyboard.press("Escape");
  await profileCard.waitFor({state: "hidden"});
  assert.equal(await secondProfile.evaluate(element => element === document.activeElement), true, "Escape did not restore avatar focus");
  await firstProfile.focus();
  await firstProfile.press("Enter");
  assert.equal(await profileCard.isVisible(), true, "Avatar is not keyboard-activatable");
  await page.locator(".social-profile-close").click();
  await profileCard.waitFor({state: "hidden"});
  await firstProfile.click();
  await page.setViewportSize({width: 360, height: 640});
  await page.waitForFunction(() => {
    const bounds = document.getElementById("social-profile-card").getBoundingClientRect();
    return bounds.left >= 0 && bounds.right <= innerWidth && bounds.top >= 0 && bounds.bottom <= innerHeight;
  });
  const profileBounds = await profileCard.boundingBox();
  assert.ok(profileBounds.x >= 0 && profileBounds.x + profileBounds.width <= 360, "Profile overflows narrow viewport");
  assert.ok(profileBounds.y >= 0 && profileBounds.y + profileBounds.height <= 640, "Profile overflows viewport height");
  assert.deepEqual(await previewSize(), {width: 220, height: 220}, "Mobile profile portrait lost its enlarged size");
  await page.mouse.click(1, 1);
  await profileCard.waitFor({state: "hidden"});
  await page.setViewportSize({width: 1600, height: 1000});
  await assertThreadArchive(page);
  await page.setViewportSize({width: 360, height: 640});
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "Thread archive overflows mobile viewport");
  await page.setViewportSize({width: 1600, height: 1000});
  await page.click('[data-view="social-view"]');

  // Broadcast fixtures are browser-local and never create real room obligations.
  const broadcastPage = await browser.newPage();
  await broadcastPage.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
  const broadcastNames = await broadcastPage.evaluate(() => {
    const [first, second, third] = INDEX.social.personas;
    const broadcast = (id, extra = {}) => ({
      id, personaId: first.personaId, displayName: first.displayName, contextName: first.contextName,
      timestamp: "2026-11-02T12:00:00Z", kind: "chat", text: "@MeShBoArD, thoughts?",
      isBroadcast: true, broadcastRecipients: [second.personaId, third.personaId],
      broadcastResponded: [second.personaId], broadcastPending: [third.personaId], ...extra,
    });
    INDEX.social.messages = [
      broadcast("room-main"),
      broadcast("room-root", {threadId: "room-thread", questionTitle: "Room question?"}),
      broadcast("room-answer", {threadId: "room-thread"}),
      broadcast("room-complete", {broadcastResponded: [second.personaId, third.personaId], broadcastPending: []}),
    ];
    INDEX.social.threads = [{id: "room-thread", questionMessageId: "room-root", ownerPersonaId: first.personaId, status: "open"}];
    renderSocialBoard();
    const people = new Map(INDEX.social.personas.map(persona => [persona.personaId, persona]));
    const node = document.createElement("div");
    node.innerHTML = renderMentionText("@Meshboard Builder, @meshboard! <script>bad</script> name@meshboard.example @meshboarder @meshboard-team", people);
    if (people.size && [...people.values()].some(persona => persona.displayName === "Meshboard Builder")) {
      if (node.querySelectorAll(".social-mention").length !== 2) throw Error("Full persona/group mention ambiguity");
    }
    if (node.querySelectorAll('[data-mention-scope="meshboard"]').length !== 1 || node.querySelector("script")) throw Error("Broadcast token boundaries or escaping");
    return {pending: third.displayName, responded: second.displayName, count: people.size};
  });
  await broadcastPage.click('[data-view="social-view"]');
  await loadAllChatHistory(broadcastPage);
  const assertBroadcastHidden = async selector => {
    assert.equal(await broadcastPage.locator(`${selector} .social-broadcast`).count(), 0, "Broadcast tracking should not be rendered");
    assert.doesNotMatch(await broadcastPage.locator(selector).innerText(),
      /Room-wide response required|Awaiting:|Responded:|Recorded responses only/);
  };
  await assertBroadcastHidden("#social-messages");
  await broadcastPage.locator('#social-message-room-main [data-mention-scope="meshboard"]').click();
  assert.equal(await broadcastPage.locator(".social-persona.highlighted").count(), broadcastNames.count);
  await broadcastPage.locator("#social-message-room-root .social-thread-link").click();
  await assertBroadcastHidden("#social-thread-panel");
  await broadcastPage.click('[data-view="social-threads-view"]');
  await broadcastPage.locator('.social-thread-archive-item[data-thread-id="room-thread"] > summary').click();
  await broadcastPage.locator("#social-archive-message-room-answer").waitFor();
  await assertBroadcastHidden("#social-threads");
  const retainedBroadcasts = await broadcastPage.evaluate(() => INDEX.social.messages.map(message => ({
    id: message.id, isBroadcast: message.isBroadcast, recipients: message.broadcastRecipients.length,
    responded: message.broadcastResponded.length, pending: message.broadcastPending.length,
  })));
  assert.deepEqual(retainedBroadcasts, ["room-main", "room-root", "room-answer", "room-complete"].map(id => ({
    id, isBroadcast: true, recipients: 2, responded: id === "room-complete" ? 2 : 1, pending: id === "room-complete" ? 0 : 1,
  })), "Hiding the display changed agent-readable broadcast metadata");
  await broadcastPage.locator('#social-archive-message-room-answer [data-mention-scope="meshboard"]').click();
  assert.equal(await broadcastPage.locator("#social-view.active").count(), 1);
  assert.equal(await broadcastPage.locator(".social-persona.highlighted").count(), broadcastNames.count);
  await broadcastPage.close();

  // Thread and user-message fixtures stay in this isolated browser page, never in the saved board.
  const colorPage = await browser.newPage();
  await colorPage.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
  await colorPage.evaluate(() => {
    const [first, second] = INDEX.social.personas;
    const message = (id, persona, extra = {}) => ({
      id, personaId: persona.personaId, displayName: persona.displayName, contextName: persona.contextName,
      timestamp: "2026-10-14T12:00:00Z", kind: "reply", text: "Browser-only color fixture", ...extra,
    });
    INDEX.social.messages = [
      message("color-open", first, {threadId: "color-thread-open", questionTitle: "Open fixture?", text: `Browser-only color fixture @${second.displayName}`}),
      message("color-answer", second, {threadId: "color-thread-open"}),
      message("color-closed", second, {threadId: "color-thread-closed", questionTitle: "Closed fixture?"}),
      message("color-user", second, {isUser: true}),
    ];
    INDEX.social.threads = [
      {id: "color-thread-open", questionMessageId: "color-open", ownerPersonaId: first.personaId, status: "open"},
      {id: "color-thread-closed", questionMessageId: "color-closed", ownerPersonaId: second.personaId, status: "closed", closedAt: "2026-10-15T12:00:00Z"},
    ];
    renderSocialBoard();
  });
  await colorPage.click('[data-view="social-view"]');
  await loadAllChatHistory(colorPage);
  await colorPage.locator('.social-thread-link.open').click();
  const fixtureMention = colorPage.locator("#social-messages .social-mention");
  assert.equal(await fixtureMention.count(), 1, "Fixture mention is not emphasized");
  const mentionedPersona = await fixtureMention.getAttribute("data-persona-id");
  await fixtureMention.click();
  assert.equal(await colorPage.locator(`.social-persona[data-persona-id="${mentionedPersona}"]`).evaluate(
    element => element.classList.contains("highlighted")), true, "Mention does not highlight its persona");
  const sampleColors = () => colorPage.evaluate(() =>
    [...document.querySelectorAll(".social-bubble,.social-thread-message")].map(element => {
      const style = getComputedStyle(element);
      const personaId = element.dataset.personaId || element.closest(".social-message-row").dataset.personaId;
      return {
        personaId, border: style.borderColor, background: style.backgroundColor, text: style.color,
        name: element.matches(".social-thread-message") ? getComputedStyle(element.querySelector("strong")).color : style.color,
      };
    })
  );
  const initialColors = await sampleColors();
  assert.ok(initialColors.length >= 5, "Color fixtures did not exercise general/user/thread messages");
  assert.equal(new Set(initialColors.map(item => item.background)).size, 1, "Thread and user backgrounds differ");
  assert.equal(new Set(initialColors.map(item => item.text)).size, 1, "Message text varies by persona");
  for (const item of initialColors) {
    assert.equal(item.border, colorToRgb(registeredColors[item.personaId]));
    assert.equal(item.name, item.text, "Thread names still use persona colors");
  }
  await colorPage.evaluate(() => {
    for (const element of document.querySelectorAll(".social-bubble.threaded")) {
      for (const animation of element.getAnimations()) {
        animation.pause();
        animation.currentTime = 1900;
      }
    }
  });
  assert.deepEqual(await sampleColors(), initialColors, "Thread animation overwrites author border/background");
  await colorPage.emulateMedia({ reducedMotion: "reduce" });
  const animations = await colorPage.locator(".social-bubble.threaded").evaluateAll(elements => elements.map(element => getComputedStyle(element).animationName));
  assert.ok(animations.every(name => name === "none"), "Reduced motion is not honored");
  await colorPage.emulateMedia({ reducedMotion: "no-preference" });
  await colorPage.evaluate(() => {
    const base = INDEX.social.messages.find(message => message.id === "color-user");
    const [first, second, third] = INDEX.social.personas;
    INDEX.social.messages.find(message => message.id === "color-open").reactions = [{emoji: "😂", personaId: second.personaId}];
    INDEX.social.messages.push(
      {...base, id: "emoji-reply", text: "😂", replyTo: "color-open", isUser: false},
      {...base, id: "emoji-duplicate", text: "😂😂", replyTo: "color-open", isUser: false},
      {...base, id: "emoji-many", personaId: third.personaId, displayName: third.displayName,
        text: "😂 👍🏽 👨‍👩‍👧‍👦 🇮🇳 1️⃣", replyTo: "color-open", isUser: false},
      {...base, id: "emoji-chain", personaId: third.personaId, displayName: third.displayName,
        text: "😂", replyTo: "emoji-reply", isUser: false},
      {...base, id: "emoji-self", personaId: first.personaId, text: "🙌", replyTo: "color-open", isUser: false},
      {...base, id: "emoji-status", personaId: first.personaId, text: "✅", replyTo: "color-open", isUser: false},
      {...base, id: "emoji-thread-reaction", personaId: first.personaId, displayName: first.displayName,
        text: "😂", replyTo: "color-answer", threadId: "color-thread-open", isUser: false},
      {...base, id: "reaction-followup", text: "A normal reply to the reaction.", replyTo: "emoji-reply", isUser: false},
      {...base, id: "emoji-standalone", text: "😂", isUser: false},
      {...base, id: "emoji-user", text: "👍🏽", isUser: true},
      {...base, id: "emoji-answer", text: "👨‍👩‍👧‍👦", threadId: "color-thread-open", isUser: false},
      {...base, id: "emoji-mixed", text: "hello 😂", replyTo: "color-open", isUser: false},
      {...base, id: "emoji-question", text: "🤔", questionTitle: "Emoji fixture?", threadId: "emoji-thread", isUser: false},
    );
    INDEX.social.threads.push({id: "emoji-thread", questionMessageId: "emoji-question", ownerPersonaId: base.personaId, status: "open"});
    renderSocialBoard();
  });
  await colorPage.locator('.social-thread-link[data-thread-id="color-thread-open"]').click();
  const emojiStyles = await colorPage.evaluate(() =>
    [...document.querySelectorAll(".social-bubble.emoji-only,.social-thread-message.emoji-only")].map(element => {
      const style = getComputedStyle(element);
      const body = element.matches(".social-thread-message") ? element.querySelector("p") : element;
      return {border: style.borderWidth, background: style.backgroundColor, shadow: style.boxShadow, animation: style.animationName, size: parseFloat(getComputedStyle(body).fontSize)};
    })
  );
  assert.equal(emojiStyles.length, 4, "Emoji fixtures did not cover main, user, thread answer, and question");
  for (const style of emojiStyles) {
    assert.equal(style.border, "0px", "Emoji retains a message border");
    assert.equal(style.background, "rgba(0, 0, 0, 0)", "Emoji retains a message fill");
    assert.equal(style.shadow, "none", "Emoji retains a message shadow");
    assert.equal(style.animation, "none", "Emoji retains a thread glow");
    assert.equal(style.size, 44, "Emoji was not enlarged");
  }
  assert.equal(await colorPage.locator("#social-message-emoji-mixed .social-bubble:not(.emoji-only)").count(), 1, "Mixed text/emoji lost its normal box");
  assert.equal(await colorPage.locator("#social-message-emoji-standalone .social-message-meta").count(), 1, "Standalone emoji lost author/time");
  assert.equal(await colorPage.locator("#social-message-emoji-reply").count(), 0, "Emoji reaction still has its own row");
  const laugh = colorPage.locator('#social-message-color-open .social-reaction[data-emoji="😂"]');
  assert.equal(await laugh.getAttribute("data-count"), "2", "Repeated or legacy reactions inflated the distinct-person count");
  const names = await colorPage.evaluate(() => INDEX.social.personas.slice(1, 3).map(persona => persona.displayName));
  assert.deepEqual((await laugh.getAttribute("title")).split(", ").sort(), names.sort(), "Grouped reaction lost author names");
  assert.equal(await colorPage.locator('#social-message-color-open .social-reaction[data-emoji="🙌"]').count(), 0, "Forbidden self-reaction was displayed");
  assert.equal(await colorPage.locator('#social-message-color-open .social-reaction[data-emoji="✅"]').count(), 1, "Self status reaction was lost");
  for (const emoji of ["👍🏽", "👨‍👩‍👧‍👦", "🇮🇳", "1️⃣"]) {
    assert.equal(await colorPage.locator(`#social-message-color-open .social-reaction[data-emoji="${emoji}"]`).getAttribute("data-count"), "1", `Reaction split a joined or modified emoji: ${emoji}`);
  }
  assert.equal(await colorPage.locator('#social-thread-message-color-answer .social-reaction[data-emoji="😂"]').count(), 1, "Thread reaction was not attached to its answer");
  assert.equal(await colorPage.locator("#social-thread-message-emoji-thread-reaction").count(), 0, "Thread reaction counted as an answer");
  assert.equal(await colorPage.locator("#social-message-reaction-followup .social-reply span").textContent(), "😂", "Quote lost original reaction context");
  await colorPage.locator("#social-message-reaction-followup .social-reply").click();
  assert.ok(await colorPage.locator("#social-message-color-open").evaluate(element => element.classList.contains("highlighted-message")), "Quote to a folded reaction did not navigate to its visible source");
  const projectionChecks = await colorPage.evaluate(() => {
    const snapshot = JSON.stringify(INDEX.social);
    const first = socialDisplayMessages(INDEX.social);
    const second = socialDisplayMessages(INDEX.social);
    const unusual = socialDisplayMessages({messages: [
      {id: "missing", personaId: "a", text: "😂", replyTo: "unknown"},
      {id: "cycle-a", personaId: "a", text: "😂", replyTo: "cycle-b"},
      {id: "cycle-b", personaId: "b", text: "😂", replyTo: "cycle-a"},
      {id: "already-reacted", personaId: "a", text: "😂", replyTo: "missing", reactions: [{emoji: "👍", personaId: "b"}]},
    ]});
    return {
      unchanged: snapshot === JSON.stringify(INDEX.social),
      repeatable: JSON.stringify(first.messages) === JSON.stringify(second.messages),
      preserved: unusual.messages.map(message => message.id),
    };
  });
  assert.equal(projectionChecks.unchanged, true, "Reaction rendering mutated saved index data");
  assert.equal(projectionChecks.repeatable, true, "Rerender duplicated reactions");
  assert.deepEqual(projectionChecks.preserved, ["missing", "cycle-a", "cycle-b", "already-reacted"], "Unresolved/cyclic or already-reacted-to emoji posts were silently discarded");
  await colorPage.locator(".social-profile-trigger").first().click();
  assert.equal(await colorPage.locator("#social-profile-card").isVisible(), true);
  await colorPage.evaluate(() => renderSocialBoard());
  assert.equal(await colorPage.locator("#social-profile-card").isVisible(), false, "Rerender left a stale profile open");
  await colorPage.evaluate(() => {
    const [first, second] = INDEX.social.personas;
    const base = INDEX.social.messages.find(message => message.id === "color-answer");
    INDEX.social.messages.push(
      {...base, id: "archive-root", threadId: null, questionTitle: "Root without threadId?", text: "The complete root is still included.", timestamp: "2026-10-16T12:00:00Z"},
      {...base, id: "archive-closed-reply", threadId: "color-thread-closed", replyTo: "color-closed",
        text: "<b>Literal text, not markup.</b> " + "Long reply. ".repeat(1000) + "FULL-REPLY-END",
        reactions: [{emoji: "👍", personaId: first.personaId}]},
      ...Array.from({length: 27}, (_, index) => ({
        ...base, id: `archive-reply-${index}`, threadId: "color-thread-open", replyTo: "color-open",
        text: `Full reply ${index}`, timestamp: `2026-10-14T12:01:${String(index).padStart(2, "0")}Z`,
      })),
    );
    INDEX.social.threads.push({id: "archive-root-thread", questionMessageId: "archive-root", ownerPersonaId: second.personaId, status: "open"});
    INDEX.social.messages.reverse();
    INDEX.social.threads.reverse();
  });
  await assertThreadArchive(colorPage);
  assert.equal(await colorPage.locator('#social-archive-message-color-answer .social-reaction[data-emoji="😂"]').count(), 1, "Full thread view lost reaction badges");
  assert.equal(await colorPage.locator("#social-archive-message-emoji-thread-reaction").count(), 0, "Full thread view treats a reaction as a reply");
  assert.equal(await colorPage.locator("#social-archive-message-archive-closed-reply p b").count(), 0, "Reply text was interpreted as HTML");
  assert.equal(await colorPage.locator("#social-archive-message-archive-closed-reply .social-reaction").getAttribute("title"),
    await colorPage.evaluate(() => INDEX.social.personas[0].displayName), "Archive lost reaction authorship");
  assert.equal(await colorPage.locator("#social-archive-message-emoji-answer.emoji-only").count(), 1, "Archive lost standalone emoji presentation");
  const archiveReply = colorPage.locator("#social-archive-message-archive-closed-reply .social-reply");
  await archiveReply.click();
  assert.ok(await colorPage.locator("#social-archive-message-color-closed").evaluate(element => element.classList.contains("highlighted-message")), "Archive reply quote does not navigate locally");
  await colorPage.locator("#social-archive-message-color-open > p .social-mention").click();
  assert.equal(await colorPage.locator("#social-view.active").count(), 1, "Archive mention did not open the persona roster");
  assert.equal(await colorPage.locator(`.social-persona[data-persona-id="${mentionedPersona}"].highlighted`).count(), 1, "Archive mention did not highlight its persona");
  await colorPage.click('[data-view="social-threads-view"]');
  await colorPage.evaluate(() => { INDEX.social.threads = []; renderSocialThreads(); });
  assert.equal(await colorPage.locator(".social-thread-archive-item").count(), 0, "Empty archive retained old threads");
  assert.equal(await colorPage.locator("#social-threads .social-empty").isVisible(), true, "Empty archive has no honest empty state");
  await colorPage.close();

  await page.click('[data-view="artifacts-view"]');
  await page.fill(
    "#artifact-search",
    "C:\\Users\\mishrad\\Downloads\\SFMC-Migration-Resource-Report 3.html",
  );
  await page.click("#artifact-search-button");
  await page.waitForSelector(".artifact-result");
  const artifactResults = await page.locator(".artifact-result").allTextContents();
  assert.ok(
    artifactResults[0].includes("Likely origin") &&
      artifactResults[0].includes("WorkDesk") &&
      artifactResults[0].includes("a9d82458-6aa8-4b5a-8f13-c01e53f6078a"),
    "Artifact Finder did not rank the original WorkDesk chat first",
  );
  assert.ok(
    artifactResults.some(result => result.includes("GeneratingReports")),
    "Artifact Finder did not show the later GeneratingReports evidence",
  );

  await page.click('[data-view="graph-view"]');
  await page.waitForSelector("#graph canvas");
  await page.waitForTimeout(1800);

  const graphState = await page.evaluate(() => ({
    forceGraphLoaded: typeof window.ForceGraph === "function",
    forcesLoaded: ["forceX", "forceY", "forceCollide"].every(name => typeof window.d3?.[name] === "function"),
    metrics: Object.fromEntries(
      [...document.querySelectorAll(".metric")].map(metric => [
        metric.querySelector("span")?.textContent || "",
        Number(metric.querySelector("strong")?.textContent || 0),
      ]),
    ),
    canvas: (() => {
      const canvas = document.querySelector("#graph canvas");
      return canvas ? { width: canvas.width, height: canvas.height } : null;
    })(),
  }));

  assert.equal(graphState.forceGraphLoaded, true, "ForceGraph did not load");
  assert.equal(graphState.forcesLoaded, true, "Required d3 force modules did not load");
  assert.ok(graphState.metrics["Graph nodes"] > 0, "No graph nodes were loaded");
  assert.ok(graphState.metrics["Graph edges"] > 0, "No graph links were loaded");
  assert.ok(graphState.canvas?.width > 0 && graphState.canvas?.height > 0, "Graph Canvas has no size");
  assert.equal(
    await page.evaluate(() =>
      window.CONTEXT_MESH_GRAPH.graphData().nodes.every(node => node.type === "context")
    ),
    true,
    "Default graph includes non-context detail nodes",
  );
  assert.equal(
    await page.evaluate(() => {
      const nodes = window.CONTEXT_MESH_GRAPH.graphData().nodes;
      return new Set(nodes.map(node => node.outlineColor)).size === nodes.length;
    }),
    true,
    "Context outline colors are not unique",
  );
  const familyLayout = await page.evaluate(() => {
    const nodes = window.CONTEXT_MESH_GRAPH.graphData().nodes;
    const radius = node => Math.hypot(node.familyX || 0, node.familyY || 0);
    return {
      connected: nodes.filter(node => node.familyConnected).map(radius),
      isolated: nodes.filter(node => !node.familyConnected).map(radius),
    };
  });
  assert.ok(familyLayout.connected.length > 0, "No connected context family was detected");
  assert.ok(familyLayout.isolated.length > 0, "No isolated outer contexts were detected");
  assert.ok(
    Math.max(...familyLayout.connected) < Math.min(...familyLayout.isolated),
    "Connected context families are not positioned inside isolated contexts",
  );
  assert.equal(
    await page.evaluate(() =>
      window.CONTEXT_MESH_GRAPH.graphData().links.every(link => link.confidence === "high")
    ),
    true,
    "Default graph includes low-confidence relationships",
  );
  const defaultNodeCount = await page.evaluate(
    () => window.CONTEXT_MESH_GRAPH.graphData().nodes.length,
  );
  await page.selectOption("#animation-duration", "5");
  await page.click("#animate-graph");
  await page.waitForTimeout(250);
  const animatedNodeCount = await page.evaluate(
    () => window.CONTEXT_MESH_GRAPH.graphData().nodes.length,
  );
  assert.ok(
    animatedNodeCount > 0 && animatedNodeCount < defaultNodeCount,
    "Timeline animation did not progressively reveal nodes",
  );
  assert.ok(
    (await page.locator("#animation-status").textContent()).includes("Timeline"),
    "Timeline animation did not report progress",
  );
  await page.click("#animate-graph");
  await page.waitForTimeout(100);
  assert.equal(
    await page.evaluate(() => window.CONTEXT_MESH_GRAPH.graphData().nodes.length),
    defaultNodeCount,
    "Stopping timeline animation did not restore the complete graph",
  );
  await page.click("#animate-graph");
  await page.waitForTimeout(5300);
  assert.equal(
    await page.evaluate(() => window.CONTEXT_MESH_GRAPH.graphData().nodes.length),
    defaultNodeCount,
    "Completed timeline animation did not end on the complete graph",
  );
  assert.equal(
    await page.locator("#animate-graph").textContent(),
    "Replay timeline",
    "Completed timeline animation is not replayable",
  );

  await page.waitForTimeout(2400);
  const canvas = page.locator("#graph canvas");
  const beforeSearch = await canvas.screenshot();
  await page.fill("#graph-search", "Runner");
  await page.waitForTimeout(150);
  const afterSearch = await canvas.screenshot();
  assert.notDeepEqual(afterSearch, beforeSearch, "Search did not repaint the settled graph");

  await page.selectOption("#detail-level", "core");
  await page.waitForTimeout(100);
  assert.equal(
    await page.evaluate(() =>
      window.CONTEXT_MESH_GRAPH.graphData().nodes.some(node => node.type === "zmem")
    ),
    false,
    "zmem nodes remained visible in the core graph",
  );
  await page.selectOption("#detail-level", "full");
  await page.selectOption("#evidence-level", "all");
  await page.waitForTimeout(100);
  assert.equal(
    await page.evaluate(() =>
      window.CONTEXT_MESH_GRAPH.graphData().nodes.some(node => node.type === "zmem")
    ),
    true,
    "zmem nodes were not restored in the full graph",
  );

  await page.fill("#graph-search", "");
  await page.click("#fit-graph");
  await page.waitForTimeout(900);
  const targetId = await page.evaluate(() => {
    const graph = window.CONTEXT_MESH_GRAPH;
    const node = graph
      .graphData()
      .nodes.find(item => item.type === "context" && item.familyConnected);
    node.fx = node.x;
    node.fy = node.y;
    graph.centerAt(node.x, node.y, 0);
    graph.zoom(1.5, 0);
    return node.id;
  });
  await page.waitForTimeout(250);
  const canvasBox = await canvas.boundingBox();
  assert.ok(canvasBox, "Graph Canvas has no bounding box");
  let target;
  let hovered = false;
  for (let attempt = 0; attempt < 5 && !hovered; attempt += 1) {
    target = await page.evaluate(id => {
      const graph = window.CONTEXT_MESH_GRAPH;
      const node = graph.graphData().nodes.find(item => item.id === id);
      const screen = graph.graph2ScreenCoords(node.x, node.y);
      return { id, x: screen.x, y: screen.y };
    }, targetId);
    await page.mouse.move(canvasBox.x + target.x, canvasBox.y + target.y);
    await page.waitForTimeout(100);
    hovered = (await page.locator("#graph").evaluate(element => element.style.cursor)) === "grab";
  }
  assert.equal(hovered, true, "Could not hover the target context node");
  const targetX = canvasBox.x + target.x;
  const targetY = canvasBox.y + target.y;
  await page.mouse.click(targetX, targetY);
  await page.waitForFunction(() => !document.querySelector("#inspector")?.classList.contains("empty"));
  assert.notEqual(await page.locator("#inspector h2").textContent(), "Select a node");

  await page.mouse.click(targetX, targetY, { button: "right" });
  assert.equal(
    await page.evaluate(id => {
      const node = window.CONTEXT_MESH_GRAPH.graphData().nodes.find(item => item.id === id);
      return Number.isFinite(node.fx) && Number.isFinite(node.fy);
    }, target.id),
    true,
    "Right-click did not pin the node",
  );
  await page.mouse.dblclick(targetX, targetY, { delay: 80 });
  assert.equal(
    await page.evaluate(id => {
      const node = window.CONTEXT_MESH_GRAPH.graphData().nodes.find(item => item.id === id);
      return node.fx == null && node.fy == null;
    }, target.id),
    true,
    "Double-click did not unpin the node",
  );

  await page.check("#pin-on-release");
  await page.evaluate(id => {
    const graph = window.CONTEXT_MESH_GRAPH;
    const node = graph.graphData().nodes.find(item => item.id === id);
    node.fx = node.x;
    node.fy = node.y;
    graph.resumeAnimation();
  }, target.id);
  await page.waitForTimeout(250);
  const dragPoint = await page.evaluate(id => {
    const graph = window.CONTEXT_MESH_GRAPH;
    const node = graph.graphData().nodes.find(item => item.id === id);
    const screen = graph.graph2ScreenCoords(node.x, node.y);
    return { x: screen.x, y: screen.y };
  }, target.id);
  await page.mouse.move(canvasBox.x + 12, canvasBox.y + 12);
  await page.waitForTimeout(50);
  await page.mouse.move(canvasBox.x + dragPoint.x, canvasBox.y + dragPoint.y);
  await page.waitForTimeout(100);
  assert.equal(
    await page.locator("#graph").evaluate(element => element.style.cursor),
    "grab",
    "Could not hover the context before drag",
  );
  await page.mouse.down();
  await page.mouse.move(
    canvasBox.x + dragPoint.x + 140,
    canvasBox.y + dragPoint.y + 70,
    { steps: 8 },
  );
  await page.mouse.up();
  await page.waitForTimeout(800);
  const recenteredFamily = await page.evaluate(id => {
    const graph = window.CONTEXT_MESH_GRAPH;
    const node = graph.graphData().nodes.find(item => item.id === id);
    const familyContexts = graph
      .graphData()
      .nodes.filter(item => item.type === "context" && item.familyId === node.familyId);
    const screen = graph.graph2ScreenCoords(node.x, node.y);
    return {
      pinned: Number.isFinite(node.fx) && Number.isFinite(node.fy),
      familyCentered: familyContexts.every(
        item =>
          Math.abs(item.familyX - node.x) < 0.01 &&
          Math.abs(item.familyY - node.y) < 0.01,
      ),
      screen,
      width: document.querySelector("#graph canvas").clientWidth,
      height: document.querySelector("#graph canvas").clientHeight,
    };
  }, target.id);
  assert.equal(recenteredFamily.pinned, true, "Pin after drag did not pin the context");
  assert.equal(
    recenteredFamily.familyCentered,
    true,
    "Pin after drag did not recenter the context family",
  );
  assert.ok(
    Math.abs(recenteredFamily.screen.x - recenteredFamily.width / 2) < 35 &&
      Math.abs(recenteredFamily.screen.y - recenteredFamily.height / 2) < 35,
    "Pin after drag did not center the viewport on the moved context",
  );
  await page.uncheck("#pin-on-release");
  await page.click("#unpin-all");
  await page.waitForTimeout(150);

  const fullNodeCount = await page.evaluate(() => window.CONTEXT_MESH_GRAPH.graphData().nodes.length);
  await page.selectOption("#local-depth", "1");
  await page.waitForTimeout(100);
  const localNodeCount = await page.evaluate(() => window.CONTEXT_MESH_GRAPH.graphData().nodes.length);
  assert.ok(localNodeCount < fullNodeCount, "Local-depth view did not reduce the graph");

  await page.locator("#repel-force").evaluate(element => {
    element.value = "0.6";
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await page.click("#reheat-graph");
  await page.click("#fit-graph");
  await page.waitForTimeout(400);

  await page.evaluate(() => {
    const graph = window.CONTEXT_MESH_GRAPH;
    const link = graph.graphData().links[0];
    const source = typeof link.source === "object"
      ? link.source
      : graph.graphData().nodes.find(node => node.id === link.source);
    const target = typeof link.target === "object"
      ? link.target
      : graph.graphData().nodes.find(node => node.id === link.target);
    source.x = source.fx = -90;
    source.y = source.fy = 0;
    target.x = target.fx = 90;
    target.y = target.fy = 0;
    graph.graphData({ nodes: [source, target], links: [link] });
    graph.centerAt(0, 0, 0);
    graph.zoom(2, 0);
  });
  await page.waitForTimeout(250);
  let linkPoint;
  let linkHovered = false;
  for (let attempt = 0; attempt < 5 && !linkHovered; attempt += 1) {
    linkPoint = await page.evaluate(() => {
      const graph = window.CONTEXT_MESH_GRAPH;
      const link = graph.graphData().links[0];
      const source = typeof link.source === "object" ? link.source : null;
      const target = typeof link.target === "object" ? link.target : null;
      return graph.graph2ScreenCoords(
        (source.x + target.x) / 2,
        (source.y + target.y) / 2,
      );
    });
    await page.mouse.move(canvasBox.x + 12, canvasBox.y + 12);
    await page.waitForTimeout(30);
    await page.mouse.move(canvasBox.x + linkPoint.x, canvasBox.y + linkPoint.y);
    await page.waitForTimeout(100);
    linkHovered =
      (await page.locator("#inspector").getAttribute("data-inspector-kind")) === "link";
  }
  assert.equal(linkHovered, true, "Could not hover the target connection");
  assert.equal(await page.locator("#inspector h2").textContent(), "Why are these connected?");
  assert.ok(
    (await page.locator("#inspector").textContent()).includes("Why this link exists"),
    "Link hover did not explain the relationship",
  );
  await page.mouse.click(canvasBox.x + linkPoint.x, canvasBox.y + linkPoint.y);
  assert.ok(
    (await page.locator("#inspector").textContent()).includes("Connection selected"),
    "Link click did not lock the connection inspector",
  );

  await page.click('[data-view="contexts-view"]');
  const firstContext = page.locator(".context-card").first();
  await firstContext.locator("summary").click();
  assert.equal(await firstContext.evaluate(element => element.open), true);

  if (screenshotPath) {
    await page.reload({ waitUntil: "load" });
    await page.click('[data-view="graph-view"]');
    await page.selectOption("#local-depth", "0");
    await page.selectOption("#detail-level", "core");
    await page.selectOption("#evidence-level", "high");
    await page.fill("#graph-search", "");
    await page.click("#fit-graph");
    await page.waitForTimeout(1400);
    await page.screenshot({ path: screenshotPath, fullPage: true });
  }

  assert.deepEqual(errors, [], errors.join("\n"));
  console.log(
    `Browser smoke passed: ${graphState.metrics["Graph nodes"]} nodes, ` +
    `${graphState.metrics["Graph edges"]} links`,
  );
} finally {
  await browser.close();
}

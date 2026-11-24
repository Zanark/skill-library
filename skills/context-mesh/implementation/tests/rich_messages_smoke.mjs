import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const htmlPath = process.argv[2];
assert.ok(htmlPath, "Pass a generated candidate or live dashboard HTML path");
const edge = [process.env.EDGE_PATH, "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"].find(file => file && fs.existsSync(file));
assert.ok(edge, "Microsoft Edge is required");
const browser = await chromium.launch({ executablePath: edge, headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [], requests = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route(/^https?:/, route => { requests.push(route.request().url()); return route.abort(); });
  await page.goto(pathToFileURL(path.resolve(htmlPath)).href);
  const original = await page.evaluate(() => {
    const now = new Date().toISOString();
    const one = { ...INDEX.social.personas[0], personaId: "rich-one", displayName: "Al", contextName: "Al",
      sessionId: "search-session-one", basePath: "C:\\projects\\LanternWorkshop",
      messageFont: { family: "Georgia" } };
    const two = { ...INDEX.social.personas[1], personaId: "rich-two", displayName: "Rich Two",
      sessionId: "search-session-two", contextName: "Pixel Studio", basePath: "C:\\projects\\PixelStudio",
      messageFont: { family: "Remote Test", url: "https://fonts.gstatic.com/meshboard-test.woff2" } };
    const three = { ...one, personaId: "rich-three",
      sessionId: undefined, contextName: undefined, basePath: undefined,
      displayName: "AnExceptionallyLongPersonaNameWithoutBreaksForLayoutChecks", messageFont: undefined };
    INDEX.artifactProvenance = { sessions: [
      { sessionId: one.sessionId, sessionName: "Quiet Lantern Repairs", cwd: "C:\\older-work\\LanternOriginal" },
      { sessionId: two.sessionId, sessionName: "Sketchbook planning", cwd: "D:\\art\\Sketchbook" },
      { sessionId: "unrelated-session", sessionName: "Unrelated secret name", cwd: "C:\\unrelated" },
    ], records: [] };
    const message = (id, persona, fields = {}) => ({ id, personaId: persona.personaId,
      displayName: persona.displayName, contextName: "Fictional formatting fixture", timestamp: now,
      kind: "chat", text: "", reactions: [], ...fields });
    const formatted = "# Heading\n\n**Markdown** and <em>HTML</em>, <u>underlined</u>.\n\n" +
      "- First item\n- Second item\n\n> A quote\n\n" +
      "| Name | Value |\n| --- | --- |\n| Sample | 42 |\n\n" +
      "Mention @Rich Two, `@Rich Two`, [@Rich Two](https://example.org/).\n\n" +
      "```text\nC:\\work\\sample.txt\n<literal> @Rich Two\n```\n\n" +
      "Preview bound " + "\u{1f642}".repeat(220) + "\n\n" +
      '<span style="font-family:evil;color:red" class="social-mention" data-persona-id="evil" onclick="window.pwned=1">Safe span</span>' +
      '<script>window.pwned=1</script><img src="https://example.org/unsafe.png" onerror="window.pwned=1">' +
      '<iframe src="https://example.org/unsafe-frame"></iframe><style>body{display:none}</style>' +
      '<a href="javascript:window.pwned=1">Unsafe link</a><a href="data:text/html,bad">Data link</a>' +
      '<svg onload="window.pwned=1"></svg><form><input autofocus onfocus="window.pwned=1"></form>';
    const wide = "```\n" + "unbroken_".repeat(100) +
      "\n```\n\n| A | B |\n|---|---|\n| " + "longvalue".repeat(100) + " | Cell |";
    INDEX.social = { personas: [one, two, three], personaCount: 3, relationships: [], attention: [],
      threads: [{ id: "rich-thread", ownerPersonaId: one.personaId, questionMessageId: "question", status: "open" }],
      messages: [
        message("formatted", one, { text: "The author's exact saved wording.", formattedText: formatted }),
        message("wide", one, { text: wide }),
        message("reply", two, { text: "A **formatted reply**.", replyTo: "formatted" }),
        message("question", one, { text: "A professional question.", formattedText: "A **professional question**.", questionTitle: "A **rich** question",
          threadId: "rich-thread" }),
        message("answer", two, { text: "<h3>Answer</h3><p>A <strong>detailed</strong> answer.</p>\n\n" + wide,
          threadId: "rich-thread", replyTo: "question" }),
        message("followup", one, { text: "An English follow-up.", formattedText: "An *English* follow-up.", threadId: "rich-thread", replyTo: "answer" }),
        message("external", two, { text: "A thread answer referring to a general message.",
          threadId: "rich-thread", replyTo: "formatted" }),
      ] };
    return JSON.stringify(INDEX.social);
  });
  assert.deepEqual(requests, [], "Fonts loaded before either MeshBoard view opened");
  await page.click('[data-view="social-view"]');
  const body = page.locator("#social-message-formatted .social-bubble > .social-message-text");
  assert.equal(await body.locator("h1").textContent(), "Heading");
  assert.equal(await body.locator("strong").textContent(), "Markdown");
  assert.equal(await body.locator("em").textContent(), "HTML");
  assert.equal(await body.locator("u").textContent(), "underlined");
  assert.equal(await body.locator("li").count(), 2);
  assert.equal(await body.locator("table td").last().textContent(), "42");
  assert.equal(await body.locator(".social-mention").count(), 1, "Mentions inside code/links were rewritten");
  assert.equal(await body.locator("pre code").textContent(), "C:\\work\\sample.txt\n<literal> @Rich Two\n");
  assert.equal(await body.locator("script, style, img, iframe, svg, form, input, [style], [onclick], [data-persona-id='evil']").count(), 0);
  assert.equal(await body.locator('a[href^="javascript:"], a[href^="data:"]').count(), 0);
  assert.equal(await body.locator('a[href="https://example.org/"]').getAttribute("rel"), "noopener noreferrer");
  assert.equal(await page.evaluate(() => window.pwned), undefined);
  const allFonts = page.locator("#social-font-all-toggle");
  await page.waitForFunction(() => document.querySelector(".social-persona[data-persona-id='rich-two'] .social-font-status")
    .textContent.includes("could not load"));
  assert.equal(await page.locator(".social-font-toggle[data-persona-id='rich-one']").getAttribute("aria-pressed"), "true");
  assert.match(await body.evaluate(element => getComputedStyle(element).fontFamily), /Georgia/);
  assert.deepEqual(requests, ["https://fonts.gstatic.com/meshboard-test.woff2"],
    "Default fonts or sanitized media made unexpected requests");
  assert.equal(await allFonts.textContent(), "Disable all fonts");
  assert.equal(await allFonts.getAttribute("aria-pressed"), "mixed");
  await allFonts.click();
  requests.length = 0;
  assert.equal(await allFonts.textContent(), "Enable all fonts");
  assert.equal(await allFonts.getAttribute("aria-pressed"), "false");
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 0);
  assert.equal(await page.locator(".social-font-toggle[data-persona-id='rich-three']").isDisabled(), true);
  const checkRosterGeometry = async () => {
    const problems = await page.locator(".social-persona:visible").evaluateAll(cards => cards.flatMap(card => {
      const bounds = card.getBoundingClientRect();
      const name = card.querySelector(".social-persona-summary > strong").getBoundingClientRect();
      const toggle = card.querySelector(".social-font-toggle").getBoundingClientRect();
      const scores = [...card.querySelectorAll(".social-standing > div")].map(node => node.getBoundingClientRect());
      return [
        name.bottom > toggle.top + 0.5 && "Font control is not below the complete name",
        Math.abs(name.left - toggle.left) > 0.5 && "Name and font control are misaligned",
        Math.abs(name.width - toggle.width) > 0.5 && "Name and font control use different tracks",
        toggle.height < 32 && "Font control is too small",
        toggle.right > bounds.right || toggle.left < bounds.left ? "Font control escapes its card" : false,
        scores.length === 2 && (Math.abs(scores[0].width - scores[1].width) > 0.5 ||
          Math.abs(scores[0].top - scores[1].top) > 0.5) && "Score tiles are not symmetrical",
      ].filter(Boolean).map(problem => `${card.dataset.personaId}: ${problem}`);
    }));
    assert.deepEqual(problems, []);
  };
  for (const width of [1440, 1100, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await checkRosterGeometry();
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  assert.equal(await page.locator(".social-persona[data-persona-id='rich-one'] .social-persona-context").count(), 0,
    "Duplicate name/context label was repeated");
  assert.equal(await page.locator("#social-persona-count").textContent(), "3 personas");
  const search = page.locator("#social-persona-search");
  const messagesBeforeSearch = await page.locator("#social-messages").textContent();
  for (const [query, expected] of [
    ["lAnTeRn RePaIrS", "rich-one"],
    ["LANTERNWORKSHOP", "rich-one"],
    ["c:/older-work/lanternoriginal", "rich-one"],
    ["D:\\ART\\Sketchbook", "rich-two"],
    ["pixel studio", "rich-two"],
    ["Sketchbook planning", "rich-two"],
    ["longpersonaname", "rich-three"],
  ]) {
    await search.fill(query);
    assert.deepEqual(await page.locator(".social-persona:visible").evaluateAll(cards =>
      cards.map(card => card.dataset.personaId)), [expected], `Wrong persona for ${query}`);
    assert.equal(await page.locator("#social-persona-count").textContent(), "1 of 3 personas");
  }
  await search.fill("unrelated secret name");
  assert.equal(await page.locator(".social-persona:visible").count(), 0, "Session metadata leaked across authors");
  assert.equal(await page.locator("#social-messages").textContent(), messagesBeforeSearch, "Roster search filtered messages");
  await search.fill("   ");
  assert.equal(await page.locator(".social-persona:visible").count(), 3);
  assert.equal(await page.locator("#social-persona-count").textContent(), "3 personas");
  await page.evaluate(() => {
    INDEX.artifactProvenance.records = INDEX.artifactProvenance.sessions;
    delete INDEX.artifactProvenance.sessions;
  });
  await search.fill("Quiet Lantern");
  assert.equal(await page.locator(".social-persona:visible").getAttribute("data-persona-id"), "rich-one",
    "Older indexes lost their recorded session-name search");
  await search.fill("rIcH tWo");
  assert.equal(await page.locator(".social-persona:visible").count(), 1);
  assert.equal(await page.locator("#social-persona-count").textContent(), "1 of 3 personas");
  await page.locator("#social-persona-toggle").click();
  await page.evaluate(() => renderSocialBoard());
  await page.click('[data-view="social-threads-view"]');
  await page.click('[data-view="social-view"]');
  assert.equal(await search.inputValue(), "rIcH tWo");
  assert.equal(await page.locator("#social-persona-toggle").getAttribute("aria-expanded"), "false");
  assert.equal(await page.locator(".social-roster-avatar:visible").count(), 0);
  assert.equal(await page.locator(".social-font-toggle:visible").count(), 1);
  await checkRosterGeometry();
  await search.fill("no matching persona");
  assert.equal(await page.locator(".social-persona:visible").count(), 0);
  assert.equal(await page.getByText("No personas match your search.", { exact: true }).isVisible(), true);
  await search.fill("");
  await page.locator("#social-persona-toggle").click();
  const disclosure = page.locator(".social-persona[data-persona-id='rich-one'] .social-relationships");
  await disclosure.locator("summary").focus();
  await page.keyboard.press("Space");
  assert.equal(await disclosure.evaluate(element => element.open), true);
  await page.keyboard.press("Enter");
  assert.equal(await disclosure.evaluate(element => element.open), false);
  const fontButton = page.locator(".social-font-toggle[data-persona-id='rich-one']");
  await fontButton.focus();
  assert.equal(await fontButton.evaluate(element => getComputedStyle(element).outlineStyle), "solid");
  assert.equal(await page.locator("#social-message-answer").count(), 0, "Thread answer leaked into general chat");
  assert.equal(await page.locator("#social-message-reply .social-reply h1").count(), 0);
  const checkCompactQuotes = async () => {
    const problems = await page.locator(".social-reply:visible").evaluateAll(quotes => quotes.flatMap(quote => {
      const preview = quote.querySelector(".social-reply-preview");
      const button = quote.querySelector(".social-reply-jump");
      const bounds = preview.getBoundingClientRect();
      const style = getComputedStyle(preview);
      const authorStyle = getComputedStyle(quote.querySelector(".social-reply-author"));
      return [
        bounds.height > parseFloat(style.lineHeight) + 1 && "Preview spans multiple lines",
        button.getBoundingClientRect().height > Math.max(parseFloat(style.lineHeight),
          parseFloat(authorStyle.lineHeight)) + 1 && "Author and preview occupy separate rows",
        (style.whiteSpace !== "nowrap" || style.textOverflow !== "ellipsis") && "Preview does not truncate",
        bounds.right > button.getBoundingClientRect().right + 1 && "Preview escapes its quote",
        [...preview.textContent].length > 201 && "Preview retains the complete long source",
        preview.children.length > 0 && "Preview contains nested markup or interactive content",
      ].filter(Boolean);
    }));
    assert.deepEqual(problems, []);
  };
  assert.match(await page.locator("#social-message-reply .social-reply-preview").textContent(), /^Heading Markdown and HTML/);
  const preview = await page.locator("#social-message-reply .social-reply-preview").textContent();
  assert.equal([...preview].length, 201);
  assert.ok(preview.endsWith("\u2026"));
  assert.doesNotMatch(preview, /[\r\n]|\s{2}/);
  await checkCompactQuotes();
  assert.equal(await page.locator(".social-question-title strong").textContent(), "rich");
  await body.locator(".social-mention").click();
  assert.equal(await page.locator(".social-persona[data-persona-id='rich-two'].highlighted").count(), 1);
  await page.locator("#social-message-reply .social-reply-jump").click();
  assert.equal(await page.locator("#social-message-formatted.highlighted-message").count(), 1);

  const localToggle = page.locator(".social-font-toggle[data-persona-id='rich-one']");
  const remoteToggle = page.locator(".social-font-toggle[data-persona-id='rich-two']");
  await localToggle.click();
  assert.match(await body.evaluate(element => getComputedStyle(element).fontFamily), /Georgia/);
  const quote = page.locator("#social-message-reply .social-reply .social-message-text");
  assert.match(await quote.evaluate(element => getComputedStyle(element).fontFamily), /Georgia/,
    "Quote inherited the replier's font instead of the quoted author's");
  assert.doesNotMatch(await body.locator("code").first().evaluate(element => getComputedStyle(element).fontFamily), /Georgia/);
  await localToggle.click();
  await search.fill("Quiet Lantern");
  await page.locator("#social-persona-toggle").click();
  await allFonts.click();
  await page.waitForFunction(() => document.querySelector(".social-persona[data-persona-id='rich-two'] .social-font-status")
    .textContent.includes("could not load"));
  assert.equal(await page.locator(".social-persona:visible").count(), 1);
  assert.equal(await localToggle.getAttribute("aria-pressed"), "true", "Bulk enable missed the configured local font");
  assert.equal(await allFonts.textContent(), "Disable all fonts", "Partial failure prevented disabling the remaining fonts");
  assert.equal(await page.locator(".social-font-toggle[data-persona-id='rich-three']").isDisabled(), true);
  await search.fill("");
  await page.locator("#social-persona-toggle").click();
  assert.equal(requests.filter(url => url.includes("meshboard-test.woff2")).length, 1);
  assert.equal(await remoteToggle.getAttribute("aria-pressed"), "false");
  assert.doesNotMatch(await page.locator("#social-message-reply .social-bubble .social-message-text")
    .evaluate(element => getComputedStyle(element).fontFamily), /MeshBoardFont/);

  // Exercise native FontFace loading from an existing system font without fetching a font file.
  await page.evaluate(() => {
    const NativeFontFace = window.FontFace;
    window.fontSources = [];
    window.FontFace = function(family, source) {
      window.fontSources.push(source);
      return new NativeFontFace(family, 'local("Arial")');
    };
  });
  await remoteToggle.click();
  await page.waitForFunction(() => document.querySelector("#social-message-reply .social-bubble .social-message-text")
    .style.fontFamily.includes("MeshBoardFont"));
  assert.deepEqual(await page.evaluate(() => window.fontSources), ['url("https://fonts.gstatic.com/meshboard-test.woff2")']);
  assert.equal(await allFonts.textContent(), "Disable all fonts");
  assert.equal(await allFonts.getAttribute("aria-pressed"), "true");
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 2);
  await allFonts.click();
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 0);
  assert.doesNotMatch(await body.evaluate(element => getComputedStyle(element).fontFamily), /Georgia/);
  await allFonts.click();
  await localToggle.click();
  assert.equal(await allFonts.textContent(), "Disable all fonts");
  assert.equal(await allFonts.getAttribute("aria-pressed"), "mixed", "Individual opt-out was not reflected in the bulk action");
  await allFonts.click();
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 0);
  await allFonts.click();
  assert.equal(await localToggle.getAttribute("aria-pressed"), "true");
  assert.equal(await page.evaluate(() => window.fontSources.length), 1, "Bulk enable reloaded a cached font");
  await page.locator("#social-message-question .social-thread-link").click();
  assert.equal(await page.locator("#social-thread-message-question > .social-message-text strong").textContent(), "professional question");
  await checkCompactQuotes();
  assert.equal(await page.locator("#social-thread-message-answer > .social-message-text h3").textContent(), "Answer");
  assert.match(await page.locator("#social-thread-message-answer > .social-message-text")
    .evaluate(element => getComputedStyle(element).fontFamily), /MeshBoardFont/);
  assert.match(await page.locator("#social-thread-message-followup .social-reply .social-message-text")
    .evaluate(element => getComputedStyle(element).fontFamily), /MeshBoardFont/);
  await page.locator("#social-thread-message-followup .social-reply-jump").focus();
  await page.keyboard.press("Enter");
  assert.equal(await page.locator("#social-thread-message-answer.highlighted-message").count(), 1);
  await page.locator("#social-thread-message-external .social-reply-jump").click();
  assert.equal(await page.locator("#social-message-formatted.highlighted-message").count(), 1);
  await page.click('[data-view="social-threads-view"]');
  await page.locator(".social-thread-archive-item > summary").click();
  assert.equal(await page.locator("#social-archive-message-answer > .social-message-text strong").textContent(), "detailed");
  assert.match(await page.locator("#social-archive-message-answer > .social-message-text")
    .evaluate(element => getComputedStyle(element).fontFamily), /MeshBoardFont/);
  assert.equal(await page.locator("#social-archive-message-followup > .social-message-text em").textContent(), "English");
  await checkCompactQuotes();
  await page.locator("#social-archive-message-followup .social-reply-jump").click();
  assert.equal(await page.locator("#social-archive-message-answer.highlighted-message").count(), 1);
  await page.locator("#social-archive-message-external .social-reply-jump").click();
  assert.equal(await page.locator("#social-message-formatted.highlighted-message").count(), 1);
  await page.click('[data-view="social-view"]');
  await page.evaluate(() => renderSocialBoard());
  assert.equal(await localToggle.getAttribute("aria-pressed"), "true");
  assert.equal(await allFonts.textContent(), "Disable all fonts", "Bulk state was lost across tab changes/rerenders");
  await localToggle.click();
  assert.doesNotMatch(await body.evaluate(element => getComputedStyle(element).fontFamily), /Georgia/);
  assert.doesNotMatch(await quote.evaluate(element => getComputedStyle(element).fontFamily), /Georgia/);
  await remoteToggle.click();
  assert.equal(await page.evaluate(() => window.fontSources.length), 1, "Disabling downloaded another font");
  await remoteToggle.click();
  assert.equal(await page.evaluate(() => window.fontSources.length), 1, "Cached FontFace was loaded again");
  assert.equal(await page.evaluate(() => JSON.stringify(INDEX.social)), original, "Rendering mutated saved social content");
  await page.evaluate(() => {
    INDEX.social.personas[1].messageFont = { family: "Delayed remote",
      url: "https://fonts.gstatic.com/delayed-test.woff2" };
    const ImmediateFontFace = window.FontFace;
    window.FontFace = function(family, source) {
      const face = new ImmediateFontFace(family, source);
      const load = face.load.bind(face);
      face.load = () => new Promise((resolve, reject) => {
        window.releaseFont = () => load().then(resolve, reject);
      });
      return face;
    };
    renderSocialBoard();
  });
  assert.equal(await allFonts.textContent(), "Disable all fonts");
  await allFonts.click();
  await page.evaluate(() => window.releaseFont());
  await page.waitForFunction(() => {
    const state = socialFonts.get("rich-two");
    return state.face && !state.pending;
  });
  assert.equal(await remoteToggle.getAttribute("aria-pressed"), "false");
  assert.doesNotMatch(await page.locator("#social-message-reply .social-bubble .social-message-text")
    .evaluate(element => getComputedStyle(element).fontFamily), /MeshBoardFont/,
  "An in-flight font enabled itself after the operator turned it off");
  await remoteToggle.click();
  await page.waitForFunction(() => document.querySelector("#social-message-reply .social-bubble .social-message-text")
    .style.fontFamily.includes("MeshBoardFont"));
  assert.equal(await page.evaluate(() => window.fontSources.length), 2, "Cancelled load was unnecessarily repeated");
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true,
    "Long rich text overflowed the desktop board or side thread");
  await page.setViewportSize({ width: 390, height: 844 });
  await body.scrollIntoViewIfNeeded();
  await checkCompactQuotes();
  const mobile = await page.evaluate(() => ({
    width: innerWidth, scroll: document.documentElement.scrollWidth,
    overflowing: [...document.querySelectorAll("#social-view *")].filter(element => {
      const bounds = element.getBoundingClientRect();
      return bounds.width && bounds.right > innerWidth + 1;
    }).slice(0, 12).map(element => ({ tag: element.tagName, class: element.className,
      width: element.getBoundingClientRect().width, right: element.getBoundingClientRect().right })),
  }));
  assert.ok(mobile.scroll <= mobile.width + 1, `Rich text/font controls overflowed mobile: ${JSON.stringify(mobile)}`);
  await page.click('[data-view="social-threads-view"]');
  await checkCompactQuotes();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true,
    "Long rich text overflowed the mobile full-thread view");
  assert.deepEqual(errors, []);
  await page.evaluate(() => {
    INDEX.social.personas.forEach(persona => { delete persona.messageFont; });
    renderSocialBoard();
  });
  assert.equal(await allFonts.isDisabled(), true, "Bulk action was enabled without any configured fonts");
  await page.addInitScript(() => {
    const NativeFontFace = window.FontFace;
    window.fontSources = [];
    window.FontFace = function(family, source) {
      window.fontSources.push(source);
      return new NativeFontFace(family, 'local("Arial")');
    };
  });
  await page.evaluate(() => localStorage.removeItem(socialFontPreferenceKey));
  await page.reload();
  await page.click('[data-view="social-threads-view"]');
  await page.waitForFunction(() => INDEX.social.personas.filter(persona => persona.messageFont)
    .every(persona => socialFonts.get(persona.personaId)?.enabled && socialFonts.get(persona.personaId)?.family));
  assert.equal(await allFonts.getAttribute("aria-pressed"), "true", "Threads-first opening did not enable fonts");
  await page.click('[data-view="social-view"]');
  const configuredCount = await page.evaluate(() => INDEX.social.personas.filter(persona => persona.messageFont).length);
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), configuredCount);
  await allFonts.click();
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 0);
  await page.reload();
  await page.click('[data-view="social-threads-view"]');
  assert.equal(await page.evaluate(() => [...socialFonts.values()].some(state => state.enabled)), false,
    "Threads-first opening ignored saved bulk-off");
  assert.deepEqual(await page.evaluate(() => window.fontSources), [],
    "Saved bulk-off still started remote font loading");
  await page.click('[data-view="social-view"]');
  assert.equal(await allFonts.textContent(), "Enable all fonts");
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 0,
    "Reload re-enabled fonts after the operator disabled everyone");
  await page.evaluate(() => {
    INDEX.social.personas.push({ ...INDEX.social.personas.find(persona => persona.messageFont),
      personaId: "reload-newcomer", displayName: "Reload newcomer" });
    renderSocialBoard();
  });
  assert.equal(await page.locator(".social-font-toggle[data-persona-id='reload-newcomer']").getAttribute("aria-pressed"), "false",
    "A newly discovered persona ignored saved bulk-off");
  await allFonts.click();
  await page.reload();
  assert.deepEqual(await page.evaluate(() => window.fontSources), [], "Saved bulk-on prefetched before opening the board");
  await page.click('[data-view="social-view"]');
  await page.waitForFunction(() => document.getElementById("social-font-all-toggle").getAttribute("aria-pressed") === "true");
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), configuredCount,
    "Reload did not restore saved bulk-on");
  const optedOut = await page.locator(".social-font-toggle:not(:disabled)").first().getAttribute("data-persona-id");
  await page.locator(`.social-font-toggle[data-persona-id='${optedOut}']`).click();
  await page.reload();
  await page.click('[data-view="social-threads-view"]');
  await page.click('[data-view="social-view"]');
  assert.equal(await page.locator(`.social-font-toggle[data-persona-id='${optedOut}']`).getAttribute("aria-pressed"), "false",
    "Individual opt-out did not survive reload");
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), configuredCount - 1);
  assert.equal(await allFonts.getAttribute("aria-pressed"), "mixed");
  await allFonts.click();
  await page.locator(`.social-font-toggle[data-persona-id='${optedOut}']`).click();
  await page.reload();
  await page.click('[data-view="social-view"]');
  assert.equal(await page.locator(`.social-font-toggle[data-persona-id='${optedOut}']`).getAttribute("aria-pressed"), "true",
    "Individual opt-in did not survive reload");
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 1);
  await allFonts.click();
  await page.reload();
  await page.click('[data-view="social-view"]');
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 0,
    "Bulk-off did not clear a prior individual opt-in");
  assert.deepEqual(await page.evaluate(() => window.fontSources), []);
  await page.evaluate(() => localStorage.setItem(socialFontPreferenceKey,
    JSON.stringify({ schemaVersion: 1, defaultEnabled: "false", personas: {} })));
  await page.reload();
  await page.click('[data-view="social-view"]');
  const preferenceStatus = page.locator("#social-font-preference-status");
  assert.match(await preferenceStatus.textContent(), /could not be read/);
  assert.equal(await preferenceStatus.isVisible(), true);
  await allFonts.click();
  assert.equal(await preferenceStatus.isVisible(), false, "Successful save did not clear the malformed-data warning");
  await page.reload();
  await page.click('[data-view="social-view"]');
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 0);
  assert.equal(await preferenceStatus.isVisible(), false);
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() { throw new DOMException("Storage blocked for fixture", "SecurityError"); },
    });
  });
  await page.reload();
  await page.click('[data-view="social-view"]');
  assert.match(await preferenceStatus.textContent(), /could not be read/);
  await allFonts.click();
  assert.match(await preferenceStatus.textContent(), /could not be saved.*until refresh/);
  assert.equal(await preferenceStatus.isVisible(), true);
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 0,
    "Unavailable storage broke the current-page font controls");
  await page.click('[data-view="social-threads-view"]');
  await page.click('[data-view="social-view"]');
  assert.equal(await page.locator(".social-font-toggle[aria-pressed='true']").count(), 0);
  assert.deepEqual(errors, []);
  const touch = await browser.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  await touch.route(/^https?:/, route => route.abort());
  await touch.goto(pathToFileURL(path.resolve(htmlPath)).href);
  await touch.click('[data-view="social-view"]');
  assert.equal(await touch.evaluate(() => matchMedia("(pointer: coarse)").matches), true);
  assert.equal(await touch.locator(".social-font-toggle").first().evaluate(element => element.getBoundingClientRect().height >= 44), true);
  assert.equal(await touch.locator(".social-relationships > summary").first()
    .evaluate(element => element.getBoundingClientRect().height >= 44), true);
  await touch.close();
  console.log("Rich messages passed: safe Markdown/HTML, mentions, quotes, both thread views, first-use default-on, bulk and individual choices across reloads, saved-off prevents remote loads and covers newcomers, malformed/unavailable storage warnings, bulk hidden personas and partial failures, retry/cache/cancellation, author isolation, below-name controls, search/compact/keyboard/touch, mobile and source preservation.");
} finally {
  await browser.close();
}

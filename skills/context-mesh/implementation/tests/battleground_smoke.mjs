import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const supplied = path.resolve(process.argv[2] || "");
assert.ok(fs.existsSync(supplied), "Pass the generated dashboard path");
const root = path.resolve(import.meta.dirname, "..");
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "mesh-battleground-"));
let html = fs.readFileSync(supplied, "utf8").replaceAll("\r\n", "\n");
if (process.argv.includes("--bundled")) {
  const activeRoot = path.resolve(path.dirname(supplied), "..");
  const template = fs.readFileSync(path.join(root, "scripts", "build_context_mesh.py"), "utf8");
  for (const file of ["dashboard.js", "dashboard.css"]) {
    const active = fs.readFileSync(path.join(activeRoot, "assets", file), "utf8").replaceAll("\r\n", "\n");
    const candidate = fs.readFileSync(path.join(root, "assets", file), "utf8").replaceAll("\r\n", "\n");
    assert.ok(html.includes(active), `Rebuild the dashboard before replacing ${file}`);
    html = html.replace(active, () => candidate);
  }
  if (!html.includes('id="battleground-graph"')) {
    const button = template.match(/^  <button id="battleground-graph".*$/m)?.[0];
    assert.ok(button, "Missing generated Battleground button");
    html = html.replace('<button id="animate-graph">Animate timeline</button>',
      `<button id="animate-graph">Animate timeline</button>\n${button}`);
  }
  if (!html.includes('id="battleground-speed"')) {
    const control = template.match(/^  <label class="chip".*id="battleground-speed".*$/m)?.[0];
    assert.ok(control, "Missing Battleground speed control");
    html = html.replace('<input id="graph-search"', `${control}\n  <input id="graph-search"`);
  }
}
const candidate = path.join(temporary, "dashboard.html");
fs.writeFileSync(candidate, html);
const edge = [process.env.EDGE_PATH,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].find(file => file && fs.existsSync(file));
assert.ok(edge, "Microsoft Edge is required");
let browser;
try {
  browser = await chromium.launch({ executablePath: edge, headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route(/^https?:/, route => route.abort());
  await page.goto(pathToFileURL(candidate).href);
  await page.click('[data-view="graph-view"]');
  await page.waitForFunction(() => window.CONTEXT_MESH_GRAPH?.graphData().nodes.length);

  const plans = await page.evaluate(() => {
    const nodes = ["a", "b", "c", "d", "hub", "isolated"].map(id => ({
      id, label: id, type: id === "hub" ? "hub" : "context"
    }));
    const links = [["a", "b"], ["a", "c"], ["b", "c"], ["c", "d"], ["hub", "a"], ["hub", "d"]]
      .map(([source, target]) => ({ source, target, type: "test", confidence: "high" }));
    const data = { nodes, links };
    const saved = JSON.stringify(data);
    const firsts = new Set();
    const winners = new Set();
    let multiSpearImpactsOnly = true;
    for (let seed = 1; seed <= 120; seed += 1) {
      let state = seed;
      const random = () => ((state = (Math.imul(state, 1664525) + 1013904223) >>> 0) / 4294967296);
      const plan = battlegroundPlan(data, random);
      firsts.add(plan[0].node.id);
      const order = new Map(plan.map((step, index) => [step.node.id, index]));
      if (new Set(order.keys()).size !== nodes.length) throw Error("Lost or duplicate node");
      const shots = plan.flatMap(step => step.incoming);
      if (shots.length !== links.length) throw Error("Lost or duplicate connection");
      if (!shots.every(shot => order.get(shot.fromId) < order.get(shot.toId))) throw Error("Spear orientation");
      const eligible = plan.filter(step => step.node.type !== "hub");
      const outgoing = new Map();
      shots.forEach(shot => outgoing.set(shot.fromId, (outgoing.get(shot.fromId) || 0) + 1));
      const best = Math.max(...eligible.map(step => outgoing.get(step.node.id) || 0));
      eligible.filter(step => (outgoing.get(step.node.id) || 0) === best).forEach(step => winners.add(step.node.id));
      multiSpearImpactsOnly &&= plan.every(step => step.heavy === (step.incoming.length > 1));
    }
    return {
      isolatedNeverStarts: !firsts.has("isolated"), differentStarts: firsts.size > 1,
      differentWinners: winners.size > 1, inputUnchanged: saved === JSON.stringify(data),
      multiSpearImpactsOnly,
      noEdgesRejected: battlegroundPlan({ nodes, links: [] }) === null
    };
  });
  for (const [name, passed] of Object.entries(plans)) assert.equal(passed, true, name);

  const fixture = await page.evaluate(() => {
    window.originalBattleGraph = INDEX.graph;
    const nodes = ["a", "b", "c", "hub", "isolated"].map((id, index) => ({
      id, label: id === "c" ? "<img src=x onerror=alert(1)>" : id,
      type: id === "hub" ? "hub" : "context", date: "2026-01-01",
      dateBasis: "fixture date", x: index * 120, y: index * 70
    }));
    const edges = [["a", "b"], ["a", "c"], ["b", "c"], ["hub", "a"], ["hub", "b"], ["hub", "c"]]
      .map(([source, target]) => ({ source, target, type: "cross-reference", confidence: "high" }));
    INDEX.graph = { nodes, edges };
    document.getElementById("detail-level").value = "full";
    updateGraphData();
    const node = graph.graphData().nodes.find(item => item.id === "a");
    pinnedPositions.set(node.id, { x: 120, y: 80 });
    updateGraphData();
    return { nodes: nodes.length, edges: edges.length };
  });
  await page.click("#battleground-graph");
  await page.waitForFunction(() => battleground?.revealed === 1);
  const first = await page.evaluate(() => battleground.steps[0].node.id);
  assert.notEqual(first, "isolated");
  assert.equal(await page.locator("#battleground-graph").getAttribute("aria-pressed"), "true");
  assert.equal(await page.locator("#fit-graph").isDisabled(), true);
  assert.equal(await page.evaluate(() => timelineAnimationFrame), null);
  assert.equal(await page.evaluate(() => graph.enableNodeDrag()), false);

  const singleImpact = await page.evaluate(() => {
    const state = battleground;
    cancelAnimationFrame(state.frame);
    const index = state.steps.findIndex(step => step.incoming.length === 1);
    advanceBattleground(state.startedAt + index * state.slotMs + 620);
    cancelAnimationFrame(state.frame);
    return { hits: state.hits, noInkCuts: state.cutNodes.size === 0,
      noImpactFrames: !document.getElementById("graph-stage").classList.contains("battleground-impact"),
      shaking: !!document.getElementById("graph").style.transform };
  });
  assert.equal(singleImpact.hits, 1);
  for (const field of ["noInkCuts", "noImpactFrames", "shaking"]) assert.equal(singleImpact[field], true, field);

  // Drive the real animation clock to a launch, impact and final beat without long sleeps.
  const impact = await page.evaluate(async () => {
    cancelAnimationFrame(battleground.frame);
    const state = battleground;
    const index = state.steps.findIndex(step => step.incoming.length > 1);
    advanceBattleground(state.startedAt + index * state.slotMs + 400);
    cancelAnimationFrame(state.frame);
    const launch = [...state.shots.values()].some(shot => !shot.hit &&
      state.now > shot.launchAt && state.now < shot.impactAt);
    advanceBattleground(state.startedAt + index * state.slotMs + 620);
    cancelAnimationFrame(state.frame);
    const target = state.steps[index].node;
    const context = document.createElement("canvas").getContext("2d");
    drawNode(target, context, 1);
    for (const link of graph.graphData().links) drawBattlegroundLink(link, context, 1);
    await new Promise(resolve => requestAnimationFrame(resolve));
    const center = graph.centerAt();
    return { launch, hits: state.hits, shaking: !!document.getElementById("graph").style.transform,
      heavy: document.getElementById("graph-stage").classList.contains("battleground-impact"),
      cameraMoved: Math.abs(graph.zoom() - state.camera.zoom) > 0.001 ||
        Math.abs(center.x - state.camera.x) > 0.001 || Math.abs(center.y - state.camera.y) > 0.001 };
  });
  assert.equal(impact.launch, true);
  assert.ok(impact.hits > 0);
  assert.equal(impact.shaking, true);
  assert.equal(impact.heavy, true, JSON.stringify(impact));
  assert.equal(impact.cameraMoved, true);
  const animeFrames = await page.evaluate(() => {
    const state = battleground;
    const originalNow = state.now;
    const target = currentNodeById.get(state.cut.nodeId);
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 420;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const render = age => {
      state.now = state.cut.time + age;
      context.setTransform(1, 0, 0, 1, 0, 0);
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.translate(210 - target.x, 210 - target.y);
      drawBattlegroundImpact(context, 1);
      return { image: canvas.toDataURL(), pixels: context.getImageData(0, 0, 420, 420).data };
    };
    const frames = [render(10), render(110), render(210)];
    const steady = render(65);
    const expired = render(310);
    const paperAndInk = frames.every(frame => {
      let paper = 0;
      let ink = 0;
      for (let index = 0; index < frame.pixels.length; index += 4) {
        if (frame.pixels[index + 3] < 250) continue;
        if (frame.pixels[index] > 220) paper += 1;
        if (frame.pixels[index] < 40) ink += 1;
      }
      return paper > 500 && ink > 500;
    });
    state.now = originalNow;
    const samePixels = frames[0].pixels.every((value, index) => value === steady.pixels[index]);
    return { threeDistinctInkCuts: new Set(frames.map(frame => frame.image)).size === 3,
      heldPose: samePixels, paperAndInk,
      clearsAfterImpact: expired.pixels.every(value => value === 0) };
  });
  for (const [name, passed] of Object.entries(animeFrames)) assert.equal(passed, true, name);
  if (process.env.CONTEXT_MESH_SCREENSHOT) {
    await page.screenshot({ path: process.env.CONTEXT_MESH_SCREENSHOT, fullPage: true });
  }
  const result = await page.evaluate(() => {
    const state = battleground;
    advanceBattleground(state.startedAt + state.durationMs + 10);
    cancelAnimationFrame(state.frame);
    const node = graph.graphData().nodes.find(item => item.id === state.winnerId);
    const outgoing = new Map();
    state.steps.flatMap(step => step.incoming).forEach(shot =>
      outgoing.set(shot.fromId, (outgoing.get(shot.fromId) || 0) + 1));
    return { hits: state.hits, winner: state.winnerId, winnerType: node?.type,
      winnerScore: state.scores.get(state.winnerId),
      highestEligible: Math.max(...state.data.nodes.filter(item => item.type !== "hub")
        .map(item => outgoing.get(item.id) || 0)),
      scoresMatchOutgoing: state.data.nodes.every(item =>
        (state.scores.get(item.id) || 0) === (outgoing.get(item.id) || 0)),
      finished: state.finished, nodes: graph.graphData().nodes.length,
      links: graph.graphData().links.length, pinned: graph.graphData().nodes.find(item => item.id === "a").fx,
      free: graph.graphData().nodes.filter(item => item.id !== "a").every(item => item.fx == null),
      interactive: graph.enableNodeDrag(), cleanTransform: document.getElementById("graph").style.transform === "",
      noInjection: !state.hud.querySelector("img") };
  });
  assert.equal(result.hits, fixture.edges);
  assert.equal(result.nodes, fixture.nodes);
  assert.equal(result.links, fixture.edges);
  assert.notEqual(result.winnerType, "hub");
  assert.equal(result.winnerScore, result.highestEligible);
  for (const field of ["scoresMatchOutgoing", "finished", "free", "interactive", "cleanTransform", "noInjection"]) assert.equal(result[field], true, field);
  assert.equal(result.pinned, 120);
  await page.click("#battleground-graph");
  await page.waitForFunction(() => battleground?.revealed === 1);
  assert.notEqual(await page.evaluate(() => battleground.steps[0].node.id), first, "Consecutive seeds repeated");
  await page.keyboard.press("Escape");
  assert.equal(await page.evaluate(() => battleground), null);
  assert.equal(await page.locator(".battleground-hud").count(), 0);
  assert.equal(await page.locator("#fit-graph").isDisabled(), false);
  assert.equal(await page.evaluate(() => graph.graphData().nodes.length), fixture.nodes);

  const speedResults = [];
  const timelineDuration = await page.locator("#animation-duration").inputValue();
  for (const speed of [2, 4, 8]) {
    await page.selectOption("#battleground-speed", String(speed));
    await page.click("#battleground-graph");
    await page.waitForFunction(() => battleground?.revealed === 1);
    assert.equal(await page.locator("#battleground-speed").isDisabled(), true);
    const paced = await page.evaluate(() => {
      const state = battleground;
      cancelAnimationFrame(state.frame);
      advanceBattleground(state.startedAt + state.steps.length * state.slotMs);
      cancelAnimationFrame(state.frame);
      const awaitedImpacts = state.durationMs > state.steps.length * state.slotMs;
      const waitedForImpacts = !awaitedImpacts || !state.finished;
      advanceBattleground(state.startedAt + state.durationMs + 1);
      cancelAnimationFrame(state.frame);
      const outgoing = new Map();
      state.steps.flatMap(step => step.incoming).forEach(shot =>
        outgoing.set(shot.fromId, (outgoing.get(shot.fromId) || 0) + 1));
      return { speed: state.speed, slotMs: state.slotMs, hits: state.hits, finished: state.finished,
        waitedForImpacts, awaitedImpacts,
        scoresMatchOutgoing: state.data.nodes.every(node =>
          (state.scores.get(node.id) || 0) === (outgoing.get(node.id) || 0)) };
    });
    assert.equal(paced.slotMs, 1100 / speed);
    assert.equal(paced.hits, fixture.edges);
    for (const name of ["finished", "waitedForImpacts", "scoresMatchOutgoing"]) assert.equal(paced[name], true, name);
    if (speed === 8) assert.equal(paced.awaitedImpacts, true);
    assert.equal(await page.locator("#battleground-speed").isDisabled(), false);
    assert.equal(await page.locator("#battleground-speed").inputValue(), String(speed));
    assert.equal(await page.locator("#animation-duration").inputValue(), timelineDuration);
    speedResults.push(paced);
    await page.keyboard.press("Escape");
  }
  await page.selectOption("#battleground-speed", "1");

  await page.click("#battleground-graph");
  await page.click("#animate-graph");
  assert.equal(await page.evaluate(() => battleground), null);
  assert.equal(await page.locator("#animate-graph").innerText(), "Stop animation");
  await page.click("#battleground-graph");
  assert.equal(await page.evaluate(() => timelineAnimationFrame), null);
  await page.selectOption("#evidence-level", "all");
  assert.equal(await page.evaluate(() => battleground), null);
  await page.click("#battleground-graph");
  await page.click('[data-view="social-view"]');
  assert.equal(await page.evaluate(() => battleground), null);

  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.click('[data-view="graph-view"]');
  await page.selectOption("#battleground-speed", "8");
  await page.click("#battleground-graph");
  const reduced = await page.evaluate(() => {
    const state = battleground;
    cancelAnimationFrame(state.frame);
    state.steps.forEach(step => { step.heavy = true; });
    advanceBattleground(state.startedAt + 2 * state.slotMs + 5);
    cancelAnimationFrame(state.frame);
    const shot = [...state.shots.values()][0];
    state.cut = { nodeId: shot.toId, fromId: shot.fromId, time: state.now };
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    drawBattlegroundImpact(context, 1);
    return { reduced: state.reducedMotion,
      speedWorks: state.speed === 8 && state.slotMs === 20,
      noShake: document.getElementById("graph").style.transform === "",
      noFlash: !document.getElementById("graph-stage").classList.contains("battleground-impact"),
      noAnimeInk: context.getImageData(0, 0, canvas.width, canvas.height).data.every(value => value === 0),
      scoreWorks: state.hits > 0 };
  });
  for (const [name, passed] of Object.entries(reduced)) assert.equal(passed, true, name);
  await page.keyboard.press("Escape");
  await page.selectOption("#animation-duration", "5");
  await page.click("#animate-graph");
  await page.waitForFunction(() => timelineAnimationFrame == null, { }, { timeout: 10000 });
  assert.equal(await page.locator("#animate-graph").innerText(), "Replay timeline");
  assert.equal(await page.evaluate(() => graph.graphData().nodes.length), fixture.nodes);
  assert.equal(await page.evaluate(() => graph.graphData().links.length), fixture.edges);
  await page.evaluate(() => {
    INDEX.graph = { nodes: [{ id: "alone", label: "alone", type: "context" }], edges: [] };
    updateGraphData();
  });
  await page.click("#battleground-graph");
  assert.equal(await page.evaluate(() => battleground), null);
  assert.match(await page.locator("#animation-status").innerText(), /at least one visible connection/);
  assert.equal(await page.evaluate(() => graph.graphData().nodes.length), 1);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.selectOption("#battleground-speed", "1");
  await page.evaluate(() => {
    INDEX.graph = window.originalBattleGraph;
    pinnedPositions.clear();
    positionCache.clear();
    document.getElementById("detail-level").value = "full";
    updateGraphData();
    window.beforeActualBattle = JSON.stringify(INDEX.graph);
  });
  await page.click("#battleground-graph");
  await page.waitForFunction(() => battleground?.revealed === 1);
  const live = await page.evaluate(() => {
    const state = battleground;
    cancelAnimationFrame(state.frame);
    const beat = state.steps.findIndex(step => step.incoming.length > 1);
    advanceBattleground(state.startedAt + beat * state.slotMs + 620);
    cancelAnimationFrame(state.frame);
    return { nodes: state.data.nodes.length, links: state.data.links.length,
      finitePositions: state.data.nodes.every(node => Number.isFinite(node.x) && Number.isFinite(node.y)) };
  });
  if (process.env.CONTEXT_MESH_LIVE_SCREENSHOT) {
    await page.screenshot({ path: process.env.CONTEXT_MESH_LIVE_SCREENSHOT, fullPage: true });
  }
  const liveResult = await page.evaluate(() => {
    const state = battleground;
    advanceBattleground(state.startedAt + state.durationMs + 10);
    cancelAnimationFrame(state.frame);
    const result = { hits: state.hits, inputUnchanged: window.beforeActualBattle === JSON.stringify(INDEX.graph),
      winnerExcludesHub: state.data.nodes.find(node => node.id === state.winnerId)?.type !== "hub",
      complete: graph.graphData().nodes.length === state.data.nodes.length &&
        graph.graphData().links.length === state.data.links.length };
    stopBattleground();
    return result;
  });
  assert.equal(liveResult.hits, live.links);
  for (const [name, passed] of Object.entries(liveResult)) {
    if (name !== "hits") assert.equal(passed, true, name);
  }
  assert.equal(live.finitePositions, true);
  assert.deepEqual(errors, [], "Unexpected browser errors");
  console.log(JSON.stringify({ plans, singleImpact, impact, animeFrames, result, speedResults, reduced, live, liveResult,
    cancellationAndModeSwitching: true, timelineComplete: true, noEdgeCase: true }));
} finally {
  await browser?.close();
  fs.rmSync(temporary, { recursive: true, force: true });
}

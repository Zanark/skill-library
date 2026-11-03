import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const htmlPath = process.env.DOCUMENTATION_MESH_HTML;
assert.ok(htmlPath && fs.existsSync(htmlPath), "Set DOCUMENTATION_MESH_HTML to a generated report");
const candidates = [
  process.env.EDGE_PATH,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);
const edgePath = candidates.find(candidate => fs.existsSync(candidate));
assert.ok(edgePath, "Microsoft Edge executable was not found");

const errors = [];
const browser = await chromium.launch({
  executablePath: edgePath,
  headless: true,
  args: ["--allow-file-access-from-files"],
});

try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
  page.on("pageerror", error => errors.push(`pageerror: ${error.message}`));
  page.on("console", message => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  await page.goto(pathToFileURL(path.resolve(htmlPath)).href, { waitUntil: "load" });
  await page.waitForSelector(".document");
  const initialDocuments = await page.locator(".document").count();
  assert.ok(initialDocuments > 0, "Catalogue did not load");
  const firstTitle = await page.locator(".document .title").first().textContent();
  await page.fill("#doc-search", firstTitle);
  assert.ok((await page.locator(".document").count()) > 0, "Catalogue search failed");
  await page.fill("#doc-search", "");
  const familyOptions = await page.locator("#family-filter option").count();
  if (familyOptions > 1) {
    await page.selectOption("#family-filter", { index: 1 });
    assert.ok((await page.locator(".document").count()) > 0, "Family filter removed every document");
    await page.selectOption("#family-filter", "");
  }
  await page.click('[data-view="health"]');
  await page.waitForSelector(".finding");
  assert.ok((await page.locator(".finding").count()) > 0, "Health findings did not load");
  await page.click('[data-view="graph"]');
  await page.waitForSelector("#graph-canvas canvas");
  await page.waitForTimeout(1200);
  const state = await page.evaluate(() => ({
    forceGraph: typeof window.ForceGraph === "function",
    nodes: window.document.querySelector("#graph-canvas canvas")?.width > 0,
    graphNodes: window.document.querySelector("#graph-canvas canvas") &&
      window.DOCUMENTATION_MESH_INDEX.graph.nodes.length,
    defaultEdges: window.DOCUMENTATION_MESH_INDEX.graph.edges
      .filter(edge => edge.shownByDefault)
      .every(edge => edge.confidence === "high"),
  }));
  assert.equal(state.forceGraph, true, "ForceGraph did not load");
  assert.equal(state.nodes, true, "Graph canvas has no size");
  assert.ok(state.graphNodes > 0, "Graph contains no nodes");
  assert.equal(state.defaultEdges, true, "Default graph includes non-strong edges");
  await page.waitForTimeout(1800);
  assert.equal(
    await page.evaluate(() =>
      window.DOCUMENTATION_MESH_GRAPH.graphData().nodes.every(
        node => Number.isFinite(node.x) && Number.isFinite(node.y),
      ),
    ),
    true,
    "Graph contains non-finite coordinates",
  );
  await page.evaluate(() => {
    const graph = window.DOCUMENTATION_MESH_GRAPH;
    const link = graph.graphData().links[0];
    graph.onLinkClick()(link);
  });
  assert.match(await page.locator("#inspector").textContent(), /Why connected\?/);
  await page.evaluate(() => {
    const graph = window.DOCUMENTATION_MESH_GRAPH;
    const node = graph.graphData().nodes[0];
    graph.onNodeRightClick()(node);
  });
  assert.equal(
    await page.evaluate(() => {
      const node = window.DOCUMENTATION_MESH_GRAPH.graphData().nodes[0];
      return Number.isFinite(node.fx) && Number.isFinite(node.fy);
    }),
    true,
    "Right-click pin handler did not pin",
  );
  await page.click("#unpin-all");
  assert.equal(
    await page.evaluate(() =>
      window.DOCUMENTATION_MESH_GRAPH.graphData().nodes.every(
        node => node.fx == null && node.fy == null,
      ),
    ),
    true,
    "Unpin all did not clear pins",
  );
  await page.fill("#graph-search", "Guide");
  await page.selectOption("#detail-level", "full");
  await page.selectOption("#evidence-level", "incidental");
  await page.selectOption("#local-depth", "1");
  await page.click("#reheat-graph");
  await page.selectOption("#animation-duration", "5");
  await page.click("#animate-graph");
  await page.waitForTimeout(250);
  assert.match(await page.locator("#animation-status").textContent(), /Timeline/);
  await page.click("#animate-graph");
  await page.setViewportSize({ width: 800, height: 900 });
  await page.waitForTimeout(100);
  assert.ok((await page.locator("#graph-canvas").boundingBox()).width > 0, "Responsive graph collapsed");
  assert.deepEqual(errors, [], errors.join("\n"));
} finally {
  await browser.close();
}

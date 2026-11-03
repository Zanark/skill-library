"use strict";

const INDEX = window.CONTEXT_MESH_INDEX;
const TYPE_COLORS = {
  context: "#60a5fa",
  memory: "#34d399",
  zmem: "#c084fc",
  hub: "#fbbf24"
};
const EDGE_COLORS = {
  "cross-reference": "#7dd3fc",
  "contains-memory": "#3f7f73",
  "zmem-reference": "#9a70c2",
  semantic: "#a78bfa",
  episodic: "#d8b4fe",
  procedural: "#f0abfc",
  unscoped: "#596173"
};

let graph = null;
let graphInitialized = false;
let hoveredNode = null;
let hoveredLink = null;
let selectedNodeId = null;
let selectedLinkKey = null;
let lockedInspection = null;
let localDepth = 0;
let graphSearch = "";
let adjacency = new Map();
let degreeById = new Map();
let positionCache = new Map();
let currentNodeById = new Map();
let currentLinkByKey = new Map();
let pinnedPositions = new Map();
let familyAnchorOverrides = new Map();
let timelineAnimationFrame = null;
let timelineAnimationData = null;
let battleground = null;
let lastBattlegroundStarter = null;

const physics = {
  center: 0.52,
  repel: 10,
  link: 1,
  distance: 250,
  collision: 60,
  friction: 0.4,
  cooling: 0.023,
  nodeSize: 1,
  linkThickness: 1,
  textFade: 0
};

const esc = value =>
  String(value ?? "").replace(
    /[&<>"']/g,
    character =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      })[character]
  );

const clamp = (value, minimum, maximum) =>
  Math.max(minimum, Math.min(maximum, value));

function list(items, empty = "Nothing recorded.") {
  return items?.length
    ? `<ul>${items.map(item => `<li>${esc(item)}</li>`).join("")}</ul>`
    : `<p class="muted">${empty}</p>`;
}

function renderPortfolio() {
  const summary = document.getElementById("summary");
  const metrics = [
    ["Contexts", INDEX.summary.contextCount],
    ["zmem memories", INDEX.summary.zmemCount],
    ["Graph nodes", INDEX.summary.graphNodeCount],
    ["Graph edges", INDEX.summary.graphEdgeCount],
    ["Fresh contexts", INDEX.summary.freshness.fresh],
    ["Stale contexts", INDEX.summary.freshness.stale]
  ];
  summary.innerHTML = metrics
    .map(
      ([label, value]) =>
        `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`
    )
    .join("");

  const renderContexts = () => {
    const query = document.getElementById("search").value.toLowerCase();
    const freshness = document.getElementById("freshness-filter").value;
    const rows = INDEX.contexts.filter(
      context =>
        (!freshness || context.freshness.label === freshness) &&
        (!query || JSON.stringify(context).toLowerCase().includes(query))
    );
    document.getElementById("contexts").innerHTML = rows
      .map(
        context => `
          <details class="context-card" data-status="${context.freshness.label}">
            <summary>
              <span class="context-title">${esc(context.name)}</span>
              <span class="path">${esc(context.basePath)}</span>
              <span class="badge ${context.freshness.label}">
                ${context.freshness.label} - ${context.lastUpdated || "unknown"}
              </span>
            </summary>
            <div class="content">
              <div class="columns">
                <div class="card"><h3>Identity</h3>${list(context.identity)}</div>
                <div class="card"><h3>Current focus</h3>${list(context.focus)}</div>
                <div class="card"><h3>Threads</h3>${list(context.threads)}</div>
                <div class="card"><h3>Next steps</h3>${list(context.nextSteps)}</div>
                <div class="card"><h3>Open questions / re-verify</h3>${list(context.openQuestions, "None recorded.")}</div>
                <div class="card"><h3>Memory nodes indexed</h3>${list(context.memory.map(memory => memory.text))}</div>
              </div>
              <div class="card" style="margin-top:12px">
                <h3>Timeline</h3>
                <div class="timeline">
                  ${
                    context.timeline.length
                      ? context.timeline
                          .map(
                            event => `
                              <div class="event">
                                <time>${esc(event.date)}</time> - <strong>${esc(event.title)}</strong>
                                <p>${esc(event.summary)}</p>
                              </div>`
                          )
                          .join("")
                      : '<p class="muted">No dated journal entries.</p>'
                  }
                </div>
              </div>
            </div>
          </details>`
      )
      .join("");
  };

  document.getElementById("search").addEventListener("input", renderContexts);
  document
    .getElementById("freshness-filter")
    .addEventListener("change", renderContexts);
  renderContexts();
}

function artifactLogicalName(value) {
  const fileName = String(value || "")
    .trim()
    .replaceAll("/", "\\")
    .split("\\")
    .pop()
    .toLowerCase();
  const dot = fileName.lastIndexOf(".");
  const stem = dot >= 0 ? fileName.slice(0, dot) : fileName;
  const suffix = dot >= 0 ? fileName.slice(dot) : "";
  return `${stem.replace(/\s+(?:\(\d+\)|\d+)$/, "")}${suffix}`;
}

function artifactActionLabel(action) {
  return (
    {
      created: "Created",
      generated: "Generated",
      modified: "Modified",
      requested: "Requested",
      inspected: "Inspected only",
      mentioned: "Mentioned only"
    }[action] || action
  );
}

function artifactScore(record, query) {
  const normalizedQuery = query.trim().replaceAll("/", "\\").toLowerCase();
  const logicalQuery = artifactLogicalName(normalizedQuery);
  const actionScores = {
    created: 400,
    generated: 380,
    modified: 300,
    requested: 170,
    inspected: 90,
    mentioned: 40
  };
  let score = actionScores[record.action] || 0;
  if (record.logicalName === logicalQuery) {
    score += 140;
  }
  if (record.fileName?.toLowerCase() === normalizedQuery) {
    score += 1;
  }
  if (record.logicalName.includes(logicalQuery)) {
    score += 25;
  }
  return score;
}

function artifactMatches(record, query) {
  const normalizedQuery = query.trim().replaceAll("/", "\\").toLowerCase();
  const logicalQuery = artifactLogicalName(normalizedQuery);
  if (logicalQuery.length < 3) {
    return false;
  }
  return (
    record.logicalName === logicalQuery ||
    record.logicalName.includes(logicalQuery) ||
    logicalQuery.includes(record.logicalName) ||
    record.fileName?.toLowerCase().includes(normalizedQuery) ||
    record.path?.toLowerCase().includes(normalizedQuery) ||
    record.paths?.some(path => path.toLowerCase().includes(normalizedQuery))
  );
}

function renderArtifactResults(query) {
  const container = document.getElementById("artifact-results");
  const records = INDEX.artifactProvenance?.records || [];
  if (!query.trim()) {
    container.innerHTML =
      '<div class="card artifact-empty"><strong>Paste a file path or filename to trace it back to a chat.</strong></div>';
    return;
  }

  const matches = records
    .filter(record => artifactMatches(record, query))
    .map(record => ({ ...record, searchScore: artifactScore(record, query) }))
    .sort(
      (left, right) =>
        right.searchScore - left.searchScore ||
        String(left.firstSeen).localeCompare(String(right.firstSeen))
    )
    .slice(0, 12);

  if (!matches.length) {
    container.innerHTML = `
      <div class="card artifact-empty">
        <strong>No local session evidence found.</strong>
        <p class="muted">The file may predate the indexed history window, use a different name, or have been created outside Copilot.</p>
      </div>`;
    return;
  }

  const topIsOrigin = ["created", "generated", "modified"].includes(
    matches[0].action
  );
  container.innerHTML = matches
    .map((record, index) => {
      const paths = record.paths?.length
        ? record.paths
        : record.path
          ? [record.path]
          : [];
      const rank =
        index === 0
          ? topIsOrigin
            ? "Likely origin"
            : "Best available match"
          : artifactActionLabel(record.action);
      const evidence = (record.evidence || [])
        .map(
          item => `
            <details>
              <summary>${esc(artifactActionLabel(item.action))} - ${esc(item.timestamp || "time unknown")}</summary>
              <blockquote>${esc(item.excerpt || "No excerpt recorded.")}</blockquote>
              ${
                item.prompt
                  ? `<p><strong>Nearby user prompt</strong></p><blockquote>${esc(item.prompt)}</blockquote>`
                  : ""
              }
            </details>`
        )
        .join("");
      return `
        <article class="card artifact-result ${index === 0 ? "origin" : "secondary"}">
          <div class="artifact-result-head">
            <div>
              <div class="artifact-rank">${esc(rank)}</div>
              <h3>${esc(record.sessionName || "Unnamed session")}</h3>
              <span class="badge">${esc(artifactActionLabel(record.action))}</span>
            </div>
            <span class="artifact-score">Evidence rank ${record.searchScore}</span>
          </div>
          <div class="artifact-meta">
            <div><strong>Session ID</strong><span class="artifact-paths">${esc(record.sessionId)}</span></div>
            <div><strong>Working directory</strong><span class="artifact-paths">${esc(record.cwd || "Unknown")}</span></div>
            <div><strong>First evidence</strong>${esc(record.firstSeen || "Unknown")}</div>
            <div><strong>Last evidence</strong>${esc(record.lastSeen || "Unknown")}</div>
            <div><strong>Session state</strong><span class="artifact-paths">${esc(record.sessionStatePath)}</span></div>
            <div><strong>Matched name</strong><span class="artifact-paths">${esc(record.logicalName)}</span></div>
          </div>
          ${
            paths.length
              ? `<div><strong>Observed path${paths.length > 1 ? "s" : ""}</strong>${list(paths)}</div>`
              : ""
          }
          <div class="artifact-evidence">
            <strong>Why this chat matched</strong>
            ${evidence || '<p class="muted">No concise excerpt was retained.</p>'}
          </div>
        </article>`;
    })
    .join("");
}

function bindArtifactFinder() {
  const input = document.getElementById("artifact-search");
  const status = document.getElementById("artifact-index-status");
  const metadata = INDEX.artifactProvenance || {};
  status.textContent = `${(metadata.records || []).length.toLocaleString()} artifact/session matches indexed from ${metadata.sessionCount || 0} local chats across the last ${metadata.historyDays || "configured"} days.`;
  const search = () => renderArtifactResults(input.value);
  document
    .getElementById("artifact-search-button")
    .addEventListener("click", search);
  input.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      search();
    }
  });
  const initialQuery = new URLSearchParams(window.location.search).get("artifact");
  if (initialQuery) {
    input.value = initialQuery;
    renderArtifactResults(initialQuery);
  } else {
    renderArtifactResults("");
  }
}

function forceCurve(value, coefficient = 0.01) {
  return (
    (Math.pow(coefficient, 1 - value) - coefficient) / (1 - coefficient)
  );
}

function nodeId(endpoint) {
  return typeof endpoint === "object" ? endpoint.id : endpoint;
}

function linkKey(link) {
  const endpoints = [nodeId(link.source), nodeId(link.target)].sort();
  return `${endpoints[0]}|${endpoints[1]}|${link.type}`;
}

function capturePositions() {
  if (!graph) {
    return;
  }
  graph.graphData().nodes.forEach(node => {
    positionCache.set(node.id, {
      x: node.x,
      y: node.y,
      vx: node.vx,
      vy: node.vy,
      fx: node.fx,
      fy: node.fy
    });
  });
}

function requestGraphRedraw() {
  graph?.resumeAnimation();
}

function typeVisible(node) {
  const detailLevel = document.getElementById("detail-level").value;
  if (node.type === "context") {
    return true;
  }
  if (node.type === "memory") {
    return detailLevel === "context-memory" || detailLevel === "full";
  }
  if (node.type === "hub" || node.type === "zmem") {
    return detailLevel === "full";
  }
  return false;
}

function edgeVisible(edge) {
  return (
    document.getElementById("evidence-level").value === "all" ||
    edge.confidence === "high"
  );
}

function neighborhoodIds(seedId, depth, candidateIds, edges) {
  if (!seedId || !depth || !candidateIds.has(seedId)) {
    return candidateIds;
  }
  const neighbors = new Map();
  edges.forEach(edge => {
    if (!candidateIds.has(edge.source) || !candidateIds.has(edge.target)) {
      return;
    }
    if (!neighbors.has(edge.source)) {
      neighbors.set(edge.source, new Set());
    }
    if (!neighbors.has(edge.target)) {
      neighbors.set(edge.target, new Set());
    }
    neighbors.get(edge.source).add(edge.target);
    neighbors.get(edge.target).add(edge.source);
  });

  const visible = new Set([seedId]);
  let frontier = new Set([seedId]);
  for (let hop = 0; hop < depth; hop += 1) {
    const next = new Set();
    frontier.forEach(id => {
      (neighbors.get(id) || []).forEach(neighbor => {
        if (!visible.has(neighbor)) {
          visible.add(neighbor);
          next.add(neighbor);
        }
      });
    });
    frontier = next;
  }
  return visible;
}

function stableAngle(value) {
  let hash = 0;
  for (const character of String(value)) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  }
  return (hash % 360) * (Math.PI / 180);
}

function assignFamilyTargets(nodes, links) {
  const nodeById = new Map(nodes.map(node => [node.id, node]));
  const contexts = nodes.filter(node => node.type === "context");
  const contextIds = new Set(contexts.map(node => node.id));
  const neighbors = new Map(contexts.map(node => [node.id, new Set()]));

  links.forEach(link => {
    const source = nodeId(link.source);
    const target = nodeId(link.target);
    if (
      link.type === "cross-reference" &&
      contextIds.has(source) &&
      contextIds.has(target)
    ) {
      neighbors.get(source).add(target);
      neighbors.get(target).add(source);
    }
  });

  const components = [];
  const visited = new Set();
  contexts
    .slice()
    .sort((left, right) => left.id.localeCompare(right.id))
    .forEach(context => {
      if (visited.has(context.id)) {
        return;
      }
      const ids = [];
      const queue = [context.id];
      visited.add(context.id);
      while (queue.length) {
        const id = queue.shift();
        ids.push(id);
        [...(neighbors.get(id) || [])]
          .sort()
          .forEach(neighbor => {
            if (!visited.has(neighbor)) {
              visited.add(neighbor);
              queue.push(neighbor);
            }
          });
      }
      components.push(ids.sort());
    });

  const connected = components
    .filter(component => component.length > 1)
    .sort((left, right) => right.length - left.length || left[0].localeCompare(right[0]));
  const isolated = components
    .filter(component => component.length === 1)
    .sort((left, right) => left[0].localeCompare(right[0]));
  const familyByContext = new Map();
  const anchorByFamily = new Map();

  connected.forEach((component, index) => {
    const familyId = `family:${component.join(",")}`;
    const angle = stableAngle(familyId);
    const radius = index === 0 ? 0 : 260;
    const fallback = {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius
    };
    anchorByFamily.set(
      familyId,
      familyAnchorOverrides.get(familyId) || fallback
    );
    component.forEach(id => familyByContext.set(id, familyId));
  });

  isolated.forEach((component, index) => {
    const familyId = `family:${component[0]}`;
    const angle =
      (index / Math.max(isolated.length, 1)) * 2 * Math.PI - Math.PI / 2;
    const fallback = {
      x: Math.cos(angle) * 620,
      y: Math.sin(angle) * 620
    };
    anchorByFamily.set(
      familyId,
      familyAnchorOverrides.get(familyId) || fallback
    );
    familyByContext.set(component[0], familyId);
  });

  const contextByLabel = new Map(contexts.map(node => [node.label, node]));
  const linkedFamilies = new Map(nodes.map(node => [node.id, new Set()]));
  links.forEach(link => {
    const source = nodeId(link.source);
    const target = nodeId(link.target);
    if (familyByContext.has(source)) {
      linkedFamilies.get(target)?.add(familyByContext.get(source));
    }
    if (familyByContext.has(target)) {
      linkedFamilies.get(source)?.add(familyByContext.get(target));
    }
  });

  nodes.forEach(node => {
    let familyId = familyByContext.get(node.id);
    if (!familyId && node.type === "memory") {
      const owner = contextByLabel.get(node.group);
      familyId = owner ? familyByContext.get(owner.id) : null;
    }
    if (!familyId) {
      const families = [...(linkedFamilies.get(node.id) || [])];
      familyId = families.length === 1 ? families[0] : "family:outer-memory";
    }

    const familyContexts = components.find(
      component => `family:${component.join(",")}` === familyId
    );
    const connectedFamily = Boolean(familyContexts?.length > 1);
    let anchor = anchorByFamily.get(familyId);
    if (!anchor) {
      const angle = stableAngle(node.id);
      anchor = { x: Math.cos(angle) * 850, y: Math.sin(angle) * 850 };
    }
    const orbitRadius =
      node.type === "context" ? 0 : node.type === "memory" ? 135 : 220;
    const orbitAngle = stableAngle(node.id);
    node.familyId = familyId;
    node.familySize = familyContexts?.length || 0;
    node.familyConnected = connectedFamily;
    node.familyX = anchor.x + Math.cos(orbitAngle) * orbitRadius;
    node.familyY = anchor.y + Math.sin(orbitAngle) * orbitRadius;
  });
}

function buildGraphData() {
  capturePositions();
  const candidateNodes = INDEX.graph.nodes.filter(typeVisible);
  const candidateIds = new Set(candidateNodes.map(node => node.id));
  const candidateEdges = INDEX.graph.edges
    .map(edge => ({ ...edge, source: nodeId(edge.source), target: nodeId(edge.target) }))
    .filter(
      edge =>
        edgeVisible(edge) &&
        candidateIds.has(edge.source) &&
        candidateIds.has(edge.target)
    );
  const visibleIds = neighborhoodIds(
    selectedNodeId,
    localDepth,
    candidateIds,
    candidateEdges
  );
  const nodes = candidateNodes
    .filter(node => visibleIds.has(node.id))
    .map(node => {
      const result = { ...node, ...(positionCache.get(node.id) || {}) };
      const pinned = pinnedPositions.get(node.id);
      if (pinned) {
        result.fx = pinned.x;
        result.fy = pinned.y;
      }
      return result;
    });
  const nodeIds = new Set(nodes.map(node => node.id));
  const links = candidateEdges
    .filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .map(edge => ({ ...edge }));

  adjacency = new Map(nodes.map(node => [node.id, new Set()]));
  degreeById = new Map(nodes.map(node => [node.id, 0]));
  links.forEach(link => {
    adjacency.get(link.source).add(link.target);
    adjacency.get(link.target).add(link.source);
    degreeById.set(link.source, degreeById.get(link.source) + 1);
    degreeById.set(link.target, degreeById.get(link.target) + 1);
  });
  nodes.forEach(node => {
    node.degree = degreeById.get(node.id) || 0;
  });
  assignFamilyTargets(nodes, links);
  currentNodeById = new Map(nodes.map(node => [node.id, node]));
  currentLinkByKey = new Map(links.map(link => [linkKey(link), link]));
  return { nodes, links };
}

function nodeRadius(node) {
  const degreeRadius = clamp(3 * Math.sqrt((node.degree || 0) + 1), 4, 30);
  const typeMultiplier = {
    context: 1.35,
    hub: 1.15,
    memory: 0.58,
    zmem: 0.62
  }[node.type] || 1;
  return degreeRadius * typeMultiplier * physics.nodeSize;
}

function isNodeRelated(node) {
  if (hoveredLink) {
    return (
      node.id === nodeId(hoveredLink.source) ||
      node.id === nodeId(hoveredLink.target)
    );
  }
  if (!hoveredNode) {
    return true;
  }
  return (
    node.id === hoveredNode.id ||
    adjacency.get(hoveredNode.id)?.has(node.id)
  );
}

function isLinkRelated(link) {
  if (hoveredLink) {
    return linkKey(link) === linkKey(hoveredLink);
  }
  if (!hoveredNode) {
    return true;
  }
  return (
    nodeId(link.source) === hoveredNode.id ||
    nodeId(link.target) === hoveredNode.id
  );
}

function searchMatches(node) {
  return (
    !graphSearch ||
    `${node.label} ${node.detail || ""} ${node.group || ""}`
      .toLowerCase()
      .includes(graphSearch)
  );
}

function nodeDisplayColor(node) {
  return node.type === "context" && node.outlineColor
    ? node.outlineColor
    : TYPE_COLORS[node.type] || "#94a3b8";
}

function drawNode(node, context, globalScale) {
  const radius = nodeRadius(node);
  if (![node.x, node.y, radius, globalScale].every(Number.isFinite)) {
    return;
  }
  const related = isNodeRelated(node);
  const matches = searchMatches(node);
  const searchHighlighted = Boolean(graphSearch) && matches;
  const hoverRelated = Boolean(hoveredNode || hoveredLink) && related;
  const faded =
    ((hoveredNode || hoveredLink) && !related) || (graphSearch && !matches);
  const alpha = faded ? 0.07 : 0.94;
  const selected = node.id === selectedNodeId;
  const pinned = node.fx != null && node.fy != null;

  context.save();
  context.globalAlpha = alpha;
  if (battleground && !battleground.finished && !battleground.reducedMotion) {
    const visualNow = battleground.visualNow ?? battleground.now;
    const age = Math.max(0, visualNow - battleground.births.get(node.id));
    const spawn = 1 - Math.exp(-age / 105) * Math.cos(age / 52);
    const hit = battleground.impacts.get(node.id);
    const rawHitAge = hit ? Math.max(0, visualNow - hit.time) : Infinity;
    const hitAge = hit?.heavy && rawHitAge < 300 ? Math.floor(rawHitAge / 100) * 100 : rawHitAge;
    const recoil = hitAge < 360 ? Math.sin(hitAge / 32) * Math.exp(-hitAge / 95) * 0.24 : 0;
    context.translate(node.x, node.y);
    context.scale(Math.max(0.01, spawn + recoil), Math.max(0.01, spawn - recoil));
    context.translate(-node.x, -node.y);
    if (hitAge < 650) {
      context.strokeStyle = hit.heavy ? "#fff3c4" : nodeDisplayColor(node);
      context.lineWidth = 3 / globalScale;
      context.globalAlpha = 1 - hitAge / 650;
      context.beginPath();
      context.arc(node.x, node.y, radius + hitAge / (9 * globalScale), 0, Math.PI * 2);
      context.stroke();
      context.globalAlpha = alpha;
    }
  }
  if (battleground?.winnerId === node.id) {
    context.strokeStyle = "#fbbf24";
    context.lineWidth = 5 / globalScale;
    context.shadowColor = "#fbbf24";
    context.shadowBlur = 22;
    context.beginPath();
    context.arc(node.x, node.y, radius + 10 / globalScale, 0, Math.PI * 2);
    context.stroke();
    context.shadowBlur = 0;
  }

  if (node.type === "context" || selected) {
    const displayColor = nodeDisplayColor(node);
    const glow = context.createRadialGradient(
      node.x,
      node.y,
      radius * 0.25,
      node.x,
      node.y,
      radius * 2.4
    );
    glow.addColorStop(0, `${displayColor}88`);
    glow.addColorStop(1, "rgba(0,0,0,0)");
    context.fillStyle = glow;
    context.beginPath();
    context.arc(node.x, node.y, radius * 2.4, 0, 2 * Math.PI);
    context.fill();
  }

  context.fillStyle =
    node.type === "context" ? "#26364f" : nodeDisplayColor(node);
  context.beginPath();
  context.arc(node.x, node.y, radius, 0, 2 * Math.PI);
  context.fill();

  if (node.type === "context") {
    context.strokeStyle = nodeDisplayColor(node);
    context.lineWidth = 3.2 / globalScale;
    context.beginPath();
    context.arc(node.x, node.y, radius + 2 / globalScale, 0, 2 * Math.PI);
    context.stroke();
  }

  if (selected || pinned || searchHighlighted) {
    context.strokeStyle = selected
      ? "#ffffff"
      : pinned
        ? "#fbbf24"
        : "#c4b5fd";
    context.lineWidth = (selected ? 2.4 : 1.4) / globalScale;
    context.beginPath();
    context.arc(
      node.x,
      node.y,
      radius + (node.type === "context" ? 7 : 3) / globalScale,
      0,
      2 * Math.PI
    );
    context.stroke();
  }

  const textAlpha = clamp(
    Math.log2(Math.max(globalScale, 0.01)) + 1 - physics.textFade,
    0,
    1
  );
  const showLabel =
    node.type === "context" ||
    node.type === "hub" ||
    hoverRelated ||
    searchHighlighted ||
    textAlpha > (node.type === "memory" ? 0.72 : 0.58);

  if (showLabel) {
    const baseFont = node.type === "context" ? 13 : node.type === "hub" ? 12 : 10;
    const fontSize = (baseFont * Math.sqrt(1 / Math.max(globalScale, 0.08)));
    const label =
      node.label.length > 64 ? `${node.label.slice(0, 63)}...` : node.label;
    context.globalAlpha = alpha * Math.max(0.24, textAlpha);
    context.font = `${node.type === "context" ? 600 : 400} ${fontSize}px Inter, Segoe UI, sans-serif`;
    context.textAlign = "center";
    context.textBaseline = "top";
    context.lineWidth = 3 / globalScale;
    context.strokeStyle = "rgba(17,20,28,0.9)";
    context.fillStyle = "#e7e9ef";
    context.strokeText(label, node.x, node.y + radius + 5 / globalScale);
    context.fillText(label, node.x, node.y + radius + 5 / globalScale);
  }
  context.restore();
}

function paintPointerArea(node, color, context) {
  if (![node.x, node.y].every(Number.isFinite)) {
    return;
  }
  context.fillStyle = color;
  context.beginPath();
  context.arc(node.x, node.y, nodeRadius(node) + 7, 0, 2 * Math.PI);
  context.fill();
}

function paintLinkPointerArea(link, color, context) {
  const source = graphNode(link.source);
  const target = graphNode(link.target);
  if (
    !source ||
    !target ||
    ![source.x, source.y, target.x, target.y].every(Number.isFinite)
  ) {
    return;
  }
  const deltaX = target.x - source.x;
  const deltaY = target.y - source.y;
  const length = Math.hypot(deltaX, deltaY);
  const sourcePadding = nodeRadius(source) + 12;
  const targetPadding = nodeRadius(target) + 12;
  if (length <= sourcePadding + targetPadding) {
    return;
  }
  const unitX = deltaX / length;
  const unitY = deltaY / length;
  context.strokeStyle = color;
  context.lineWidth = 10;
  context.beginPath();
  context.moveTo(
    source.x + unitX * sourcePadding,
    source.y + unitY * sourcePadding
  );
  context.lineTo(
    target.x - unitX * targetPadding,
    target.y - unitY * targetPadding
  );
  context.stroke();
}

function linkColor(link) {
  if ((hoveredNode || hoveredLink) && !isLinkRelated(link)) {
    return "rgba(95,105,125,0.025)";
  }
  const base = EDGE_COLORS[link.type] || "#667085";
  if (linkKey(link) === selectedLinkKey) {
    return "#ffffff";
  }
  return hoveredNode || hoveredLink ? `${base}ee` : `${base}48`;
}

function linkWidth(link) {
  const base = link.type === "cross-reference" ? 1.6 : 0.65;
  const selected = linkKey(link) === selectedLinkKey;
  return (
    base *
    physics.linkThickness *
    (selected ? 3 : isLinkRelated(link) ? 1.7 : 1)
  );
}

function configureForces() {
  if (!graph) {
    return;
  }
  const centerStrength = forceCurve(physics.center);
  graph
    .d3Force("center", null)
    .d3Force(
      "x",
      d3.forceX(node => node.familyX || 0).strength(centerStrength)
    )
    .d3Force(
      "y",
      d3.forceY(node => node.familyY || 0).strength(centerStrength)
    )
    .d3Force(
      "collide",
      d3
        .forceCollide(node => Math.max(physics.collision, nodeRadius(node) + 8))
        .strength(0.5)
    )
    .d3AlphaMin(0.001)
    .d3AlphaDecay(physics.cooling)
    .d3VelocityDecay(physics.friction);

  const charge = graph.d3Force("charge");
  if (charge) {
    charge
      .strength(-Math.pow(physics.repel, 3))
      .distanceMin(30)
      .theta(0.9);
  }

  const link = graph.d3Force("link");
  if (link) {
    const strength = forceCurve(physics.link);
    link
      .distance(physics.distance)
      .strength(edge => {
        const sourceDegree = degreeById.get(nodeId(edge.source)) || 1;
        const targetDegree = degreeById.get(nodeId(edge.target)) || 1;
        return strength / Math.min(sourceDegree, targetDegree);
      });
  }
  graph.d3ReheatSimulation();
}

function nodeAnimationTime(node, earliestTime) {
  if (node.type === "hub") {
    return earliestTime;
  }
  const parsed = Date.parse(node.date || "");
  return Number.isFinite(parsed) ? parsed : Number.POSITIVE_INFINITY;
}

function stopTimelineAnimation({ restore = true, fit = true } = {}) {
  if (timelineAnimationFrame != null) {
    cancelAnimationFrame(timelineAnimationFrame);
  }
  timelineAnimationFrame = null;
  const button = document.getElementById("animate-graph");
  button.textContent = "Animate timeline";
  if (restore && graph && timelineAnimationData) {
    graph.graphData(timelineAnimationData);
    configureForces();
    if (fit) graph.zoomToFit(700, 70);
  }
  timelineAnimationData = null;
}

function animateTimeline() {
  if (!graph) {
    return;
  }
  stopBattleground({ restore: true });
  if (timelineAnimationFrame != null) {
    stopTimelineAnimation({ restore: true });
    document.getElementById("animation-status").textContent =
      "Animation stopped. Complete graph restored.";
    return;
  }

  const data = buildGraphData();
  const finiteTimes = data.nodes
    .map(node => Date.parse(node.date || ""))
    .filter(Number.isFinite);
  const earliestTime = finiteTimes.length ? Math.min(...finiteTimes) : 0;
  const orderedNodes = [...data.nodes].sort((left, right) => {
    const timeDifference =
      nodeAnimationTime(left, earliestTime) - nodeAnimationTime(right, earliestTime);
    if (timeDifference) {
      return timeDifference;
    }
    const typeOrder = { context: 0, hub: 1, memory: 2, zmem: 3 };
    return (
      (typeOrder[left.type] ?? 9) - (typeOrder[right.type] ?? 9) ||
      left.label.localeCompare(right.label)
    );
  });
  const duration =
    Number(document.getElementById("animation-duration").value) * 1000;
  const button = document.getElementById("animate-graph");
  const status = document.getElementById("animation-status");
  timelineAnimationData = data;
  button.textContent = "Stop animation";
  graph.graphData({ nodes: [], links: [] });

  let startedAt = null;
  let lastCount = -1;
  const tick = timestamp => {
    if (startedAt == null) {
      startedAt = timestamp;
    }
    const progress = clamp((timestamp - startedAt) / duration, 0, 1);
    const count = Math.min(
      orderedNodes.length,
      Math.max(1, Math.ceil(progress * orderedNodes.length))
    );
    if (count !== lastCount) {
      const nodes = orderedNodes.slice(0, count);
      const visibleIds = new Set(nodes.map(node => node.id));
      const links = data.links.filter(
        link =>
          visibleIds.has(nodeId(link.source)) &&
          visibleIds.has(nodeId(link.target))
      );
      graph.graphData({ nodes, links });
      const current = nodes[nodes.length - 1];
      status.textContent =
        `Timeline ${count}/${orderedNodes.length}` +
        ` - ${current.date || "undated"} (${current.dateBasis || "date unavailable"})`;
      lastCount = count;
    }
    if (progress < 1) {
      timelineAnimationFrame = requestAnimationFrame(tick);
      return;
    }
    timelineAnimationFrame = null;
    graph.graphData(data);
    configureForces();
    button.textContent = "Replay timeline";
    status.textContent =
      `Timeline complete - ${orderedNodes.length} nodes revealed once.`;
    timelineAnimationData = null;
    graph.zoomToFit(700, 70);
  };
  timelineAnimationFrame = requestAnimationFrame(tick);
}

function battlegroundPlan(data, random = Math.random) {
  const nodes = [...data.nodes];
  for (let index = nodes.length - 1; index > 0; index -= 1) {
    const other = Math.floor(random() * (index + 1));
    [nodes[index], nodes[other]] = [nodes[other], nodes[index]];
  }
  const connected = new Set(data.links
    .filter(link => nodeId(link.source) !== nodeId(link.target))
    .flatMap(link => [nodeId(link.source), nodeId(link.target)]));
  const starters = nodes.filter(node => connected.has(node.id));
  if (!starters.length) return null;
  const alternatives = starters.filter(node => node.id !== lastBattlegroundStarter);
  const first = (alternatives.length ? alternatives : starters)[0];
  const neighbors = new Map(nodes.map(node => [node.id, new Set()]));
  data.links.forEach(link => {
    neighbors.get(nodeId(link.source))?.add(nodeId(link.target));
    neighbors.get(nodeId(link.target))?.add(nodeId(link.source));
  });
  const remaining = new Set(nodes);
  const revealed = new Set();
  const ordered = [];
  let next = first;
  while (remaining.size) {
    remaining.delete(next);
    ordered.push(next);
    revealed.add(next.id);
    next = nodes.find(node => remaining.has(node) &&
      [...neighbors.get(node.id)].some(id => revealed.has(id))) ||
      nodes.find(node => remaining.has(node) && connected.has(node.id)) ||
      [...remaining][0];
  }
  const order = new Map(ordered.map((node, index) => [node.id, index]));
  const steps = ordered.map(node => ({ node, incoming: [], heavy: false }));
  data.links.forEach(edge => {
    const source = nodeId(edge.source);
    const target = nodeId(edge.target);
    if (source === target || !order.has(source) || !order.has(target)) return;
    const later = order.get(source) > order.get(target) ? source : target;
    steps[order.get(later)].incoming.push({
      edge, fromId: later === source ? target : source, toId: later
    });
  });
  steps.forEach(step => { step.heavy = step.incoming.length > 1; });
  return steps;
}

function releaseBattlegroundStage(state) {
  state.data.nodes.forEach(node => {
    const fixed = state.fixed.get(node.id);
    node.fx = fixed.fx;
    node.fy = fixed.fy;
  });
  graph.enableNodeDrag(state.interactions.drag)
    .enablePanInteraction(state.interactions.pan)
    .enableZoomInteraction(state.interactions.zoom);
  state.controls.forEach(([element, disabled]) => { element.disabled = disabled; });
  document.getElementById("graph").style.transform = "";
  document.getElementById("graph-stage").classList.remove("battleground-impact");
  document.getElementById("graph-stage").style.removeProperty("--impact-angle");
  state.hud.classList.remove("heavy-impact");
}

function stopBattleground({ restore = true, fit = true } = {}) {
  if (!battleground) return;
  const state = battleground;
  cancelAnimationFrame(state.frame);
  releaseBattlegroundStage(state);
  state.hud.remove();
  document.getElementById("graph-stage").classList.remove("battleground-active");
  const button = document.getElementById("battleground-graph");
  button.textContent = "Play Battleground";
  button.setAttribute("aria-pressed", "false");
  battleground = null;
  if (!state.finished) {
    document.getElementById("animation-status").textContent = restore ?
      "Battleground stopped. Complete graph restored." : "Battleground stopped. Graph filters updated.";
  }
  if (restore) {
    graph.graphData(state.data);
    configureForces();
    if (fit) graph.zoomToFit(state.reducedMotion ? 0 : 650, 70);
  }
}

function drawBattlegroundLink(link, context, globalScale) {
  if (!battleground || battleground.finished) return;
  const shot = battleground.shots.get(linkKey(link));
  const visualNow = battleground.visualNow ?? battleground.now;
  if (!shot || visualNow < shot.launchAt) return;
  const source = currentNodeById.get(shot.fromId);
  const target = currentNodeById.get(shot.toId);
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const distance = Math.hypot(dx, dy);
  if (!distance) return;
  const progress = battleground.reducedMotion ? 1 :
    clamp((visualNow - shot.launchAt) / (shot.impactAt - shot.launchAt), 0, 1);
  const reach = distance + nodeRadius(target) + 12 / globalScale;
  const headX = source.x + dx / distance * reach * progress;
  const headY = source.y + dy / distance * reach * progress;
  const arrived = visualNow >= shot.impactAt;
  context.save();
  context.strokeStyle = arrived ? "#d4ad6d99" : "#ffd891";
  context.lineWidth = (arrived ? 1.4 : 3) / globalScale;
  context.beginPath();
  context.moveTo(source.x, source.y);
  context.lineTo(headX, headY);
  context.stroke();
  context.translate(headX, headY);
  context.rotate(Math.atan2(dy, dx));
  context.fillStyle = "#fff1bd";
  context.beginPath();
  context.moveTo(0, 0);
  context.lineTo(-15 / globalScale, -5 / globalScale);
  context.lineTo(-11 / globalScale, 0);
  context.lineTo(-15 / globalScale, 5 / globalScale);
  context.closePath();
  context.fill();
  context.restore();
}

function drawBattlegroundImpact(context, globalScale) {
  const state = battleground;
  if (!state?.cut || state.finished || state.reducedMotion) return;
  const age = state.now - state.cut.time;
  if (age < 0 || age >= 300) return;
  const target = currentNodeById.get(state.cut.nodeId);
  const source = currentNodeById.get(state.cut.fromId);
  const phase = Math.floor(age / 100);
  const angle = Math.atan2(target.y - source.y, target.x - source.x);
  const radius = Math.min(175, graph.width() * 0.3, graph.height() * 0.3);
  const core = clamp(nodeRadius(target) * globalScale, 22, 46);
  const ink = "#101018";
  const paper = "#efe6ce";
  context.save();
  context.translate(target.x, target.y);
  context.scale(1 / globalScale, 1 / globalScale);
  context.rotate(angle);

  // Three held ink drawings, with a steady paper field rather than alternating full-screen flashes.
  context.beginPath();
  for (let index = 0; index < 48; index += 1) {
    const theta = index / 48 * Math.PI * 2;
    const length = radius * (index % 2 ? 0.48 : 0.8 + Math.sin(index * 17 + phase * 7) * 0.2);
    const x = Math.cos(theta) * length;
    const y = Math.sin(theta) * length;
    if (!index) context.moveTo(x, y);
    else context.lineTo(x, y);
  }
  context.closePath();
  context.fillStyle = paper;
  context.fill();
  context.save();
  context.clip();
  context.strokeStyle = ink;
  context.lineWidth = 3;
  for (let index = 0; index < 23; index += 1) {
    const theta = index / 23 * Math.PI * 2 + phase * 0.17;
    const inner = core + 10 + (index % 4) * 7;
    context.beginPath();
    context.moveTo(Math.cos(theta) * inner, Math.sin(theta) * inner);
    context.lineTo(Math.cos(theta + 0.04) * radius, Math.sin(theta + 0.04) * radius);
    context.stroke();
  }
  context.fillStyle = ink;
  context.beginPath();
  context.ellipse(phase === 1 ? 7 : -4, 0,
    core * [1.32, 0.74, 1.1][phase], core * [0.72, 1.3, 0.92][phase],
    [0.18, -0.22, 0.05][phase], 0, Math.PI * 2);
  context.fill();
  if (phase === 1) {
    context.fillStyle = paper;
    context.beginPath();
    context.ellipse(10, -5, core * 0.4, core * 0.9, -0.22, 0, Math.PI * 2);
    context.fill();
  }
  context.lineWidth = 5;
  context.beginPath();
  context.moveTo(-radius, -9 + phase * 5);
  context.lineTo(core + 48, 2);
  context.stroke();
  context.fillStyle = ink;
  context.beginPath();
  context.moveTo(core + 54, 2);
  context.lineTo(core + 18, -12);
  context.lineTo(core + 25, 2);
  context.lineTo(core + 15, 14);
  context.closePath();
  context.fill();
  context.strokeStyle = paper;
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(-core * 1.4, 1);
  context.lineTo(core * 1.6, 1);
  context.stroke();
  context.strokeStyle = ink;
  context.lineWidth = 1.5;
  for (let index = 0; index < 9; index += 1) {
    const x = core + 14 + index * 6;
    context.beginPath();
    context.moveTo(x, 12 + phase * 3);
    context.lineTo(x + 24, 45 + index * 3);
    context.stroke();
  }
  context.restore();
  context.restore();
}

function advanceBattleground(timestamp) {
  const state = battleground;
  if (!state) return;
  state.now = timestamp;
  if (state.finished) {
    if (timestamp - state.finishedAt >= 1300) {
      graph.zoomToFit(state.reducedMotion ? 0 : 900, 70);
      state.frame = null;
      return;
    }
    state.frame = requestAnimationFrame(advanceBattleground);
    return;
  }
  const elapsed = timestamp - state.startedAt;
  const count = Math.min(state.steps.length, Math.floor(elapsed / state.slotMs) + 1);
  while (state.revealed < count) {
    const step = state.steps[state.revealed];
    const bornAt = state.startedAt + state.revealed * state.slotMs;
    state.births.set(step.node.id, bornAt);
    state.camera = {
      x: graph.centerAt().x, y: graph.centerAt().y, zoom: graph.zoom(),
      target: step.node, bornAt
    };
    step.incoming.forEach((shot, index) => {
      shot.launchAt = bornAt + (state.reducedMotion ? 0 : 180 + 100 * index / step.incoming.length);
      shot.impactAt = shot.launchAt + (state.reducedMotion ? 0 : 400);
      shot.heavy = step.heavy;
      state.shots.set(linkKey(shot.edge), shot);
    });
    state.revealed += 1;
    graph.graphData({
      nodes: state.steps.slice(0, state.revealed).map(item => item.node),
      links: [...state.shots.values()].map(shot => shot.edge)
    });
    state.hud.querySelector(".battleground-name").textContent = step.node.label;
  }
  for (const shot of state.shots.values()) {
    if (shot.hit || timestamp < shot.impactAt) continue;
    shot.hit = true;
    state.scores.set(shot.fromId, (state.scores.get(shot.fromId) || 0) + 1);
    state.impacts.set(shot.toId, { time: shot.impactAt, heavy: shot.heavy });
    state.lastImpact = { time: shot.impactAt, heavy: shot.heavy };
    if (shot.heavy && !state.reducedMotion && !state.cutNodes.has(shot.toId)) {
      state.cutNodes.add(shot.toId);
      state.cut = { nodeId: shot.toId, fromId: shot.fromId, time: shot.impactAt };
    }
    state.hits += 1;
  }
  const impactAge = state.lastImpact ? timestamp - state.lastImpact.time : Infinity;
  const cutAge = state.cut ? timestamp - state.cut.time : Infinity;
  const heavy = !state.reducedMotion && cutAge >= 0 && cutAge < 300;
  state.visualNow = heavy ? state.cut.time + Math.floor(cutAge / 100) * 100 : timestamp;
  document.getElementById("graph-stage").classList.toggle("battleground-impact", Boolean(heavy));
  state.hud.classList.toggle("heavy-impact", Boolean(heavy));
  if (heavy) document.getElementById("graph-stage").style.setProperty("--impact-angle", `${Math.floor(cutAge / 100) * 37}deg`);
  const shake = !state.reducedMotion && impactAge < 260 ? (1 - impactAge / 260) * 9 : 0;
  document.getElementById("graph").style.transform = shake ?
    `translate(${Math.sin(impactAge * 0.13) * shake}px, ${Math.cos(impactAge * 0.17) * shake * 0.65}px)` : "";
  if (!state.reducedMotion && state.camera) {
    const camera = state.camera;
    const progress = clamp((state.visualNow - camera.bornAt) / 480, 0, 1);
    const eased = 1 + 2.7 * Math.pow(progress - 1, 3) + 1.7 * Math.pow(progress - 1, 2);
    graph.centerAt(
      camera.x + (camera.target.x - camera.x) * eased,
      camera.y + (camera.target.y - camera.y) * eased, 0
    );
    graph.zoom(camera.zoom + (1.65 - camera.zoom) * eased + shake / 70, 0);
  }
  const progressText = `${state.revealed}/${state.steps.length} nodes | ${state.hits} outgoing spear hits`;
  if (state.progressText !== progressText) {
    state.progressText = progressText;
    state.hud.querySelector(".battleground-score").textContent = progressText;
    document.getElementById("animation-status").textContent =
      `Battleground - ${progressText}. Randomized, not historical chronology. Memory hub excluded from victory.`;
  }
  if (elapsed >= state.durationMs) {
    const eligible = state.data.nodes.filter(node => node.type !== "hub" && state.scores.has(node.id));
    const best = Math.max(0, ...eligible.map(node => state.scores.get(node.id)));
    const tied = eligible.filter(node => state.scores.get(node.id) === best);
    const winner = tied.length ? tied[Math.floor(Math.random() * tied.length)] : null;
    state.winnerId = winner?.id || null;
    state.finished = true;
    state.finishedAt = timestamp;
    releaseBattlegroundStage(state);
    graph.graphData(state.data);
    configureForces();
    if (winner && !state.reducedMotion) {
      graph.centerAt(winner.x, winner.y, 550);
      graph.zoom(1.65, 550);
    }
    const result = winner ? `${winner.label} wins with ${best} outgoing spear hit${best === 1 ? "" : "s"}` :
      "No eligible winner: only the excluded memory hub sent spears";
    state.hud.querySelector(".battleground-name").textContent = result;
    state.hud.querySelector(".battleground-heading").textContent = "BATTLEGROUND // FINAL";
    document.getElementById("animation-status").textContent =
      `${result}. Complete mesh restored. Ties are random; the memory hub cannot win.`;
    const button = document.getElementById("battleground-graph");
    button.textContent = "Play Battleground";
    button.setAttribute("aria-pressed", "false");
  }
  requestGraphRedraw();
  state.frame = requestAnimationFrame(advanceBattleground);
}

function playBattleground() {
  if (!graph) return;
  if (battleground && !battleground.finished) {
    stopBattleground();
    document.getElementById("animation-status").textContent = "Battleground stopped. Complete graph restored.";
    return;
  }
  stopBattleground({ fit: false });
  stopTimelineAnimation({ restore: true, fit: false });
  const data = buildGraphData();
  const steps = battlegroundPlan(data);
  if (!steps) {
    document.getElementById("animation-status").textContent =
      "Battleground needs at least one visible connection. Adjust Detail, Evidence or Local depth.";
    return;
  }
  lastBattlegroundStarter = steps[0].node.id;
  const fixed = new Map(data.nodes.map(node => [node.id, { fx: node.fx, fy: node.fy }]));
  data.nodes.forEach(node => {
    node.x = Number.isFinite(node.x) ? node.x : node.familyX + Math.cos(stableAngle(node.id)) * 90;
    node.y = Number.isFinite(node.y) ? node.y : node.familyY + Math.sin(stableAngle(node.id)) * 90;
    node.fx = node.x;
    node.fy = node.y;
  });
  const hud = document.createElement("div");
  hud.className = "battleground-hud";
  hud.setAttribute("aria-hidden", "true");
  hud.innerHTML = '<div class="battleground-heading">BATTLEGROUND // RANDOMIZED</div><strong class="battleground-name">Entering the arena</strong><div class="battleground-score"></div><small>Outgoing hits decide victory. Memory hub excluded. Escape to stop.</small>';
  document.getElementById("graph-stage").append(hud);
  document.getElementById("graph-stage").classList.add("battleground-active");
  const controls = [...document.querySelectorAll("#fit-graph, #reheat-graph, #unpin-all, #battleground-speed, #physics-panel input")]
    .map(element => [element, element.disabled]);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const speed = Number(document.getElementById("battleground-speed").value);
  const slotMs = (reducedMotion ? 160 : 1100) / speed;
  const durationMs = steps.reduce((duration, step, index) => {
    if (!step.incoming.length) return duration;
    const impactAt = index * slotMs + (reducedMotion ? 0 :
      580 + 100 * (step.incoming.length - 1) / step.incoming.length);
    return Math.max(duration, impactAt + (reducedMotion ? 0 : 300));
  }, steps.length * slotMs);
  battleground = {
    data, steps, fixed, hud, controls, reducedMotion, speed, slotMs, durationMs, revealed: 0, hits: 0,
    // Let existing fit/inspection camera tweens finish before cinematic camera ownership.
    startedAt: performance.now() + (reducedMotion ? 0 : 1000), now: performance.now(),
    births: new Map(), shots: new Map(), impacts: new Map(), scores: new Map(), cutNodes: new Set(),
    interactions: { drag: graph.enableNodeDrag(), pan: graph.enablePanInteraction(), zoom: graph.enableZoomInteraction() }
  };
  controls.forEach(([element]) => { element.disabled = true; });
  graph.enableNodeDrag(false).enablePanInteraction(false).enableZoomInteraction(false);
  hoveredNode = null;
  hoveredLink = null;
  graph.graphData({ nodes: [], links: [] });
  const button = document.getElementById("battleground-graph");
  button.textContent = "Stop Battleground";
  button.setAttribute("aria-pressed", "true");
  battleground.frame = requestAnimationFrame(advanceBattleground);
}

function updateGraphData({ fit = false } = {}) {
  if (!graph) {
    return;
  }
  stopBattleground({ restore: false });
  if (timelineAnimationFrame != null) {
    stopTimelineAnimation({ restore: false });
  }
  const data = buildGraphData();
  graph.graphData(data);
  configureForces();
  if (lockedInspection) {
    restoreLockedInspection();
  }
  if (fit) {
    window.setTimeout(() => {
      if (!battleground || battleground.finished) graph.zoomToFit(700, 70);
    }, 250);
  }
}

const RELATIONSHIP_LABELS = {
  "cross-reference": "Context cross-reference",
  "contains-memory": "Context memory",
  "zmem-reference": "zmem context reference",
  semantic: "Semantic memory",
  episodic: "Episodic memory",
  procedural: "Procedural memory",
  unscoped: "Unscoped zmem memory"
};

function graphNode(endpoint) {
  const id = nodeId(endpoint);
  return (
    currentNodeById.get(id) ||
    INDEX.graph.nodes.find(node => node.id === id) ||
    (typeof endpoint === "object" ? endpoint : null)
  );
}

function resetInspector() {
  const inspector = document.getElementById("inspector");
  inspector.className = "card empty";
  inspector.removeAttribute("data-inspector-kind");
  inspector.innerHTML = `
    <h2>Select a node or connection</h2>
    <p class="muted">Click a node for its context. Hover or click a connection to see why the two nodes are linked.</p>`;
}

function restoreLockedInspection() {
  if (lockedInspection?.kind === "node") {
    const node = currentNodeById.get(lockedInspection.id);
    if (node) {
      inspectNode(node, { lock: false });
      return;
    }
  }
  if (lockedInspection?.kind === "link") {
    const link = currentLinkByKey.get(lockedInspection.id);
    if (link) {
      inspectLink(link, { lock: false });
      return;
    }
  }
  resetInspector();
}

function inspectLink(link, { lock = false } = {}) {
  const source = graphNode(link.source);
  const target = graphNode(link.target);
  if (!source || !target) {
    return;
  }
  const key = linkKey(link);
  if (lock) {
    lockedInspection = { kind: "link", id: key };
    selectedLinkKey = key;
  }
  const selected = selectedLinkKey === key;
  const inspector = document.getElementById("inspector");
  inspector.className = "card";
  inspector.dataset.inspectorKind = "link";
  inspector.innerHTML = `
    <h2>Why are these connected?</h2>
    <p class="relationship-badges">
      <span class="badge unknown">${esc(RELATIONSHIP_LABELS[link.type] || link.type)}</span>
      <span class="badge confidence-${esc(link.confidence || "low")}">${esc(link.confidence || "low")} confidence</span>
    </p>
    <div class="connection-pair">
      <button data-action="inspect-source">
        <i class="dot" style="background:${nodeDisplayColor(source)}"></i>
        <span><strong>${esc(source.label)}</strong><small>${esc(source.type)}</small></span>
      </button>
      <span class="connection-arrow">&harr;</span>
      <button data-action="inspect-target">
        <i class="dot" style="background:${nodeDisplayColor(target)}"></i>
        <span><strong>${esc(target.label)}</strong><small>${esc(target.type)}</small></span>
      </button>
    </div>
    <h3>Why this link exists</h3>
    <p>${esc(link.reason || "The graph source records a direct relationship between these nodes.")}</p>
    <h3>Exact persisted evidence</h3>
    ${list(link.evidence || [], "No additional evidence was recorded.")}
    <div class="node-meta">
      <strong>Relationship class</strong><span>${esc(link.relationshipClass || "unspecified")}</span>
      <strong>Default graph</strong><span>${link.confidence === "high" ? "Included" : "Hidden unless incidental references are enabled"}</span>
    </div>
    <div class="inspector-actions">
      <button data-action="center-link">Center connection</button>
      ${selected ? '<span class="muted">Connection selected</span>' : '<span class="muted">Hover preview</span>'}
    </div>`;
  inspector
    .querySelector('[data-action="inspect-source"]')
    .addEventListener("click", () => inspectNode(source));
  inspector
    .querySelector('[data-action="inspect-target"]')
    .addEventListener("click", () => inspectNode(target));
  inspector
    .querySelector('[data-action="center-link"]')
    .addEventListener("click", () => {
      const x = ((source.x || 0) + (target.x || 0)) / 2;
      const y = ((source.y || 0) + (target.y || 0)) / 2;
      graph.centerAt(x, y, 500);
      graph.zoom(2.2, 500);
    });
  requestGraphRedraw();
}

function inspectNode(node, { lock = true } = {}) {
  selectedNodeId = node.id;
  selectedLinkKey = null;
  if (lock) {
    lockedInspection = { kind: "node", id: node.id };
  }
  const context = INDEX.contexts.find(item => item.id === node.id);
  const inspector = document.getElementById("inspector");
  inspector.className = "card";
  inspector.dataset.inspectorKind = "node";
  const pinned = pinnedPositions.has(node.id);
  if (context) {
    inspector.innerHTML = `
      <h2>${esc(context.name)}</h2>
      <p><span class="badge ${context.freshness.label}">${context.freshness.label}</span></p>
      <p class="path">${esc(context.basePath)}</p>
      <div class="inspector-actions">
        <button data-action="center">Center</button>
        <button data-action="toggle-pin">${pinned ? "Unpin" : "Pin"}</button>
      </div>
      <h3>Current focus</h3>${list(context.focus)}
      <h3>Next steps</h3>${list(context.nextSteps)}
      <h3>Open questions</h3>${list(context.openQuestions, "None recorded.")}
      <div class="node-meta">
        <strong>Connections</strong><span>${node.degree || 0}</span>
        <strong>Layout family</strong><span>${node.familyConnected ? `${node.familySize} connected contexts - center stage` : "isolated context - outer ring"}</span>
        <strong>Timeline date</strong><span>${esc(node.date || "undated")}</span>
        <strong>Date basis</strong><span>${esc(node.dateBasis || "unavailable")}</span>
      </div>`;
  } else {
    inspector.innerHTML = `
      <h2>${esc(node.label)}</h2>
      <p><span class="badge unknown">${esc(node.type)}</span></p>
      <div class="inspector-actions">
        <button data-action="center">Center</button>
        <button data-action="toggle-pin">${pinned ? "Unpin" : "Pin"}</button>
      </div>
      <p>${esc(node.detail)}</p>
      <div class="node-meta">
        <strong>Group</strong><span>${esc(node.group || "Unscoped")}</span>
        <strong>Connections</strong><span>${node.degree || 0}</span>
        <strong>Layout family</strong><span>${esc(node.familyId || "outer memory")}</span>
        <strong>Timeline date</strong><span>${esc(node.date || "undated")}</span>
        <strong>Date basis</strong><span>${esc(node.dateBasis || "unavailable")}</span>
        <strong>Position</strong><span>${Math.round(node.x || 0)}, ${Math.round(node.y || 0)}</span>
      </div>`;
  }
  inspector.querySelector('[data-action="center"]').addEventListener("click", () => {
    graph.centerAt(node.x, node.y, 500);
    graph.zoom(2.2, 500);
  });
  inspector
    .querySelector('[data-action="toggle-pin"]')
    .addEventListener("click", () => togglePin(node));
  requestGraphRedraw();
}

function pinNode(node) {
  if (Number.isFinite(node.x) && Number.isFinite(node.y)) {
    node.fx = node.x;
    node.fy = node.y;
    pinnedPositions.set(node.id, { x: node.x, y: node.y });
  }
}

function unpinNode(node) {
  node.fx = null;
  node.fy = null;
  pinnedPositions.delete(node.id);
  graph?.d3ReheatSimulation();
}

function togglePin(node) {
  if (pinnedPositions.has(node.id)) {
    unpinNode(node);
  } else {
    pinNode(node);
  }
  inspectNode(node);
}

function recenterFamilyOnNode(node) {
  if (node.type !== "context" || !node.familyId) {
    return;
  }
  familyAnchorOverrides.set(node.familyId, { x: node.x, y: node.y });
  const data = graph.graphData();
  assignFamilyTargets(data.nodes, data.links);
  configureForces();
  graph.centerAt(node.x, node.y, 600);
  graph.d3ReheatSimulation();
}

function initializeGraph() {
  if (graphInitialized) {
    return;
  }
  graphInitialized = true;
  const container = document.getElementById("graph");
  graph = ForceGraph()(container)
    .width(container.clientWidth)
    .height(container.clientHeight)
    .backgroundColor("#181b24")
    .nodeId("id")
    .nodeLabel(() => "")
    .nodeCanvasObject(drawNode)
    .nodePointerAreaPaint(paintPointerArea)
    .linkPointerAreaPaint(paintLinkPointerArea)
    .linkColor(linkColor)
    .linkWidth(linkWidth)
    .linkCanvasObject(drawBattlegroundLink)
    .linkCanvasObjectMode(() => battleground && !battleground.finished ? "replace" : "after")
    .onRenderFramePost(drawBattlegroundImpact)
    .linkHoverPrecision(8)
    .enableNodeDrag(true)
    .enablePanInteraction(true)
    .enableZoomInteraction(true)
    .minZoom(0.03)
    .maxZoom(12)
    .autoPauseRedraw(true)
    .cooldownTicks(Infinity)
    .cooldownTime(Infinity)
    .onNodeHover(node => {
      hoveredNode = node;
      if (node) {
        hoveredLink = null;
      }
      container.style.cursor = node ? "grab" : "move";
      requestGraphRedraw();
    })
    .onNodeClick(node => {
      hoveredLink = null;
      inspectNode(node);
      if (localDepth > 0) {
        updateGraphData({ fit: true });
      }
    })
    .onLinkHover(link => {
      hoveredLink = link;
      if (link) {
        hoveredNode = null;
        container.style.cursor = "pointer";
        inspectLink(link, { lock: false });
      } else {
        container.style.cursor = "move";
        restoreLockedInspection();
      }
      requestGraphRedraw();
    })
    .onLinkClick(link => {
      hoveredNode = null;
      hoveredLink = link;
      inspectLink(link, { lock: true });
    })
    .onNodeRightClick((node, event) => {
      event.preventDefault();
      togglePin(node);
    })
    .onNodeDrag(node => {
      selectedNodeId = node.id;
    })
    .onNodeDragEnd(node => {
      const pinAfterDrag =
        document.getElementById("pin-on-release").checked;
      if (pinAfterDrag || pinnedPositions.has(node.id)) {
        pinNode(node);
      } else {
        unpinNode(node);
      }
      if (pinAfterDrag) {
        recenterFamilyOnNode(node);
      }
      inspectNode(node);
      graph.d3ReheatSimulation();
    })
    .onBackgroundClick(() => {
      hoveredNode = null;
      hoveredLink = null;
      selectedLinkKey = null;
      lockedInspection = null;
      resetInspector();
      requestGraphRedraw();
    });

  container.addEventListener("dblclick", event => {
    if (!hoveredNode) {
      return;
    }
    event.preventDefault();
    unpinNode(hoveredNode);
    inspectNode(hoveredNode);
  });
  container.addEventListener(
    "click",
    event => {
      if (!hoveredLink) {
        return;
      }
      event.preventDefault();
      event.stopImmediatePropagation();
      inspectLink(hoveredLink, { lock: true });
    },
    true
  );

  window.CONTEXT_MESH_GRAPH = graph;
  updateGraphData({ fit: true });
}

function bindPhysicsControl(id, property, formatter = value => value) {
  const input = document.getElementById(id);
  const output = document.getElementById(`${id}-value`);
  const update = () => {
    physics[property] = Number(input.value);
    output.value = formatter(physics[property]);
    if (graph) {
      configureForces();
      requestGraphRedraw();
    }
  };
  input.addEventListener("input", update);
  update();
}

function bindGraphControls() {
  bindPhysicsControl("center-force", "center", value =>
    forceCurve(value).toFixed(3)
  );
  bindPhysicsControl("repel-force", "repel", value =>
    `${-Math.pow(value, 3).toFixed(0)}`
  );
  bindPhysicsControl("link-force", "link", value =>
    forceCurve(value).toFixed(3)
  );
  bindPhysicsControl("link-distance", "distance", value => `${value}px`);
  bindPhysicsControl("collision-radius", "collision", value => `${value}px`);
  bindPhysicsControl("friction", "friction", value => value.toFixed(2));
  bindPhysicsControl("cooling", "cooling", value => value.toFixed(3));
  bindPhysicsControl("node-size", "nodeSize", value => `${value.toFixed(1)}x`);
  bindPhysicsControl(
    "link-thickness",
    "linkThickness",
    value => `${value.toFixed(2)}x`
  );
  bindPhysicsControl("text-fade", "textFade", value => value.toFixed(1));

  document.getElementById("fit-graph").addEventListener("click", () => {
    graph?.zoomToFit(700, 70);
  });
  document.getElementById("reheat-graph").addEventListener("click", () => {
    graph?.d3ReheatSimulation();
  });
  document
    .getElementById("animate-graph")
    .addEventListener("click", animateTimeline);
  document.getElementById("battleground-graph").addEventListener("click", playBattleground);
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && battleground && !battleground.finished) {
      stopBattleground();
      document.getElementById("animation-status").textContent = "Battleground stopped. Complete graph restored.";
    }
  });
  window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", () => {
    if (battleground && !battleground.finished) {
      stopBattleground();
      document.getElementById("animation-status").textContent = "Motion preference changed. Complete graph restored.";
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && battleground && !battleground.finished) stopBattleground();
  });
  document.getElementById("unpin-all").addEventListener("click", () => {
    pinnedPositions.clear();
    familyAnchorOverrides.clear();
    graph?.graphData().nodes.forEach(node => {
      node.fx = null;
      node.fy = null;
    });
    updateGraphData({ fit: true });
  });
  ["detail-level", "evidence-level"].forEach(id => {
    document.getElementById(id).addEventListener("change", () => {
      updateGraphData({ fit: true });
    });
  });
  document.getElementById("graph-search").addEventListener("input", event => {
    graphSearch = event.target.value.trim().toLowerCase();
    requestGraphRedraw();
  });
  document.getElementById("local-depth").addEventListener("change", event => {
    localDepth = Number(event.target.value);
    updateGraphData({ fit: true });
  });
}

function relationshipFor(leftId, rightId) {
  const relationship = (INDEX.social?.relationships || []).find(
    item =>
      (item.left === leftId && item.right === rightId) ||
      (item.left === rightId && item.right === leftId)
  );
  return relationship || { relation: "stranger", mutualContexts: [] };
}

function avatarRecipe(seed) {
  if (typeof seed !== "string" || !/^[a-f0-9]+$/i.test(seed)) {
    throw new TypeError("Avatar seed must be a non-empty hexadecimal string");
  }
  // Keep the shared recipe order stable; both art styles must describe the same character.
  let state = 2166136261;
  for (const character of seed.toLowerCase()) {
    state = Math.imul(state ^ character.charCodeAt(0), 16777619) >>> 0;
  }
  const pick = count => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value ^= value + Math.imul(value ^ (value >>> 7), 61 | value);
    return ((value ^ (value >>> 14)) >>> 0) % count;
  };
  const background = ["#cde9f7", "#f7d8c6", "#d9d2f3", "#d2ead5", "#f6e5ad", "#f0d0e3", "#c5e7e2", "#dbdff5"][pick(8)];
  const skin = ["#f8d7b4", "#eebc91", "#d99b72", "#bc805d", "#955d43", "#704536"][pick(6)];
  const hair = ["#292632", "#55392d", "#9b5535", "#d4a648", "#ebe0c6", "#747889", "#694382", "#be5874"][pick(8)];
  const shirt = ["#447ba8", "#a44860", "#477e67", "#73549b", "#bb7834", "#3b7e89", "#b95342", "#565d85"][pick(8)];
  const hairStyle = pick(8);
  const eyeStyle = pick(4);
  const mouthStyle = pick(5);
  const accessory = pick(5);
  const faceWidth = 25 + pick(5);
  const faceHeight = 31 + pick(4);
  const eyeSpacing = 11 + pick(3);
  const eyeColor = ["#516a80", "#6a4934", "#467764", "#3b3448"][pick(4)];
  const eyebrowTilt = pick(3) - 1;
  return { background, skin, hair, shirt, hairStyle, eyeStyle, mouthStyle, accessory, faceWidth, faceHeight, eyeSpacing, eyeColor, eyebrowTilt };
}

function avatarDataUri(seed) {
  const { background, skin, hair, shirt, hairStyle, eyeStyle, mouthStyle, accessory, faceWidth, faceHeight, eyeSpacing, eyeColor, eyebrowTilt } = avatarRecipe(seed);
  const ink = "#292b3b";
  const backHair = [
    "",
    "",
    '<path d="M32 54Q26 82 35 98L45 88 83 88 94 98Q104 77 96 48Z"/>',
    '<path d="M30 50Q26 17 64 17Q102 17 98 56L100 97Q87 105 78 94H50Q38 105 27 97Z"/>',
    '<path d="M31 51Q22 17 64 16Q105 18 97 57L105 115 82 112 74 89H50L44 113 22 115Z"/>',
    "",
    '<circle cx="87" cy="21" r="15"/><circle cx="90" cy="20" r="8" fill="#fff" opacity=".12"/>',
    "",
  ][hairStyle];
  const frontHair = [
    '<path d="M33 53V39Q35 18 63 18Q93 18 96 43L94 55 84 39 70 40 56 33 43 40Z"/>',
    '<path d="M32 55Q26 27 48 20Q80 7 96 34L96 55 85 43 83 29Q64 51 39 44L38 57Z"/>',
    '<circle cx="35" cy="39" r="11"/><circle cx="40" cy="26" r="12"/><circle cx="56" cy="21" r="13"/><circle cx="73" cy="22" r="13"/><circle cx="88" cy="30" r="12"/><circle cx="94" cy="44" r="9"/>',
    '<path d="M31 57V38Q34 16 64 17Q96 17 98 42L94 63 85 41 78 33Q59 45 39 39L39 61Z"/>',
    '<path d="M31 57Q25 23 54 18Q85 8 98 40L93 65 84 36Q59 48 41 39L37 64Z"/>',
    '<path d="M31 53 27 31 40 34 44 14 57 25 68 10 76 25 91 19 91 35 101 36 95 56 83 40 68 38 51 33 39 44Z"/>',
    '<path d="M32 55Q26 18 64 18Q96 18 97 50L89 56 82 35Q63 43 42 36L38 57Z"/>',
    '<path d="M34 51Q29 44 36 36L40 42 39 57ZM89 42 94 36Q101 44 94 53L89 57Z"/>',
  ][hairStyle];
  const eyes = [64 - eyeSpacing, 64 + eyeSpacing].map((x, index) => {
    if (eyeStyle === 2 || (eyeStyle === 3 && index === 1)) {
      return `<path d="M${x - 5} 61Q${x} 55 ${x + 5} 61" fill="none" stroke="${ink}" stroke-width="3" stroke-linecap="round"/>`;
    }
    return `<ellipse cx="${x}" cy="60" rx="6" ry="${eyeStyle === 1 ? 7 : 5.5}" fill="#fff"/><ellipse cx="${x}" cy="61" rx="3.3" ry="4" fill="${eyeColor}"/><circle cx="${x}" cy="61" r="1.8" fill="${ink}"/><circle cx="${x - 1}" cy="59.5" r="1" fill="#fff"/>`;
  }).join("");
  const mouths = [
    `<path d="M53 78Q64 88 75 78" fill="none" stroke="${ink}" stroke-width="3" stroke-linecap="round"/>`,
    `<path d="M52 77H76Q73 91 64 91Q55 91 52 77Z" fill="${ink}"/><path d="M55 78H73L71 82H57Z" fill="#fff"/><path d="M59 88Q64 83 69 88" fill="#e5919c"/>`,
    `<ellipse cx="64" cy="81" rx="5" ry="6" fill="${ink}"/><ellipse cx="64" cy="84" rx="3" ry="2" fill="#e5919c"/>`,
    `<path d="M54 81Q65 86 74 76" fill="none" stroke="${ink}" stroke-width="3" stroke-linecap="round"/>`,
    `<path d="M57 81Q64 79 71 81" fill="none" stroke="${ink}" stroke-width="3" stroke-linecap="round"/>`,
  ];
  const accessories = [
    "",
    `<g fill="none" stroke="${ink}" stroke-width="2.5"><circle cx="${64 - eyeSpacing}" cy="61" r="10"/><circle cx="${64 + eyeSpacing}" cy="61" r="10"/><path d="M${74 - eyeSpacing} 60Q64 56 ${54 + eyeSpacing} 60M34 57 43 59M85 59 94 57"/></g>`,
    `<g fill="none" stroke="${ink}" stroke-width="2.5"><rect x="${53 - eyeSpacing}" y="52" width="22" height="17" rx="4"/><rect x="${53 + eyeSpacing}" y="52" width="22" height="17" rx="4"/><path d="M${75 - eyeSpacing} 58H${53 + eyeSpacing}M33 55 41 57M87 57 95 55"/></g>`,
    '<circle cx="94" cy="73" r="4" fill="#f3c65e" stroke="#75522e" stroke-width="1.5"/>',
    `<g fill="${ink}" opacity=".35"><circle cx="45" cy="72" r="1.3"/><circle cx="49" cy="70" r="1.3"/><circle cx="51" cy="73" r="1.3"/><circle cx="77" cy="73" r="1.3"/><circle cx="79" cy="70" r="1.3"/><circle cx="83" cy="72" r="1.3"/></g>`,
  ];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" data-avatar-version="face-v1">
    <rect width="128" height="128" rx="18" fill="${background}"/>
    <circle cx="18" cy="18" r="36" fill="#fff" opacity=".2"/>
    <g data-feature="hair-back" fill="${hair}">${backHair}</g>
    <path d="M23 128V119Q24 101 52 96L64 103 76 96Q104 101 105 119V128Z" fill="${shirt}"/>
    <path d="M55 87H73V99Q64 110 55 99Z" fill="${skin}"/>
    <path d="M55 89Q64 98 73 89V95Q64 102 55 95Z" fill="${ink}" opacity=".12"/>
    <g fill="${skin}" stroke="${ink}" stroke-width="1.5"><ellipse cx="${64 - faceWidth}" cy="64" rx="6" ry="9"/><ellipse cx="${64 + faceWidth}" cy="64" rx="6" ry="9"/><ellipse cx="64" cy="62" rx="${faceWidth}" ry="${faceHeight}"/></g>
    <g data-feature="hair" fill="${hair}">${frontHair}</g>
    <g data-feature="eyebrows" fill="none" stroke="${hair}" stroke-width="3" stroke-linecap="round"><path d="M${59 - eyeSpacing} ${49 + eyebrowTilt * 2}L${69 - eyeSpacing} 49M${59 + eyeSpacing} 49L${69 + eyeSpacing} ${49 + eyebrowTilt * 2}"/></g>
    <g data-feature="eyes">${eyes}</g>
    <path d="M63 64 60 72H65" fill="none" stroke="${ink}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" opacity=".35"/>
    <g data-feature="mouth">${mouths[mouthStyle]}</g>
    <g data-feature="accessory">${accessories[accessory]}</g>
    <path d="M48 100 55 106M80 100 73 106" fill="none" stroke="#fff" stroke-width="2" opacity=".45"/>
  </svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}

function avatarDataUriV2(seed) {
  const { background, skin, hair, shirt, hairStyle, eyeStyle, mouthStyle, accessory, faceWidth, faceHeight, eyeSpacing, eyeColor, eyebrowTilt } = avatarRecipe(seed);
  const ink = "#252333";
  const tint = (hex, amount) => `#${[1, 3, 5].map(offset => {
    const channel = parseInt(hex.slice(offset, offset + 2), 16);
    return Math.round(channel + ((amount < 0 ? 0 : 255) - channel) * Math.abs(amount)).toString(16).padStart(2, "0");
  }).join("")}`;
  const head = `M${64 - faceWidth} 54C${64 - faceWidth} ${67 - faceHeight} 48 ${62 - faceHeight} 64 ${62 - faceHeight}C80 ${62 - faceHeight} ${64 + faceWidth} ${67 - faceHeight} ${64 + faceWidth} 54L${63 + faceWidth} 69C${61 + faceWidth} ${faceHeight + 51} 77 ${faceHeight + 60} 64 ${faceHeight + 62}C51 ${faceHeight + 60} ${67 - faceWidth} ${faceHeight + 51} ${65 - faceWidth} 69Z`;
  const rearHair = [
    "",
    "",
    '<path d="M32 46C23 56 26 88 34 99L46 90H82L95 99C105 87 104 56 96 45Z"/>',
    '<path d="M31 49C24 7 105 6 98 57L101 96Q90 108 77 94H50Q36 108 26 96Z"/>',
    '<path d="M30 48C20 8 108 7 98 58L104 114Q92 118 80 110L74 88H51L45 111Q33 117 23 113Z"/>',
    "",
    '<circle cx="87" cy="21" r="15"/>',
    "",
  ][hairStyle];
  const frontHair = [
    '<path d="M33 53L32 40C32 12 95 10 96 43L94 55Q88 50 83 39Q75 44 66 38Q55 30 45 39L39 55Z"/>',
    '<path d="M32 55C20 33 33 19 52 16C77 6 99 20 97 44L94 57L85 44L82 31C72 47 53 51 39 44L38 57Z"/>',
    '<circle cx="35" cy="40" r="10"/><circle cx="39" cy="28" r="12"/><circle cx="54" cy="21" r="13"/><circle cx="71" cy="21" r="13"/><circle cx="87" cy="29" r="12"/><circle cx="94" cy="42" r="9"/>',
    '<path d="M31 59V39C31 10 98 10 98 43L94 64L85 42L78 33C66 43 51 44 39 39L39 62Z"/>',
    '<path d="M30 59C22 23 43 15 58 16C82 8 102 27 98 44L93 65L84 36C73 45 55 48 41 39L37 65Z"/>',
    '<path d="M31 54Q31 42 27 31L40 35Q43 24 44 14L57 25L68 10Q70 20 77 26L91 19L91 35L101 36Q96 43 95 56L83 41L68 38L51 34L39 45Z"/>',
    '<path d="M32 55C24 20 44 17 64 18C87 13 102 29 97 50L89 57L82 35C69 43 53 43 42 36L38 57Z"/>',
    '<path d="M34 52Q29 43 36 35Q38 40 41 43L39 57ZM89 43Q92 40 94 35Q102 44 94 54L89 57Z"/>',
  ][hairStyle];
  const hairLines = [
    "M37 38C40 22 63 21 78 25M43 40Q51 31 58 34M64 30Q77 38 88 32M86 34Q90 38 91 44",
    "M34 39C28 25 51 17 64 20M40 39C55 42 74 30 81 24M45 43C60 45 77 37 84 29M86 26Q94 32 93 43",
    "M31 39C28 30 43 29 43 38M31 25C34 17 48 19 47 28M45 17C48 9 63 13 62 22M62 15C69 9 81 16 77 23M80 24C88 18 98 29 92 35M88 38Q97 33 99 43",
    "M34 37C34 16 77 16 88 28M40 35Q62 39 79 27M85 34Q93 42 93 52M34 46L34 53",
    "M33 42C29 20 59 17 71 21M40 35Q61 43 83 29M85 35Q93 46 92 55M35 64Q31 88 30 104M93 65Q95 91 98 107",
    "M34 40L30 35L41 40M47 24Q47 31 52 33M64 25L68 17L72 30M80 30L87 25L86 37M91 41L97 39M56 34L60 28",
    "M35 38C33 21 56 20 69 22M42 34Q63 40 83 27M48 38Q66 42 82 32M88 32Q94 39 93 46",
    "M35 43L37 48M94 42L92 48",
  ][hairStyle];
  const eyes = [64 - eyeSpacing, 64 + eyeSpacing].map((x, index) => {
    if (eyeStyle === 2 || (eyeStyle === 3 && index === 1)) {
      return `<path d="M${x - 5.3} 61Q${x} 53.8 ${x + 5.3} 61" fill="none" stroke="${ink}" stroke-width="2.8" stroke-linecap="round"/><path d="M${x - 4.5} 63Q${x} 65 ${x + 4.5} 63" fill="none" stroke="${tint(skin, -.25)}" stroke-width=".8" opacity=".45"/>`;
    }
    const radius = eyeStyle === 1 ? 7.5 : 6.1;
    return `<ellipse cx="${x}" cy="60.5" rx="6.8" ry="${radius}" fill="url(#eye-white)" stroke="${ink}" stroke-width="1.25"/>
      <ellipse cx="${x + .3}" cy="61" rx="4" ry="4.8" fill="url(#iris)" stroke="${tint(eyeColor, -.45)}" stroke-width=".7"/>
      <ellipse cx="${x + .4}" cy="61.4" rx="2.3" ry="3" fill="${ink}"/>
      <circle cx="${x - 1.3}" cy="58.7" r="1.55" fill="#fff"/><circle cx="${x + 1.7}" cy="63.4" r=".65" fill="#fff" opacity=".8"/>
      <path d="M${x - 5.9} ${60.5 - radius * .4}Q${x} ${59.7 - radius} ${x + 5.8} ${60.5 - radius * .4}" fill="none" stroke="${ink}" stroke-width="1.8" stroke-linecap="round"/>`;
  }).join("");
  const mouths = [
    `<path d="M53.5 78Q64 88.5 74.5 78" fill="none" stroke="${ink}" stroke-width="2.6" stroke-linecap="round"/><path d="M59 86Q64 88 69 86" fill="none" stroke="${tint(skin, .32)}" stroke-width="1.1" stroke-linecap="round"/>`,
    `<path d="M52 77Q64 79 76 77C74 94 54 94 52 77Z" fill="${ink}" stroke="${ink}" stroke-width="1.3"/><path d="M54 78Q64 80 74 78L71.5 83H56.5Z" fill="url(#eye-white)"/><path d="M58 88Q64 82.5 70 88Q64 93 58 88Z" fill="#ed8997"/><path d="M60 88Q64 85.5 68 88" fill="none" stroke="#ffb5bd" stroke-width=".8"/>`,
    `<ellipse cx="64" cy="81" rx="5.3" ry="6.6" fill="${ink}" stroke="${tint(skin, -.35)}" stroke-width=".8"/><path d="M60.5 84Q64 80.8 67.5 84Q67 87 64 87Q61 87 60.5 84" fill="#ed8997"/><path d="M60 89Q64 90 68 89" fill="none" stroke="${tint(skin, .3)}" stroke-width="1"/>`,
    `<path d="M54 81Q66 87 74 76" fill="none" stroke="${ink}" stroke-width="2.5" stroke-linecap="round"/><path d="M71.5 75.5L75.5 76.5" stroke="${tint(skin, -.25)}" stroke-width=".9" stroke-linecap="round"/>`,
    `<path d="M57 81Q64 79 71 81" fill="none" stroke="${ink}" stroke-width="2.2" stroke-linecap="round"/><path d="M59.5 84Q64 85 68.5 84" fill="none" stroke="${tint(skin, .28)}" stroke-width="1" stroke-linecap="round"/>`,
  ];
  const accessories = [
    "",
    `<g fill="#e1efff" fill-opacity=".09" stroke="${ink}" stroke-width="2.8"><circle cx="${64 - eyeSpacing}" cy="60.5" r="10"/><circle cx="${64 + eyeSpacing}" cy="60.5" r="10"/><path d="M${74 - eyeSpacing} 59Q64 55.5 ${54 + eyeSpacing} 59M34 55L43 58M85 58L94 55" fill="none"/></g><g fill="none" stroke="#fff" stroke-width="1.1" opacity=".55"><path d="M${57 - eyeSpacing} 56Q${61 - eyeSpacing} 50.5 ${67 - eyeSpacing} 52M${57 + eyeSpacing} 56Q${61 + eyeSpacing} 50.5 ${67 + eyeSpacing} 52"/></g>`,
    `<g fill="#e1efff" fill-opacity=".08" stroke="${ink}" stroke-width="2.8"><rect x="${54 - eyeSpacing}" y="51" width="20" height="19" rx="4.5"/><rect x="${54 + eyeSpacing}" y="51" width="20" height="19" rx="4.5"/><path d="M${74 - eyeSpacing} 57H${54 + eyeSpacing}M33 54L42 57M86 57L95 54" fill="none"/></g><path d="M${57 - eyeSpacing} 53H${68 - eyeSpacing}M${57 + eyeSpacing} 53H${68 + eyeSpacing}" stroke="#fff" stroke-width="1.1" opacity=".6"/>`,
    '<circle cx="94" cy="73" r="4.3" fill="url(#gold)" stroke="#78502b" stroke-width="1.1"/><circle cx="92.8" cy="71.8" r="1.25" fill="#fff5c3"/>',
    `<g fill="${tint(skin, -.55)}" opacity=".65"><circle cx="44" cy="72" r="1"/><circle cx="48" cy="70.5" r="1.1"/><circle cx="51" cy="73" r="1"/><circle cx="77" cy="73" r="1"/><circle cx="80" cy="70.5" r="1.1"/><circle cx="84" cy="72" r="1"/></g>`,
  ];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128" data-avatar-version="face-v2-preview">
    <defs>
      <linearGradient id="background" x2="1" y2="1"><stop stop-color="${tint(background, .18)}"/><stop offset=".55" stop-color="${background}"/><stop offset="1" stop-color="${tint(background, -.24)}"/></linearGradient>
      <radialGradient id="skin" cx=".35" cy=".29" r=".79"><stop stop-color="${tint(skin, .24)}"/><stop offset=".58" stop-color="${skin}"/><stop offset="1" stop-color="${tint(skin, -.25)}"/></radialGradient>
      <linearGradient id="hair" x1=".15" y1="0" x2=".8" y2="1"><stop stop-color="${tint(hair, .27)}"/><stop offset=".4" stop-color="${hair}"/><stop offset="1" stop-color="${tint(hair, -.48)}"/></linearGradient>
      <linearGradient id="hair-back" x2="1" y2=".6"><stop stop-color="${tint(hair, -.1)}"/><stop offset="1" stop-color="${tint(hair, -.55)}"/></linearGradient>
      <linearGradient id="shirt" x1=".2" y1="0" x2=".8" y2="1"><stop stop-color="${tint(shirt, .18)}"/><stop offset=".45" stop-color="${shirt}"/><stop offset="1" stop-color="${tint(shirt, -.48)}"/></linearGradient>
      <linearGradient id="eye-white" x2=".1" y2="1"><stop stop-color="#d5dde9"/><stop offset=".3" stop-color="#fff"/><stop offset="1" stop-color="#eff1f4"/></linearGradient>
      <radialGradient id="iris" cx=".35" cy=".3"><stop stop-color="${tint(eyeColor, .34)}"/><stop offset=".65" stop-color="${eyeColor}"/><stop offset="1" stop-color="${tint(eyeColor, -.5)}"/></radialGradient>
      <linearGradient id="gold" x2="1" y2="1"><stop stop-color="#fff0a5"/><stop offset=".45" stop-color="#f6c64e"/><stop offset="1" stop-color="#b97820"/></linearGradient>
      <clipPath id="portrait"><rect width="128" height="128" rx="18"/></clipPath>
      <clipPath id="head"><path d="${head}"/></clipPath>
      <clipPath id="hair-front">${frontHair}</clipPath>
      <filter id="shadow" x="-.3" y="-.2" width="1.6" height="1.5"><feDropShadow dx="0" dy="2" stdDeviation="1.3" flood-color="#252333" flood-opacity=".22"/></filter>
    </defs>
    <g clip-path="url(#portrait)">
      <rect width="128" height="128" fill="url(#background)"/>
      <circle cx="27" cy="14" r="66" fill="#fff" opacity=".12"/>
      <circle cx="120" cy="119" r="50" fill="#fff" opacity=".08"/>
      <ellipse cx="65" cy="124" rx="47" ry="8" fill="${ink}" opacity=".16"/>
      <g filter="url(#shadow)">
        <g data-feature="hair-back" fill="url(#hair-back)" stroke="${tint(hair, -.55)}" stroke-width="1.3">${rearHair}</g>
        ${hairStyle === 6 ? `<path d="M77 26C69 8 97 6 99 19C100 30 83 33 81 23C80 15 92 14 93 21" fill="none" stroke="${tint(hair, .5)}" stroke-width="1.6" stroke-linecap="round" opacity=".85"/>` : ""}
        <path d="M22 129V120C23 105 40 100 52 97L64 103L76 97C91 100 105 106 106 120V129Z" fill="url(#shirt)" stroke="${ink}" stroke-width="1.5"/>
        <path d="M26 124C26 111 42 105 50 104M97 127Q98 113 86 108" fill="none" stroke="${tint(shirt, .48)}" stroke-width="1.4" opacity=".65"/>
        <path d="M38 129L40 114M91 129L89 116" stroke="${tint(shirt, -.45)}" stroke-width="1.3" opacity=".55"/>
        <path d="M55 85H73V100Q64 109 55 100Z" fill="url(#skin)" stroke="${ink}" stroke-width="1.2"/>
        <path d="M55 88Q64 96 73 88V95Q64 104 55 96Z" fill="${tint(skin, -.38)}" opacity=".65"/>
        <g fill="url(#skin)" stroke="${ink}" stroke-width="1.35"><ellipse cx="${64 - faceWidth}" cy="64" rx="5.5" ry="8.5"/><ellipse cx="${64 + faceWidth}" cy="64" rx="5.5" ry="8.5"/></g>
        <path d="M${63 - faceWidth} 61Q${68 - faceWidth} 59 ${66 - faceWidth} 68M${65 + faceWidth} 61Q${60 + faceWidth} 59 ${62 + faceWidth} 68" fill="none" stroke="${tint(skin, -.38)}" stroke-width="1.3" stroke-linecap="round"/>
        <path d="${head}" fill="url(#skin)" stroke="${ink}" stroke-width="1.65"/>
        <g clip-path="url(#head)">
          ${hairStyle === 7 ? "" : `<ellipse cx="64" cy="41" rx="31" ry="12" fill="${tint(skin, -.48)}" opacity=".13"/>`}
          <ellipse cx="44" cy="73" rx="8" ry="4.2" fill="#e27d78" opacity=".12"/>
          <ellipse cx="84" cy="73" rx="8" ry="4.2" fill="#e27d78" opacity=".12"/>
          <path d="M${67 - faceWidth} 61Q${68 - faceWidth} 79 56 89" fill="none" stroke="${tint(skin, .45)}" stroke-width="1.2" opacity=".6"/>
        </g>
        <g data-feature="hair" fill="url(#hair)" stroke="${tint(hair, -.6)}" stroke-width="1.1" stroke-linejoin="round">${frontHair}</g>
        <g clip-path="url(#hair-front)" fill="none" stroke-linecap="round">
          <path d="${hairLines}" stroke="${tint(hair, .65)}" stroke-width="1.2" opacity=".75"/>
          <ellipse cx="50" cy="21" rx="28" ry="8" stroke="${tint(hair, .75)}" stroke-width="3" opacity=".2" transform="rotate(-16 50 21)"/>
        </g>
        <g data-feature="eyebrows" fill="none" stroke="${tint(hair, -.52)}" stroke-width="2.7" stroke-linecap="round"><path d="M${59 - eyeSpacing} ${49 + eyebrowTilt * 2}Q${64 - eyeSpacing} 46 ${69 - eyeSpacing} 49M${59 + eyeSpacing} 49Q${64 + eyeSpacing} 46 ${69 + eyeSpacing} ${49 + eyebrowTilt * 2}"/></g>
        <g data-feature="eyes">${eyes}</g>
        <path d="M63 65Q63 69 60.5 72Q64 74 67 72" fill="none" stroke="${tint(skin, -.38)}" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M64 65L64.8 69" stroke="${tint(skin, .5)}" stroke-width="1.1" stroke-linecap="round"/>
        <g data-feature="mouth">${mouths[mouthStyle]}</g>
        <g data-feature="accessory">${accessories[accessory]}</g>
        <path d="M51 99Q64 111 77 99" fill="none" stroke="${tint(shirt, -.55)}" stroke-width="3"/>
        <path d="M49 101L56 106M79 101L72 106" stroke="#fff6dc" stroke-width="1.8" stroke-linecap="round" opacity=".8"/>
      </g>
      <rect x=".6" y=".6" width="126.8" height="126.8" rx="17.5" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1.2"/>
    </g>
  </svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}

function socialDateLabel(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Undated" : parsed.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function socialTimeLabel(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "" : parsed.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function renderMentionText(text, personaById) {
  const names = new Map([...personaById.values()].map(persona => [persona.displayName.toLowerCase(), persona]));
  const tokens = [...new Set([...personaById.values()].map(persona => persona.displayName).concat("meshboard"))]
    .sort((a, b) => b.length - a.length).map(name => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(?<![\\p{L}\\p{N}_@])@(${tokens.join("|")})(?![\\p{L}\\p{N}_-])`, "giu");
  const value = String(text || "");
  let offset = 0;
  let rendered = "";
  for (const match of value.matchAll(pattern)) {
    const name = match[1].toLowerCase();
    const attributes = name === "meshboard" ? 'data-mention-scope="meshboard"' : `data-persona-id="${esc(names.get(name).personaId)}"`;
    rendered += esc(value.slice(offset, match.index)) + `<button class="social-mention" type="button" ${attributes}>${esc(match[0])}</button>`;
    offset = match.index + match[0].length;
  }
  return rendered + esc(value.slice(offset));
}

function renderSocialMessageText(text, personaById) {
  const displayText = String(text || "").trim();
  return displayText ? `<p class="social-message-text">${renderMentionText(displayText, personaById)}</p>` : "";
}

function isEmojiOnly(text) {
  const value = String(text || "").trim();
  // Keep modifiers, joined emoji, flags, and keycaps together; bare digits are not emoji.
  return value.length > 0 && /^(?:\p{Extended_Pictographic}\uFE0F?\p{Emoji_Modifier}?(?:\u200D\p{Extended_Pictographic}\uFE0F?\p{Emoji_Modifier}?)*(?:[\u{E0020}-\u{E007E}]+\u{E007F})?|\p{Regional_Indicator}{2}|[0-9#*]\uFE0F?\u20E3|\s)+$/u.test(value);
}

function bindSocialProfiles() {
  const root = document.getElementById("social-view");
  const card = document.createElement("div");
  card.id = "social-profile-card";
  card.className = "social-profile-card";
  card.hidden = true;
  card.setAttribute("aria-labelledby", "social-profile-name");
  document.body.appendChild(card);
  let timer;
  let anchor;
  let pinned = false;
  const cancelHover = () => window.clearTimeout(timer);
  const close = (restoreFocus = false) => {
    cancelHover();
    const previous = anchor;
    anchor?.setAttribute("aria-expanded", "false");
    anchor?.removeAttribute("aria-describedby");
    anchor = null;
    pinned = false;
    card.hidden = true;
    card.innerHTML = "";
    if (restoreFocus && previous?.isConnected) previous.focus();
  };
  const position = () => {
    const bounds = anchor.getBoundingClientRect();
    const width = card.offsetWidth;
    const height = card.offsetHeight;
    const left = bounds.right + width + 10 <= window.innerWidth - 12
      ? bounds.right + 10 : bounds.left - width - 10;
    card.style.left = `${Math.max(12, Math.min(left, window.innerWidth - width - 12))}px`;
    card.style.top = `${Math.max(12, Math.min(bounds.top, window.innerHeight - height - 12))}px`;
  };
  const show = (trigger, pin) => {
    const persona = INDEX.social.personas.find(item => item.personaId === trigger.dataset.personaId);
    if (!persona) throw new Error(`Unknown profile persona: ${trigger.dataset.personaId}`);
    close();
    anchor = trigger;
    pinned = pin;
    card.dataset.pinned = String(pin);
    card.classList.toggle("social-profile-large", pin && trigger.classList.contains("social-roster-profile-trigger"));
    card.setAttribute("role", pin ? "dialog" : "tooltip");
    card.style.setProperty("--persona-color", persona.profileColor);
    const hasSession = typeof persona.sessionId === "string" && /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(persona.sessionId);
    const unavailable = "No valid creation-session GUID is recorded for this persona.";
    card.innerHTML = `<div class="social-profile-heading"><img class="social-profile-avatar" src="${personaAvatarDataUri(persona)}" alt=""><div><div class="social-profile-title"><h3 id="social-profile-name">${esc(persona.displayName)}</h3>${pin ? `<button class="social-profile-poke" type="button" aria-label="Copy poke command for ${esc(persona.displayName)}" title="${hasSession ? "Poke: copy the command to resume this persona's creation session" : unavailable}"${hasSession ? "" : " disabled"}><span aria-hidden="true">👉</span></button>` : ""}</div><small>${esc(persona.contextName)}</small></div>${pin ? '<button class="social-profile-close" type="button" aria-label="Close persona profile">×</button>' : ""}</div>${pin ? `<p class="social-profile-copy-status" role="status"${hasSession ? " hidden" : ""}>${hasSession ? "" : unavailable}</p>` : ""}<p class="social-profile-description">${esc(persona.persona || "No description provided.")}</p>${persona.natureSummary ? `<small>${esc(persona.natureSummary)}</small>` : ""}${renderSocialCharacter(persona)}`;
    if (pin && hasSession) {
      const button = card.querySelector(".social-profile-poke");
      const status = card.querySelector(".social-profile-copy-status");
      const command = `copilot --resume "${persona.sessionId}" -i "Refresh context using context-offload and context-mesh. Preserve the existing character and identity; do not create a duplicate persona. Read incoming messages and relevant threads, update the context store, and refresh the mesh."`;
      button.addEventListener("click", async () => {
        const hadFocus = document.activeElement === button;
        button.disabled = true;
        status.replaceChildren();
        try {
          if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(command);
          } else {
            const input = document.createElement("textarea");
            input.value = command;
            input.readOnly = true;
            input.style.cssText = "position:fixed;left:-9999px;top:0";
            card.appendChild(input);
            try {
              input.select();
              if (!document.execCommand("copy")) throw new Error("Clipboard copy was rejected");
            } finally {
              input.remove();
            }
          }
          status.textContent = "Command copied. Paste it into your terminal to run it.";
        } catch (error) {
          console.error("Could not copy persona poke command", error);
          status.textContent = "Copy failed. Select and copy the command below:";
          const input = document.createElement("textarea");
          input.className = "social-profile-copy-command";
          input.setAttribute("aria-label", "Poke command to copy manually");
          input.readOnly = true;
          input.value = command;
          status.appendChild(input);
        } finally {
          button.disabled = false;
          status.hidden = false;
          if (button.isConnected) {
            if (hadFocus && document.activeElement === document.body) button.focus({ preventScroll: true });
            position();
          }
        }
      });
    }
    card.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    if (!pin) trigger.setAttribute("aria-describedby", card.id);
    position();
    if (pin) card.querySelector(".social-profile-close").focus();
  };
  root.addEventListener("pointerover", event => {
    const trigger = event.target.closest?.(".social-profile-trigger");
    if (!trigger || pinned || trigger.contains(event.relatedTarget)) return;
    cancelHover();
    timer = window.setTimeout(() => {
      if (trigger.isConnected && trigger.matches(":hover")) show(trigger, false);
    }, 1000);
  });
  root.addEventListener("pointerout", event => {
    const trigger = event.target.closest?.(".social-profile-trigger");
    if (!trigger || trigger.contains(event.relatedTarget)) return;
    cancelHover();
    if (!pinned) close();
  });
  root.addEventListener("click", event => {
    const trigger = event.target.closest?.(".social-profile-trigger");
    if (!trigger) return;
    if (pinned && anchor === trigger) close();
    else show(trigger, true);
  });
  card.addEventListener("click", event => {
    if (event.target.closest(".social-profile-close")) close(true);
  });
  document.addEventListener("click", event => {
    if (!card.contains(event.target) && !event.target.closest?.(".social-profile-trigger")) close();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") close(true);
  });
  window.addEventListener("scroll", event => {
    if (card.hidden || card.contains(event.target)) return;
    if (pinned && anchor.isConnected) position();
    else close();
  }, true);
  window.addEventListener("resize", () => {
    if (!card.hidden) position();
  });
  return { close };
}

function bindSocialRoster() {
  const roster = document.getElementById("social-personas");
  const controls = document.createElement("div");
  controls.className = "social-roster-controls";
  controls.innerHTML = '<label for="social-persona-search">Find a persona</label><input id="social-persona-search" type="search" placeholder="Search personas..." aria-controls="social-personas"><button id="social-persona-toggle" type="button" aria-controls="social-personas" aria-expanded="true">Collapse all</button>';
  roster.before(controls);
  const empty = document.createElement("p");
  empty.className = "muted";
  empty.textContent = "No personas match your search.";
  empty.setAttribute("role", "status");
  empty.hidden = true;
  roster.after(empty);
  const search = controls.querySelector("input");
  const toggle = controls.querySelector("button");
  let collapsed = false;
  const apply = () => {
    socialProfiles.close();
    const query = search.value.trim().toLocaleLowerCase();
    const entries = [...roster.querySelectorAll(".social-persona")];
    for (const entry of entries) {
      entry.hidden = !entry.querySelector(".social-persona-summary strong").textContent.toLocaleLowerCase().includes(query);
    }
    empty.hidden = !entries.length || entries.some(entry => !entry.hidden);
    roster.classList.toggle("names-only", collapsed);
    toggle.textContent = collapsed ? "Expand all" : "Collapse all";
    toggle.setAttribute("aria-expanded", String(!collapsed));
  };
  search.addEventListener("input", apply);
  toggle.addEventListener("click", () => {
    collapsed = !collapsed;
    apply();
  });
  return {
    apply,
    reveal(personaId) {
      const target = personaId && roster.querySelector(`.social-persona[data-persona-id="${CSS.escape(personaId)}"]`);
      if (!personaId || target?.hidden) {
        search.value = "";
        apply();
      }
    },
  };
}

const socialMediaVisibility = new Map();

function socialMediaUrl(value) {
  if (typeof value !== "string" || /[\x00-\x20\x7f\\]/.test(value)) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password || url.port || url.hash ||
        !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(url.hostname) ||
        /(?:^|\.)(?:localhost|local|localdomain|internal|test|invalid|example|onion|lan|home|corp)$/.test(url.hostname) ||
        /\b(?:token|secret|password|passwd|api[_ -]?key|connection[_ -]?string)\s*[=:]\s*[^\s,;]+/i.test(decodeURIComponent(value))) return null;
    return url.href;
  } catch (error) {
    if (error instanceof TypeError || error instanceof URIError) return null;
    throw error;
  }
}

function isEmojiOnlyMessage(message) {
  return !message.attachments?.length && isEmojiOnly(message.text);
}

function socialMessageSummary(message) {
  return message.text || (message.attachments || []).map(attachment =>
    `[${attachment.type === "gif" ? "GIF" : attachment.type} attachment]`).join(" · ");
}

function renderSocialAttachments(message) {
  if (!message.attachments) return "";
  if (!Array.isArray(message.attachments)) return '<p class="social-media-error" role="status">Attachment data is invalid.</p>';
  return `<div class="social-attachments">${message.attachments.map((attachment, index) => {
    const url = socialMediaUrl(attachment?.url);
    const source = socialMediaUrl(attachment?.sourceUrl ?? attachment?.url);
    if (!url || !source || !["image", "gif", "sticker"].includes(attachment?.type) ||
        typeof attachment.alt !== "string" || !attachment.alt.trim() ||
        typeof attachment.context !== "string" || !attachment.context.trim()) {
      return '<p class="social-media-error" role="status">Attachment blocked: use a public HTTPS image URL, description and conversational relevance.</p>';
    }
    const label = attachment.type === "gif" ? "GIF" : attachment.type;
    const key = JSON.stringify([message.personaId, message.id, index]);
    return `<figure class="social-media social-media-type-${attachment.type}" data-media-key="${esc(key)}" data-media-url="${esc(url)}" data-media-type="${attachment.type}" data-media-label="${label}">
      <img class="social-media-image" alt="${esc(attachment.alt)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" hidden>
      <figcaption><span class="social-media-kind">${label}</span><a href="${esc(source)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">Source: ${esc(new URL(source).hostname)}</a></figcaption>
      <div class="social-media-controls"><button class="social-media-toggle" type="button" hidden>Show ${label}</button><span class="social-media-status" role="status" aria-live="polite"></span></div>
    </figure>`;
  }).join("")}</div>`;
}

function bindSocialMedia(container) {
  container.querySelectorAll(".social-media").forEach(figure => {
    const image = figure.querySelector("img");
    const button = figure.querySelector(".social-media-toggle");
    const status = figure.querySelector(".social-media-status");
    const controls = figure.querySelector(".social-media-controls");
    const key = figure.dataset.mediaKey;
    const label = figure.dataset.mediaLabel;
    let enabled = socialMediaVisibility.has(key) ? socialMediaVisibility.get(key) === true
      : figure.dataset.mediaType === "image" || !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const update = () => {
      controls.hidden = false;
      button.hidden = enabled;
      button.textContent = `Show ${label}`;
      image.hidden = !enabled;
      if (enabled) {
        figure.dataset.mediaState = "loading";
        status.textContent = `Loading ${label}...`;
        image.src = figure.dataset.mediaUrl;
      } else {
        image.removeAttribute("src");
        figure.dataset.mediaState = "hidden";
        status.textContent = `${label} not loaded because reduced motion is enabled.`;
      }
    };
    image.addEventListener("load", () => {
      if (!enabled) return;
      figure.dataset.mediaState = "loaded";
      status.textContent = "";
      controls.hidden = true;
    });
    const showError = () => {
      enabled = false;
      image.hidden = true;
      image.removeAttribute("src");
      socialMediaVisibility.set(key, "error");
      figure.dataset.mediaState = "error";
      controls.hidden = false;
      button.hidden = false;
      status.textContent = `${label} unavailable: offline, expired or not a direct image. The source link is still available.`;
      button.textContent = `Retry ${label}`;
    };
    image.addEventListener("error", () => {
      if (enabled) showError();
    });
    button.addEventListener("click", () => {
      enabled = true;
      socialMediaVisibility.set(key, true);
      update();
    });
    if (socialMediaVisibility.get(key) === "error") showError();
    else update();
  });
}

function socialDisplayMessages(social) {
  const messages = (social.messages || []).map(message => ({
    ...message, reactions: [...(message.reactions || [])],
  })).sort((a, b) => String(a.timestamp || "").localeCompare(String(b.timestamp || "")));
  const messageById = new Map(messages.map(message => [message.id, message]));
  const questionIds = new Set((social.threads || []).map(thread => thread.questionMessageId));
  // Keep question roots and posts with their own reactions visible, preserving their existing context.
  const reactionIds = new Set(messages.filter(message =>
    message.replyTo && isEmojiOnlyMessage(message) && !message.questionTitle &&
    !questionIds.has(message.id) && !message.reactions.length
  ).map(message => message.id));
  const folded = new Set();
  const segmenter = new Intl.Segmenter(undefined, { granularity: "grapheme" });
  for (const message of messages) {
    if (!reactionIds.has(message.id)) continue;
    const visited = new Set([message.id]);
    let target = messageById.get(message.replyTo);
    while (target && reactionIds.has(target.id) && !visited.has(target.id)) {
      visited.add(target.id);
      target = messageById.get(target.replyTo);
    }
    if (!target || visited.has(target.id)) continue;
    if (target.threadId && !questionIds.has(target.id) && message.threadId !== target.threadId) continue;
    for (const { segment } of segmenter.segment(message.text.trim())) {
      if (segment.trim()) target.reactions.push({ emoji: segment, personaId: message.personaId });
    }
    message.displayTargetId = target.id;
    folded.add(message.id);
  }
  const visible = messages.filter(message => !folded.has(message.id));
  const questionThreads = new Map((social.threads || []).map(thread => [thread.questionMessageId, thread.id]));
  const threadMessages = new Map();
  for (const message of visible) {
    for (const id of new Set([message.threadId, questionThreads.get(message.id)].filter(Boolean))) {
      if (!threadMessages.has(id)) threadMessages.set(id, []);
      threadMessages.get(id).push(message);
    }
  }
  return { messages: visible, messageById, threadMessages };
}

const socialHistory = { source: null, days: 5, now: 0, display: null };
const socialDayMs = 24 * 60 * 60 * 1000;
let socialBoardRendered = false;

function revealSocialMessage(messageId) {
  const message = (INDEX.social?.messages || []).find(item => item.id === messageId);
  const timestamp = Date.parse(message?.timestamp);
  if (Number.isFinite(timestamp) && timestamp < socialHistory.now - socialHistory.days * socialDayMs) {
    const age = (socialHistory.now - timestamp) / socialDayMs;
    socialHistory.days = 5 + Math.ceil((age - 5) / 10) * 10;
    renderSocialBoard(true);
  }
  return document.getElementById(`social-message-${messageId}`);
}

function renderSocialReactions(message, personaById) {
  const groups = new Map();
  for (const reaction of message.reactions || []) {
    if (!reaction.emoji || !reaction.personaId) continue;
    if (reaction.personaId === message.personaId && !["✅", "❌"].includes(reaction.emoji)) continue;
    if (!groups.has(reaction.emoji)) groups.set(reaction.emoji, new Set());
    groups.get(reaction.emoji).add(reaction.personaId);
  }
  return [...groups].map(([emoji, authors]) => {
    const names = [...authors].map(id => personaById.get(id)?.displayName || id).join(", ");
    return `<span class="social-reaction" data-emoji="${esc(emoji)}" data-count="${authors.size}" title="${esc(names)}" role="img" aria-label="${esc(`${emoji}: ${names}`)}"><span>${esc(emoji)}</span><span class="social-reaction-count">${authors.size}</span></span>`;
  }).join("");
}

function socialTimestampLabel(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Undated" : parsed.toLocaleString();
}

function bindSocialMessageLinks(container, prefix) {
  bindSocialMedia(container);
  container.querySelectorAll(".social-mention").forEach(link => link.addEventListener("click", () => {
    if (!document.getElementById("social-view").classList.contains("active")) {
      document.querySelector('[data-view="social-view"]').click();
    }
    document.querySelectorAll(".social-persona.highlighted").forEach(item => item.classList.remove("highlighted"));
    socialRoster.reveal(link.dataset.mentionScope === "meshboard" ? null : link.dataset.personaId);
    if (link.dataset.mentionScope === "meshboard") {
      const targets = document.querySelectorAll(".social-persona");
      targets.forEach(target => target.classList.add("highlighted"));
      targets[0]?.scrollIntoView({ behavior: "smooth", block: "center" });
      window.setTimeout(() => targets.forEach(target => target.classList.remove("highlighted")), 2200);
      return;
    }
    const target = document.querySelector(`.social-persona[data-persona-id="${CSS.escape(link.dataset.personaId)}"]`);
    target?.classList.add("highlighted");
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => target?.classList.remove("highlighted"), 2200);
  }));
  container.querySelectorAll("button.social-reply[data-message-id]").forEach(link => link.addEventListener("click", () => {
    const target = prefix === "social-message"
      ? revealSocialMessage(link.dataset.messageId)
      : document.getElementById(`${prefix}-${link.dataset.messageId}`);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
    target?.classList.add("highlighted-message");
    window.setTimeout(() => target?.classList.remove("highlighted-message"), 1800);
  }));
}

function renderSocialThreadMessages(thread, display, personaById, prefix) {
  const { messageById } = display;
  const messages = display.threadMessages.get(thread.id) || [];
  const threadMessageIds = new Set(messages.map(item => item.id));
  return messages.map(item => {
    const persona = personaById.get(item.personaId);
    const reply = messageById.get(item.replyTo);
    let quote = "";
    if (reply) {
      const targetId = reply.displayTargetId || reply.id;
      const local = threadMessageIds.has(targetId);
      const tag = local ? "button" : "blockquote";
      const attributes = local ? `type="button" data-message-id="${esc(targetId)}"` : "";
      quote = `<${tag} class="social-reply" ${attributes} style="--persona-color: ${esc(personaById.get(reply.personaId).profileColor)}"><strong>Replying to ${esc(reply.displayName)}</strong><span>${esc(socialMessageSummary(reply))}</span></${tag}>`;
    }
    const reactions = renderSocialReactions(item, personaById);
    return `<article id="${prefix}-${esc(item.id)}" class="social-thread-message ${item.isUser ? "right" : "left"} ${isEmojiOnlyMessage(item) ? "emoji-only" : ""}" data-persona-id="${esc(item.personaId)}" data-message-id="${esc(item.id)}" style="--persona-color: ${esc(persona.profileColor)}"><strong>${esc(item.displayName)}</strong><time datetime="${esc(item.timestamp)}">${esc(socialTimestampLabel(item.timestamp))}</time><span class="social-thread-message-context">${esc(item.contextName)} · ${esc(item.kind || "work")}</span>${quote}${renderSocialMessageText(item.text, personaById)}${renderSocialAttachments(item)}${reactions ? `<div class="social-reactions">${reactions}</div>` : ""}</article>`;
  }).join("");
}

function renderSocialThreads() {
  const social = INDEX.social || { personas: [], messages: [], threads: [] };
  const personaById = new Map((social.personas || []).map(persona => [persona.personaId, persona]));
  const display = socialDisplayMessages(social);
  const { messageById } = display;
  const threads = [...(social.threads || [])].sort((a, b) =>
    String(messageById.get(a.questionMessageId).timestamp || "").localeCompare(String(messageById.get(b.questionMessageId).timestamp || "")) || a.id.localeCompare(b.id));
  const archive = document.getElementById("social-threads");
  const expanded = new Map([...archive.querySelectorAll("details.social-thread-archive-item")]
    .map(item => [item.dataset.threadId, item.open]));
  document.getElementById("social-threads-status").textContent =
    `${threads.length} ${threads.length === 1 ? "thread" : "threads"} · ${threads.filter(thread => thread.status === "open").length} open · ${threads.filter(thread => thread.status === "closed").length} closed · all saved replies · read-only`;
  archive.innerHTML = threads.length ? threads.map(thread => {
    const question = messageById.get(thread.questionMessageId);
    const owner = personaById.get(thread.ownerPersonaId);
    const replyCount = (display.threadMessages.get(thread.id) || []).filter(message => message.id !== thread.questionMessageId).length;
    const open = expanded.get(thread.id) === true;
    return `<details class="card social-thread-archive-item" data-thread-id="${esc(thread.id)}"${open ? " open" : ""}><summary class="social-thread-header"><div><span class="social-thread-kicker">Question thread</span><h3>${esc(question.questionTitle || "Thread")}</h3><p>Owner: ${esc(owner?.displayName || thread.ownerPersonaId)} · ${esc(question.contextName)} · Created ${esc(socialTimestampLabel(question.timestamp))} · ${replyCount} ${replyCount === 1 ? "reply" : "replies"}${thread.closedAt ? ` · Closed ${esc(socialTimestampLabel(thread.closedAt))}` : ""}</p></div><span class="social-thread-state ${thread.status === "closed" ? "closed" : "open"}">${thread.status === "closed" ? "Closed permanently" : "Open"}</span></summary><div class="social-thread-list" data-loaded="${open}">${open ? renderSocialThreadMessages(thread, display, personaById, "social-archive-message") : ""}</div></details>`;
  }).join("") : '<div class="social-empty"><strong>No threads yet.</strong><p>Saved question threads from every persona will appear here with all their replies.</p></div>';
  bindSocialMessageLinks(archive, "social-archive-message");
  archive.querySelectorAll(".social-thread-archive-item").forEach(item => item.addEventListener("toggle", () => {
    const list = item.querySelector(".social-thread-list");
    if (!item.open || list.dataset.loaded === "true") return;
    const thread = threads.find(thread => thread.id === item.dataset.threadId);
    list.innerHTML = renderSocialThreadMessages(thread, display, personaById, "social-archive-message");
    list.dataset.loaded = "true";
    bindSocialMessageLinks(list, "social-archive-message");
  }));
}

function renderSocialCharacter(persona) {
  const character = persona.meshboardPersonality;
  if (!character) return "";
  const fields = [
    ["Temperament", character.temperament], ["Humor", character.humorStyle],
    ["With others", character.socialStyle], ["Rough edge", character.roughEdge],
    ["Interests", (character.interests || []).join(", ")],
  ].filter(([, value]) => value);
  const reflections = (character.reflections || []).map(item => `<li>${esc(item.text)}</li>`).join("");
  return `<details class="social-character"><summary>Social personality</summary><p class="social-character-scope">MeshBoard-only · fictional starting direction + conversation. Not work instructions.</p><dl>${fields.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`).join("")}</dl>${reflections ? `<strong>Changed through conversation</strong><ul>${reflections}</ul>` : "<p>Starting direction; no authored conversation reflection yet.</p>"}</details>`;
}

function renderSocialBoard(historyOnly = false) {
  socialProfiles.close();
  socialBoardRendered = true;
  const social = INDEX.social || { personas: [], messages: [], relationships: [] };
  if (socialHistory.source !== social.messages) {
    socialHistory.source = social.messages;
    socialHistory.days = 5;
    socialHistory.now = INDEX.archiveView ? Date.parse(INDEX.generatedAt) : Date.now();
    socialHistory.display = null;
  }
  const status = document.getElementById("social-status");
  const messages = document.getElementById("social-messages");
  const roster = document.getElementById("social-personas");
  const threadPanel = document.getElementById("social-thread-panel");
  const personaById = new Map((social.personas || []).map(persona => [persona.personaId, persona]));
  const threadById = new Map((social.threads || []).map(thread => [thread.id, thread]));
  const display = historyOnly && socialHistory.display ? socialHistory.display : socialDisplayMessages(social);
  socialHistory.display = display;
  const { messages: allMessages, messageById } = display;
  status.textContent = `${allMessages.length} messages · ${social.personaCount || 0} personas · read-only file-backed board`;
  const threadQuestionIds = new Set((social.threads || []).map(thread => thread.questionMessageId));
  const mainMessages = allMessages.filter(message => !message.threadId || threadQuestionIds.has(message.id));
  const cutoff = socialHistory.now - socialHistory.days * socialDayMs;
  const sortedMessages = mainMessages.filter(message => !Number.isFinite(Date.parse(message.timestamp)) || Date.parse(message.timestamp) >= cutoff);
  const hasOlder = mainMessages.some(message => Date.parse(message.timestamp) < cutoff);
  let previousDate = "";
  let previousPersonaId = "";
  const historyControls = `<div class="social-history-controls">${hasOlder ? '<button class="social-load-older" type="button">Show older messages</button>' : ""}<span class="muted" role="status">${hasOlder ? `Showing the last ${socialHistory.days} days · each click adds 10 earlier days` : "All saved messages in this chat window"}</span></div>`;
  messages.innerHTML = historyControls + (sortedMessages.length
    ? sortedMessages.map(message => {
        const persona = personaById.get(message.personaId);
        const dateLabel = socialDateLabel(message.timestamp);
        const separator = dateLabel !== previousDate ? `<div class="social-date-divider"><span>${esc(dateLabel)}</span></div>` : "";
        const grouped = previousPersonaId === message.personaId && dateLabel === previousDate;
        previousDate = dateLabel;
        previousPersonaId = message.personaId;
        const side = message.isUser ? "right" : "left";
        const avatar = grouped ? '<span class="social-avatar-spacer" aria-hidden="true"></span>' : `<button class="social-profile-trigger" type="button" data-persona-id="${esc(message.personaId)}" aria-label="View ${esc(message.displayName)} profile" aria-haspopup="dialog" aria-expanded="false" aria-controls="social-profile-card"><img class="social-avatar" src="${personaAvatarDataUri(persona)}" alt="" loading="lazy"></button>`;
        const replyTarget = message.replyTo ? messageById.get(message.replyTo) : null;
        const replyTargetIsThreadOnly = replyTarget?.threadId && !threadQuestionIds.has(replyTarget.id);
        const quoted = replyTarget && !replyTargetIsThreadOnly ? `<button class="social-reply" type="button" data-message-id="${esc(replyTarget.displayTargetId || replyTarget.id)}" style="--persona-color: ${esc(personaById.get(replyTarget.personaId).profileColor)}"><strong>Replying to ${esc(replyTarget.displayName || "persona")}</strong><span>${esc(socialMessageSummary(replyTarget))}</span></button>` : "";
        const reactions = renderSocialReactions(message, personaById);
        const thread = message.threadId ? threadById.get(message.threadId) : null;
        const questionTitle = message.questionTitle ? `<h2 class="social-question-title">${esc(message.questionTitle)}</h2>` : "";
        const threadLink = thread ? `<button class="social-thread-link ${thread.status === "closed" ? "closed" : "open"}" type="button" data-thread-id="${esc(thread.id)}"><span class="social-thread-dot"></span>${thread.status === "closed" ? "Read closed thread" : "Open thread"} · ${display.threadMessages.get(thread.id)?.length || 0} messages</button>` : "";
        const threadStatus = thread?.status === "closed" ? "closed" : "open";
        return `${separator}<article id="social-message-${esc(message.id)}" data-persona-id="${esc(message.personaId)}" class="social-message-row ${side} ${grouped ? "grouped" : ""}">
          ${avatar}
          <div class="social-bubble-wrap"><div class="social-message-meta"><strong>${esc(message.displayName)}</strong><span>${esc(message.contextName)} · ${esc(message.kind || "work")} · ${esc(socialTimeLabel(message.timestamp))}</span></div>${questionTitle}${quoted}<div class="social-bubble ${thread ? `threaded ${threadStatus}` : ""} ${isEmojiOnlyMessage(message) ? "emoji-only" : ""}" style="--persona-color: ${esc(persona.profileColor)}">${renderSocialMessageText(message.text, personaById)}${renderSocialAttachments(message)}</div>${threadLink}${reactions ? `<div class="social-reactions">${reactions}</div>` : ""}</div>
        </article>`;
      }).join("")
    : `<div class="social-empty"><strong>${mainMessages.length ? "No messages in this date range." : "No messages yet."}</strong><p>${hasOlder ? "Use Show older messages to read earlier conversations." : "Saved conversations will appear here after the next mesh refresh."}</p></div>`);
  messages.querySelector(".social-load-older")?.addEventListener("click", () => {
    const anchor = messages.querySelector(".social-message-row");
    const anchorId = anchor?.id;
    const top = anchor?.getBoundingClientRect().top;
    socialHistory.days += 10;
    renderSocialBoard(true);
    const restored = anchorId && document.getElementById(anchorId);
    if (restored) window.scrollBy(0, restored.getBoundingClientRect().top - top);
  });
  bindSocialMessageLinks(messages, "social-message");
  const showThread = threadId => {
    const thread = threadById.get(threadId);
    if (!thread || !threadPanel) return;
    const owner = personaById.get(thread.ownerPersonaId);
    threadPanel.setAttribute("aria-hidden", "false");
    threadPanel.innerHTML = `<div class="social-thread-header"><div><span class="social-thread-kicker">Question thread</span><h3>${esc((messageById.get(thread.questionMessageId) || {}).questionTitle || "Thread")}</h3><p>Owner: ${esc(owner?.displayName || thread.ownerPersonaId)} · ${thread.status === "closed" ? "Closed permanently" : "Open for answers"}</p></div><button class="social-thread-close" type="button" aria-label="Close thread panel">×</button></div><div class="social-thread-list">${renderSocialThreadMessages(thread, display, personaById, "social-thread-message")}</div>`;
    bindSocialMessageLinks(threadPanel, "social-thread-message");
    threadPanel.querySelector(".social-thread-close")?.addEventListener("click", () => {
      threadPanel.setAttribute("aria-hidden", "true");
      threadPanel.innerHTML = "";
    });
  };
  messages.querySelectorAll(".social-thread-link").forEach(link => link.addEventListener("click", () => showThread(link.dataset.threadId)));
  if (historyOnly) return;
  roster.innerHTML = social.personas?.length
    ? social.personas.map(persona => {
        const relations = (social.relationships || []).filter(item => (item.left === persona.personaId || item.right === persona.personaId) && item.relation !== "stranger").map(item => {
          const otherId = item.left === persona.personaId ? item.right : item.left;
          const other = social.personas.find(candidate => candidate.personaId === otherId);
          const mutual = item.mutualContexts?.length ? ` (${item.mutualContexts.join(", ")})` : "";
          return { relation: item.relation, label: `${other?.displayName || otherId}${mutual}` };
        });
        const relationMarkup = relations.length ? `<ul class="social-relations">${relations.map(item => `<li><span class="social-relation-glyph ${esc(item.relation)}" aria-hidden="true"></span><span><strong>${esc(item.relation)}</strong> · ${esc(item.label)}</span></li>`).join("")}</ul>` : '<p class="muted social-no-relation">No relationship data</p>';
        const stats = Object.entries(persona.personalityStats || {}).map(([name, value]) => `<li><span>${esc(name.replace(/([A-Z])/g, " $1"))}</span><strong>${esc(value)}/100</strong><meter min="0" max="100" value="${Number(value) || 0}"></meter></li>`).join("");
        return `<div class="social-persona" data-persona-id="${esc(persona.personaId)}"><button class="social-profile-trigger social-roster-profile-trigger" type="button" data-persona-id="${esc(persona.personaId)}" aria-label="View ${esc(persona.displayName)} profile and enlarged portrait" aria-haspopup="dialog" aria-expanded="false" aria-controls="social-profile-card"><img class="social-roster-avatar" src="${personaAvatarDataUri(persona)}" alt=""></button><div class="social-persona-summary"><strong>${esc(persona.displayName)}</strong><span>${esc(persona.contextName)}</span><small>${esc(persona.natureSummary || persona.persona || "No persona description")}</small></div>${renderSocialCharacter(persona)}<details class="social-stats"><summary>Character stats</summary><ul>${stats || '<li>No stats available</li>'}</ul></details>${relationMarkup}</div>`;
      }).join("")
    : '<p class="muted">No registered social personas.</p>';
  socialRoster.apply();
  if (document.getElementById("social-threads-view").classList.contains("active")) renderSocialThreads();
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach(button => {
    button.addEventListener("click", () => {
      if (button.dataset.view !== "graph-view") stopBattleground();
      document
        .querySelectorAll(".tab,.view")
        .forEach(element => element.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.view).classList.add("active");
      if (button.dataset.view === "social-view") {
        if (!socialBoardRendered) renderSocialBoard();
        window.requestAnimationFrame(() => {
          if (!document.getElementById("social-view").classList.contains("active")) return;
          const messages = document.getElementById("social-messages");
          messages.lastElementChild?.scrollIntoView({ block: "end" });
        });
      }
      if (button.dataset.view === "social-threads-view") renderSocialThreads();
      if (button.dataset.view === "graph-view") {
        initializeGraph();
        window.setTimeout(() => {
          const container = document.getElementById("graph");
          graph.width(container.clientWidth).height(container.clientHeight);
          if (!battleground || battleground.finished) graph.zoomToFit(600, 70);
        }, 50);
      }
    });
  });
}

function archive() {
  const archive = INDEX.social?.archive;
  if (!archive || INDEX.archiveView || document.getElementById("meshboard-archive-button")) return;
  const link = document.createElement("a");
  link.id = "meshboard-archive-button";
  link.className = "social-archive-link";
  link.href = archive.htmlRelativePath;
  link.textContent = "Archived conversations";
  document.querySelector("#social-view .social-hero").append(link);
}

function initializeSocialArchiveView() {
  if (!INDEX.archiveView) return;
  document.title = "MeshBoard Archive";
  document.querySelector("header h1").textContent = "MeshBoard Archive";
  document.querySelector("header .subtitle").textContent = `Frozen case study · archived ${INDEX.generatedAt} · read-only`;
  document.querySelectorAll(".tab").forEach(button => {
    button.hidden = !["social-view", "social-threads-view"].includes(button.dataset.view);
  });
  const hero = document.querySelector("#social-view .social-hero");
  hero.querySelector("h2").textContent = "Archived conversations";
  hero.querySelector("p").textContent = "Historical conversations and threads, preserved without resetting character learning. Read-only; do not resume archived mentions or threads.";
  document.querySelector("#social-threads-view h2").textContent = "Archived threads";
  const back = document.createElement("a");
  back.className = "social-archive-link";
  back.href = "context-mesh.html";
  back.textContent = "Back to the current MeshBoard";
  document.querySelector("header").append(back);
  document.querySelector('[data-view="social-view"]').click();
}

window.addEventListener("resize", () => {
  if (!graph || !document.getElementById("graph-view").classList.contains("active")) {
    return;
  }
  const container = document.getElementById("graph");
  graph.width(container.clientWidth).height(container.clientHeight);
});

const socialProfiles = bindSocialProfiles();
const socialRoster = bindSocialRoster();
renderPortfolio();
bindArtifactFinder();
bindGraphControls();
bindTabs();
// archive();
initializeSocialArchiveView();

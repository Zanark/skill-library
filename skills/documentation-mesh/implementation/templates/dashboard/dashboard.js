"use strict";

const INDEX = window.DOCUMENTATION_MESH_INDEX;
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" })[c]);
const nodeId = endpoint => typeof endpoint === "object" ? endpoint.id : endpoint;
const edgeKey = edge => edge.id || `${nodeId(edge.source)}|${nodeId(edge.target)}|${edge.type}`;
const byId = new Map(INDEX.documents.map(document => [document.id, document]));
const healthByType = INDEX.healthFindings.reduce((map, finding) => map.set(finding.type, (map.get(finding.type) || 0) + 1), new Map());
let graph;
let selectedNode = null;
let selectedEdge = null;
let hoveredNode = null;
let hoveredEdge = null;
let currentNodes = [];
let currentEdges = [];
let localDepth = 0;
let animationFrame = null;
let familyOverrides = new Map();

function metrics(target, rows) {
  document.getElementById(target).innerHTML = rows.map(([label,value]) => `<div class="metric"><strong>${Number(value).toLocaleString()}</strong><span>${esc(label)}</span></div>`).join("");
}

function list(items, empty = "None recorded.") {
  return items?.length ? `<ul>${items.map(item => `<li>${esc(item)}</li>`).join("")}</ul>` : `<p class="muted">${esc(empty)}</p>`;
}

function evidenceList(items) {
  return items?.length ? items.map(item => `<blockquote><strong>${esc(item.sourceFile)}:${item.lineStart}${item.lineEnd !== item.lineStart ? `-${item.lineEnd}` : ""}</strong><br>${esc(item.excerpt)}</blockquote>`).join("") : `<p class="muted">No evidence retained.</p>`;
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach(button => button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(item => item.classList.toggle("active", item === button));
    document.querySelectorAll(".view").forEach(view => view.classList.toggle("active", view.id === button.dataset.view));
    if (button.dataset.view === "graph") {
      initGraph();
      setTimeout(() => graph.width(document.getElementById("graph-canvas").clientWidth).height(document.getElementById("graph-canvas").clientHeight), 20);
    }
  }));
}

function setupCatalogue() {
  metrics("summary", [
    ["Documents", INDEX.statistics.documentCount],
    ["Strong relationships", INDEX.statistics.defaultEdgeCount],
    ["Optional relationships", INDEX.statistics.optionalEdgeCount],
    ["Health findings", INDEX.statistics.healthFindingCount],
    ["Cache reused", INDEX.statistics.cacheReused],
    ["Reparsed", INDEX.statistics.cacheReparsed]
  ]);
  const families = [...new Set(INDEX.documents.map(document => document.family))].sort();
  const owners = [...new Set(INDEX.documents.map(document => document.owner).filter(Boolean))].sort();
  document.getElementById("catalogue-controls").innerHTML = `
    <input id="doc-search" type="text" placeholder="Search title, path, summary, tags, owner, commands, code references">
    <select id="family-filter"><option value="">All families</option>${families.map(value => `<option>${esc(value)}</option>`).join("")}</select>
    <select id="status-filter"><option value="">All status</option>${["active","deprecated","archived","draft","generated","unknown"].map(value => `<option>${value}</option>`).join("")}</select>
    <select id="owner-filter"><option value="">All owners</option>${owners.map(value => `<option>${esc(value)}</option>`).join("")}</select>
    <label class="chip"><input id="orphan-filter" type="checkbox"> Orphans</label>
    <label class="chip"><input id="broken-filter" type="checkbox"> Broken links</label>
    <label class="chip"><input id="diagram-filter" type="checkbox"> Diagrams</label>
    <label class="chip"><input id="code-filter" type="checkbox"> Code references</label>`;
  const findingDocs = type => new Set(INDEX.healthFindings.filter(finding => finding.type === type).map(finding => finding.documentId));
  const orphans = findingDocs("orphan");
  const broken = new Set(INDEX.healthFindings.filter(finding => finding.type.startsWith("broken-")).map(finding => finding.documentId));
  const render = () => {
    const query = document.getElementById("doc-search").value.toLowerCase();
    const family = document.getElementById("family-filter").value;
    const status = document.getElementById("status-filter").value;
    const owner = document.getElementById("owner-filter").value;
    const rows = INDEX.documents.filter(doc => {
      const corpus = JSON.stringify([doc.title,doc.collectionPath,doc.summary,doc.tags,doc.owner,doc.commands,doc.codeReferences]).toLowerCase();
      return (!query || corpus.includes(query)) &&
        (!family || doc.family === family) &&
        (!status || doc.status === status) &&
        (!owner || doc.owner === owner) &&
        (!window.document.getElementById("orphan-filter").checked || orphans.has(doc.id)) &&
        (!window.document.getElementById("broken-filter").checked || broken.has(doc.id)) &&
        (!window.document.getElementById("diagram-filter").checked || doc.hasDiagrams) &&
        (!window.document.getElementById("code-filter").checked || doc.codeReferences.length);
    });
    document.getElementById("documents").innerHTML = rows.length ? rows.map(document => {
      const incoming = INDEX.graph.edges.filter(edge => edge.shownByDefault && nodeId(edge.target) === document.id);
      const outgoing = INDEX.graph.edges.filter(edge => edge.shownByDefault && nodeId(edge.source) === document.id);
      const findings = INDEX.healthFindings.filter(finding => finding.documentId === document.id);
      const provenance = INDEX.gitProvenance.documents?.[document.id] || {};
      return `<details class="document" id="document-${document.id}">
        <summary><span class="title">${esc(document.title)}</span><span class="path">${esc(document.collectionPath)}</span><span class="badge ${esc(document.status)}">${esc(document.status)}</span></summary>
        <div class="content"><div class="grid">
          <section class="panel"><h3>Overview</h3><p>${esc(document.summary || document.purpose || "No summary extracted.")}</p><p><strong>Purpose:</strong> ${esc(document.purpose || "Unknown")}</p><p><strong>Audience:</strong> ${esc(document.audience || "Not stated")}</p></section>
          <section class="panel"><h3>Metadata</h3><p><strong>Family:</strong> ${esc(document.family)}</p><p><strong>Owner:</strong> ${esc(document.owner || "Not stated")}</p><p><strong>Tags:</strong> ${esc(document.tags.join(", ") || "None")}</p><p><strong>Frontmatter:</strong></p><pre>${esc(JSON.stringify(document.frontmatter,null,2))}</pre></section>
          <section class="panel"><h3>Timeline</h3><p><strong>Created:</strong> ${esc(document.earliestKnownCreationDate || "Unknown")}</p><p><strong>Updated:</strong> ${esc(document.lastMeaningfulUpdate || "Unknown")}</p><p><strong>Date source:</strong> ${esc(document.dateProvenance)}</p><p><strong>Contributors:</strong> ${esc((provenance.contributors || []).join(", ") || "Unknown")}</p></section>
          <section class="panel"><h3>Incoming links</h3>${list(incoming.map(edge => byId.get(nodeId(edge.source))?.title || nodeId(edge.source)))}</section>
          <section class="panel"><h3>Outgoing links</h3>${list(outgoing.map(edge => byId.get(nodeId(edge.target))?.title || nodeId(edge.target)))}</section>
          <section class="panel"><h3>Referenced systems</h3>${list([
            ...document.codeReferences.map(item => `Code: ${item.value}`),
            ...document.commands.map(item => `Command: ${item.value}`),
            ...document.workItems.map(item => `Work item: ${item.id}`),
            ...document.pullRequests.map(item => `PR: ${item.id}`),
            ...document.incidents.map(item => `Incident: ${item.id}`)
          ])}</section>
          <section class="panel"><h3>Quality findings</h3>${list(findings.map(finding => finding.title))}</section>
          <section class="panel"><h3>Source evidence</h3>${evidenceList(document.headings.slice(0,6).map(item => item.evidence))}</section>
        </div></div></details>`;
    }).join("") : `<div class="empty panel">No documents match the selected filters.</div>`;
  };
  document.getElementById("catalogue-controls").querySelectorAll("input,select").forEach(control => control.addEventListener(control.tagName === "INPUT" && control.type === "text" ? "input" : "change", render));
  render();
}

function graphControls() {
  document.getElementById("graph-controls").innerHTML = `
    <button id="fit-graph">Fit</button><button id="reheat-graph">Reheat</button><button id="unpin-all">Unpin all</button><button id="animate-graph">Animate timeline</button>
    <label class="chip">Duration <select id="animation-duration"><option value="5">5s</option><option value="12" selected>12s</option><option value="30">30s</option></select></label>
    <input id="graph-search" type="text" placeholder="Search graph">
    <label class="chip">Detail <select id="detail-level"><option value="documents">Core documents</option><option value="sections">Documents and sections</option><option value="entities">Documents and entities</option><option value="full">Full graph</option></select></label>
    <label class="chip">Evidence <select id="evidence-level"><option value="strong">Strong only</option><option value="inferred">Include strong inference</option><option value="incidental">Include incidental</option></select></label>
    <label class="chip">Status <select id="graph-status"><option value="active-deprecated">Active and deprecated</option><option value="active">Active only</option><option value="all">All</option></select></label>
    <label class="chip">Local depth <select id="local-depth"><option value="0">Global</option><option value="1">1 hop</option><option value="2">2 hops</option><option value="3">3 hops</option></select></label>
    <label class="chip"><input id="pin-after-drag" type="checkbox"> Pin after drag</label>
    <details class="physics panel"><summary>Physics controls</summary><div class="physics-grid">
      ${[
        ["center","Center force",0,1,.01,.52],["repel","Repel force",0,20,.5,10],["link","Link force",0,1,.01,1],["distance","Link distance",30,500,5,250],
        ["collision","Collision radius",4,100,2,60],["cooling","Cooling",.005,.08,.001,.023],["friction","Friction",.05,.9,.05,.4],["node-size","Node size",.5,2.5,.1,1],
        ["link-width","Link thickness",.25,3,.25,1],["text-fade","Text fade",-2,3,.1,0]
      ].map(([id,label,min,max,step,value]) => `<label>${label}<output id="${id}-value">${value}</output><input id="${id}" type="range" min="${min}" max="${max}" step="${step}" value="${value}"></label>`).join("")}
    </div></details>`;
}

function allowedNode(node, detail, status) {
  const typeAllowed = detail === "full" || node.type === "document" ||
    (detail === "sections" && node.type === "section") ||
    (detail === "entities" && node.type !== "section");
  const statusAllowed = status === "all" || node.type !== "document" ||
    (status === "active" ? ["active","unknown"].includes(node.status) : !["archived","draft","generated"].includes(node.status));
  return typeAllowed && statusAllowed;
}

function familyLayout(nodes, edges) {
  const familyStats = new Map();
  nodes.filter(node => node.type === "document").forEach(node => {
    if (!familyStats.has(node.family)) familyStats.set(node.family,{count:0,connected:0});
    familyStats.get(node.family).count++;
  });
  edges.forEach(edge => {
    const source = nodes.find(node => node.id === nodeId(edge.source));
    const target = nodes.find(node => node.id === nodeId(edge.target));
    if (source?.type === "document") familyStats.get(source.family).connected++;
    if (target?.type === "document") familyStats.get(target.family).connected++;
  });
  const families = [...familyStats].sort((a,b) => b[1].count-a[1].count || a[0].localeCompare(b[0]));
  const anchors = new Map();
  families.forEach(([family,stats],index) => {
    if (familyOverrides.has(family)) return anchors.set(family,familyOverrides.get(family));
    const connected = stats.connected > 0;
    const radius = connected ? (index === 0 ? 0 : 280 + 65 * Math.floor(index / 8)) : 850 + 75 * index;
    const angle = index * 2.399963229728653;
    anchors.set(family,{x:Math.cos(angle)*radius,y:Math.sin(angle)*radius,connected});
  });
  nodes.forEach(node => {
    const anchor = anchors.get(node.family) || {x:0,y:0,connected:false};
    node.familyX = anchor.x; node.familyY = anchor.y; node.familyConnected = anchor.connected;
  });
}

function adjacencyFor(edges) {
  const map = new Map();
  edges.forEach(edge => {
    const source=nodeId(edge.source), target=nodeId(edge.target);
    if (!map.has(source)) map.set(source,new Set());
    if (!map.has(target)) map.set(target,new Set());
    map.get(source).add(target); map.get(target).add(source);
  });
  return map;
}

function graphData() {
  const detail = document.getElementById("detail-level").value;
  const evidence = document.getElementById("evidence-level").value;
  const status = document.getElementById("graph-status").value;
  const confidence = evidence === "strong" ? new Set(["high"]) : evidence === "inferred" ? new Set(["high","medium"]) : new Set(["high","medium","low","unknown"]);
  let nodes = INDEX.graph.nodes.filter(node => allowedNode(node,detail,status)).map(node => ({...node}));
  const ids = new Set(nodes.map(node => node.id));
  let edges = INDEX.graph.edges.filter(edge => ids.has(nodeId(edge.source)) && ids.has(nodeId(edge.target)) && confidence.has(edge.confidence)).map(edge => ({...edge}));
  if (localDepth && (selectedNode || nodes[0])) {
    const start = selectedNode?.id || nodes[0].id;
    const adjacency = adjacencyFor(edges);
    const visible = new Set([start]);
    let frontier = new Set([start]);
    for (let depth=0; depth<localDepth; depth++) {
      const next = new Set();
      frontier.forEach(id => (adjacency.get(id)||[]).forEach(neighbor => { if(!visible.has(neighbor)){visible.add(neighbor);next.add(neighbor);} }));
      frontier = next;
    }
    nodes = nodes.filter(node => visible.has(node.id));
    const localIds = new Set(nodes.map(node => node.id));
    edges = edges.filter(edge => localIds.has(nodeId(edge.source)) && localIds.has(nodeId(edge.target)));
  }
  familyLayout(nodes,edges);
  return {nodes,edges};
}

function forceCurve(value, coefficient=.01) { return (Math.pow(coefficient,1-value)-coefficient)/(1-coefficient); }

function applyPhysics() {
  if (!graph) return;
  const center = +document.getElementById("center").value;
  const repel = +document.getElementById("repel").value;
  const link = +document.getElementById("link").value;
  const distance = +document.getElementById("distance").value;
  const collision = +document.getElementById("collision").value;
  const cooling = +document.getElementById("cooling").value;
  const friction = +document.getElementById("friction").value;
  graph.d3Force("charge").strength(-Math.pow(repel,3));
  graph.d3Force("link").distance(distance).strength(forceCurve(link));
  graph.d3Force("collide", d3.forceCollide(node => collision + Math.min(35,node.degree*1.8)));
  graph.d3Force("x", d3.forceX(node => node.familyX).strength(forceCurve(center)));
  graph.d3Force("y", d3.forceY(node => node.familyY).strength(forceCurve(center)));
  graph.d3AlphaMin(.001).d3AlphaDecay(cooling).d3VelocityDecay(friction);
  graph.linkWidth(edge => (hoveredEdge && edgeKey(edge)===edgeKey(hoveredEdge) ? 4 : 1.2) * +document.getElementById("link-width").value);
}

function displayGraph() {
  if (!graph) return;
  const data = graphData();
  currentNodes = data.nodes; currentEdges = data.edges;
  graph.graphData({nodes:currentNodes,links:currentEdges});
  applyPhysics();
  graph.d3ReheatSimulation();
}

function redrawGraph() {
  if (graph) graph.nodeCanvasObject(nodePaint);
}

function connected(endpoint, other, edges=currentEdges) {
  return edges.some(edge => (nodeId(edge.source)===endpoint.id && nodeId(edge.target)===other.id) || (nodeId(edge.target)===endpoint.id && nodeId(edge.source)===other.id));
}

function inspectNode(node) {
  selectedNode=node; selectedEdge=null;
  const doc = byId.get(node.id);
  document.getElementById("inspector").innerHTML = doc ? `<h2>${esc(doc.title)}</h2><p class="path">${esc(doc.collectionPath)}</p><p>${esc(doc.summary)}</p><p><strong>Status:</strong> ${esc(doc.status)}</p><p><strong>Owner:</strong> ${esc(doc.owner||"Not stated")}</p><p><strong>Family:</strong> ${esc(doc.family)}</p><p><strong>Strong degree:</strong> ${node.degree}</p><button data-open-document="${doc.id}">Open catalogue card</button>` : `<h2>${esc(node.label)}</h2><p><strong>Type:</strong> ${esc(node.type)}</p><p>${esc(node.path)}</p>`;
  document.querySelector("[data-open-document]")?.addEventListener("click", event => {
    document.querySelector('[data-view="catalogue"]').click();
    const card=document.getElementById(`document-${event.target.dataset.openDocument}`); if(card){card.open=true;card.scrollIntoView({behavior:"smooth"});}
  });
  if (localDepth) displayGraph(); else redrawGraph();
}

function inspectEdge(edge) {
  selectedEdge=edge; selectedNode=null;
  const source = currentNodes.find(node => node.id===nodeId(edge.source));
  const target = currentNodes.find(node => node.id===nodeId(edge.target));
  document.getElementById("inspector").innerHTML = `<h2>${esc(source?.label)} → ${esc(target?.label)}</h2><div class="badges"><span class="badge">${esc(edge.type)}</span><span class="badge">${esc(edge.relationshipClass)}</span><span class="badge">${esc(edge.confidence)}</span></div><h3>Why connected?</h3><p>${esc(edge.reason)}</p><p><strong>Directional:</strong> ${edge.directional?"Yes":"No"}</p><p><strong>Extraction:</strong> ${esc(edge.extractionMethod)}</p><p><strong>Default visibility:</strong> ${edge.shownByDefault?"Visible":"Hidden"}</p>${edge.caveat?`<p><strong>Caveat:</strong> ${esc(edge.caveat)}</p>`:""}<h3>Persisted evidence</h3>${evidenceList(edge.evidence)}`;
  redrawGraph();
}

function nodePaint(node,ctx,scale) {
  const query=document.getElementById("graph-search").value.toLowerCase();
  const searched=query && JSON.stringify(node).toLowerCase().includes(query);
  const selected=selectedNode?.id===node.id;
  const faded=hoveredNode && hoveredNode.id!==node.id && !connected(hoveredNode,node);
  const size=(5+Math.min(15,Math.sqrt(node.degree+1)*2.5))*+document.getElementById("node-size").value;
  ctx.globalAlpha=faded?.18:1;
  ctx.beginPath();ctx.arc(node.x,node.y,size,0,2*Math.PI);ctx.fillStyle=node.type==="document"?"#263449":node.type==="section"?"#6b4f18":"#3f2a56";ctx.fill();
  ctx.lineWidth=(searched||selected?4:2.2)/scale;ctx.strokeStyle=searched?"#fbbf24":selected?"#ffffff":node.outlineColor;ctx.stroke();
  const fade=+document.getElementById("text-fade").value;
  if(scale+fade>.65 || searched || selected || node.degree>8){ctx.globalAlpha=faded?.12:Math.min(1,Math.max(.3,scale+.2));ctx.font=`${Math.max(9,12/Math.sqrt(scale))}px Segoe UI`;ctx.fillStyle="#edf1f7";ctx.fillText(node.label,node.x+size+3,node.y+3);}
  ctx.globalAlpha=1;
}

function initGraph() {
  if (graph) return;
  graphControls();
  const container=document.getElementById("graph-canvas");
  graph=ForceGraph()(container).width(container.clientWidth).height(container.clientHeight).backgroundColor("rgba(0,0,0,0)")
    .nodeCanvasObject(nodePaint).nodePointerAreaPaint((node,color,ctx)=>{ctx.fillStyle=color;ctx.beginPath();ctx.arc(node.x,node.y,14,0,2*Math.PI);ctx.fill();})
    .linkColor(edge => hoveredEdge&&edgeKey(edge)===edgeKey(hoveredEdge)?"#fbbf24":edge.shownByDefault?"#6ea8d7":"#66527d")
    .linkDirectionalArrowLength(edge=>edge.directional?3:0).linkDirectionalArrowRelPos(1)
    .onNodeHover(node=>{hoveredNode=node;container.style.cursor=node?"grab":"";redrawGraph();})
    .onLinkHover(edge=>{hoveredEdge=edge;container.style.cursor=edge?"pointer":"";if(edge)inspectEdge(edge);redrawGraph();})
    .onNodeClick(inspectNode).onLinkClick(inspectEdge)
    .onNodeRightClick(node=>{node.fx=node.x;node.fy=node.y;redrawGraph();})
    .onNodeDrag(node=>{node.fx=node.x;node.fy=node.y;})
    .onNodeDragEnd(node=>{
      if(document.getElementById("pin-after-drag").checked){node.fx=node.x;node.fy=node.y;familyOverrides.set(node.family,{x:node.x,y:node.y,connected:true});currentNodes.filter(item=>item.family===node.family).forEach(item=>{item.familyX=node.x;item.familyY=node.y;});graph.centerAt(node.x,node.y,500);}
      else {node.fx=null;node.fy=null;}
      applyPhysics();graph.d3ReheatSimulation();
    });
  window.DOCUMENTATION_MESH_GRAPH=graph;
  container.addEventListener("dblclick",()=>{if(hoveredNode){hoveredNode.fx=null;hoveredNode.fy=null;graph.d3ReheatSimulation();}});
  document.getElementById("fit-graph").onclick=()=>graph.zoomToFit(700,50);
  document.getElementById("reheat-graph").onclick=()=>graph.d3ReheatSimulation();
  document.getElementById("unpin-all").onclick=()=>{currentNodes.forEach(node=>{node.fx=null;node.fy=null;});familyOverrides.clear();displayGraph();};
  ["detail-level","evidence-level","graph-status"].forEach(id=>document.getElementById(id).onchange=displayGraph);
  document.getElementById("local-depth").onchange=event=>{localDepth=+event.target.value;displayGraph();};
  document.getElementById("graph-search").oninput=redrawGraph;
  ["center","repel","link","distance","collision","cooling","friction","node-size","link-width","text-fade"].forEach(id=>document.getElementById(id).oninput=event=>{document.getElementById(`${id}-value`).textContent=event.target.value;applyPhysics();redrawGraph();graph.d3ReheatSimulation();});
  document.getElementById("animate-graph").onclick=toggleAnimation;
  displayGraph();
  setTimeout(()=>graph.zoomToFit(800,60),400);
}

function toggleAnimation() {
  const button=document.getElementById("animate-graph");
  if(animationFrame){cancelAnimationFrame(animationFrame);animationFrame=null;displayGraph();button.textContent="Replay timeline";document.getElementById("animation-status").textContent="Timeline stopped; complete graph restored.";return;}
  const full=graphData(); const dated=[...full.nodes].sort((a,b)=>(a.date||"9999").localeCompare(b.date||"9999")||a.id.localeCompare(b.id));
  const duration=+document.getElementById("animation-duration").value*1000; const start=performance.now(); button.textContent="Stop animation";
  const frame=now=>{const progress=Math.min(1,(now-start)/duration);const count=Math.max(1,Math.ceil(dated.length*progress));const visible=new Set(dated.slice(0,count).map(node=>node.id));graph.graphData({nodes:full.nodes.filter(node=>visible.has(node.id)),links:full.edges.filter(edge=>visible.has(nodeId(edge.source))&&visible.has(nodeId(edge.target)))});document.getElementById("animation-status").textContent=`Timeline ${Math.round(progress*100)}% · ${count}/${dated.length} nodes visible`;if(progress<1)animationFrame=requestAnimationFrame(frame);else{animationFrame=null;graph.graphData({nodes:full.nodes,links:full.edges});button.textContent="Replay timeline";document.getElementById("animation-status").textContent="Timeline complete; undated nodes appeared last.";graph.d3ReheatSimulation();}};
  animationFrame=requestAnimationFrame(frame);
}

function setupHealth() {
  metrics("health-summary",[
    ["Broken links",healthByType.get("broken-link")||0],["Broken anchors",healthByType.get("broken-anchor")||0],["Orphans",healthByType.get("orphan")||0],
    ["Missing ownership",healthByType.get("missing-owner")||0],["Duplicates",(healthByType.get("duplicate-document")||0)+(healthByType.get("near-duplicate-document")||0)]
  ]);
  const types=[...healthByType.keys()].sort();
  document.getElementById("health-controls").innerHTML=`<input id="health-search" type="text" placeholder="Search findings"><select id="health-type"><option value="">All issue types</option>${types.map(type=>`<option>${esc(type)}</option>`).join("")}</select><select id="health-severity"><option value="">All severity</option><option>error</option><option>warning</option><option>info</option></select>`;
  const render=()=>{const query=document.getElementById("health-search").value.toLowerCase(),type=document.getElementById("health-type").value,severity=document.getElementById("health-severity").value;const rows=INDEX.healthFindings.filter(finding=>(!query||JSON.stringify(finding).toLowerCase().includes(query))&&(!type||finding.type===type)&&(!severity||finding.severity===severity));document.getElementById("health-findings").innerHTML=rows.length?rows.map(finding=>`<details class="finding"><summary><span class="title">${esc(finding.title)}</span><span class="path">${esc(byId.get(finding.documentId)?.collectionPath||finding.documentId)}</span><span class="badge ${esc(finding.severity)}">${esc(finding.severity)}</span></summary><div class="content"><p>${esc(finding.reason)}</p>${evidenceList(finding.evidence)}<button data-health-doc="${finding.documentId}">Open document</button></div></details>`).join(""):`<div class="empty panel">No findings match.</div>`;document.querySelectorAll("[data-health-doc]").forEach(button=>button.onclick=()=>{document.querySelector('[data-view="catalogue"]').click();const card=document.getElementById(`document-${button.dataset.healthDoc}`);if(card){card.open=true;card.scrollIntoView({behavior:"smooth"});}});};
  document.getElementById("health-controls").querySelectorAll("input,select").forEach(control=>control.addEventListener(control.tagName==="INPUT"?"input":"change",render));render();
}

function setupTimeline() {
  document.getElementById("timeline-controls").innerHTML=`<input id="timeline-search" type="text" placeholder="Search timeline"><select id="timeline-type"><option value="">All events</option><option>created</option><option>updated</option></select>`;
  const render=()=>{const query=document.getElementById("timeline-search").value.toLowerCase(),type=document.getElementById("timeline-type").value;const rows=INDEX.timeline.filter(event=>(!query||JSON.stringify(event).toLowerCase().includes(query))&&(!type||event.type===type));document.getElementById("timeline-events").innerHTML=rows.map(event=>`<article class="event"><time>${esc(event.timestamp||"Unknown")}</time><span class="badge">${esc(event.type)}</span><div><strong>${esc(event.title)}</strong><div class="muted">${esc(event.source)} · ${esc(event.confidence)}</div></div></article>`).join("");};
  document.getElementById("timeline-controls").querySelectorAll("input,select").forEach(control=>control.addEventListener(control.tagName==="INPUT"?"input":"change",render));render();
}

function setupProvenance() {
  const input=document.getElementById("provenance-search"),target=document.getElementById("provenance-results");
  const render=()=>{const query=input.value.trim().toLowerCase();if(!query){target.innerHTML=`<p class="muted">Search indexed Git paths, titles, authors, commits, or optional local artifacts.</p>`;return;}const rows=INDEX.documents.map(document=>({document,git:INDEX.gitProvenance.documents?.[document.id]})).filter(item=>JSON.stringify(item).toLowerCase().includes(query)).slice(0,40);const artifacts=(INDEX.artifactProvenance.records||[]).filter(record=>JSON.stringify(record).toLowerCase().includes(query)).slice(0,20);target.innerHTML=[...rows.map(({document,git})=>`<div class="provenance-result"><strong>${esc(document.title)}</strong><div class="path">${esc(document.collectionPath)}</div><p>Created: ${esc(git?.creation?.timestamp||"Unknown")} · ${esc(git?.creation?.commit||"No commit")}</p><p>Last update: ${esc(git?.lastMeaningfulUpdate?.timestamp||document.lastMeaningfulUpdate||"Unknown")} · ${esc(git?.lastMeaningfulUpdate?.author||"Unknown author")}</p></div>`),...artifacts.map((record,index)=>`<div class="provenance-result"><strong>${index===0&&["created","generated","modified"].includes(record.action)?"Likely origin":"Artifact evidence"}: ${esc(record.fileName)}</strong><p>${esc(record.sessionName)} · ${esc(record.action)}</p></div>`)].join("")||`<p class="muted">No provenance evidence matched.</p>`;};
  input.addEventListener("input",render);render();
}

setupTabs();
setupCatalogue();
setupHealth();
setupTimeline();
setupProvenance();

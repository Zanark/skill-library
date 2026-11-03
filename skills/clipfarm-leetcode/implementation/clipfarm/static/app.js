const $ = (id) => document.getElementById(id);
const activeStatuses = new Set(["queued", "running"]);
const layoutNames = { auto: "Auto", follow: "Follow", fit: "Full frame", split: "Stacked feeds", manual: "Manual crop", leetcode: "LeetCode" };
const layoutHelp = {
  auto: "Heuristic analysis recommends a composition. Review the result; no detector gets every face, scene, or screen right.",
  follow: "Follows a sustained detected face. Uncertain detection preserves the full frame instead of guessing a crop. Fast motion and cuts need review.",
  fit: "Keeps the entire source visible inside the vertical canvas. A good choice for slides, demonstrations, and screen recordings.",
  split: "Stacks a face feed above a content feed. Draw both source regions or enter their coordinates to identify the feeds explicitly.",
  manual: "A fixed 9:16 crop around your focal point. Place the point on the source, or use the horizontal and vertical sliders.",
  leetcode: "Avatar above a code-only region; boxed captions below. Draw both regions explicitly. Lower captions follow your reference, not the generic safe guides. Multi-part editorial workflows run through the CLI.",
};
const defaultSafe = { top: 14, bottom: 35, left: 6, right: 14, enabled: true };
const state = {
  health: null, projects: [], project: null, clipId: null, dirty: false, invalid: new Map(), invalidValues: new Map(),
  busy: "", generation: 0, editSerial: 0, jobs: [], polling: false, pollTimer: null,
  pollError: false, selected: new Set(), cueLimit: 100, previewId: null, previewChoice: new Map(),
  loadedSource: null, pendingSeek: null, xhr: null, uploadFile: null, uploadAbort: false,
  refreshNeeded: false, cueRows: [], safe: { ...defaultSafe }, toastTimer: null, cancelling: new Set(),
};

function node(tag, className = "", text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = String(text);
  return element;
}
function button(text, className, handler, label) {
  const element = node("button", className, text);
  element.type = "button";
  if (label) element.setAttribute("aria-label", label);
  element.addEventListener("click", handler);
  return element;
}
function currentClip() { return state.project?.clips.find((clip) => clip.id === state.clipId) || null; }
function uuid() { return crypto.randomUUID().replaceAll("-", ""); }
function clamp(number, low, high) { return Math.max(low, Math.min(high, number)); }
function timecode(seconds, precise = false) {
  if (!Number.isFinite(seconds)) return "00:00";
  const milliseconds = Math.round(Math.max(0, seconds) * 1000);
  const hours = Math.floor(milliseconds / 3600000);
  const minutes = Math.floor(milliseconds / 60000) % 60;
  const secs = Math.floor(milliseconds / 1000) % 60;
  const base = `${hours ? `${String(hours).padStart(2, "0")}:` : ""}${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  return precise ? `${base}.${String(milliseconds % 1000).padStart(3, "0")}` : base;
}
function durationLabel(seconds) {
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  if (seconds >= 60) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${Math.round(seconds * 10) / 10}s`;
}
function parseTime(value) {
  const text = String(value).trim().replace(",", ".");
  if (/^\d+(?:\.\d+)?$/.test(text)) return Number(text);
  const parts = text.split(":");
  if (parts.length < 2 || parts.length > 3 || !parts.every((part, index) => (index === parts.length - 1 ? /^\d{1,2}(?:\.\d+)?$/ : /^\d+$/).test(part))) return NaN;
  if (Number(parts.at(-1)) >= 60 || (parts.length === 3 && Number(parts[1]) >= 60)) return NaN;
  return parts.reduce((total, part) => total * 60 + Number(part), 0);
}
function errorText(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => `${(item.loc || []).filter((part) => part !== "body").join(".")}: ${item.msg || "Invalid value"}`).join("\n");
  return "The local server could not complete this request.";
}
async function api(path, { method = "GET", body, signal } = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method, signal, cache: "no-store",
      headers: { Accept: "application/json", ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Cannot reach the local ClipFarm server. Keep the launcher running, then retry. Your unsaved edits are still here.");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(errorText(data?.detail));
    error.status = response.status;
    throw error;
  }
  if (data === null) throw new Error("The local server returned an unexpected response.");
  return data;
}
function toast(message) {
  clearTimeout(state.toastTimer);
  $("toast").textContent = message;
  $("toast").hidden = false;
  state.toastTimer = setTimeout(() => { $("toast").hidden = true; }, 6500);
}
function showError(error, target) {
  const message = error.status === 409
    ? "This project changed on disk while you were editing. Your unsaved edits have not been overwritten. Copy any edits you need to keep, then reload the saved project and reapply them."
    : error.message || String(error);
  $("error-message").textContent = message;
  $("error-banner").hidden = false;
  const dialogTarget = target || ($("import-dialog").open ? "import-error" : $("transcript-dialog").open ? "transcript-error" : $("suggest-dialog").open ? "suggest-error" : null);
  if (dialogTarget) { $(dialogTarget).textContent = message; $(dialogTarget).hidden = false; }
  if (error.status === 409) showStale("A newer saved revision exists. Reload discards your unsaved edits; copy anything you want to preserve first.");
}
function clearErrors() {
  for (const id of ["error-banner", "import-error", "transcript-error", "suggest-error"]) $(id).hidden = true;
}
function showStale(message) {
  state.refreshNeeded = true;
  $("stale-message").textContent = message;
  $("stale-banner").hidden = false;
}
async function runAction(label, action, errorTarget) {
  if (state.busy) return;
  clearErrors();
  state.busy = label;
  syncControls();
  try { return await action(); }
  catch (error) {
    if (error.name === "AbortError") toast("Upload cancelled. Your existing project was not changed.");
    else showError(error, errorTarget);
  } finally {
    state.busy = "";
    syncControls();
  }
}
function setBusyLabel(label) {
  state.busy = label;
  $("busy-label").textContent = label;
}
function syncControls() {
  const busy = Boolean(state.busy);
  const project = state.project;
  const clip = currentClip();
  document.querySelectorAll("button, input, textarea, select").forEach((element) => { element.disabled = busy; });
  const disable = (id, condition) => { $(id).disabled = busy || condition; };
  $("clip-controls").disabled = busy || !clip;
  $("busy-status").hidden = !busy;
  $("busy-label").textContent = state.busy;
  $("workspace").setAttribute("aria-busy", String(busy));
  disable("save-project", !project || !state.dirty);
  disable("refresh-project", !project);
  for (const id of ["render-preview", "analyze-clip", "export-clip"]) disable(id, !clip || state.health?.ffmpeg === false);
  for (const id of ["add-clip", "open-suggest", "open-transcript", "empty-transcript-import", "add-cue", "source-seek", "draw-mode"]) disable(id, !project);
  for (const id of ["play-source", "back-source", "forward-source", "mute-source"]) disable(id, !project || Boolean($("source-video").error));
  disable("draw-mode", !clip);
  disable("batch-export", !project || state.selected.size === 0 || state.health?.ffmpeg === false);
  disable("transcribe-start", !project || !state.health?.transcription || state.health?.ffmpeg === false || !project.media.has_audio);
  disable("upload-submit", !state.uploadFile);
  disable("transcript-submit", !project);
  disable("suggest-submit", !project?.cues.length);
  disable("transcript-scope", !project?.cues.length);
  $("cancel-upload").disabled = !state.xhr;
  $("error-dismiss").disabled = false;
  document.querySelectorAll(".job-cancel").forEach((element) => { element.disabled = element.dataset.pending === "true"; });
  $("save-state").textContent = state.dirty ? "Unsaved changes" : `Saved · revision ${project?.revision ?? 0}`;
  $("save-state").classList.toggle("dirty", state.dirty);
}
function guardDiscard() {
  return !state.dirty || window.confirm("This project has unsaved clip or transcript edits. Discard those edits and continue?");
}
function markDirty() {
  state.dirty = true;
  state.editSerial += 1;
  $("save-state").textContent = "Unsaved changes";
  $("save-state").classList.add("dirty");
  $("save-project").disabled = Boolean(state.busy);
  renderPreview();
}
function invalidField(key, input, message) {
  if (message) { state.invalid.set(key, message); state.invalidValues.set(key, input.value); }
  else { state.invalid.delete(key); state.invalidValues.delete(key); }
  input.setCustomValidity(message);
  input.setAttribute("aria-invalid", String(Boolean(message)));
}
function clipValidation(clip) {
  if (!clip.title.trim()) return "Give this cut a title.";
  if (!Number.isFinite(clip.start) || !Number.isFinite(clip.end)) return "Use seconds or hh:mm:ss for the in and out points.";
  if (clip.start < 0 || clip.end <= clip.start) return "The out point must be after the in point.";
  if (clip.end > state.project.media.duration + 0.001) return "The cut must end within the source video.";
  if (clip.end - clip.start > 180.001) return "A shared vertical cut can be at most 180 seconds.";
  if (clip.layout === "leetcode" && (!clip.face_region || !clip.content_region)) return "LeetCode needs explicit avatar and code/results regions.";
  return "";
}
function validateDraft() {
  if (!state.project) throw new Error("Open a project first.");
  if (state.invalid.size) throw new Error(`Fix the invalid edit before saving: ${state.invalid.values().next().value}`);
  for (const clip of state.project.clips) {
    const issue = clipValidation(clip);
    if (issue) throw new Error(`${clip.title || "Untitled cut"}: ${issue}`);
  }
  for (const cue of state.project.cues) {
    if (!cue.text.trim() || cue.text.length > 4000 || !Number.isFinite(cue.start) || !Number.isFinite(cue.end) || cue.start < 0 || cue.end <= cue.start || cue.end > state.project.media.duration + 0.1) {
      throw new Error(`Caption at ${timecode(cue.start)} needs nonempty text and valid in/out times within the source.`);
    }
  }
}
async function ensureSaved() {
  validateDraft();
  if (!state.dirty) return;
  const project = state.project;
  const saved = await api(`/projects/${project.id}`, {
    method: "PATCH", body: { revision: project.revision, name: project.name, clips: project.clips, cues: project.cues },
  });
  applyProject(saved);
  await refreshLibrary();
}
function applyProject(project, { selectId, resetSource = false } = {}) {
  const changedProject = state.project?.id !== project.id;
  state.project = project;
  state.dirty = false;
  state.invalid.clear();
  state.invalidValues.clear();
  state.refreshNeeded = false;
  $("stale-banner").hidden = true;
  state.clipId = project.clips.some((clip) => clip.id === (selectId || state.clipId))
    ? selectId || state.clipId : project.clips[0]?.id || null;
  if (changedProject) {
    state.generation += 1;
    state.jobs = [];
    state.selected = new Set();
    state.cueLimit = 100;
    state.previewChoice.clear();
    $("transcript-search").value = "";
    $("transcript-scope").value = "clip";
  }
  state.selected = new Set([...state.selected].filter((id) => project.clips.some((clip) => clip.id === id)));
  renderProject(changedProject || resetSource);
}
function renderLibrary() {
  $("project-list").replaceChildren();
  $("project-count").textContent = state.projects.length;
  $("library-loading").hidden = true;
  $("library-empty").hidden = state.projects.length > 0;
  for (const project of state.projects) {
    const item = button("", `project-card${project.id === state.project?.id ? " active" : ""}`, () => openProject(project.id));
    item.setAttribute("aria-label", `Open ${project.name}`);
    if (project.id === state.project?.id) item.setAttribute("aria-current", "page");
    const thumbnail = node("img", "project-thumb");
    thumbnail.src = `/api/projects/${encodeURIComponent(project.id)}/poster`;
    thumbnail.alt = "";
    thumbnail.loading = "lazy";
    thumbnail.addEventListener("error", () => { thumbnail.hidden = true; }, { once: true });
    const text = node("span", "project-card-text");
    text.append(node("span", "project-card-name", project.name), node("span", "project-card-meta", `${durationLabel(project.media.duration)} · ${project.clip_count} ${project.clip_count === 1 ? "cut" : "cuts"}`));
    item.append(thumbnail, text);
    item.disabled = Boolean(state.busy);
    $("project-list").append(item);
  }
}
async function refreshLibrary() {
  try { state.projects = await api("/projects"); renderLibrary(); }
  catch (error) { $("library-loading").textContent = "Library unavailable. Retry the local connection."; throw error; }
}
async function openProject(id) {
  if (state.busy || id === state.project?.id || !guardDiscard()) return;
  await runAction("Opening source and project…", async () => {
    const project = await api(`/projects/${encodeURIComponent(id)}`);
    applyProject(project);
    startPolling();
  });
}
function renderProject(resetSource = false) {
  const project = state.project;
  if (!project) return;
  $("welcome").hidden = true;
  $("workspace").hidden = false;
  $("studio-navigation").hidden = false;
  $("top-project").textContent = project.name;
  $("project-name").textContent = project.name;
  $("project-meta").textContent = `${durationLabel(project.media.duration)} source · ${project.media.width} × ${project.media.height} · ${Math.round(project.media.fps * 100) / 100} fps${project.media.has_audio ? "" : " · No audio track"}`;
  $("source-dimensions").textContent = `${project.media.width} × ${project.media.height}`;
  if (resetSource || state.loadedSource !== project.id) {
    $("source-video").pause();
    state.loadedSource = project.id;
    state.pendingSeek = 0;
    $("source-video").poster = `/api/projects/${project.id}/poster`;
    $("source-video").src = `/api/projects/${project.id}/source`;
    $("source-stage").style.aspectRatio = `${project.media.width} / ${project.media.height}`;
    $("source-placeholder").hidden = false;
    $("playback-error").hidden = true;
    $("draw-mode").value = "none";
    $("play-source").textContent = "Play";
    $("source-seek").max = project.media.duration;
    $("source-seek").value = "0";
    state.previewId = null;
  }
  renderLibrary();
  renderClips();
  renderInspector();
  renderTranscript();
  renderJobs();
  updatePlayhead();
  syncControls();
}
function selectClip(id, seek = true) {
  if (state.busy || !state.project?.clips.some((clip) => clip.id === id)) return;
  if (state.invalid.size) { showError(new Error("Finish the invalid field before switching cuts. This keeps your unfinished edit from being lost.")); return; }
  state.clipId = id;
  state.cueLimit = 100;
  renderClips();
  renderInspector();
  renderTranscript();
  syncControls();
  if (seek) seekSource(currentClip().start);
}
function renderClips() {
  const clips = state.project?.clips || [];
  const list = $("clip-list");
  const scrollLeft = list.scrollLeft;
  list.replaceChildren();
  $("clip-count").textContent = clips.length;
  $("clips-empty").hidden = clips.length > 0;
  list.hidden = clips.length === 0;
  $("batch-toolbar").hidden = clips.length === 0;
  for (const [index, clip] of clips.entries()) {
    const card = node("article", `clip-card${clip.id === state.clipId ? " active" : ""}`);
    const top = node("div", "clip-card-top");
    const check = node("input", "clip-select");
    check.type = "checkbox";
    check.checked = state.selected.has(clip.id);
    check.setAttribute("aria-label", `Select ${clip.title} for batch export`);
    check.addEventListener("change", () => {
      if (check.checked) state.selected.add(clip.id); else state.selected.delete(clip.id);
      renderBatch();
    });
    top.append(node("span", "clip-index", `CUT ${String(index + 1).padStart(2, "0")}`), check);
    const pick = button("", "clip-pick", () => selectClip(clip.id), `Edit ${clip.title}`);
    pick.setAttribute("aria-pressed", String(clip.id === state.clipId));
    const bottom = node("span", "clip-card-bottom");
    bottom.append(node("span", "", layoutNames[clip.layout]), node("span", "", durationLabel(clip.end - clip.start)));
    pick.append(node("span", "clip-card-title", clip.title || "Untitled cut"), node("span", "clip-card-time", `${timecode(clip.start)} → ${timecode(clip.end)}`), bottom);
    card.append(top, pick);
    list.append(card);
  }
  list.scrollLeft = scrollLeft;
  renderBatch();
}
function renderBatch() {
  const total = state.project?.clips.length || 0;
  $("select-all-clips").checked = total > 0 && state.selected.size === total;
  $("select-all-clips").indeterminate = state.selected.size > 0 && state.selected.size < total;
  $("batch-count").textContent = `${state.selected.size} selected`;
  $("batch-export").textContent = state.selected.size ? `Export selected (${state.selected.size})` : "Export selected";
  $("batch-export").disabled = Boolean(state.busy) || state.selected.size === 0 || state.health?.ffmpeg === false;
}
function renderInspector() {
  const clip = currentClip();
  $("inspector-empty").hidden = Boolean(clip);
  $("clip-controls").hidden = !clip;
  if (clip) {
    $("clip-title").value = clip.title;
    $("clip-start").value = timecode(clip.start, true);
    $("clip-end").value = timecode(clip.end, true);
    for (const id of ["clip-title", "clip-start", "clip-end"]) { $(id).setCustomValidity(""); $(id).setAttribute("aria-invalid", "false"); }
    $("clip-layout").value = clip.layout;
    $("focus-x").value = clip.focus_x;
    $("focus-y").value = clip.focus_y;
    $("clip-captions").checked = clip.captions;
    $("caption-style").value = clip.caption_style;
    $("clip-reason").textContent = clip.reason;
    $("clip-reason").hidden = !clip.reason;
    for (const editor of document.querySelectorAll(".region-editor")) {
      const region = clip[editor.dataset.region];
      for (const input of editor.querySelectorAll("input")) {
        input.value = region ? Math.round(region[input.dataset.axis] * 1000) / 1000 : "";
        input.setCustomValidity("");
        input.setAttribute("aria-invalid", "false");
      }
    }
    $("region-validation").textContent = "";
    $("regions-details").open = ["split", "leetcode"].includes(clip.layout) || Boolean(clip.face_region || clip.content_region);
  }
  updateInspectorFeedback();
  renderPreview();
  renderSourceOverlay();
}
function updateInspectorFeedback() {
  const clip = currentClip();
  if (!clip) return;
  const leetcode = clip.layout === "leetcode";
  $("subtitle-y").min = leetcode ? "0.77" : "0.2";
  $("subtitle-y").max = leetcode ? "0.88" : "0.63";
  $("subtitle-y").value = clip.subtitle_y;
  $("results-zoom-control").hidden = !leetcode;
  $("results-zoom").checked = Boolean(clip.results_zoom);
  $("focus-x-value").textContent = `${Math.round(clip.focus_x * 100)}%`;
  $("focus-y-value").textContent = `${Math.round(clip.focus_y * 100)}%`;
  $("subtitle-y-value").textContent = `${Math.round(clip.subtitle_y * 100)}%`;
  $("layout-help").textContent = layoutHelp[clip.layout];
  $("clip-validation").textContent = clipValidation(clip);
  $("analysis-result").hidden = !clip.analysis;
  if (clip.analysis) {
    $("analysis-label").textContent = `${layoutNames[clip.analysis.layout]} · ${Math.round(clip.analysis.confidence * 100)}% heuristic confidence`;
    $("analysis-message").textContent = clip.analysis.message;
    $("analysis-warnings").replaceChildren(...clip.analysis.warnings.map((warning) => node("li", "", warning)));
  }
  $("clip-range-highlight").hidden = false;
  $("clip-range-highlight").style.left = `${clamp(clip.start / state.project.media.duration, 0, 1) * 100}%`;
  $("clip-range-highlight").style.width = `${clamp((clip.end - clip.start) / state.project.media.duration, 0, 1) * 100}%`;
}
function renderSourceOverlay() {
  const clip = currentClip();
  const mode = $("draw-mode").value;
  $("source-overlay").classList.toggle("drawing", Boolean(clip) && mode !== "none" && !state.busy);
  const modeHelp = {
    none: "Choose a source tool to place a focal point or draw feed regions. Coordinates in the inspector work without browser playback.",
    focus: "Click on the source to anchor a fixed manual crop. Fine-tune with the focus sliders in the inspector.",
    face: "Drag a rectangle around the face feed. For stacked feeds, define the content region separately.",
    content: "Drag a rectangle around the screen or content feed. Choose Stack in the inspector to combine it with the face feed.",
  };
  $("draw-help").textContent = clip ? modeHelp[mode] : "Create or select a cut to frame it. You can add a manual cut at the current playhead.";
  for (const [key, id] of [["face_region", "face-box"], ["content_region", "content-box"]]) {
    const region = clip?.[key];
    $(id).hidden = !region;
    if (region) positionRegion($(id), region);
  }
  $("focus-marker").hidden = !clip || (mode !== "focus" && clip.layout !== "manual");
  if (clip) {
    $("focus-marker").style.left = `${clip.focus_x * 100}%`;
    $("focus-marker").style.top = `${clip.focus_y * 100}%`;
  } else $("clip-range-highlight").hidden = true;
}
function positionRegion(element, region) {
  Object.assign(element.style, { left: `${region.x * 100}%`, top: `${region.y * 100}%`, width: `${region.w * 100}%`, height: `${region.h * 100}%` });
}
function latestRender() {
  const renders = state.jobs.filter((job) => job.clip_id === state.clipId && job.status === "completed" && job.output && ["preview", "export"].includes(job.kind));
  return renders.find((job) => job.id === state.previewChoice.get(state.clipId)) || renders[0] || null;
}
function renderPreview() {
  const clip = currentClip();
  const job = clip ? latestRender() : null;
  const video = $("preview-video");
  if (job?.id !== state.previewId) {
    video.pause();
    if (job) {
      video.src = `/api/jobs/${job.id}/video`;
    } else {
      video.removeAttribute("src");
      video.load();
    }
    state.previewId = job?.id || null;
  }
  video.hidden = !job;
  $("composition-guide").hidden = Boolean(job);
  $("preview-download").hidden = !job;
  if (job) {
    $("preview-download").href = `/api/jobs/${job.id}/video?download=true`;
    $("preview-download").setAttribute("download", "");
    const outdated = job.revision < state.project.revision || state.dirty;
    $("preview-status").textContent = state.dirty ? "Unsaved edits · previous render" : outdated ? `Older render · revision ${job.revision}` : `Rendered · revision ${job.revision}`;
    $("preview-status").classList.toggle("outdated", outdated);
  } else {
    $("preview-status").textContent = clip ? "Composition guide · render to review" : "Select a cut to get started";
    $("preview-status").classList.remove("outdated");
  }
  const layout = clip?.layout === "auto" ? clip.analysis?.layout || "auto" : clip?.layout || "auto";
  $("layout-diagram").dataset.layout = layout;
  $("layout-diagram").dataset.resultsZoom = String(Boolean(clip?.results_zoom));
  $("diagram-primary-label").textContent = layout === "fit" ? "FULL SOURCE" : layout === "leetcode" ? "AVATAR" : layout === "split" ? "FACE FEED" : "SUBJECT";
  $("diagram-secondary-label").textContent = layout === "leetcode" && clip?.results_zoom ? "RESULTS FOCUS" : "CONTENT";
  $("caption-sample").style.top = `${(clip?.subtitle_y ?? 0.6) * 100}%`;
  $("caption-sample").hidden = clip ? !clip.captions : false;
  $("caption-sample").classList.toggle("punchy", clip?.caption_style === "punchy");
  $("caption-sample").classList.toggle("leetcode", layout === "leetcode");
}
function renderTranscript() {
  const project = state.project;
  if (!project) return;
  const clip = currentClip();
  const search = $("transcript-search").value.trim().toLocaleLowerCase();
  const all = $("transcript-scope").value === "all" || !clip || Boolean(search);
  const cues = project.cues.filter((cue) => (all || (cue.end > clip.start && cue.start < clip.end)) && (!search || cue.text.toLocaleLowerCase().includes(search))).sort((a, b) => a.start - b.start || a.end - b.end);
  $("cue-count").textContent = project.cues.length;
  $("transcript-empty").hidden = project.cues.length > 0;
  const note = project.transcript_note ? `${project.transcript_note} ` : "";
  $("transcript-note").textContent = project.cues.length
    ? `${note}${search ? "Searching the full source. " : ""}${cues.length} ${cues.length === 1 ? "caption" : "captions"} ${all ? "in view" : "overlapping this cut"}. Times are source-relative; edits affect every cut using these words.`
    : note;
  $("transcript-list").replaceChildren();
  state.cueRows = [];
  if (project.cues.length && !cues.length) {
    $("transcript-list").append(node("p", "section-empty small muted", search ? "No captions match your search." : "No captions overlap this cut. View the full source or add a caption."));
  }
  for (const cue of cues.slice(0, state.cueLimit)) $("transcript-list").append(renderCue(cue));
  $("transcript-more").hidden = cues.length <= state.cueLimit;
  $("transcript-more").textContent = `Show more captions (${Math.min(state.cueLimit, cues.length)} of ${cues.length})`;
  updateCueHighlight();
}
function renderCue(cue) {
  const row = node("article", "cue-row");
  const times = node("div", "cue-times");
  const seek = button("Seek ↗", "text-button", () => seekSource(cue.start), `Seek to caption at ${timecode(cue.start)}`);
  times.append(seek);
  const timeInputs = {};
  for (const field of ["start", "end"]) {
    const input = node("input");
    input.type = "text";
    input.inputMode = "decimal";
    const key = `cue:${cue.id}:${field}`;
    input.value = state.invalidValues.get(key) ?? timecode(cue[field], true);
    input.setCustomValidity(state.invalid.get(key) || "");
    input.setAttribute("aria-invalid", String(state.invalid.has(key)));
    input.spellcheck = false;
    input.setAttribute("aria-label", `Caption ${field} time at ${timecode(cue.start)}`);
    timeInputs[field] = input;
    input.addEventListener("input", () => {
      const parsed = parseTime(input.value);
      invalidField(`cue:${cue.id}:${field}`, input, Number.isFinite(parsed) && parsed >= 0 ? "" : "Enter a valid caption time in seconds or hh:mm:ss.");
      if (Number.isFinite(parsed) && parsed >= 0) cue[field] = parsed;
      message.textContent = cue.end <= cue.start ? "Caption end must be after its start." : "";
      markDirty();
    });
    times.append(input);
  }
  const text = node("textarea", "cue-text");
  text.value = cue.text;
  text.rows = 2;
  text.maxLength = 4000;
  text.setAttribute("aria-label", `Caption text at ${timecode(cue.start)}`);
  text.setCustomValidity(state.invalid.get(`cue:${cue.id}:text`) || "");
  text.setAttribute("aria-invalid", String(state.invalid.has(`cue:${cue.id}:text`)));
  text.addEventListener("input", () => {
    cue.text = text.value;
    invalidField(`cue:${cue.id}:text`, text, text.value.trim() ? "" : "Caption text cannot be empty. Remove the caption if it is not needed.");
    markDirty();
  });
  const remove = button("×", "icon-button cue-delete", () => {
    if (state.busy) return;
    if (!window.confirm("Remove this caption from the full transcript? This affects every cut that uses it.")) return;
    state.project.cues = state.project.cues.filter((entry) => entry.id !== cue.id);
    for (const key of [...state.invalid.keys()]) if (key.startsWith(`cue:${cue.id}:`)) { state.invalid.delete(key); state.invalidValues.delete(key); }
    markDirty();
    renderTranscript();
    syncControls();
  }, `Remove caption at ${timecode(cue.start)}`);
  const message = node("span", "cue-error");
  message.setAttribute("role", "status");
  row.append(times, text, remove, message);
  state.cueRows.push({ row, cue });
  return row;
}
function updateCueHighlight() {
  const time = $("source-video").currentTime || 0;
  for (const { row, cue } of state.cueRows) row.classList.toggle("current", time >= cue.start && time < cue.end);
}
function seekSource(time) {
  if (!state.project) return;
  const bounded = clamp(time, 0, state.project.media.duration);
  if ($("source-video").readyState >= 1) {
    try { $("source-video").currentTime = bounded; } catch { state.pendingSeek = bounded; }
  } else state.pendingSeek = bounded;
  $("source-seek").value = bounded;
  $("source-time").textContent = `${timecode(bounded)} / ${timecode(state.project.media.duration)}`;
}
function playhead() { return state.pendingSeek ?? $("source-video").currentTime ?? 0; }
function updatePlayhead() {
  if (!state.project) return;
  const time = playhead();
  $("source-time").textContent = `${timecode(time)} / ${timecode(state.project.media.duration)}`;
  if (document.activeElement !== $("source-seek")) $("source-seek").value = time;
  updateCueHighlight();
}
function newClip() {
  if (!state.project || state.busy) return;
  if (state.invalid.size) { showError(new Error("Finish invalid edits before creating another cut.")); return; }
  const duration = state.project.media.duration;
  const start = clamp(playhead(), 0, Math.max(0, duration - 0.1));
  const clip = {
    id: uuid(), title: `Cut ${state.project.clips.length + 1}`, start, end: Math.min(duration, start + 45),
    layout: "auto", focus_x: 0.5, focus_y: 0.5, face_region: null, content_region: null,
    captions: true, caption_style: "clean", subtitle_y: 0.6, analysis: null, reason: "",
  };
  state.project.clips.push(clip);
  state.selected.add(clip.id);
  state.clipId = clip.id;
  markDirty();
  renderClips();
  renderInspector();
  renderTranscript();
  syncControls();
  $("clip-title").focus();
}
function addCue() {
  if (!state.project || state.busy) return;
  if (state.invalid.size) { showError(new Error("Finish invalid captions before adding another.")); return; }
  const clip = currentClip();
  const onlyClip = $("transcript-scope").value === "clip" && clip && !$("transcript-search").value.trim();
  const upper = onlyClip ? clip.end : state.project.media.duration;
  const lower = onlyClip ? clip.start : 0;
  const start = clamp(playhead(), lower, Math.max(lower, upper - 0.05));
  const cue = { id: uuid(), start, end: Math.min(upper, start + 3), text: "Edit this caption" };
  state.project.cues.push(cue);
  $("transcript-search").value = "";
  state.cueLimit = Math.max(state.cueLimit, state.project.cues.length);
  markDirty();
  renderTranscript();
  syncControls();
  const entry = state.cueRows.find((item) => item.cue.id === cue.id);
  entry?.row.scrollIntoView({ block: "nearest" });
  entry?.row.querySelector("textarea").focus();
  entry?.row.querySelector("textarea").select();
}
function renderJobs() {
  const focusedAction = document.activeElement?.closest("#job-list") ? document.activeElement.dataset.jobAction : null;
  const previousScroll = $("job-list").scrollTop;
  $("job-list").replaceChildren();
  $("job-count").textContent = state.jobs.length;
  $("jobs-empty").hidden = state.jobs.length > 0;
  const active = state.jobs.filter((job) => activeStatuses.has(job.status)).length;
  $("jobs-summary").textContent = active ? `${active} IN PROGRESS` : "LOCAL PROCESSING";
  const titles = { analyze: "Framing analysis", preview: "Preview", export: "Export", transcribe: "Transcription" };
  for (const job of state.jobs.slice(0, 40)) {
    const row = node("article", "job-row");
    const heading = node("div", "job-heading");
    const name = state.project?.clips.find((clip) => clip.id === job.clip_id)?.title;
    const titleWrap = node("div");
    titleWrap.append(node("div", "job-title", `${titles[job.kind]}${name ? ` · ${name}` : ""}`));
    const date = new Date(job.created_at);
    titleWrap.append(node("div", "job-date", `${Number.isNaN(date.valueOf()) ? "" : date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })} · revision ${job.revision}`));
    heading.append(titleWrap, node("span", `job-status ${job.status}`, job.status));
    row.append(heading, node("p", "job-message", job.message || titles[job.kind]));
    if (activeStatuses.has(job.status)) {
      const progress = node("progress");
      progress.max = 1;
      progress.value = clamp(job.progress || 0, 0, 1);
      progress.setAttribute("aria-label", `${titles[job.kind]} progress`);
      row.append(progress);
    }
    if (job.error) row.append(node("p", "job-error", job.error));
    const footer = node("div", "job-footer");
    if (activeStatuses.has(job.status)) {
      const cancel = button("Cancel job", "text-button job-cancel", async () => {
        if (state.cancelling.has(job.id)) return;
        state.cancelling.add(job.id);
        cancel.dataset.pending = "true";
        cancel.disabled = true;
        const generation = state.generation;
        try {
          const updated = await api(`/jobs/${job.id}/cancel`, { method: "POST" });
          if (generation !== state.generation) return;
          state.jobs = state.jobs.map((entry) => entry.id === job.id ? updated : entry);
          renderJobs();
          toast("Cancellation requested. The worker will stop this job safely.");
        } catch (error) { showError(error); }
        finally {
          state.cancelling.delete(job.id);
          if (generation === state.generation) renderJobs();
        }
      });
      cancel.dataset.jobAction = `cancel:${job.id}`;
      cancel.dataset.pending = String(state.cancelling.has(job.id));
      cancel.disabled = state.cancelling.has(job.id);
      footer.append(cancel);
    }
    if (job.status === "completed" && job.output && ["preview", "export"].includes(job.kind)) {
      if (state.project?.clips.some((clip) => clip.id === job.clip_id)) {
        const review = button("Review render", "text-button", () => {
          if (state.busy || state.invalid.size) {
            if (state.invalid.size) showError(new Error("Finish invalid edits before changing the preview."));
            return;
          }
          state.previewChoice.set(job.clip_id, job.id);
          selectClip(job.clip_id, false);
          $("vertical-stage").scrollIntoView({ block: "center", behavior: "smooth" });
        });
        review.dataset.jobAction = `review:${job.id}`;
        footer.append(review);
      }
      const download = node("a", "text-button", "Download MP4");
      download.href = `/api/jobs/${job.id}/video?download=true`;
      download.setAttribute("download", "");
      download.dataset.jobAction = `video:${job.id}`;
      footer.append(download);
    }
    if (job.status === "completed" && job.output && job.kind === "transcribe") {
      const download = node("a", "text-button", "Download timed transcript");
      download.href = `/api/jobs/${job.id}/transcript`;
      download.setAttribute("download", "");
      download.dataset.jobAction = `transcript:${job.id}`;
      footer.append(download);
    }
    if (job.status === "completed" && job.subtitles) {
      const download = node("a", "text-button", "Download SRT");
      download.href = `/api/jobs/${job.id}/subtitles`;
      download.setAttribute("download", "");
      download.dataset.jobAction = `subtitles:${job.id}`;
      footer.append(download);
    }
    if (["preview", "export"].includes(job.kind) && job.status === "completed" && job.revision < (state.project?.revision ?? 0)) {
      footer.append(node("span", "job-outdated", "Older than the saved project"));
    }
    row.append(footer);
    $("job-list").append(row);
  }
  if (state.jobs.length > 40) $("job-list").append(node("p", "jobs-empty small muted", "Showing the 40 most recent jobs for this source."));
  $("job-list").scrollTop = previousScroll;
  if (focusedAction) [...$("job-list").querySelectorAll("[data-job-action]")].find((element) => element.dataset.jobAction === focusedAction)?.focus({ preventScroll: true });
  renderPreview();
}
function startPolling() {
  clearTimeout(state.pollTimer);
  if (!state.polling) void pollJobs();
}
async function pollJobs() {
  if (state.polling || !state.project) return;
  state.polling = true;
  const generation = state.generation;
  const projectId = state.project.id;
  try {
    const jobs = await api(`/projects/${projectId}/jobs`);
    if (generation !== state.generation) return;
    const old = new Map(state.jobs.map((job) => [job.id, job]));
    const finished = jobs.filter((job) => old.has(job.id) && activeStatuses.has(old.get(job.id).status) && !activeStatuses.has(job.status));
    state.jobs = jobs;
    state.pollError = false;
    renderJobs();
    if (finished.some((job) => job.status === "completed")) await refreshAfterJobs(generation);
    const failed = finished.find((job) => job.status === "failed" || job.status === "interrupted");
    if (failed) toast(`${failed.kind === "transcribe" ? "Transcription" : "A processing job"} did not finish. See the render desk for details.`);
    else if (finished.some((job) => job.status === "completed")) toast("Local processing finished. Review the result in the cutting room.");
  } catch (error) {
    if (generation === state.generation && !state.pollError) { state.pollError = true; showError(error); }
  } finally {
    state.polling = false;
    clearTimeout(state.pollTimer);
    if (state.project) state.pollTimer = setTimeout(pollJobs, state.jobs.some((job) => activeStatuses.has(job.status)) ? 1500 : 5000);
  }
}
async function refreshAfterJobs(generation) {
  if (generation !== state.generation) return;
  if (state.dirty || state.busy) {
    showStale("Background work finished. Your edits are safe, but its analysis or transcript may not be loaded. Reload the saved project when ready; unsaved edits will be discarded.");
    return;
  }
  const serial = state.editSerial;
  const project = await api(`/projects/${state.project.id}`);
  if (generation !== state.generation) return;
  if (state.dirty || state.busy || state.editSerial !== serial) {
    showStale("Background work finished while you were editing. Reload the saved project to review its analysis or transcript after preserving your edits.");
    return;
  }
  applyProject(project);
  await refreshLibrary();
}
async function queueJob(kind, clipId = null, model = null) {
  const project = state.project;
  const job = await api(`/projects/${project.id}/jobs`, { method: "POST", body: { kind, ...(clipId ? { clip_id: clipId } : {}), ...(model ? { model } : {}) } });
  state.jobs = [job, ...state.jobs.filter((item) => item.id !== job.id)];
  if (clipId && ["preview", "export"].includes(kind)) state.previewChoice.delete(clipId);
  renderJobs();
  startPolling();
  return job;
}
async function startClipJob(kind) {
  const clip = currentClip();
  if (!clip) return;
  const labels = { analyze: "Saving edits and queueing framing analysis…", preview: "Saving edits and queueing a preview…", export: "Saving edits and queueing an export…" };
  await runAction(labels[kind], async () => {
    await ensureSaved();
    await queueJob(kind, clip.id);
    toast(`${kind === "analyze" ? "Framing analysis" : kind === "preview" ? "Preview" : "Export"} queued. Progress and cancellation are in the render desk.`);
  });
}
function openDialog(id) {
  if (state.busy) return;
  clearErrors();
  if (id === "transcript-dialog") renderTranscriptionAvailability();
  $(id).showModal();
  syncControls();
}
function importTab(mode) {
  const upload = mode === "upload";
  for (const [name, active] of [["upload", upload], ["path", !upload]]) {
    $(`${name}-tab`).classList.toggle("active", active);
    $(`${name}-tab`).setAttribute("aria-selected", String(active));
    $(`${name}-tab`).tabIndex = active ? 0 : -1;
    $(`${name}-panel`).hidden = !active;
  }
}
function showImportProgress(label, value = null) {
  $("import-progress").hidden = false;
  $("import-progress-label").textContent = label;
  if (value === null) $("upload-progress").removeAttribute("value"); else $("upload-progress").value = value;
}
function uploadFile(file, name) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    state.xhr = xhr;
    state.uploadAbort = false;
    xhr.open("POST", "/api/projects/upload");
    xhr.responseType = "json";
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && event.loaded < event.total) {
        const ratio = event.loaded / event.total;
        showImportProgress(`Copying into the local workspace · ${Math.round(ratio * 100)}%`, ratio);
      } else showImportProgress("Video received. Probing media and preparing the project—large recordings can take a while.");
    });
    xhr.upload.addEventListener("load", () => {
      showImportProgress("Video received. Probing media and preparing the project—large recordings can take a while.");
      $("cancel-upload").hidden = true;
    });
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300 && xhr.response) resolve(xhr.response);
      else {
        const error = new Error(errorText(xhr.response?.detail));
        error.status = xhr.status;
        reject(error);
      }
    });
    xhr.addEventListener("error", () => reject(new Error("The local upload connection was interrupted. Check that the server is running, or use a local path to avoid copying large files.")));
    xhr.addEventListener("abort", () => reject(new DOMException("Upload cancelled", "AbortError")));
    xhr.addEventListener("loadend", () => { state.xhr = null; $("cancel-upload").hidden = true; });
    const form = new FormData();
    form.append("file", file);
    if (name) form.append("name", name);
    $("cancel-upload").hidden = false;
    $("cancel-upload").disabled = false;
    xhr.send(form);
  });
}
function chooseVideo(file) {
  if (!file || state.busy) return;
  state.uploadFile = file;
  const size = file.size / (1024 ** 3);
  $("video-file-name").textContent = `${file.name} · ${size >= 1 ? `${size.toFixed(2)} GB` : `${(file.size / (1024 ** 2)).toFixed(1)} MB`}`;
  syncControls();
}
async function completeImport(project) {
  applyProject(project, { resetSource: true });
  $("import-dialog").close();
  $("import-progress").hidden = true;
  $("import-path").value = "";
  $("import-name").value = "";
  $("video-file").value = "";
  state.uploadFile = null;
  $("video-file-name").textContent = "No file selected";
  await refreshLibrary();
  startPolling();
  toast("Source ready. Add a timed transcript to find moments, or start with a manual cut.");
}
function setupDrop(id, onFile) {
  const zone = $(id);
  for (const type of ["dragenter", "dragover"]) zone.addEventListener(type, (event) => {
    event.preventDefault();
    if (!state.busy) zone.classList.add("dragover");
  });
  for (const type of ["dragleave", "drop"]) zone.addEventListener(type, (event) => {
    event.preventDefault();
    zone.classList.remove("dragover");
  });
  zone.addEventListener("drop", (event) => { if (!state.busy && event.dataTransfer.files.length) onFile(event.dataTransfer.files[0]); });
}
async function chooseTranscript(file) {
  if (!file || state.busy) return;
  try {
    const text = await file.text();
    $("transcript-content").value = text;
    $("transcript-filename").value = file.name;
  } catch { showError(new Error("Could not read that transcript file. Try pasting its timed content instead."), "transcript-error"); }
}
function renderTranscriptionAvailability() {
  const available = Boolean(state.health?.transcription);
  $("transcribe-options").hidden = !available;
  const text = $("transcribe-availability");
  text.replaceChildren();
  if (!state.health) {
    text.textContent = "Connect to the local engine to check whether optional transcription is installed.";
  } else if (!available) {
    text.append(document.createTextNode("Optional transcription is not installed. Restart with "));
    text.append(node("code", "", ".\\Start-ClipFarm.ps1 -Transcription"));
    text.append(document.createTextNode(" to install the .[transcribe] extra, or import an existing timed transcript."));
  } else if (state.project && !state.project.media.has_audio) text.textContent = "This source has no audio track. Import an existing transcript or add captions manually.";
  else text.textContent = "On-device speech recognition is available. Review its words and timings before export.";
}
async function checkHealth() {
  try {
    state.health = await api("/health");
    $("health-dot").className = "status-dot ok";
    $("health-label").textContent = "Local engine connected";
    $("version-label").textContent = `v${state.health.version}`;
    $("health-retry").hidden = true;
    $("health-warning").hidden = state.health.ffmpeg !== false;
    $("health-warning").textContent = "FFmpeg is unavailable. Video import, analysis, and rendering need the media engine. Check the local launcher’s setup output, then retry the connection.";
  } catch (error) {
    state.health = null;
    $("health-dot").className = "status-dot offline";
    $("health-label").textContent = "Local engine offline";
    $("health-retry").hidden = false;
    showError(error);
  }
  renderTranscriptionAvailability();
  syncControls();
}
function loadSafeSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem("clipfarm.safe-guide") || "null");
    if (saved && typeof saved === "object") {
      for (const key of ["top", "bottom", "left", "right"]) if (Number.isFinite(saved[key])) state.safe[key] = saved[key];
      if (typeof saved.enabled === "boolean") state.safe.enabled = saved.enabled;
    }
  } catch { /* Private browsing can make local storage unavailable. */ }
  for (const key of ["top", "bottom", "left", "right"]) {
    const input = $(`safe-${key}`);
    state.safe[key] = clamp(state.safe[key], Number(input.min), Number(input.max));
    input.value = state.safe[key];
  }
  if (state.safe.top + state.safe.bottom >= 95) {
    state.safe.bottom = 94 - state.safe.top;
    $("safe-bottom").value = state.safe.bottom;
  }
  $("safe-toggle").checked = state.safe.enabled;
  applySafeSettings();
}
function applySafeSettings() {
  for (const key of ["top", "bottom", "left", "right"]) document.documentElement.style.setProperty(`--safe-${key}`, `${state.safe[key]}%`);
  $("safe-overlay").hidden = !state.safe.enabled;
  try { localStorage.setItem("clipfarm.safe-guide", JSON.stringify(state.safe)); } catch { /* The guide still works without storage. */ }
}
function bindEvents() {
  document.querySelectorAll(".import-launch").forEach((element) => element.addEventListener("click", () => openDialog("import-dialog")));
  document.querySelectorAll(".dialog-close").forEach((element) => element.addEventListener("click", () => { if (!state.busy) element.closest("dialog").close(); }));
  document.querySelectorAll("dialog").forEach((dialog) => dialog.addEventListener("cancel", (event) => { if (state.busy) event.preventDefault(); }));
  $("error-dismiss").addEventListener("click", () => { $("error-banner").hidden = true; });
  $("health-retry").addEventListener("click", () => runAction("Reconnecting to the local engine…", async () => { await checkHealth(); await refreshLibrary(); }));
  for (const id of ["refresh-project", "stale-reload"]) $(id).addEventListener("click", () => {
    if (!state.project || !guardDiscard()) return;
    void runAction("Reloading the saved project…", async () => { applyProject(await api(`/projects/${state.project.id}`)); await refreshLibrary(); startPolling(); });
  });
  $("save-project").addEventListener("click", () => runAction("Saving your cuts and transcript…", async () => { await ensureSaved(); toast("Changes saved locally."); }));
  $("upload-tab").addEventListener("click", () => importTab("upload"));
  $("path-tab").addEventListener("click", () => importTab("path"));
  for (const id of ["upload-tab", "path-tab"]) $(id).addEventListener("keydown", (event) => {
    if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      const target = event.key === "Home" ? "upload" : event.key === "End" ? "path" : id === "upload-tab" ? "path" : "upload";
      importTab(target);
      $(`${target}-tab`).focus();
    }
  });
  $("video-file").addEventListener("change", (event) => chooseVideo(event.target.files[0]));
  setupDrop("video-drop", chooseVideo);
  $("upload-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!state.uploadFile || !guardDiscard()) return;
    void runAction("Importing video. Large files and media probing can take time…", async () => {
      showImportProgress("Copying this video into the local workspace…", 0);
      try { await completeImport(await uploadFile(state.uploadFile, $("import-name").value.trim())); }
      finally { $("import-progress").hidden = true; }
    }, "import-error");
  });
  $("path-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!guardDiscard()) return;
    void runAction("Opening the local video and probing its media streams…", async () => {
      showImportProgress("Probing the original file. Long recordings and slower disks can take a while.");
      $("cancel-upload").hidden = true;
      try {
        const name = $("import-name").value.trim();
        await completeImport(await api("/projects/import", { method: "POST", body: { path: $("import-path").value.trim(), ...(name ? { name } : {}) } }));
      } finally { $("import-progress").hidden = true; }
    }, "import-error");
  });
  $("cancel-upload").addEventListener("click", () => state.xhr?.abort());
  for (const id of ["open-transcript", "empty-transcript-import"]) $(id).addEventListener("click", () => openDialog("transcript-dialog"));
  $("transcript-file").addEventListener("change", (event) => chooseTranscript(event.target.files[0]));
  setupDrop("transcript-drop", chooseTranscript);
  $("transcript-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!state.project) return;
    if (state.project.cues.length && !window.confirm("Replace the entire transcript? Existing shared captions will be replaced after current edits are saved.")) return;
    void runAction("Saving edits and importing the timed transcript…", async () => {
      const content = $("transcript-content").value;
      const firstLine = content.split(/\r?\n/).find((line) => line.trim() && !line.trimStart().startsWith("#")) || "";
      const inferred = /^[\[{]/.test(content.trimStart()) ? "transcript.json"
        : content.trimStart().startsWith("WEBVTT") ? "transcript.vtt"
        : /^\s*(?:\d+:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?(?:\s|$)/.test(firstLine) && !content.includes("-->")
          ? "transcript.txt" : "transcript.srt";
      const filename = $("transcript-filename").value.trim() || inferred;
      await ensureSaved();
      const project = await api(`/projects/${state.project.id}/transcript`, { method: "POST", body: { filename, content } });
      applyProject(project);
      $("transcript-dialog").close();
      $("transcript-content").value = "";
      $("transcript-filename").value = "";
      $("transcript-file").value = "";
      await refreshLibrary();
      toast(`${project.cues.length} timed captions imported. Find moments to suggest your first cuts.`);
    }, "transcript-error");
  });
  $("transcribe-start").addEventListener("click", () => {
    if (!window.confirm("Start local transcription? The selected model may download on first use. Your audio stays local. This replaces existing captions, and long recordings may take considerable time.")) return;
    void runAction("Saving edits and queueing on-device transcription…", async () => {
      await ensureSaved();
      await queueJob("transcribe", null, $("transcribe-model").value);
      $("transcript-dialog").close();
      toast("Transcription queued. Follow model preparation and processing in the render desk.");
    }, "transcript-error");
  });
  $("open-suggest").addEventListener("click", () => {
    if (!state.project?.cues.length) { openDialog("transcript-dialog"); return; }
    openDialog("suggest-dialog");
  });
  $("suggest-form").addEventListener("submit", (event) => {
    event.preventDefault();
    void runAction("Reading the transcript and finding possible cuts…", async () => {
      const min = Number($("suggest-min").value);
      const max = Number($("suggest-max").value);
      if (max < min) throw new Error("Maximum duration must be at least the minimum duration.");
      const count = Number($("suggest-count").value);
      await ensureSaved();
      const previous = new Set(state.project.clips.map((clip) => clip.id));
      const project = await api(`/projects/${state.project.id}/suggest`, { method: "POST", body: { min_duration: min, max_duration: max, count, keywords: $("suggest-keywords").value.trim() } });
      const added = project.clips.filter((clip) => !previous.has(clip.id));
      applyProject(project, { selectId: added[0]?.id });
      for (const clip of added) state.selected.add(clip.id);
      renderClips();
      $("suggest-dialog").close();
      await refreshLibrary();
      toast(added.length ? `${added.length} suggested cuts added. Review their context, framing, and captions.` : "No new cuts met those settings. Try a shorter minimum duration or different keywords.");
    }, "suggest-error");
  });
  $("add-clip").addEventListener("click", newClip);
  $("delete-clip").addEventListener("click", () => {
    const clip = currentClip();
    if (!clip || !window.confirm(`Remove “${clip.title}” from this project? Existing rendered files are kept. Save changes to confirm removal.`)) return;
    state.project.clips = state.project.clips.filter((item) => item.id !== clip.id);
    state.selected.delete(clip.id);
    for (const key of [...state.invalid.keys()]) if (key.startsWith(`clip:${clip.id}:`) || key.startsWith(`region:${clip.id}:`)) { state.invalid.delete(key); state.invalidValues.delete(key); }
    state.clipId = state.project.clips[0]?.id || null;
    markDirty(); renderClips(); renderInspector(); renderTranscript(); syncControls();
  });
  $("select-all-clips").addEventListener("change", (event) => {
    state.selected = event.target.checked ? new Set(state.project.clips.map((clip) => clip.id)) : new Set();
    renderClips();
  });
  $("batch-export").addEventListener("click", () => {
    const ids = [...state.selected];
    if (!ids.length || !window.confirm(`Save all clip and transcript edits, then queue ${ids.length} exports? Captions are shared across cuts. Jobs are submitted sequentially, and each finished MP4/SRT can be downloaded from the render desk.`)) return;
    void runAction("Saving before batch export…", async () => {
      await ensureSaved();
      let queued = 0;
      try {
        for (const id of ids) {
          setBusyLabel(`Queueing export ${queued + 1} of ${ids.length}…`);
          await queueJob("export", id);
          queued += 1;
        }
      } catch (error) {
        throw new Error(`${queued} of ${ids.length} exports were queued before an error. Existing jobs continue; do not resubmit them accidentally. ${error.message}`);
      }
      toast(`${queued} exports queued. Download each finished file from the render desk.`);
    });
  });
  $("render-preview").addEventListener("click", () => startClipJob("preview"));
  $("analyze-clip").addEventListener("click", () => startClipJob("analyze"));
  $("export-clip").addEventListener("click", () => startClipJob("export"));
  $("clip-title").addEventListener("input", (event) => {
    const clip = currentClip(); if (!clip) return;
    clip.title = event.target.value;
    invalidField(`clip:${clip.id}:title`, event.target, clip.title.trim() ? "" : "Give this cut a title.");
    markDirty(); renderClips(); updateInspectorFeedback();
  });
  for (const field of ["start", "end"]) $(`clip-${field}`).addEventListener("input", (event) => {
    const clip = currentClip(); if (!clip) return;
    const number = parseTime(event.target.value);
    invalidField(`clip:${clip.id}:${field}`, event.target, Number.isFinite(number) && number >= 0 ? "" : "Use seconds or hh:mm:ss for the cut’s in and out points.");
    if (Number.isFinite(number) && number >= 0) clip[field] = number;
    clip.analysis = null;
    markDirty(); renderClips(); updateInspectorFeedback();
  });
  for (const id of ["clip-start", "clip-end"]) $(id).addEventListener("change", renderTranscript);
  for (const [id, field] of [["set-in", "start"], ["set-out", "end"]]) $(id).addEventListener("click", () => {
    const clip = currentClip(); if (!clip) return;
    clip[field] = playhead();
    clip.analysis = null;
    const input = $(`clip-${field}`);
    input.value = timecode(clip[field], true);
    invalidField(`clip:${clip.id}:${field}`, input, "");
    markDirty(); renderClips(); updateInspectorFeedback(); renderTranscript();
  });
  $("clip-layout").addEventListener("change", (event) => {
    const clip = currentClip(); if (!clip) return;
    clip.layout = event.target.value; clip.analysis = null;
    if (clip.layout === "leetcode") {
      if (clip.subtitle_y < 0.77 || clip.subtitle_y > 0.88) clip.subtitle_y = 0.82;
    } else {
      if (clip.subtitle_y > 0.63) clip.subtitle_y = 0.6;
      clip.results_zoom = false;
    }
    markDirty(); renderClips(); updateInspectorFeedback(); renderSourceOverlay();
    if (["split", "leetcode"].includes(clip.layout)) $("regions-details").open = true;
  });
  $("results-zoom").addEventListener("change", (event) => {
    const clip = currentClip();
    if (clip) { clip.results_zoom = event.target.checked; markDirty(); }
  });
  for (const [id, field] of [["focus-x", "focus_x"], ["focus-y", "focus_y"], ["subtitle-y", "subtitle_y"]]) $(id).addEventListener("input", (event) => {
    const clip = currentClip(); if (!clip) return;
    clip[field] = Number(event.target.value);
    if (field !== "subtitle_y") clip.analysis = null;
    markDirty(); updateInspectorFeedback(); renderSourceOverlay();
  });
  $("clip-captions").addEventListener("change", (event) => { const clip = currentClip(); if (clip) { clip.captions = event.target.checked; markDirty(); } });
  $("caption-style").addEventListener("change", (event) => { const clip = currentClip(); if (clip) { clip.caption_style = event.target.value; markDirty(); } });
  for (const editor of document.querySelectorAll(".region-editor")) {
    const field = editor.dataset.region;
    for (const input of editor.querySelectorAll("input")) input.addEventListener("input", () => {
      const clip = currentClip(); if (!clip) return;
      const inputs = [...editor.querySelectorAll("input")];
      const empty = inputs.every((element) => element.value.trim() === "");
      const region = Object.fromEntries(inputs.map((element) => [element.dataset.axis, Number(element.value)]));
      const valid = empty || (inputs.every((element) => element.value.trim() !== "" && Number.isFinite(Number(element.value))) && region.x >= 0 && region.y >= 0 && region.w > 0 && region.h > 0 && region.x + region.w <= 1.000001 && region.y + region.h <= 1.000001);
      const message = valid ? "" : "Fill all four region values. X + W and Y + H must fit between 0 and 1; width and height must be positive.";
      for (const element of inputs) { element.setCustomValidity(message); element.setAttribute("aria-invalid", String(!valid)); }
      if (valid) {
        state.invalid.delete(`region:${clip.id}:${field}`);
        clip[field] = empty ? null : region;
        clip.analysis = null;
      } else state.invalid.set(`region:${clip.id}:${field}`, message);
      $("region-validation").textContent = message;
      markDirty(); updateInspectorFeedback(); renderSourceOverlay();
    });
  }
  document.querySelectorAll(".clear-region").forEach((element) => element.addEventListener("click", () => {
    const clip = currentClip(); if (!clip) return;
    const field = element.dataset.region;
    clip[field] = null; clip.analysis = null;
    state.invalid.delete(`region:${clip.id}:${field}`);
    element.closest(".region-editor").querySelectorAll("input").forEach((input) => { input.value = ""; input.setCustomValidity(""); input.setAttribute("aria-invalid", "false"); });
    $("region-validation").textContent = "";
    markDirty(); updateInspectorFeedback(); renderSourceOverlay();
  }));
  $("draw-mode").addEventListener("change", renderSourceOverlay);
  bindSourceDrawing();
  $("transcript-search").addEventListener("input", () => { state.cueLimit = 100; renderTranscript(); });
  $("transcript-scope").addEventListener("change", () => { state.cueLimit = 100; renderTranscript(); });
  $("transcript-more").addEventListener("click", () => { state.cueLimit += 150; renderTranscript(); });
  $("add-cue").addEventListener("click", addCue);
  $("play-source").addEventListener("click", async () => {
    const video = $("source-video");
    if (!video.paused) video.pause();
    else { try { await video.play(); } catch { showError(new Error("This browser could not play the source. You can still set cut times and render a browser-friendly preview.")); } }
  });
  $("back-source").addEventListener("click", () => seekSource(playhead() - 5));
  $("forward-source").addEventListener("click", () => seekSource(playhead() + 5));
  $("source-seek").addEventListener("input", (event) => seekSource(Number(event.target.value)));
  $("mute-source").addEventListener("click", () => {
    const video = $("source-video"); video.muted = !video.muted;
    $("mute-source").textContent = video.muted ? "Unmute" : "Mute";
    $("mute-source").setAttribute("aria-pressed", String(video.muted));
  });
  for (const type of ["play", "pause", "ended"]) $("source-video").addEventListener(type, () => {
    const playing = !$("source-video").paused;
    $("play-source").textContent = playing ? "Pause" : "Play";
    $("play-source").setAttribute("aria-label", playing ? "Pause source" : "Play source");
  });
  $("source-video").addEventListener("timeupdate", updatePlayhead);
  $("source-video").addEventListener("loadedmetadata", () => {
    if (state.pendingSeek !== null) {
      const target = state.pendingSeek; state.pendingSeek = null; seekSource(target);
    }
    $("source-placeholder").hidden = true;
    $("playback-error").hidden = true;
    syncControls();
  });
  $("source-video").addEventListener("error", () => {
    if (!state.project || !$("source-video").getAttribute("src")) return;
    $("source-placeholder").hidden = true;
    $("playback-error").hidden = false;
    syncControls();
  });
  $("preview-video").addEventListener("error", () => {
    if ($("preview-video").getAttribute("src")) showError(new Error("This rendered file could not play in the browser. Try its download link, or render another preview and check the render desk for errors."));
  });
  $("safe-toggle").addEventListener("change", (event) => { state.safe.enabled = event.target.checked; applySafeSettings(); });
  for (const key of ["top", "bottom", "left", "right"]) $(`safe-${key}`).addEventListener("change", (event) => {
    const input = event.target;
    if (!input.value.trim() || !Number.isFinite(Number(input.value))) input.value = state.safe[key];
    state.safe[key] = clamp(Number(input.value), Number(input.min), Number(input.max));
    if (["top", "bottom"].includes(key) && state.safe.top + state.safe.bottom >= 95) state.safe[key] = 94 - state.safe[key === "top" ? "bottom" : "top"];
    input.value = state.safe[key];
    applySafeSettings();
  });
  $("safe-reset").addEventListener("click", () => { state.safe = { ...defaultSafe }; applySafeSettings(); loadSafeSettings(); });
  window.addEventListener("beforeunload", (event) => {
    if (state.dirty || state.busy) { event.preventDefault(); event.returnValue = ""; }
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && state.project) {
      event.preventDefault();
      if (!state.busy && state.dirty && !document.querySelector("dialog[open]")) $("save-project").click();
    }
  });
}
function bindSourceDrawing() {
  const overlay = $("source-overlay");
  let drag = null;
  const point = (event) => {
    const rect = overlay.getBoundingClientRect();
    return { x: clamp((event.clientX - rect.left) / rect.width, 0, 1), y: clamp((event.clientY - rect.top) / rect.height, 0, 1) };
  };
  const rectangle = (start, end) => ({ x: Math.min(start.x, end.x), y: Math.min(start.y, end.y), w: Math.abs(start.x - end.x), h: Math.abs(start.y - end.y) });
  overlay.addEventListener("pointerdown", (event) => {
    const clip = currentClip();
    const mode = $("draw-mode").value;
    if (!clip || state.busy || mode === "none" || event.button !== 0) return;
    if (state.invalid.size) { showError(new Error("Finish invalid fields before using the source framing tool.")); return; }
    event.preventDefault();
    const start = point(event);
    if (mode === "focus") {
      clip.focus_x = start.x; clip.focus_y = start.y; clip.layout = "manual"; clip.analysis = null;
      if (clip.subtitle_y > 0.63) clip.subtitle_y = 0.6;
      clip.results_zoom = false;
      markDirty(); renderInspector(); renderClips();
      return;
    }
    drag = { start, mode, clipId: clip.id, pointerId: event.pointerId };
    overlay.setPointerCapture(event.pointerId);
    $("drawing-box").hidden = false;
    positionRegion($("drawing-box"), rectangle(start, start));
  });
  overlay.addEventListener("pointermove", (event) => {
    if (drag && event.pointerId === drag.pointerId) positionRegion($("drawing-box"), rectangle(drag.start, point(event)));
  });
  overlay.addEventListener("pointerup", (event) => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    const region = rectangle(drag.start, point(event));
    const clip = currentClip();
    if (clip?.id === drag.clipId && region.w > 0.005 && region.h > 0.005) {
      const field = drag.mode === "face" ? "face_region" : "content_region";
      clip[field] = region; clip.analysis = null;
      state.invalid.delete(`region:${clip.id}:${field}`);
      markDirty(); renderInspector();
      $("regions-details").open = true;
    }
    if (overlay.hasPointerCapture(event.pointerId)) overlay.releasePointerCapture(event.pointerId);
    drag = null;
    $("drawing-box").hidden = true;
  });
  overlay.addEventListener("pointercancel", () => { drag = null; $("drawing-box").hidden = true; });
}

bindEvents();
loadSafeSettings();
syncControls();
await checkHealth();
try { await refreshLibrary(); } catch (error) { showError(error); }

"use strict";

(function (root) {
  function createLyricTrack(cues) {
    if (!Array.isArray(cues)) throw new TypeError("Lyric cues must be an array");
    const ids = new Set();
    let previousEnd = 0;
    const rows = cues.map((cue) => {
      if (!cue || typeof cue.id !== "string" || !cue.id.trim() ||
          typeof cue.text !== "string" || !cue.text.trim()) {
        throw new TypeError("Each lyric occurrence needs an id and text");
      }
      if (ids.has(cue.id)) throw new Error("Duplicate lyric occurrence id: " + cue.id);
      if (!Number.isFinite(cue.start) || !Number.isFinite(cue.end) ||
          cue.start < previousEnd || cue.end <= cue.start) {
        throw new RangeError("Lyric intervals must be finite, ordered and non-overlapping");
      }
      ids.add(cue.id);
      previousEnd = cue.end;
      return Object.freeze({id: cue.id, text: cue.text, start: cue.start, end: cue.end});
    });

    return Object.freeze({
      at(time) {
        if (!Number.isFinite(time)) throw new TypeError("Lyric time must be finite");
        let low = 0, high = rows.length;
        while (low < high) {
          const middle = Math.floor((low + high) / 2);
          if (rows[middle].start <= time) low = middle + 1;
          else high = middle;
        }
        const cue = rows[low - 1];
        if (!cue || time >= cue.end) return null;
        return {...cue, progress: Math.max(0, Math.min(1, (time - cue.start) / (cue.end - cue.start)))};
      },
    });
  }

  function drawLyricProgress(ctx, state, rect, colors) {
    const {x, y, width, height} = rect;
    if (![x, y, width, height].every(Number.isFinite) || width <= 0 || height <= 0) {
      throw new RangeError("Lyric progress rectangle must have finite positive dimensions");
    }
    if (state !== null && (!Number.isFinite(state.progress) || state.progress < 0 || state.progress > 1)) {
      throw new RangeError("Lyric progress must be between zero and one");
    }
    ctx.save();
    try {
      ctx.fillStyle = colors.track;
      ctx.fillRect(x, y, width, height);
      if (state !== null) {
        ctx.fillStyle = colors.fill;
        ctx.fillRect(x, y, width * state.progress, height);
      }
    } finally {
      ctx.restore();
    }
  }

  const api = Object.freeze({createLyricTrack, drawLyricProgress});
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ClipFarmLyricWindow = api;
})(globalThis);

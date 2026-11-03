# Changelog

## 0.1.0 - 2026-09-22

Initial packaged release of the local-first ClipFarm studio and reviewed
LeetCode editorial workflow.

### Included

- Local FastAPI/SQLite studio with transcript import, caption editing, framing
  controls, previews, cancellable rendering and human-readable export folders.
- Captioned 1080x1920 vertical clips with explicit avatar/content regions,
  animated result focus, dimmed surroundings and full-title thumbnails.
- Explicit camera-free vertical composition and content thumbnails. Camera-required
  defaults and existing camera-present signatures remain unchanged.
- Local source transcription with granular timestamps and resumable chunks;
  supplied SRT, WebVTT, timed JSON and timestamped TXT remain supported.
- Opt-in horizontal complete-solve videos that preserve the native layout,
  meaningful silent work and reviewed bottom caption space, without a
  three-minute output limit.
- Numbered Consolas covers with a large green circular Big-O, optional
  lime-yellow algorithm/data-structure labels exactly 3px smaller than the title,
  image-only artwork, a one-second cover hold and a four-second opening dissolve.
- Fingerprinted artwork, complexity evidence and image-rights attribution;
  immutable drafts, source maps, independent output transcription and explicit
  editorial approval before local publication.
- Offline galleries with video, subtitle and thumbnail downloads, documented
  review contracts and an installable Copilot LeetCode skill.

### Requirements and boundaries

- Python 3.11 or newer. Windows is the documented launcher environment.
  Horizontal covers require a locally installed genuine Consolas font.
- Optional speech/OCR models download on first use; inference stays local.
  The invoking editor performs semantic selection and review, not a hidden LLM API.
- No automatic social uploads, added trending music, Docker implementation or
  System Design workflow. These remain separate future work.
- Release packages contain tool source, not private recordings, transcripts,
  generated clips, context stores, model weights or proprietary fonts.

"""Copy-ready social captions and thumbnail descriptions, separate from spoken captions."""

from __future__ import annotations

import hashlib
import html
import re
from collections.abc import Sequence
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .models import Model

POSTING_FILE = "posting.json"
MAX_CAPTION_CHARACTERS = 2200
MAX_CAPTION_PASTE_CHARACTERS = 450
MAX_CAPTION_HASHTAGS = 5
_HASHTAG = re.compile(r"(?<![\w/#])#\w+", re.UNICODE)
_HASHTAG_SPACING = re.compile(rf"({_HASHTAG.pattern})\s+(?={_HASHTAG.pattern})")


def _check_caption_length(text: str) -> str:
    if len(text) > MAX_CAPTION_CHARACTERS:
        raise ValueError(
            f"Posting captions must be at most {MAX_CAPTION_CHARACTERS} Unicode code points "
            "including prose, whitespace and hashtags; shorten the authored text explicitly."
        )
    return text


def caption_paste_length(text: str) -> int:
    """Conservative clipboard budget: UTF-16 units with Windows CRLF line breaks."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return len(normalized.encode("utf-16-le")) // 2 + normalized.count("\n")


def _check_caption_paste_length(text: str, *, limit: int = MAX_CAPTION_PASTE_CHARACTERS) -> str:
    if caption_paste_length(text) > limit:
        raise ValueError(
            f"Posting captions must fit the {limit}-character safe-copy budget "
            "(UTF-16 units including Windows line breaks); shorten the authored text explicitly."
        )
    return text


def _space_separate_hashtags(text: str) -> str:
    return _HASHTAG_SPACING.sub(r"\1 ", text)


def caption_hashtag_count(text: str) -> int:
    return len(_HASHTAG.findall(text))


def _check_caption_hashtags(text: str, *, limit: int = MAX_CAPTION_HASHTAGS) -> str:
    if caption_hashtag_count(text) > limit:
        raise ValueError(
            f"Posting captions must contain at most {limit} hashtags, including authored seed tags; "
            "revise the authored tags explicitly instead of dropping prose."
        )
    return text


class PostingText(Model):
    caption: str = Field(min_length=1, max_length=MAX_CAPTION_CHARACTERS)
    alt_text: str = Field(min_length=1, max_length=4000)

    @field_validator("caption", "alt_text")
    @classmethod
    def plain_text(cls, text: str) -> str:
        text = text.strip()
        if not text or any(ord(char) < 32 and char not in "\n\r\t" for char in text):
            raise ValueError("Posting text must be nonblank readable text without control characters.")
        return text

    @field_validator("caption")
    @classmethod
    def lowercase_hashtags(cls, text: str) -> str:
        return _check_caption_length(_HASHTAG.sub(lambda match: match.group().lower(), text))


class PostingRecord(PostingText):
    schema_version: Literal[1, 2, 3, 4] = 4
    caption_paste_limit: int = Field(default=MAX_CAPTION_PASTE_CHARACTERS, ge=1,
                                    le=MAX_CAPTION_CHARACTERS, strict=True)
    caption_hashtag_limit: int = Field(default=MAX_CAPTION_HASHTAGS, ge=0,
                                      le=MAX_CAPTION_CHARACTERS, strict=True)
    video_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    thumbnail_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def safe_copy_budget(self) -> PostingRecord:
        if self.schema_version == 2:
            _check_caption_paste_length(self.caption, limit=1700)
        elif self.schema_version in (3, 4):
            self.caption = _space_separate_hashtags(self.caption)
            _check_caption_paste_length(self.caption, limit=self.caption_paste_limit)
            if self.schema_version == 4:
                _check_caption_hashtags(self.caption, limit=self.caption_hashtag_limit)
        return self


def compose_caption(caption: str, candidates: Sequence[str]) -> str:
    """Append up to five total hashtags from an editorially ordered curated pool.

    The caller is responsible for relevance; this does not discover tags or promise
    reach. Candidates must include ``#``, contain a letter, and otherwise use only
    Unicode alphanumerics/underscores, remaining valid after lowercasing. All are
    validated, even when the budget is exhausted. Hashtags already in the caption
    are skipped by case-folded identity; existing repetitions are retained. Pool
    duplicates use their shortest lowercase spelling (ties keep the first), with
    the identity's relevance position fixed by its first occurrence.

    Prefer relevance order, not the shortest generic tags or maximum count.
    Existing tag occurrences consume slots, including repetitions; excess authored
    tags fail explicitly. Nonfitting candidates are skipped, never split.
    Normalize whitespace between consecutive authored
    hashtags to one space; append more tags with a space when the caption already
    ends in a hashtag. Otherwise start the hashtag block after two newlines.
    No padding or invented tags are added when the pool is exhausted.

    The 450 safe-copy budget counts UTF-16 units and Windows CRLF line breaks,
    staying below the screenshot-visible 464-character caption. It is a local
    conservative policy, not a claimed Instagram character limit or posting guarantee.
    Both authored input after hashtag spacing and the normalized result must fit.
    Prose, its internal whitespace, URL fragments and qualifications are kept. Invalid or overlong
    input raises ValueError; prose is never truncated to fit. Legacy schema-1
    records retain their separate 2200-code-point storage limit; schema 2 keeps1700
    paste units. Schemas 3/4 persist their character budget; schema 4 also persists
    its hashtag limit. Historical records are not silently rewritten.
    """
    if not isinstance(caption, str):
        raise ValueError("The authored caption must be a string.")
    _check_caption_length(caption)
    caption = _space_separate_hashtags(caption)
    _check_caption_paste_length(caption)
    caption = PostingText.lowercase_hashtags(PostingText.plain_text(caption))
    _check_caption_paste_length(caption)
    _check_caption_hashtags(caption)
    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
        raise ValueError("Hashtag candidates must be an ordered sequence of individual strings.")

    existing_tags = list(_HASHTAG.finditer(caption))
    seen = {match.group().casefold() for match in existing_tags}
    separator = " " if existing_tags and existing_tags[-1].end() == len(caption) else "\n\n"
    unique = {}
    for index, candidate in enumerate(candidates):
        if (not isinstance(candidate, str) or not _HASHTAG.fullmatch(candidate)
                or not _HASHTAG.fullmatch(candidate.lower())
                or not any(char.isalpha() for char in candidate[1:])):
            raise ValueError(
                f"Hashtag candidate at index {index} must be one #tag with a letter and only "
                "Unicode alphanumerics/underscores, also after lowercasing; no whitespace or punctuation."
            )
        tag = candidate.lower()
        identity = tag.casefold()
        if identity not in seen and (
            identity not in unique or caption_paste_length(tag) < caption_paste_length(unique[identity])
        ):
            unique[identity] = tag

    remaining = MAX_CAPTION_PASTE_CHARACTERS - caption_paste_length(caption)
    slots = MAX_CAPTION_HASHTAGS - len(existing_tags)
    selected = []
    for tag in unique.values():
        if len(selected) >= slots:
            break
        cost = caption_paste_length(tag) + (caption_paste_length(separator) if not selected else 1)
        if cost <= remaining:
            selected.append(tag)
            remaining -= cost
    if selected:
        caption += separator + " ".join(selected)
    return _check_caption_hashtags(_check_caption_paste_length(caption))


def suggested_posting(item: dict, thumbnail: dict | None) -> PostingText:
    tags = (("#systemdesign", "#softwareengineering", "#interviewprep")
            if item.get("workflow") == "system-design" else ("#leetcode", "#programming", "#codinginterview"))
    alt = f'Thumbnail for "{item["title"]}".'
    if thumbnail:
        title = thumbnail.get("title", item["title"])
        topic = thumbnail.get("topic")
        if thumbnail.get("renderer") in {
            "problem-topic-camera-1", "problem-topic-camera-2", "problem-topic-camera-3",
        } and topic:
            alt = (f'Dark teal thumbnail with cream monospaced text: "{title}", '
                   f'a muted-red separator, then "{topic}".')
            if thumbnail.get("shot_kind") == "camera":
                alt += " A second muted-red separator sits above a framed camera-feed image."
            elif thumbnail.get("shot_kind") == "none":
                alt += " Text only; no camera image."
        else:
            alt = f'Thumbnail reading "{title}".'
    return PostingText(caption=compose_caption(item["title"], tags), alt_text=alt)


def copy_field(value: str, key: str, label: str, button: str, *, rows: int = 3) -> str:
    identity = "posting-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return (
        '<div class="copy-field"><div class="copy-heading">'
        f'<label for="{identity}">{html.escape(label)}</label>'
        f'<button type="button" data-copy-target="{identity}">{html.escape(button)}</button></div>'
        f'<textarea id="{identity}" rows="{rows}" wrap="soft" readonly spellcheck="false">{html.escape(value)}</textarea>'
        '<p class="copy-status" role="status" aria-live="polite"></p></div>'
    )


def posting_fields(text: PostingText, key: str, *, authored: bool = False) -> str:
    fields = [copy_field(value, f"{key}:{name}", label, button, rows=rows)
              for name, label, button, value, rows in (
        ("caption", "Post caption (includes hashtags)", "Copy caption", text.caption, 7),
        ("alt", "Thumbnail alt text", "Copy alt text", text.alt_text, 5),
    )]
    note = ("Prepared posting text. Review before posting." if authored else
            "Suggested posting text based on the title and cover; review before posting.")
    paste_length = caption_paste_length(text.caption)
    hashtag_count = caption_hashtag_count(text.caption)
    budget_note = (
        " Above the current safe-copy budget; revise hashtags before posting."
        if paste_length > MAX_CAPTION_PASTE_CHARACTERS else ""
    )
    if hashtag_count > MAX_CAPTION_HASHTAGS:
        budget_note += " Above the current hashtag limit; re-author this caption before posting."
    return (
        '<section class="posting-text" aria-label="Copy-ready posting text">'
        f'<p class="posting-note">{note} Hashtags are lowercase. '
        'You can also select the text and copy manually.</p>'
        f'<p class="caption-budget" data-caption-paste-count="{paste_length}" '
        f'data-caption-hashtag-count="{hashtag_count}">'
        f'{len(text.caption):,} characters; hashtags: {hashtag_count} / {MAX_CAPTION_HASHTAGS}. '
        f'Safe-copy budget: {paste_length:,} / {MAX_CAPTION_PASTE_CHARACTERS:,}. '
        f'Counts Windows line breaks and emoji conservatively; not a platform guarantee.{budget_note}</p>'
        + "".join(fields) + "</section>"
    )


POSTING_CSS = """
.posting-text{margin:22px 0;border-top:1px solid #45616a;padding-top:12px;min-width:0}
.posting-note,.caption-budget,.copy-status{color:#b4c4c4;font-size:13px;line-height:1.5}
.copy-field{margin:16px 0;min-width:0}.copy-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.copy-heading label{font-weight:600;font-size:14px}
.copy-heading button{border:1px solid #cd5c5c;border-radius:5px;background:#cd5c5c;color:#002b36;padding:8px 12px;font:600 13px system-ui;cursor:pointer}
.copy-heading button:disabled{opacity:.65;cursor:wait}
.posting-text textarea{display:block;width:100%;min-width:0;resize:vertical;background:#002b36;color:#eee8d5;border:1px solid #45616a;border-radius:5px;padding:12px;font:14px/1.5 Consolas,monospace}
.posting-text :focus-visible{outline:2px solid #cd5c5c;outline-offset:3px}
.copy-status{min-height:1.5em;margin:6px 0}
"""

POSTING_SCRIPT = """
<script>
function fitPostingText(){
    document.querySelectorAll(".posting-text textarea").forEach(text=>{
        text.style.height="auto";text.style.height=(text.scrollHeight+2)+"px";
    });
}
fitPostingText();
window.addEventListener("resize",fitPostingText);
document.addEventListener("click",async event=>{
    const button=event.target.closest("button[data-copy-target]");
    if(!button)return;
    const text=document.getElementById(button.dataset.copyTarget);
    const status=button.closest(".copy-field").querySelector(".copy-status");
    text.focus();text.select();text.setSelectionRange(0,text.value.length);
    button.disabled=true;status.textContent="Copying...";
    try{
        if(!navigator.clipboard||typeof navigator.clipboard.writeText!=="function")
            throw new Error("Clipboard API unavailable");
        await navigator.clipboard.writeText(text.value);
        status.textContent="Copied.";
    }catch(error){
        status.textContent="Clipboard unavailable or blocked. Text selected: press Ctrl+C (Cmd+C on Mac).";
        console.warn("ClipFarm clipboard copy failed:",error);
    }finally{
        button.disabled=false;
    }
});
</script>
"""

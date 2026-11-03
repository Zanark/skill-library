import os

import pytest
from playwright.sync_api import expect, sync_playwright

from clipfarm import workflow
from clipfarm.music_recommendations import RECOMMENDATION_FILE, MusicRecommendation


def suggestion(**changes):
    return MusicRecommendation.model_validate({
        "song": "Resonance", "artist": "HOME", "version": "Original Odyssey album version",
        "reference_url": "https://music.example.org/track?album=odyssey&song=resonance",
        "fit_reason": "A warm, steady backdrop for the scoped pattern explanation.",
        "mix_guidance": "Keep the original voice prominent and audition a low music level.",
        "video_sha256": "a" * 64, "recommended_by": "Fixture editor",
        "recommended_at": "2026-09-27T03:19:32+05:30", **changes,
    })


def make_bundle(root, name="clip", **changes):
    bundle = root / name
    bundle.mkdir()
    (bundle / "clip.mp4").write_bytes(b"fixture video")
    item = {
        "cut_id": "clip", "title": "A scoped coding explanation", "workflow": "leetcode",
        "duration": 166.1, "category": "explanation", "review_notes": "Fixture review",
        "video_sha256": workflow.fingerprint(bundle / "clip.mp4"),
    }
    workflow.write_json(bundle / "manifest.json", item)
    record = suggestion(video_sha256=item["video_sha256"], **changes)
    workflow.write_json(bundle / RECOMMENDATION_FILE, record.model_dump(mode="json"))
    return bundle, item, record


@pytest.mark.parametrize("field", ["song", "artist", "version", "fit_reason", "mix_guidance", "recommended_by"])
@pytest.mark.parametrize("value", [" \t ", "bad\x00text", "bad\x7ftext"])
def test_recommendations_require_nonblank_plain_text(field, value):
    with pytest.raises(ValueError, match="plain text"):
        suggestion(**{field: value})


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "data:text/html,bad", "file:///tmp/song", "not a url",
    "https://user:password@example.org/track", "https://user@example.org/track",
])
def test_recommendation_links_reject_non_http_or_credentials(url):
    with pytest.raises(ValueError):
        suggestion(reference_url=url)


@pytest.mark.parametrize("changes", [
    {"recommended_at": "2026-09-27T03:19:32"},
    {"video_sha256": "wrong"}, {"kind": "verified_trend"}, {"audio_embedded": True},
    {"schema_version": 2}, {"unexpected": "not silently ignored"},
])
def test_recommendations_do_not_accept_invalid_binding_or_false_approval_fields(changes):
    with pytest.raises(ValueError):
        suggestion(**changes)


def test_recommendation_round_trip_preserves_identity_and_provenance():
    record = suggestion(song=" Resonance ", artist=" HOME ")
    restored = MusicRecommendation.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.search_text == "HOME - Resonance"
    assert restored.kind == "suggestion"
    assert restored.recommended_at.utcoffset().total_seconds() == 19800


def test_legacy_gallery_has_no_invented_song(tmp_path):
    bundle, item, _ = make_bundle(tmp_path)
    (bundle / RECOMMENDATION_FILE).unlink()
    assert workflow.gallery_music_recommendation(bundle, item) is None
    document = workflow._write_gallery(tmp_path).read_text(encoding="utf-8")
    assert "Suggested music - add it yourself" not in document
    assert "Resonance" not in document
    assert document.count("data-copy-target=") == 2


@pytest.mark.parametrize("change", ["video", "manifest", "malformed", "stylized"])
def test_stale_or_invalid_suggestions_fail_without_replacing_gallery(tmp_path, change):
    bundle, item, _ = make_bundle(tmp_path)
    gallery = workflow._write_gallery(tmp_path)
    before = gallery.read_bytes()
    if change == "video":
        (bundle / "clip.mp4").write_bytes(b"changed video")
    elif change == "manifest":
        workflow.write_json(bundle / "manifest.json", {**item, "video_sha256": "b" * 64})
    elif change == "malformed":
        (bundle / RECOMMENDATION_FILE).write_text("not json", encoding="utf-8")
    else:
        workflow.write_json(bundle / "manifest.json", {**item, "stylized": {"music": {}}})
    with pytest.raises(ValueError):
        workflow._write_gallery(tmp_path)
    assert gallery.read_bytes() == before


def test_suggestion_html_has_escaped_text_clip_duration_and_no_embedded_audio(tmp_path):
    payload = '</textarea><img src=x onerror="window.injected=true">'
    bundle, _, record = make_bundle(tmp_path, song=payload, fit_reason=payload, version=payload)
    before = workflow.fingerprint(bundle / "clip.mp4")
    text = workflow._write_gallery(tmp_path).read_text(encoding="utf-8")
    assert "&lt;/textarea&gt;&lt;img" in text and "<img" not in text
    assert 'rel="noopener noreferrer"' in text
    assert "album=odyssey&amp;song=resonance" in text
    assert "166.1s clip" in text
    assert "current trend status are unverified" in text
    assert "this export has no added music" in text
    assert "music-instructions.txt" not in text and "<audio" not in text
    assert workflow.fingerprint(bundle / "clip.mp4") == before
    assert workflow.gallery_music_recommendation(bundle, workflow.read_json(bundle / "manifest.json")) == record


def test_offline_recommendations_copy_manual_fallback_collision_names_and_mobile(tmp_path):
    _, _, first = make_bundle(tmp_path, song='Resonance </textarea><img src=x onerror="window.injected=true">')
    _, _, second = make_bundle(tmp_path, "clip--collision", song="A Walk", artist="Tycho")
    gallery = workflow._write_gallery(tmp_path)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=os.environ.get("CLIPFARM_BROWSER_CHANNEL", "msedge" if os.name == "nt" else "chromium"),
            headless=True,
        )
        try:
            context = browser.new_context(offline=True, permissions=["clipboard-read", "clipboard-write"])
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(gallery.as_uri())
            assert page.locator("img").count() == 0
            assert page.evaluate("typeof window.injected") == "undefined"
            assert page.locator(".music-recommendation").count() == 2
            ids = page.locator("textarea").evaluate_all("items=>items.map(t=>t.id)")
            assert len(ids) == len(set(ids)) == 6
            previous = page.evaluate("navigator.clipboard.readText()")
            try:
                for folder, record in (("clip", first), ("clip--collision", second)):
                    section = page.locator(f'article[data-cut="{folder}"] .music-recommendation')
                    expect(section.locator("textarea")).to_have_value(record.search_text)
                    expect(section.get_by_text("Recommendation details", exact=True)).to_have_attribute(
                        "href", f"{folder}/{RECOMMENDATION_FILE}",
                    )
                    section.get_by_role("button", name="Copy song search").click()
                    expect(section.get_by_role("status")).to_have_text("Copied.")
                    assert page.evaluate("navigator.clipboard.readText()") == record.search_text
            finally:
                page.evaluate("value=>navigator.clipboard.writeText(value)", previous)
            for implementation in ("undefined", "{writeText:()=>Promise.reject(new Error('Denied'))}"):
                page.evaluate(f"Object.defineProperty(navigator,'clipboard',{{configurable:true,value:{implementation}}})")
                section.get_by_role("button", name="Copy song search").click()
                expect(section.get_by_role("status")).to_contain_text("Text selected: press Ctrl+C")
                assert section.locator("textarea").evaluate("t=>t.selectionStart===0&&t.selectionEnd===t.value.length")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            page.wait_for_function(
                "Array.from(document.querySelectorAll('textarea')).every(t=>t.scrollHeight<=t.clientHeight+2)",
                timeout=5000,
            )
            assert not errors
            manual = browser.new_context(offline=True, java_script_enabled=False).new_page()
            manual.goto(gallery.as_uri())
            expect(manual.locator(".music-recommendation textarea").nth(0)).to_have_value(first.search_text)
            expect(manual.locator(".music-recommendation textarea").nth(1)).to_have_value(second.search_text)
        finally:
            browser.close()

import os
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from clipfarm import posting, workflow

LIMIT = posting.MAX_CAPTION_PASTE_CHARACTERS


def test_current_limits_constrain_both_characters_and_hashtags():
    assert LIMIT == 450
    assert posting.MAX_CAPTION_HASHTAGS == 5


def test_only_hashtags_are_lowercased():
    value = posting.PostingText(
        caption="HTTP 429 and C# remain readable.\n#SystemDesign #API_Design #Über\nhttps://example.org/#Section",
        alt_text="Cover reading HTTP 429.",
    )
    assert value.caption == (
        "HTTP 429 and C# remain readable.\n#systemdesign #api_design #über\nhttps://example.org/#Section"
    )


@pytest.mark.parametrize("length", [2199, 2200])
@pytest.mark.parametrize("model", [posting.PostingText, posting.PostingRecord])
def test_legacy_storage_limit_includes_prose_whitespace_and_hashtags(length, model):
    suffix = "\n \tHTTP 429, C# and API.\n\n#LeetCode #Python"
    caption = "X" * (length - len(suffix)) + suffix
    binding = ({"schema_version": 1, "video_sha256": "a" * 64,
               "thumbnail_sha256": "b" * 64, "reviewed_by": "Fixture editor"}
               if model is posting.PostingRecord else {})
    text = model(caption=caption, alt_text="Cover", **binding)
    assert len(text.caption) == length
    assert text.caption.endswith("\n \tHTTP 429, C# and API.\n\n#leetcode #python")
    with pytest.raises(ValueError, match=str(LIMIT)):
        posting.compose_caption(caption, ["#Algorithms"])
    assert "Above the current safe-copy budget" in posting.posting_fields(text, "legacy")


@pytest.mark.parametrize("caption", ["X" * 2201, " " + "X" * 2200, "X" * 2197 + " #İ"])
def test_overlong_input_or_lowercase_expansion_is_never_silently_trimmed(caption):
    for model, binding in (
        (posting.PostingText, {}),
        (posting.PostingRecord, {
            "video_sha256": "a" * 64, "thumbnail_sha256": "b" * 64, "reviewed_by": "Fixture editor",
        }),
    ):
        with pytest.raises(ValueError, match="2200"):
            model(caption=caption, alt_text="Cover", **binding)
    with pytest.raises(ValueError, match="2200" if len(caption) > 2200 else str(LIMIT)):
        posting.compose_caption(caption, [])


@pytest.mark.parametrize("ending", ["🙂", "e\u0301", "👩🏽‍💻", " #İ"])
def test_caption_budget_counts_utf16_and_windows_newlines_after_normalization(ending):
    normalized = posting.PostingText(caption="X" + ending, alt_text="Cover").caption[1:]
    prefix = "X" * (LIMIT - posting.caption_paste_length(normalized))
    caption = prefix + ending
    result = posting.compose_caption(caption, [])
    assert result == prefix + normalized
    assert posting.caption_paste_length(result) == LIMIT
    assert posting.PostingText(caption=result, alt_text="Cover").caption == result
    with pytest.raises(ValueError, match=str(LIMIT)):
        posting.compose_caption(caption + "X", [])


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_paste_budget_reserves_windows_line_breaks_without_rewriting_prose(newline):
    caption = "Scoped explanation." + newline * 2 + "Code names: HTTP and C#."
    assert posting.caption_paste_length(caption) == 47
    result = posting.compose_caption(caption, ["#Python"])
    assert result == caption + "\n\n#python"
    assert posting.caption_paste_length(result) == 58


@pytest.mark.parametrize("units", [449, 450, 451, 927, 928, 929, 1699, 1700, 1701, 1725, 2198])
def test_new_records_enforce_safe_copy_budget_and_old_records_remain_readable(units):
    values = dict(caption="X" * units, alt_text="Cover", video_sha256="a" * 64,
                  thumbnail_sha256="b" * 64, reviewed_by="Fixture editor")
    legacy = posting.PostingRecord(schema_version=1, **values)
    assert posting.PostingRecord.model_validate(legacy.model_dump()).caption == values["caption"]
    if units <= LIMIT:
        current = posting.PostingRecord(**values)
        assert current.schema_version == 4
        assert current.caption_paste_limit == LIMIT
        assert current.caption_hashtag_limit == 5
        assert posting.PostingRecord.model_validate(current.model_dump()) == current
    else:
        with pytest.raises(ValueError, match=str(LIMIT)):
            posting.PostingRecord(**values)


def test_paste_budget_rejects_raw_whitespace_and_lowercase_expansion():
    for caption in (" " + "X" * LIMIT, "X" * (LIMIT - 3) + " #İ", "X" * (LIMIT - 1) + "🙂"):
        with pytest.raises(ValueError, match=str(LIMIT)):
            posting.compose_caption(caption, [])


@pytest.mark.parametrize("version", [1, 2])
def test_legacy_records_keep_their_original_text_and_limits(version):
    caption = "X" * 1600 + "\n\n#python\n\n#api"
    record = posting.PostingRecord(
        schema_version=version, caption=caption, alt_text="Cover",
        video_sha256="a" * 64, thumbnail_sha256="b" * 64, reviewed_by="Fixture editor",
    )
    assert record.caption == caption
    assert "Above the current safe-copy budget" in posting.posting_fields(record, "legacy")
    if version == 2:
        with pytest.raises(ValueError, match="1700"):
            posting.PostingRecord(**{**record.model_dump(), "caption": "X" * 1701})


def test_record_remembers_its_budget_and_formats_only_hashtag_gaps():
    values = dict(
        caption="HTTP and C#.\n\n  Keep this paragraph.\n\n#Python\n\n#API\t#DB",
        alt_text="Cover\n\n#Not\n#Changed", video_sha256="a" * 64,
        thumbnail_sha256="b" * 64, reviewed_by="Fixture editor",
    )
    record = posting.PostingRecord(**values)
    assert record.caption == "HTTP and C#.\n\n  Keep this paragraph.\n\n#python #api #db"
    assert record.alt_text == values["alt_text"]
    encoded = record.model_dump()
    assert encoded["caption_paste_limit"] == LIMIT
    assert posting.PostingRecord.model_validate(encoded) == record
    with pytest.raises(ValueError, match="10-character"):
        posting.PostingRecord(**values, caption_paste_limit=10)
    historical = posting.PostingRecord(**{**values, "caption": "X" * 1000}, caption_paste_limit=1200)
    assert posting.PostingRecord.model_validate(historical.model_dump()).caption_paste_limit == 1200
    assert "Above the current safe-copy budget" in posting.posting_fields(historical, "historical")


@pytest.mark.parametrize("limit", [0, 2201, True, "928", 927.5])
def test_record_rejects_invalid_declared_budget(limit):
    with pytest.raises(ValueError):
        posting.PostingRecord(caption="Scope.", caption_paste_limit=limit, alt_text="Cover",
                              video_sha256="a" * 64, thumbnail_sha256="b" * 64, reviewed_by="Fixture")


def test_short_caption_with_61_tags_is_rejected_but_schema3_remains_readable():
    caption = "Scope.\n\n" + " ".join(f"#tag{index}" for index in range(61))
    assert posting.caption_paste_length(caption) < LIMIT
    values = dict(caption=caption, alt_text="Cover", video_sha256="a" * 64,
                  thumbnail_sha256="b" * 64, reviewed_by="Fixture editor")
    legacy = posting.PostingRecord(schema_version=3, caption_paste_limit=928, **values)
    assert legacy.caption == caption
    assert "Above the current hashtag limit" in posting.posting_fields(legacy, "legacy")
    with pytest.raises(ValueError, match="at most 5 hashtags"):
        posting.PostingRecord(**values)
    with pytest.raises(ValueError, match="at most 5 hashtags"):
        posting.compose_caption(caption, [])


@pytest.mark.parametrize("limit", [-1, 2201, True, "5", 1.5])
def test_record_rejects_invalid_hashtag_limit(limit):
    with pytest.raises(ValueError):
        posting.PostingRecord(caption="Scope.", caption_hashtag_limit=limit, alt_text="Cover",
                              video_sha256="a" * 64, thumbnail_sha256="b" * 64, reviewed_by="Fixture")


def test_record_persists_hashtag_budget_and_counts_repeated_authored_tags():
    values = dict(caption="Scope. #python", alt_text="Cover", video_sha256="a" * 64,
                  thumbnail_sha256="b" * 64, reviewed_by="Fixture")
    record = posting.PostingRecord(**values, caption_hashtag_limit=1)
    assert posting.PostingRecord.model_validate(record.model_dump()).caption_hashtag_limit == 1
    with pytest.raises(ValueError, match="at most 0 hashtags"):
        posting.PostingRecord(**values, caption_hashtag_limit=0)
    with pytest.raises(ValueError, match="at most 5 hashtags"):
        posting.compose_caption("Scope. " + " ".join(["#Python"] * 6), [])


@pytest.mark.parametrize("gap", ["\n", "\r\n", "\n\n", "\t", "   ", "\r"])
def test_all_existing_and_added_hashtags_share_one_space_separated_block(gap):
    prefix = "A scoped sketch.\n\n  Keep prose spacing.\n\n"
    result = posting.compose_caption(prefix + "#Python" + gap + "#API" + gap + "#DB", ["#Coding"])
    assert result == prefix + "#python #api #db #coding"
    assert result[result.index("#"):] == " ".join(result[result.index("#"):].split())
    assert posting.compose_caption(result, []) == result


def test_existing_tag_separator_uses_one_budget_unit_not_a_new_paragraph():
    caption = "X" * (LIMIT - 11) + " #seed"
    result = posting.compose_caption(caption, ["#API"])
    assert result == caption + " #api"
    assert posting.caption_paste_length(result) == LIMIT
    assert "\n" not in result


def test_composer_preserves_scope_case_whitespace_urls_and_existing_repetitions():
    caption = (
        " \tHTTP 429 and C# API names.\n\n  A scoped sketch; NOT a complete tutorial.\r\n"
        "https://example.org/#Section\n#Python #PYTHON #Straße \t"
    )
    result = posting.compose_caption(
        caption, ["#PYTHON", "#STRASSE", "#API_Design", "#api_design", "#Über", "#über"],
    )
    expected = (
        "HTTP 429 and C# API names.\n\n  A scoped sketch; NOT a complete tutorial.\r\n"
        "https://example.org/#Section\n#python #python #straße #api_design #über"
    )
    assert result == expected
    assert posting.compose_caption(result, ["#API_DESIGN", "#ÜBER", "#Python"]) == expected


def test_composer_prefers_editorial_relevance_over_packing_short_tags():
    caption = "X" * (LIMIT - 16)
    candidates = ["#LeetCode", "#API", "#AI", "#ML", "#api"]
    assert posting.compose_caption(caption, candidates) == caption + "\n\n#leetcode"
    assert candidates == ["#LeetCode", "#API", "#AI", "#ML", "#api"]
    assert posting.compose_caption("Reviewed scope.", ["#Python", "#API", "#DB"]) == (
        "Reviewed scope.\n\n#python #api #db"
    )


def test_composer_limits_total_tags_including_seeds_and_validates_unused_candidates():
    seeds = "Scoped memory explanation.\n\n#leetcode #python #programming #codinginterview"
    candidates = ["#IsomorphicStrings", "#ZIP", "#Sets", "#CS"]
    assert posting.compose_caption(seeds, candidates) == seeds + " #isomorphicstrings"
    full = seeds + " #isomorphicstrings"
    assert posting.compose_caption(full, ["#API"]) == full
    with pytest.raises(ValueError, match="candidate at index 1"):
        posting.compose_caption(full, ["#API", "#invalid tag"])
    assert posting.compose_caption("Scope.", [f"#topic{n}" for n in range(10)]) == (
        "Scope.\n\n#topic0 #topic1 #topic2 #topic3 #topic4"
    )


def test_case_variant_deduplication_retains_shortest_spelling_and_first_relevance_position():
    caption = "X" * (LIMIT - 11)
    assert posting.compose_caption(caption, ["#STRASSE", "#Straße"]) == caption + "\n\n#straße"
    assert posting.compose_caption("Scope.", ["#STRASSE", "#API", "#Straße"]) == (
        "Scope.\n\n#straße #api"
    )


def test_composer_skips_nonfitting_tags_and_breaks_equal_length_ties_by_pool_order():
    caption = "X" * (LIMIT - 12)
    assert posting.compose_caption(caption, ["#SoftwareEngineering", "#API", "#DB"]) == (
        caption + "\n\n#api #db"
    )
    caption = "X" * (LIMIT - 13)
    assert posting.compose_caption(caption, ["#SQL", "#API", "#CLI"]) == caption + "\n\n#sql #api"


@pytest.mark.parametrize("candidates", [
    ["#leetcode", "#api", "#ai", "#ml", "#db"],
    ["#\U00010428", "#abc", "#a", "#\U00010428\U00010429"],
])
def test_composer_retains_whole_tags_and_order_at_small_unicode_budgets(candidates):
    for budget in range(36):
        caption = "X" * (LIMIT - budget)
        result = posting.compose_caption(caption, candidates)
        selected = result[len(caption):].split()
        assert posting.caption_paste_length(result) <= LIMIT
        assert result.startswith(caption)
        assert len(selected) <= posting.MAX_CAPTION_HASHTAGS
        assert selected == [tag for tag in candidates if tag in selected]


@pytest.mark.parametrize("budget,expected", [
    (0, []), (6, []), (7, ["#ai"]), (8, ["#api"]),
    (12, ["#api", "#ai"]), (13, ["#leetcode"]), (16, ["#leetcode"]),
    (17, ["#leetcode", "#ai"]), (20, ["#leetcode", "#api"]),
    (30, ["#leetcode", "#api", "#ai", "#ml", "#db"]),
])
def test_relevance_first_selection_at_exact_budget_boundaries(budget, expected):
    caption = "X" * (LIMIT - budget)
    result = posting.compose_caption(caption, ["#leetcode", "#api", "#ai", "#ml", "#db"])
    assert result[len(caption):].split() == expected


@pytest.mark.parametrize("caption,candidates,expected", [
    ("Scope.", [], "Scope."),
    ("Scope. #Python", ["#PYTHON", "#python"], "Scope. #python"),
    ("Scope.", ["#Python", "#python", "#Coding"], "Scope.\n\n#python #coding"),
    ("X" * LIMIT, ["#API"], "X" * LIMIT),
    ("X" * (LIMIT - 3), ["#AI"], "X" * (LIMIT - 3)),
    ("X" * (LIMIT - 7), ["#" + "A" * 2200, "#API"], "X" * (LIMIT - 7)),
    ("X" * (LIMIT - 8), ["#" + "A" * 2200, "#API"], "X" * (LIMIT - 8) + "\n\n#api"),
])
def test_composer_exhausted_candidates_or_budget_adds_no_padding(caption, candidates, expected):
    assert posting.compose_caption(caption, candidates) == expected


@pytest.mark.parametrize("candidate", [
    None, 42, "", "#", "Python", " #Python", "#Python ", "#two tags",
    "##Python", "#python\n#api", "#foo-bar", "#c++", "#py/th", "#123", "#___",
    "#<script>", "#py\x00thon", "#py\u200bthon", "#py\u202ethon", "#py🙂", "#İ",
])
def test_composer_rejects_invalid_candidates_even_with_exhausted_budget(candidate):
    with pytest.raises(ValueError, match="candidate at index 1"):
        posting.compose_caption("X" * LIMIT, ["#Python", candidate])


@pytest.mark.parametrize("candidates", [
    None, "#Python", b"#Python", {"#Python"}, frozenset({"#Python"}), {"#Python": True},
])
def test_composer_requires_an_ordered_candidate_sequence(candidates):
    with pytest.raises(ValueError, match="ordered sequence"):
        posting.compose_caption("Scope.", candidates)


@pytest.mark.parametrize("caption", [None, 42, "", " \n ", "Bad\x00text"])
def test_composer_rejects_invalid_authored_text(caption):
    with pytest.raises(ValueError):
        posting.compose_caption(caption, ["#Python"])


@pytest.mark.parametrize("field,value", [("caption", " \n "), ("alt_text", "\t"), ("caption", "Bad\x00text")])
def test_posting_rejects_blank_or_control_text(field, value):
    with pytest.raises(ValueError):
        posting.PostingText(**{**{"caption": "A post", "alt_text": "A cover"}, field: value})


@pytest.mark.parametrize("shot", ["camera", "none"])
@pytest.mark.parametrize("renderer", ["problem-topic-camera-1", "problem-topic-camera-2", "problem-topic-camera-3"])
def test_suggestions_describe_only_known_thumbnail_content(shot, renderer):
    value = posting.suggested_posting(
        {"title": "Specific focus", "workflow": "system-design"},
        {"title": "Design a Rate Limiter", "topic": "Specific focus",
         "renderer": renderer, "shot_kind": shot},
    )
    assert "#systemdesign" in value.caption and "#leetcode" not in value.caption
    assert "Design a Rate Limiter" in value.alt_text and "Specific focus" in value.alt_text
    assert ("framed camera-feed" in value.alt_text) == (shot == "camera")
    assert ("Text only; no camera image." in value.alt_text) == (shot == "none")


@pytest.mark.parametrize("workflow_name,expected", [
    ("system-design", "#systemdesign #softwareengineering #interviewprep"),
    ("leetcode", "#leetcode #programming #codinginterview"),
])
def test_suggestions_use_only_context_general_tags_and_respect_caption_budget(workflow_name, expected):
    value = posting.suggested_posting({"title": "A scoped sketch", "workflow": workflow_name}, None)
    assert value.caption == f"A scoped sketch\n\n{expected}"
    title = "HTTP scoped sketch. " + "X" * (LIMIT - len("HTTP scoped sketch. "))
    value = posting.suggested_posting({"title": title, "workflow": workflow_name}, None)
    assert value.caption == title
    assert "Suggested posting text" in posting.posting_fields(value, "fixture")
    with pytest.raises(ValueError, match=str(LIMIT)):
        posting.suggested_posting({"title": title + "X", "workflow": workflow_name}, None)


def make_gallery(root: Path, caption: str | None = None):
    bundle = root / "clip"
    bundle.mkdir()
    (bundle / "clip.mp4").write_bytes(b"Fixture video")
    (bundle / "thumbnail.jpg").write_bytes(b"Fixture cover")
    item = {"cut_id": "clip", "title": "HTTP 429 feedback", "workflow": "system-design",
            "duration": 12, "category": "explanation", "review_notes": "Fixture review",
            "video_sha256": workflow.fingerprint(bundle / "clip.mp4")}
    workflow.write_json(bundle / "manifest.json", item)
    text = posting.PostingRecord(
        caption=(caption if caption is not None else
                 'HTTP 429.\n\nLiteral </textarea><img src=x onerror="window.injected=true"> & text.\n\n#SystemDesign #RateLimiting'),
        alt_text='Text-only cover reading "HTTP 429" & "Rate limiter".',
        reviewed_by="Fixture editor", video_sha256=item["video_sha256"],
        thumbnail_sha256=workflow.fingerprint(bundle / "thumbnail.jpg"),
    )
    workflow.write_json(bundle / posting.POSTING_FILE, text.model_dump())
    return bundle, item, text, workflow._write_gallery(root)


@pytest.mark.parametrize("name", ["clip.mp4", "thumbnail.jpg"])
def test_stale_authored_posting_fails_instead_of_falling_back(tmp_path, name):
    bundle, item, _, _ = make_gallery(tmp_path)
    (bundle / name).write_bytes(b"Changed artifact")
    with pytest.raises(ValueError, match="different video/thumbnail"):
        workflow.gallery_posting(bundle, item)


def test_malformed_authored_posting_fails_explicitly(tmp_path):
    bundle, item, _, _ = make_gallery(tmp_path)
    (bundle / posting.POSTING_FILE).write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        workflow.gallery_posting(bundle, item)


def test_composed_posting_round_trip_keeps_media_hash_binding(tmp_path):
    caption = posting.compose_caption("HTTP 429: scoped API example.", ["#SystemDesign", "#API", "#api"])
    bundle, item, text, _ = make_gallery(tmp_path, caption)
    record, authored = workflow.gallery_posting(bundle, item)
    assert authored and record == text
    assert record.caption == caption
    assert record.video_sha256 == workflow.fingerprint(bundle / "clip.mp4")
    assert record.thumbnail_sha256 == workflow.fingerprint(bundle / "thumbnail.jpg")
    with pytest.raises(ValueError, match="different video/thumbnail"):
        workflow.gallery_posting(bundle, {**item, "video_sha256": "0" * 64})


def test_overlong_authored_posting_fails_without_suggestion_fallback(tmp_path):
    bundle, item, text, _ = make_gallery(tmp_path)
    workflow.write_json(bundle / posting.POSTING_FILE, {**text.model_dump(), "caption": "X" * 2201})
    with pytest.raises(ValueError, match="2200"):
        workflow.gallery_posting(bundle, item)
    with pytest.raises(ValueError, match="2200"):
        workflow._write_gallery(tmp_path)


def test_unsafe_new_posting_preserves_existing_gallery_and_legacy_text(tmp_path):
    bundle, _, text, path = make_gallery(tmp_path)
    previous = path.read_bytes()
    record = {**text.model_dump(), "caption": "X" * 1725}
    workflow.write_json(bundle / posting.POSTING_FILE, record)
    with pytest.raises(ValueError, match=str(LIMIT)):
        workflow._write_gallery(tmp_path)
    assert path.read_bytes() == previous
    workflow.write_json(bundle / posting.POSTING_FILE, {**record, "schema_version": 1})
    workflow._write_gallery(tmp_path)
    assert "Above the current safe-copy budget" in path.read_text(encoding="utf-8")
    assert record["caption"] in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("at_limit", [False, True])
def test_offline_gallery_copy_exact_text_blocked_clipboard_and_no_javascript(tmp_path, at_limit):
    caption = None
    if at_limit:
        scope = (
            'HTTP 429; scoped sketch, NOT a complete tutorial. 🙂\n\n'
            'Literal </textarea><img src=x onerror="window.injected=true"> & text.\n\n'
        )
        caption = posting.compose_caption(
            scope + "X" * (LIMIT - 12 - posting.caption_paste_length(scope)),
            ["#SoftwareEngineering", "#API", "#DB"],
        )
        assert posting.caption_paste_length(caption) == LIMIT
    _, _, text, path = make_gallery(tmp_path, caption)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=os.environ.get("CLIPFARM_BROWSER_CHANNEL", "msedge" if os.name == "nt" else "chromium"),
            headless=True,
        )
        try:
            context = browser.new_context(permissions=["clipboard-read", "clipboard-write"], offline=True)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(path.as_uri())
            fields = page.locator(".copy-field")
            assert fields.count() == 2
            expect(page.locator(".caption-budget")).to_have_attribute(
                "data-caption-paste-count", str(posting.caption_paste_length(text.caption)),
            )
            expect(page.locator(".caption-budget")).to_have_attribute(
                "data-caption-hashtag-count", str(posting.caption_hashtag_count(text.caption)),
            )
            assert page.locator("img").count() == 0
            assert page.evaluate("typeof window.injected") == "undefined"
            previous = page.evaluate("navigator.clipboard.readText()")
            try:
                for field, expected in ((fields.nth(0), text.caption), (fields.nth(1), text.alt_text)):
                    expect(field.locator("textarea")).to_have_value(expected)
                    field.locator("button").click()
                    expect(field.get_by_role("status")).to_have_text("Copied.")
                    # Windows' native clipboard normalizes line breaks to CRLF.
                    copied = page.evaluate("navigator.clipboard.readText()")
                    assert copied.replace("\r\n", "\n") == expected
                    if expected == text.caption:
                        assert posting.caption_paste_length(copied) <= LIMIT
                        hashtag_block = copied.replace("\r\n", "\n").rsplit("\n\n", 1)[-1]
                        assert hashtag_block.startswith("#") and "\n" not in hashtag_block
            finally:
                page.evaluate("value=>navigator.clipboard.writeText(value)", previous)
            for implementation in (
                "{writeText:()=>Promise.reject(new Error('Denied by fixture'))}", "undefined",
            ):
                page.evaluate(f"Object.defineProperty(navigator,'clipboard',{{configurable:true,value:{implementation}}})")
                fields.nth(0).locator("button").click()
                expect(fields.nth(0).get_by_role("status")).to_contain_text("Text selected: press Ctrl+C")
                assert fields.nth(0).locator("textarea").evaluate(
                    "t=>t.selectionStart===0&&t.selectionEnd===t.value.length"
                )
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            page.wait_for_function(
                "Array.from(document.querySelectorAll('textarea')).every(t=>t.scrollHeight<=t.clientHeight+2)",
                timeout=5000,
            )
            assert not errors
            no_js = browser.new_context(java_script_enabled=False, offline=True)
            manual = no_js.new_page()
            manual.goto(path.as_uri())
            expect(manual.locator("textarea").nth(0)).to_have_value(text.caption)
            expect(manual.locator("textarea").nth(1)).to_have_value(text.alt_text)
        finally:
            browser.close()

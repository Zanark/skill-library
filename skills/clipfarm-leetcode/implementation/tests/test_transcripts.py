import pytest

from clipfarm.models import Clip, Cue, Region
from clipfarm.transcripts import parse_transcript, suggest_clips


def test_srt_import_preserves_words_and_decodes_markup():
    cues, note = parse_transcript(
        "\ufeff1\r\n00:00:01,200 --> 00:00:03,456\r\n<b>Hello</b> &amp; goodbye.\r\n\r\n"
        "2\r\n00:00:04,000 --> 00:00:05,000\r\nSecond line.\r\n",
        "captions.srt", 10,
    )
    assert [(c.start, c.end, c.text) for c in cues] == [
        (1.2, 3.456, "Hello & goodbye."), (4, 5, "Second line."),
    ]
    assert "2 timed captions" in note


def test_webvtt_settings_voice_tags_and_rolling_duplicates():
    cues, _ = parse_transcript(
        "WEBVTT\n\nNOTE test note\nignore\n\nfirst\n00:01.000 --> 00:03.000 align:start\n"
        "<v Speaker><c.color>Hello</c></v>\n\n00:02.000 --> 00:04.000\nHello\n",
        "captions.vtt", 10,
    )
    assert len(cues) == 1
    assert cues[0].text == "Hello" and cues[0].end == 4


def test_tactiq_inline_timestamps_skip_headers_and_infer_bounded_ends():
    cues, note = parse_transcript(
        "# tactiq.io free youtube transcript\n# Stream title\n# https://example.test/video\n\n"
        "00:00:17.199 Okay. I think it's working.\n"
        "00:00:24.400 Another line.\n"
        "00:00:49.440 Two minutes.\n"
        "00:01:28.560 Back from the break.\n",
        "transcript_granular.txt", 600,
    )
    assert [(c.start, c.end) for c in cues] == [
        (17.199, 24.4), (24.4, 32.4), (49.44, 57.44), (88.56, 96.56),
    ]
    assert "Start times come from the transcript" in note
    assert "inferred" in note
    assert "tactiq" not in " ".join(c.text for c in cues)


def test_standalone_timestamps_allow_multiline_paragraphs_and_fractional_minutes():
    cues, _ = parse_transcript(
        "\ufeff00:00:17\r\nFirst line.\r\nAnother sentence.\r\n\r\n"
        "00:00:24\r\nNext paragraph.\r\n\r\n"
        "01:02.345 Final line.\r\n", "blocks.txt", 65,
    )
    assert [(c.start, c.end, c.text) for c in cues] == [
        (17, 24, "First line. Another sentence."),
        (24, 32, "Next paragraph."),
        (62.345, 65, "Final line."),
    ]


@pytest.mark.parametrize("text", [
    "00:00:10 First.\n00:00:10 Duplicate.",
    "00:00:10 First.\n00:00:09 Reversed.",
    "00:00:10\n00:00:15 No text before this.",
    "Unmarked words\n00:00:10 Caption.",
    "00:00:10 Fine.\n00:00:15.1234 Malformed.",
    "00:00:10 Fine.\n00:61:00 Out of range.",
    "00:00:25 Outside source.",
])
def test_start_only_transcripts_reject_ambiguous_or_invalid_timing(text):
    with pytest.raises(ValueError):
        parse_transcript(text, "captions.txt", 20)


@pytest.mark.parametrize("text", [
    "This transcript has no timestamps.", "1\n00:00:70,000 --> 00:01:15,000\nBad time",
    "1\n00:00:05,000 --> 00:00:04,000\nReversed",
    '{"segments":[{"start":1,"end":4}]}',
    '{"segments":[{"start":1,"end":4,"text":123}]}',
    '[{"start":1,"end":100,"text":"Wrong video"}]',
    '[{"start":20,"end":21,"text":"Beyond video"}]',
    '[{"start":0,"end":2,"text":"   "}]',
    '[{"start":0,"end":NaN,"text":"Not finite"}]',
])
def test_rejects_invalid_transcripts(text):
    with pytest.raises(ValueError):
        parse_transcript(text, "input.srt", 20)


def test_json_segments_and_boundary_clamp():
    cues, _ = parse_transcript('{"segments":[{"start":8,"end":10.1,"text":"End."}]}', "a.json", 10)
    assert cues[0].end == 10


def test_overlapping_caption_warning():
    _, note = parse_transcript(
        '[{"start":1,"end":5,"text":"One"},{"start":2,"end":6,"text":"Two"}]', "a.json", 10
    )
    assert "overlapping" in note


def test_suggestions_span_long_source_and_match_keywords():
    cues = [Cue(start=i * 5, end=i * 5 + 4.9,
                text=("Why the camera matters." if i % 30 == 0 else "A complete thought."))
            for i in range(1000)]
    clips = suggest_clips(cues, 5000, 20, 60, 6, "camera")
    assert len(clips) == 6
    assert all(20 <= c.end - c.start <= 60 for c in clips)
    assert all(0 <= c.start < c.end <= 5000 for c in clips)
    assert all("keyword match" in c.reason for c in clips)
    assert all(a.end <= b.start for a, b in zip(clips, clips[1:]))


def test_no_match_is_actionable_not_empty_success():
    cues = [Cue(start=0, end=30, text="A complete thought.")]
    with pytest.raises(ValueError, match="No matching"):
        suggest_clips(cues, 40, 20, 60, 6, "missingkeyword")


def test_short_source_and_sparse_speech():
    clips = suggest_clips([Cue(start=0, end=4, text="A short thought.")], 4, 20, 60, 6, "")
    assert len(clips) == 1 and clips[0].end == 4
    with pytest.raises(ValueError):
        suggest_clips([Cue(start=0, end=1, text="Hi."), Cue(start=29, end=30, text="Bye.")],
                      30, 20, 30, 6, "")


def test_clip_and_region_validation():
    with pytest.raises(ValueError):
        Clip(start=0, end=181)
    with pytest.raises(ValueError):
        Clip(start=float("nan"), end=3)
    with pytest.raises(ValueError):
        Region(x=0.8, y=0, w=0.4, h=0.5)

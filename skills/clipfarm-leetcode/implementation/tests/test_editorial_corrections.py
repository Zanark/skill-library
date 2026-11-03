import threading

import pytest

from clipfarm import media, workflow
from clipfarm.editorial_corrections import correction_layout
from clipfarm.models import Clip, Cue, EditorialCorrection, Region
from clipfarm.workflow_models import WorkflowSegment
from test_question_titles import consolas
from test_workflow import prepared, fake_draft, approve


def correction(text="Hash passwords with a salted, slow password hash; encoding is not protection."):
    return EditorialCorrection(text=text, sources=["https://cheatsheetseries.owasp.org/"])


def test_correction_measured_separate_from_spoken_captions_and_escaped(consolas):
    note = correction(r"Literal {\pos(0,0)} and \N. Fixed and sliding windows are different.")
    layout = correction_layout(note.text)
    assert 34 <= layout["font_size"] <= 44 and len(layout["lines"]) <= 4
    assert layout["content_bottom"] * 1920 < layout["bounds"][1]
    clip = Clip(start=0, end=10, layout="leetcode", camera_mode="absent",
                content_region=Region(x=0, y=0, w=1, h=1), correction=note)
    cue = Cue(start=2, end=3, text="Original speech is unchanged")
    ass = media._ass([cue], clip)
    assert "EDITOR CORRECTION:" in ass and r"Original speech is\Nunchanged" in ass
    assert "Dialogue: 2,0:00:00.00,0:00:10.00,Correction" in ass
    assert r"\{\pos" not in ass
    assert "EDITOR CORRECTION:" in media._ass([], clip)
    assert note.text not in media._srt([cue])


@pytest.mark.parametrize("text", ["", " ", "bad\ntext", "\x7f", "x" * 181])
def test_invalid_correction_text_rejected(text):
    with pytest.raises(ValueError):
        correction(text)


@pytest.mark.parametrize("sources", [[], ["file:///private"], ["https://"]])
def test_corrections_require_public_reference_sources(sources):
    with pytest.raises(ValueError):
        EditorialCorrection(text="Clear correction.", sources=sources)


def test_legacy_serialization_and_correction_review_binding(prepared, consolas):
    path, plan = prepared
    cut = plan.cuts[0]
    before = workflow.cut_signature(plan, cut)
    assert "correction" not in cut.segments[0].model_dump()
    cut.segments[0].correction = correction()
    assert workflow.validate_plan(plan) == []
    assert workflow.cut_signature(plan, cut) != before
    assert "corrections_reviewed" in workflow.review_checks(plan, cut)
    compiled, _ = workflow.compile_segments(plan, cut, threading.Event())
    assert compiled[0].correction == cut.segments[0].correction
    assert compiled[1].correction is None and "correction" not in compiled[1].model_dump()
    workflow.write_json(path, plan.model_dump())
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, cut)
    with pytest.raises(ValueError, match="Not all"):
        workflow.publish(path, cut.id)
    cut.segments[0].correction = None
    assert workflow.cut_signature(plan, cut) == before


@pytest.mark.parametrize("seconds,limit", [(60, 1), (600, 5), (1200.77, 10), (1400.65, 11)])
def test_coverage_budget_scales_with_source_and_humor_is_separate(prepared, seconds, limit):
    _, plan = prepared
    assert plan.clip_policy == "coverage-first-v1"
    plan.media.duration = seconds
    original = plan.cuts[0]
    plan.cuts = [original.model_copy(update={"id": f"core-{i}", "category": "explanation"})
                 for i in range(limit)]
    assert workflow.validate_plan(plan) == []
    plan.cuts += [original.model_copy(update={"id": f"bonus-{i}"}) for i in range(2)]
    assert workflow.validate_plan(plan) == []
    plan.cuts.append(original.model_copy(update={"id": "extra-core", "category": "explanation"}))
    assert any(f"at most {limit} core" in e for e in workflow.validate_plan(plan))
    plan.cuts.append(original.model_copy(update={"id": "extra-bonus"}))
    assert any("at most 2 genuine" in e for e in workflow.validate_plan(plan))
    plan.clip_policy = None
    assert "clip_policy" not in plan.model_dump()
    assert workflow.validate_plan(plan) == []

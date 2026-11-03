from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import cv2
import numpy as np
import pytest

from clipfarm import media
from clipfarm import workflow_vision as vision
from clipfarm.models import MediaInfo


@pytest.fixture
def workspace():
    directory = (Path(__file__).resolve().parents[1] / ".clipfarm" / "workflow-runs"
                 / "leetcode-20260920" / "vision" / "test-artifacts" / uuid4().hex)
    directory.mkdir(parents=True)
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


def word(text, x=0, y=0, score=0.95):
    return {"text": text, "score": score, "box": [[x, y], [x + 90, y],
                                                [x + 90, y + 20], [x, y + 20]]}


@pytest.mark.parametrize("text", ["BRB", "b r b", "B.R.B.", "Be RIGHT back", "be\nright\nback"])
def test_brb_variations(text):
    assert vision._classify_words([word(text)])["brb"]


@pytest.mark.parametrize("text", ["subroutine", "brbr", "be right", "BTree", "Accepted"])
def test_not_brb(text):
    assert not vision._classify_words([word(text)])["brb"]


def test_runtime_needs_result_context_and_runtime_label():
    for texts in [["int n = 12 ms"], ["Accepted", "n = 12 ms"],
                  ["Runtime: 12 ms"], ["not accepted", "Runtime: 12 ms"],
                  ["Accepted submissions", "Runtime: 12 ms"]]:
        assert vision._classify_words([word(text, y=i * 30) for i, text in enumerate(texts)])["runtime_ms"] is None
    result = vision._classify_words([word("Accepted"), word("Runtime: 0 ms", y=40)])
    assert result["accepted"] and result["runtime_ms"] == 0
    result = vision._classify_words([word("Test Result"), word("Runtime: 3.5 ms", y=40)])
    assert not result["accepted"] and result["runtime_ms"] == 3.5


def test_runtime_geometry_and_conflicts():
    words = [word("Accepted"), word("Runtime", y=40), word("5 ms", y=65),
             word("321 ms", x=1000, y=65)]
    assert vision._classify_words(words)["runtime_ms"] == 5
    words.append(word("Runtime: 9 ms", x=500, y=200))
    result = vision._classify_words(words)
    assert result["runtime_ms"] is None and "Conflicting" in result["warnings"][-1]


def test_real_leetcode_merged_labels_and_submission_vs_test_runtime():
    submission = [word("Accepted79/79 testcases passed"), word("© Runtime", y=100),
                  word("15msBeats 66.74%", y=130)]
    result = vision._classify_words(submission)
    assert result["accepted"] and result["runtime_ms"] == 15
    compact = [word("Accepted71/71 testcases passed"), word("Runtime", y=100),
               word("20msBeats81.22%", y=130)]
    assert vision._classify_words(compact)["runtime_ms"] == 20
    test_result = [word("Testcase> Test Result", x=500, y=150),
                   word("Accepted Runtime: 1 ms", x=500, y=190)]
    assert vision._classify_words(test_result)["runtime_ms"] == 1
    assert vision._classify_words(submission + test_result)["runtime_ms"] is None


def test_runtime_split_units_and_low_confidence():
    words = [word("Accepted"), word("Runtime", y=40), word("12", y=70), word("ms", x=100, y=70)]
    assert vision._classify_words(words)["runtime_ms"] == 12
    words[2]["score"] = 0.1
    assert vision._classify_words(words)["runtime_ms"] is None
    assert vision._classify_words([word("BRB", score=0.1)])["brb"]


def test_optional_import_is_actionable(monkeypatch):
    monkeypatch.setitem(sys.modules, "rapidocr", None)
    with pytest.raises(vision.VisionError, match=r"\.\[workflow\]"):
        vision.ScreenReader()


def test_vision_errors_use_cli_media_error_hierarchy(monkeypatch):
    assert issubclass(vision.VisionError, media.MediaError)
    assert issubclass(vision.VisionError, RuntimeError)

    def unavailable_model(**kwargs):
        raise RuntimeError("model initialization failed")

    monkeypatch.setitem(sys.modules, "rapidocr", SimpleNamespace(RapidOCR=unavailable_model))
    with pytest.raises(media.MediaError, match="model initialization failed"):
        vision.ScreenReader()


def test_reader_reuses_engine_and_raises_on_ocr_error(monkeypatch):
    created = []

    class Engine:
        def __init__(self, **kwargs):
            created.append(kwargs)

        def __call__(self, image):
            if len(created) > 1:
                raise RuntimeError("engine failed")
            return SimpleNamespace(boxes=[[[0, 0], [80, 0], [80, 20], [0, 20]]],
                                   txts=["BRB"], scores=[0.95])

    monkeypatch.setitem(sys.modules, "rapidocr", SimpleNamespace(RapidOCR=Engine))
    reader = vision.ScreenReader()
    image = np.zeros((80, 160, 3), np.uint8)
    assert reader.inspect(image)["brb"] and reader.inspect(image)["brb"] and len(created) == 1
    created.append({})
    with pytest.raises(vision.VisionError, match="unreviewed"):
        reader.inspect(image)


def test_no_text_is_not_approval_and_malformed_output_fails(monkeypatch):
    class Engine:
        def __init__(self, **kwargs):
            pass

        def __call__(self, image):
            return SimpleNamespace(boxes=None, txts=None, scores=None)

    monkeypatch.setitem(sys.modules, "rapidocr", SimpleNamespace(RapidOCR=Engine))
    reader = vision.ScreenReader()
    image = np.zeros((32, 32, 3), np.uint8)
    result = reader.inspect(image)
    assert result["status"] == "no_text" and result["warnings"]
    assert not result["accepted"] and result["runtime_ms"] is None
    reader._engine = lambda _: SimpleNamespace(boxes=[[[0, 0]]], txts=["Accepted"], scores=[1])
    with pytest.raises(vision.VisionError, match="Malformed"):
        reader.inspect(image)
    with pytest.raises(vision.VisionError, match="BGR"):
        reader.inspect(np.zeros((32, 32), np.uint8))


def test_modern_rapidocr_api(monkeypatch):
    class Engine:
        def __init__(self, *, params):
            assert params["EngineConfig.onnxruntime.intra_op_num_threads"] == 2
            assert params["EngineConfig.onnxruntime.use_cuda"] is False

        def __call__(self, image):
            return SimpleNamespace(boxes=[word("BRB")["box"]], txts=["BRB"], scores=[0.9])

    monkeypatch.setitem(sys.modules, "rapidocr", SimpleNamespace(RapidOCR=Engine))
    result = vision.ScreenReader().inspect(np.zeros((32, 32, 3), np.uint8))
    assert result["brb"]
    assert json.loads(json.dumps(result, allow_nan=False))["words"][0]["text"] == "BRB"


def test_endpoints_and_group_padding_respect_source():
    info = MediaInfo(duration=10, fps=10, width=320, height=180)
    intervals = vision._intervals([(4, 6), (0, 2.5), (2, 4), (9, 10)], 10)
    assert intervals == [(0, 6), (9, 10)]
    times = vision._sample_times(intervals, 2, info)
    assert times == [0, 2, 4, 6, 9, 9.9]
    ranges = vision._brb_ranges([{"time": t, "brb": True} for t in (0, 1, 9.9)], 1, 10)
    assert [(r["start"], r["end"]) for r in ranges] == [(0, 2), (8.9, 10)]
    assert not vision._brb_ranges([{"time": 2, "brb": False}], 1, 10)


def test_fractional_container_duration_snaps_final_sample_to_frame_grid():
    info = MediaInfo(duration=11140.12, fps=30, width=1280, height=720)
    assert vision._sample_times([(0, info.duration)], 60, info)[-1] == pytest.approx(11140.066666667)


@pytest.mark.parametrize("step", [0, -1, float("nan"), float("inf")])
def test_reject_invalid_step(step):
    with pytest.raises(vision.VisionError):
        vision._sample_times([(0, 1)], step, MediaInfo(duration=2, fps=30, width=32, height=32))


@pytest.mark.parametrize("intervals", [[], [(0, 0)], [(-1, 2)], [(1, 4)], [(float("nan"), 1)], [None]])
def test_reject_invalid_intervals(intervals):
    with pytest.raises(vision.VisionError):
        vision._intervals(intervals, 3)


def test_scan_error_persists_failed_not_clean(workspace, monkeypatch):
    info = MediaInfo(duration=3, fps=30, width=32, height=32)
    monkeypatch.setattr(vision, "_source_info", lambda _: (workspace / "source.mp4", info))
    monkeypatch.setattr(vision, "_frames", lambda *_: iter([(0, np.zeros((32, 32, 3), np.uint8))]))

    class BrokenReader:
        def inspect(self, image):
            raise RuntimeError("OCR exploded")

    monkeypatch.setattr(vision, "ScreenReader", BrokenReader)
    with pytest.raises(vision.VisionError, match="OCR exploded"):
        vision.scan_intervals(workspace / "source.mp4", [(0, 2)], workspace)
    report = json.loads((workspace / "report.json").read_text())
    assert report["coverage"]["status"] == "failed"
    assert report["coverage"]["certified_clean"] is False
    assert report["coverage"]["requested_samples_complete"] is False


def test_missing_dependency_persists_incomplete_report(workspace, monkeypatch):
    info = MediaInfo(duration=3, fps=30, width=32, height=32)
    monkeypatch.setattr(vision, "_source_info", lambda _: (workspace / "source.mp4", info))
    monkeypatch.setitem(sys.modules, "rapidocr", None)
    with pytest.raises(vision.VisionError, match="unavailable"):
        vision.scan_intervals(workspace / "source.mp4", [(0, 2)], workspace)
    report = json.loads((workspace / "report.json").read_text())
    assert report["coverage"]["status"] == "failed"
    assert not report["coverage"]["requested_samples_complete"]


def test_short_decode_is_not_success(workspace, monkeypatch):
    info = MediaInfo(duration=3, fps=30, width=32, height=32)
    monkeypatch.setattr(vision, "_source_info", lambda _: (workspace / "source.mp4", info))
    monkeypatch.setattr(vision, "_frames", lambda *_: iter([]))
    monkeypatch.setattr(vision, "ScreenReader", lambda: None)
    with pytest.raises(vision.VisionError, match="before all planned"):
        vision.scan_intervals(workspace / "source.mp4", [(0, 2)], workspace)
    assert json.loads((workspace / "report.json").read_text())["coverage"]["status"] == "failed"


def test_cancel_before_ocr(workspace, monkeypatch):
    event = threading.Event()
    event.set()
    monkeypatch.setattr(vision, "ScreenReader", lambda: pytest.fail("must not load OCR"))
    with pytest.raises(vision.VisionError, match="cancelled"):
        vision.scan_intervals(workspace / "missing.mp4", [(0, 1)], workspace, cancel=event)


def test_cancel_during_scan_persists_incomplete_report(workspace, monkeypatch):
    info = MediaInfo(duration=3, fps=30, width=32, height=32)
    monkeypatch.setattr(vision, "_source_info", lambda _: (workspace / "source.mp4", info))
    monkeypatch.setattr(vision, "_frames", lambda *_: iter(
        [(t, np.zeros((32, 32, 3), np.uint8)) for t in (0, 1, 2)]))
    monkeypatch.setattr(vision, "ScreenReader", lambda: SimpleNamespace(
        inspect=lambda _: vision._classify_words([])))
    event = threading.Event()
    with pytest.raises(vision.VisionError, match="cancelled"):
        vision.scan_intervals(workspace / "source.mp4", [(0, 2)], workspace,
                              progress=lambda *_: event.set(), cancel=event)
    report = json.loads((workspace / "report.json").read_text())
    assert report["coverage"]["status"] == "cancelled"
    assert not report["coverage"]["requested_samples_complete"]
    assert report["coverage"]["completed_samples"] == 1


def test_disjoint_intervals_keep_anchor_frames_without_false_scene_comparison(workspace, monkeypatch):
    info = MediaInfo(duration=10, fps=30, width=32, height=32)
    monkeypatch.setattr(vision, "_source_info", lambda _: (workspace / "source.mp4", info))
    monkeypatch.setattr(vision, "_frames", lambda *_: iter(
        [(t, np.zeros((32, 32, 3), np.uint8)) for t in (0, 1, 5, 6)]))
    monkeypatch.setattr(vision, "ScreenReader", lambda: SimpleNamespace(
        inspect=lambda _: vision._classify_words([])))
    report = vision.scan_intervals(workspace / "source.mp4", [(0, 1), (5, 6)], workspace)
    assert [sample["time"] for sample in report["samples"] if sample["image"]] == [0, 5]
    assert report["samples"][2]["scene_change_score"] is None


def test_overlapping_intervals_preserve_each_requested_endpoint(workspace, monkeypatch):
    info = MediaInfo(duration=10, fps=30, width=32, height=32)
    monkeypatch.setattr(vision, "_source_info", lambda _: (workspace / "source.mp4", info))

    def frames(source, times, info, cancel):
        assert times == [0, 2, 3, 4, 5, 6]
        return iter((t, np.zeros((32, 32, 3), np.uint8)) for t in times)

    monkeypatch.setattr(vision, "_frames", frames)
    monkeypatch.setattr(vision, "ScreenReader", lambda: SimpleNamespace(
        inspect=lambda _: vision._classify_words([])))
    report = vision.scan_intervals(workspace / "source.mp4", [(0, 5), (3, 6)], workspace, step=2)
    assert report["coverage"]["intervals"] == [(0, 6)]
    assert report["coverage"]["requested_intervals"] == [(0, 5), (3, 6)]
    assert [sample["time"] for sample in report["samples"] if sample["image"]] == [0, 3]


@pytest.fixture
def real_source(workspace):
    image = np.zeros((360, 640, 3), np.uint8)
    cv2.putText(image, "BE RIGHT BACK", (20, 180), cv2.FONT_HERSHEY_SIMPLEX,
                1.9, (255, 255, 255), 4, cv2.LINE_AA)
    png = workspace / "input.png"
    vision._save_image(png, image)
    source = workspace / "source [test] caf\u00e9.mp4"
    media._bounded([media.ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error",
                    "-y", "-loop", "1", "-i", str(png), "-t", "2", "-r", "10",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(source)])
    return source


def test_genuine_full_resolution_extract_and_stream(real_source, workspace):
    source, info = vision._source_info(real_source)
    frames = list(vision._frames(source, [0, 0.5, 1, 1.5], info, None))
    assert len(frames) == 4 and all(image.shape == (360, 640, 3) for _, image in frames)
    reader = SimpleNamespace(inspect=lambda _: vision._classify_words([word("BRB")]))
    result = vision.inspect_frame(real_source, 0.5, workspace / "evidence", reader)
    assert result["brb"] and Path(result["image"]).is_file()
    assert (result["width"], result["height"]) == (640, 360)
    with pytest.raises(vision.VisionError):
        vision.inspect_frame(real_source, info.duration, workspace, reader)


def test_genuine_frame_autorotation(real_source, workspace):
    rotated = workspace / "rotated.mp4"
    media._bounded([media.ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
                    "-display_rotation:v:0", "90", "-i", str(real_source), "-c", "copy", str(rotated)])
    source, info = vision._source_info(rotated)
    assert vision._frame(source, 0.5, info).shape == (640, 360, 3)


def test_stream_seek_tracks_actual_scene_timing(workspace):
    source = workspace / "scene-change.mp4"
    media._bounded([media.ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=red:size=320x180:rate=10:duration=3,"
                    "drawbox=x=0:y=0:w=iw:h=ih:color=blue:t=fill:enable='gte(t,1.5)'",
                    "-c:v", "libx264", "-preset", "ultrafast", "-an", str(source)])
    source, info = vision._source_info(source)
    frames = list(vision._frames(source, [0.5, 1, 1.5, 2, 2.5], info, None))
    assert [image[40, 40].argmax() for _, image in frames] == [2, 2, 0, 0, 0]


def test_real_rapidocr_and_synthetic_scan_if_installed(real_source, workspace):
    pytest.importorskip("rapidocr")
    report = vision.scan_intervals(real_source, [(0, 2)], workspace / "scan", step=0.5)
    assert len(report["samples"]) == 5
    assert all(sample["brb"] for sample in report["samples"])
    assert report["brb_ranges"][0]["start"] == 0 and report["brb_ranges"][0]["end"] == 2
    assert report["coverage"]["requested_samples_complete"] is True
    assert report["coverage"]["certified_clean"] is False
    assert all(Path(path).is_file() for path in report["contact_sheets"])


def test_ocr_worker_allows_windows_process_to_exit():
    pytest.importorskip("rapidocr")
    script = """
import threading
import numpy as np
from clipfarm.workflow_vision import ScreenReader
reader = ScreenReader()
worker = threading.Thread(target=lambda: reader.inspect(np.zeros((120, 200, 3), np.uint8)))
worker.start()
worker.join()
print("worker finished", flush=True)
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "worker finished" in result.stdout

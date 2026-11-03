import sys
import threading
from types import SimpleNamespace

import pytest

from clipfarm import transcribe as module
from clipfarm.media import CancelledError, MediaError
from clipfarm.models import MediaInfo


def test_chunked_transcription_offsets_without_loading_whole_audio(tmp_path, monkeypatch):
    calls = []
    recognition_options = []

    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            calls.append(command)

        def poll(self):
            return 0

    class Model:
        def __init__(self, name, **kwargs):
            assert name == "base" and kwargs["device"] == "cpu"

        def transcribe(self, path, **kwargs):
            recognition_options.append(kwargs)
            return iter([SimpleNamespace(start=1.0, end=2.0, text=" Words. ")]), None

    monkeypatch.setattr(module, "available", lambda: True)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Model))
    monkeypatch.setattr(module.subprocess, "Popen", Process)
    monkeypatch.setattr(module, "ffmpeg_exe", lambda: "ffmpeg")
    cues = module.transcribe(tmp_path / "source.mp4",
                             MediaInfo(duration=1205, width=640, height=360, fps=30),
                             "base", lambda *_: None, threading.Event(), language="en")
    assert [c.start for c in cues] == [1, 601, 1201]
    assert [c[c.index("-t") + 1] for c in calls] == ["600", "600", "5.0"]
    assert all(c[c.index("-protocol_whitelist") + 1] == "file,pipe" for c in calls)
    assert all(options["language"] == "en" for options in recognition_options)


def test_optional_transcription_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "available", lambda: False)
    with pytest.raises(MediaError, match="not installed"):
        module.transcribe(tmp_path / "source.mp4",
                          MediaInfo(duration=5, width=640, height=360, fps=30),
                          "base", lambda *_: None, threading.Event())


def test_cancel_before_loading_a_model(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "available", lambda: True)
    event = threading.Event()
    event.set()
    with pytest.raises(CancelledError):
        module.transcribe(tmp_path / "source.mp4",
                          MediaInfo(duration=5, width=640, height=360, fps=30),
                          "base", lambda *_: None, event)

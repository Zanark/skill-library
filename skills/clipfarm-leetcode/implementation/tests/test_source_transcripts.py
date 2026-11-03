import json
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest
import numpy as np

from clipfarm import source_transcripts as module
from clipfarm.media import CancelledError, MediaError
from clipfarm.models import MediaInfo


SHA = "a" * 64


def word(start, end, text):
    return SimpleNamespace(start=start, end=end, word=text)


def segment(*words, text=None):
    return SimpleNamespace(words=list(words),
                           text="".join(w.word for w in words) if text is None else text)


def info(duration=10, has_audio=True):
    return MediaInfo(duration=duration, width=640, height=360, fps=30, has_audio=has_audio)


def generate(tmp_path, **kwargs):
    return module.generate(
        tmp_path / "source.mp4", kwargs.pop("info", info()), source_sha256=kwargs.pop("sha", SHA),
        directory=tmp_path / "source-asr", progress=kwargs.pop("progress", lambda *_: None),
        cancel=kwargs.pop("cancel", threading.Event()), **kwargs)


@pytest.fixture
def native(monkeypatch):
    state = SimpleNamespace(loads=[], decodes=[], options=[], responses=[])

    class Model:
        def __init__(self, name, **kwargs):
            state.loads.append((name, kwargs))

        def transcribe(self, path, **kwargs):
            state.options.append(kwargs)
            response = state.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            if isinstance(response, tuple):
                segments, language = response
            else:
                segments, language = response, "en"
            return iter(segments), SimpleNamespace(language=language)

    def decode(source, offset, length, wav, cancel):
        state.decodes.append((offset, length))
        wav.write_bytes(b"mock decoded audio")

    monkeypatch.setattr(module, "available", lambda: True)
    monkeypatch.setattr(module, "_engine_version", lambda: "1.2.1")
    monkeypatch.setattr(module, "_extract_audio", decode)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Model))
    return state


def test_native_grouping_preserves_short_words_repeats_and_boundaries(tmp_path, native):
    text = [" Okay.", " I", " I", " think", " it", " is", " not", " working.",
            " But", " with", " this", " approach", " it", " will", " work."]
    native.responses = [[segment(*(word(i * 0.3, i * 0.3 + 0.2, t)
                                  for i, t in enumerate(text)))]]
    cues, metadata = generate(tmp_path)
    assert [cue.text for cue in cues] == [
        "Okay.", "I I think it is not working.", "But with this approach it will work."]
    assert " ".join(c.text for c in cues) == " ".join(t.strip() for t in text)
    assert cues[1].start == 0.3 and cues[1].end == pytest.approx(2.3)
    assert all(c.end > c.start for c in cues)
    assert all(a.start < b.start for a, b in zip(cues, cues[1:]))
    assert native.loads == [("small", {"device": "cpu", "compute_type": "int8"})]
    assert native.options == [{"word_timestamps": True, "vad_filter": True, "beam_size": 3}]
    assert metadata["word_timestamps"] is True
    assert metadata["origin"] == "generated" and metadata["model"] == "small"
    assert metadata["engine_version"] == "1.2.1" and metadata["language_hint"] is None
    assert metadata["detected_languages"] == ["en"]
    assert metadata["word_count"] == len(text)
    assert "not forced alignment" in metadata["timing_limitations"][0]
    assert "native ASR word-time estimates" in metadata["timing_note"]
    assert "JSON preserves actual starts and ends" in metadata["timing_note"]
    json.dumps(metadata, allow_nan=False)


@pytest.mark.parametrize("texts,step,lengths", [
    ([" a"] * 9, 0.1, [8, 1]),
    ([" abcdefghijklmnop"] * 4, 0.1, [3, 1]),
    ([" a"] * 7, 0.6, [6, 1]),
])
def test_readable_grouping_targets(tmp_path, native, texts, step, lengths):
    native.responses = [[segment(*(word(i * step, i * step + 0.6, t)
                                  for i, t in enumerate(texts)))]]
    cues, _ = generate(tmp_path)
    assert [len(c.text.split()) for c in cues] == lengths
    assert " ".join(c.text for c in cues) == " ".join(t.strip() for t in texts)


def test_single_long_word_keeps_its_real_time(tmp_path, native):
    long_word = "x" * 80
    native.responses = [[segment(word(0.3, 6, " " + long_word), word(6.1, 6.5, " done"))]]
    cues, _ = generate(tmp_path)
    assert [(c.start, c.end, c.text) for c in cues] == [(0.3, 6, long_word), (6.1, 6.5, "done")]


def test_long_silences_do_not_become_cue_duration(tmp_path, native):
    native.responses = [[segment(word(1, 1.2, " no"), word(100, 100.3, " with"),
                                 word(100.31, 100.5, " this"), word(100.51, 100.8, " approach"))]]
    cues, _ = generate(tmp_path, info=info(120))
    assert [(c.start, c.end, c.text) for c in cues] == [
        (1, 1.2, "no"), (100, 100.8, "with this approach")]


def test_native_spacing_punctuation_and_contractions(tmp_path, native):
    native.responses = [[segment(word(0, 0.2, " I"), word(0.2, 0.4, " can"),
                                 word(0.4, 0.5, "'t"), word(0.5, 0.8, "。"),
                                 word(1, 1.2, "你好"), word(1.2, 1.4, "世界。"))]]
    cues, _ = generate(tmp_path)
    assert [c.text for c in cues] == ["I can't。", "你好世界。"]


@pytest.mark.parametrize("number", [np.float64, np.float32, np.int64])
def test_native_numpy_timestamps_are_serialized_as_plain_numbers(tmp_path, native, number):
    native.responses = [[segment(word(number(1), number(2), " works."))]]
    cues, metadata = generate(tmp_path)
    assert [(c.start, c.end) for c in cues] == [(1, 2)]
    json.dumps(metadata, allow_nan=False)
    cached, _ = generate(tmp_path)
    assert cached[0].text == "works."


def test_millisecond_colliding_cue_starts_merge_without_changing_native_times(tmp_path, native):
    native.responses = [[segment(word(1.0001, 1.0002, " I."),
                                 word(1.0003, 1.0003, " not"),
                                 word(1.0004, 1.00045, " now."),
                                 word(1.0006, 1.0008, " I."),
                                 word(2, 2.3, " continue."))]]
    cues, _ = generate(tmp_path)
    assert [(c.start, c.end, c.text) for c in cues] == [
        (1.0001, 1.00045, "I. not now."), (1.0006, 1.0008, "I."), (2, 2.3, "continue.")]
    starts = [round(c.start * 1000) for c in cues]
    assert starts == [1000, 1001, 2000]
    resumed, metadata = generate(tmp_path)
    assert [round(c.start * 1000) for c in resumed] == starts
    assert [c.text for c in resumed] == [c.text for c in cues]
    assert metadata["reused_chunk_count"] == 1


def test_submillisecond_fragments_exceed_word_target_instead_of_losing_words(tmp_path, native):
    native.responses = [[segment(
        *(word(i * 0.00001, i * 0.00001 + 0.000002, " I") for i in range(9)),
        word(0.001, 0.002, " finish."))]]
    cues, _ = generate(tmp_path)
    assert [c.text for c in cues] == [" ".join(["I"] * 9), "finish."]
    assert [round(c.start * 1000) for c in cues] == [0, 1]
    assert cues[0].end == 0.000082


def test_chunk_offsets_and_temporal_seams_preserve_real_repeats(tmp_path, native):
    native.responses = [
        ([segment(word(599.2, 599.5, " go"), word(599.8, 600.2, " not"),
                  word(600.3, 600.5, " go"))], "en"),
        ([segment(word(1.2, 1.5, " go"), word(1.8, 2.2, " not"),
                  word(2.3, 2.5, " go"), word(2.6, 2.8, " go"))], "hi"),
        ([segment(word(3, 3.3, " finish."))], "en"),
    ]
    cues, metadata = generate(tmp_path, info=info(1205), language="en")
    assert native.decodes == [(0, 602), (598, 604), (1198, 7)]
    assert max(length for _, length in native.decodes) == 604
    assert " ".join(c.text for c in cues) == "go not go go finish."
    assert cues[0].start == 599.2 and cues[0].end == 600.8
    assert cues[-1].start == 1201 and cues[-1].end == 1201.3
    assert all(option["language"] == "en" for option in native.options)
    assert metadata["language_hint"] == "en" and metadata["detected_languages"] == ["en", "hi"]
    assert metadata["chunk_count"] == 3 and metadata["transcribed_chunk_count"] == 3
    assert metadata["reused_chunk_count"] == 0
    assert not (tmp_path / "source-asr" / "chunk.wav").exists()


@pytest.mark.parametrize("words,expected", [
    ([word(1, 1, " not"), word(1, 1.3, " now")], [(1, 1.3, "not now")]),
    ([word(1, 1.3, " stop."), word(1.3, 1.3, " no")], [(1, 1.3, "stop. no")]),
    ([word(1, 1.1, " I."), word(1, 1.2, " I")], [(1, 1.2, "I. I")]),
    ([word(1, 1, " I"), word(1.4, 1.6, " I")], [(1, 1.6, "I I")]),
])
def test_zero_duration_and_equal_start_words_are_merged_not_lost(tmp_path, native, words, expected):
    native.responses = [[segment(*words)]]
    cues, _ = generate(tmp_path)
    assert [(c.start, c.end, c.text) for c in cues] == expected


@pytest.mark.parametrize("words", [
    [word(1, 1, " no")],
    [word(1, 1, " not"), word(8, 8.2, " now")],
    [word(0, 0.2, " word"), word(8, 8, " no")],
])
def test_isolated_zero_duration_words_fail_instead_of_inventing_time(tmp_path, native, words):
    native.responses = [[segment(*words)]]
    with pytest.raises(MediaError, match="zero-duration"):
        generate(tmp_path)


@pytest.mark.parametrize("words", [
    [word(-0.1, 1, " no")], [word(2, 1, " no")], [word(1, 11, " no")],
    [word(float("nan"), 1, " no")], [word(0, float("inf"), " no")],
    [word(None, 1, " no")], [word(True, 2, " no")],
    [word(2, 3, " yes"), word(1, 2, " no")],
])
def test_invalid_native_timings_are_explicit_errors(tmp_path, native, words):
    native.responses = [[segment(*words)]]
    with pytest.raises(MediaError, match="Invalid native word timestamps"):
        generate(tmp_path)
    assert not list((tmp_path / "source-asr").glob("chunk-*.json"))


@pytest.mark.parametrize("speech", [
    SimpleNamespace(text=" do not omit this", words=None),
    SimpleNamespace(text=" do not omit this", words=[]),
    segment(word(1, 2, " omit this"), text=" do not omit this"),
])
def test_recognized_text_requires_complete_native_word_timestamps(tmp_path, native, speech):
    native.responses = [[speech]]
    with pytest.raises(MediaError, match="word timestamps|timestamped words"):
        generate(tmp_path)


def test_no_audio_does_not_load_or_decode(tmp_path, native):
    with pytest.raises(MediaError, match="no audio stream"):
        generate(tmp_path, info=info(has_audio=False))
    assert not native.loads and not native.decodes
    assert not (tmp_path / "source-asr").exists()


def test_original_source_is_unchanged(tmp_path, native):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original source bytes")
    native.responses = [[segment(word(1, 2, " done."))]]
    generate(tmp_path)
    assert source.read_bytes() == b"original source bytes"
    assert not list((tmp_path / "source-asr").glob("*.wav"))
    assert not list((tmp_path / "source-asr").glob("*.log"))


def test_source_may_not_be_inside_the_checkpoint_directory(tmp_path, native):
    directory = tmp_path / "source-asr"
    directory.mkdir()
    source = directory / "chunk.wav"
    source.write_bytes(b"original source bytes")
    with pytest.raises(MediaError, match="outside"):
        module.generate(source, info(), source_sha256=SHA, directory=directory,
                        progress=lambda *_: None, cancel=threading.Event())
    assert source.read_bytes() == b"original source bytes"
    assert not native.loads and not native.decodes


def test_no_speech_is_checkpointed_but_never_returns_empty_success(tmp_path, native):
    native.responses = [[], []]
    with pytest.raises(MediaError, match="No speech"):
        generate(tmp_path, info=info(605))
    assert len(native.loads) == 1 and len(native.decodes) == 2
    with pytest.raises(MediaError, match="No speech"):
        generate(tmp_path, info=info(605))
    assert len(native.loads) == 1 and len(native.decodes) == 2


def test_optional_dependency_failure_is_clear(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "available", lambda: False)
    with pytest.raises(MediaError, match="not installed"):
        generate(tmp_path)
    assert not (tmp_path / "source-asr" / "manifest.json").exists()


def test_import_failure_is_clear(tmp_path, native, monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(MediaError, match="not installed"):
        generate(tmp_path)


def test_cancellation_precedes_dependency_checks_model_loading_and_writes(tmp_path, monkeypatch):
    event = threading.Event()
    event.set()
    monkeypatch.setattr(module, "available", lambda: pytest.fail("checked dependency"))
    monkeypatch.setattr(module, "_engine_version", lambda: pytest.fail("checked ASR version"))
    with pytest.raises(CancelledError):
        generate(tmp_path, cancel=event)
    assert not (tmp_path / "source-asr").exists()


def test_cancel_from_loading_progress_prevents_model_load(tmp_path, native):
    event = threading.Event()
    with pytest.raises(CancelledError):
        generate(tmp_path, cancel=event, progress=lambda *_: event.set())
    assert not native.loads


def test_interrupted_resume_skips_speech_and_silent_chunks(tmp_path, native):
    native.responses = [[segment(word(1, 1.2, " first."))], [], RuntimeError("interrupted")]
    with pytest.raises(RuntimeError, match="interrupted"):
        generate(tmp_path, info=info(1205))
    directory = tmp_path / "source-asr"
    assert sorted(p.name for p in directory.glob("chunk-*.json")) == [
        "chunk-000000.json", "chunk-000001.json"]
    assert not (directory / "chunk.wav").exists()
    first_bytes = (directory / "chunk-000000.json").read_bytes()
    native.responses = [[segment(word(3, 3.3, " last."))]]
    cues, metadata = generate(tmp_path, info=info(1205))
    assert [c.text for c in cues] == ["first.", "last."]
    assert native.decodes == [(0, 602), (598, 604), (1198, 7), (1198, 7)]
    assert metadata["reused_chunk_count"] == 2 and metadata["transcribed_chunk_count"] == 1
    assert metadata["silent_chunk_count"] == 1
    assert (directory / "chunk-000000.json").read_bytes() == first_bytes
    assert not list(directory.glob("*.pending"))


def test_complete_cache_needs_no_model_or_decoder(tmp_path, native, monkeypatch):
    native.responses = [[segment(word(1, 1.2, " done."))]]
    cues, _ = generate(tmp_path)
    monkeypatch.setattr(module, "available", lambda: pytest.fail("checked dependency"))
    monkeypatch.setattr(module, "_load_model", lambda *_: pytest.fail("loaded model"))
    monkeypatch.setattr(module, "_extract_audio", lambda *_: pytest.fail("decoded again"))
    again, metadata = generate(tmp_path)
    assert [(c.start, c.end, c.text) for c in cues] == [(c.start, c.end, c.text) for c in again]
    assert metadata["reused_chunk_count"] == 1 and metadata["transcribed_chunk_count"] == 0


def test_complete_cache_survives_uninstalled_optional_asr(tmp_path, native, monkeypatch):
    native.responses = [[segment(word(1, 1.2, " done."))]]
    generate(tmp_path)
    monkeypatch.setattr(module, "_engine_version", lambda: None)
    monkeypatch.setattr(module, "available", lambda: pytest.fail("checked dependency"))
    cues, metadata = generate(tmp_path)
    assert cues[0].text == "done."
    assert metadata["engine_version"] == "1.2.1"
    assert metadata["reused_chunk_count"] == 1


def test_cancellation_during_lazy_recognition_keeps_completed_chunk(tmp_path, native):
    event = threading.Event()

    def interrupted():
        yield segment(word(1, 1.2, " unfinished"))
        event.set()
        yield segment(word(2, 2.3, " unfinished"))

    native.responses = [[segment(word(1, 1.2, " done."))], interrupted()]
    with pytest.raises(CancelledError):
        generate(tmp_path, info=info(605), cancel=event)
    assert len(list((tmp_path / "source-asr").glob("chunk-*.json"))) == 1
    assert not (tmp_path / "source-asr" / "chunk.wav").exists()
    event.clear()
    native.responses = [[segment(word(3, 3.3, " resumed."))]]
    cues, metadata = generate(tmp_path, info=info(605), cancel=event)
    assert [c.text for c in cues] == ["done.", "resumed."]
    assert metadata["reused_chunk_count"] == 1


@pytest.mark.parametrize("change", [
    {"sha": "b" * 64}, {"info": info(11)}, {"model_name": "base"}, {"language": "en"},
])
def test_incompatible_checkpoint_settings_fail_without_model_load(tmp_path, native, change):
    native.responses = [[segment(word(1, 2, " done."))]]
    generate(tmp_path)
    with pytest.raises(MediaError, match="Incompatible"):
        generate(tmp_path, **change)
    assert len(native.loads) == 1


@pytest.mark.parametrize("setting,value", [
    ("ALGORITHM_VERSION", module.ALGORITHM_VERSION + 1), ("_engine_version", lambda: "9.9.9"),
])
def test_incompatible_versions_fail(tmp_path, native, monkeypatch, setting, value):
    native.responses = [[segment(word(1, 2, " done."))]]
    generate(tmp_path)
    monkeypatch.setattr(module, setting, value)
    with pytest.raises(MediaError, match="Incompatible"):
        generate(tmp_path)


@pytest.mark.parametrize("filename,contents", [
    ("manifest.json", "{"), ("chunk-000000.json", "null"),
    ("chunk-000000.json", '{"payload": {}, "sha256": "wrong"}'),
    ("chunk-000000.json", '{"payload": {}, "sha256": "wrong", "payload": {}}'),
])
def test_corrupt_checkpoint_is_not_treated_as_a_cache_miss(tmp_path, native, filename, contents):
    native.responses = [[segment(word(1, 2, " done."))]]
    generate(tmp_path)
    (tmp_path / "source-asr" / filename).write_text(contents)
    with pytest.raises(MediaError, match="Corrupt"):
        generate(tmp_path)
    assert len(native.loads) == 1


@pytest.mark.parametrize("mutation", [
    lambda chunk: chunk["words"][0].update(text="changed"),
    lambda chunk: chunk["words"][0].update(start=3),
    lambda chunk: chunk.update(index=True),
    lambda chunk: chunk.update(words={}),
    lambda chunk: chunk.update(detected_language=["en"]),
    lambda chunk: chunk.pop("words"),
])
def test_checkpoint_integrity_and_shape_are_both_checked(tmp_path, native, mutation):
    native.responses = [[segment(word(1, 2, " done."))]]
    generate(tmp_path)
    path = tmp_path / "source-asr" / "chunk-000000.json"
    data = json.loads(path.read_text())
    mutation(data["payload"])
    path.write_text(json.dumps(data))
    with pytest.raises(MediaError, match="Corrupt"):
        generate(tmp_path)
    if data["payload"].get("words", [{}]) == [{"start": 1.0, "end": 2.0, "text": "changed"}]:
        return
    module._write_checkpoint(path, data["payload"])
    with pytest.raises(MediaError, match="Corrupt"):
        generate(tmp_path)
    assert len(native.loads) == 1


def test_orphan_and_unexpected_chunks_are_rejected(tmp_path, native):
    native.responses = [[segment(word(1, 2, " done."))]]
    generate(tmp_path)
    directory = tmp_path / "source-asr"
    manifest = directory / "manifest.json"
    saved = manifest.read_bytes()
    manifest.unlink()
    with pytest.raises(MediaError, match="without a manifest"):
        generate(tmp_path)
    manifest.write_bytes(saved)
    (directory / "chunk-000000.json").rename(directory / "chunk-999999.json")
    with pytest.raises(MediaError, match="unexpected chunk"):
        generate(tmp_path)


def test_atomic_checkpoint_failure_leaves_completed_chunks_resumable(tmp_path, native, monkeypatch):
    native.responses = [[segment(word(1, 2, " first."))], [segment(word(3, 4, " last."))]]
    original = module.os.replace

    def fail_second(source, destination):
        if destination.name == "chunk-000001.json":
            raise OSError("disk interrupted")
        return original(source, destination)

    monkeypatch.setattr(module.os, "replace", fail_second)
    with pytest.raises(OSError, match="disk interrupted"):
        generate(tmp_path, info=info(605))
    directory = tmp_path / "source-asr"
    assert (directory / "chunk-000000.json").exists()
    assert not (directory / "chunk-000001.json").exists()
    assert not list(directory.glob("*.pending"))
    monkeypatch.setattr(module.os, "replace", original)
    native.responses = [[segment(word(3, 4, " last."))]]
    cues, metadata = generate(tmp_path, info=info(605))
    assert [c.text for c in cues] == ["first.", "last."]
    assert metadata["reused_chunk_count"] == 1


def test_decoder_limits_local_input_and_extraction_window(tmp_path, monkeypatch):
    calls = []

    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            calls.append(command)

        def poll(self):
            return 0

    monkeypatch.setattr(module.subprocess, "Popen", Process)
    monkeypatch.setattr(module, "ffmpeg_exe", lambda: "ffmpeg")
    module._extract_audio(tmp_path / "source.mp4", 598, 604, tmp_path / "chunk.wav",
                          threading.Event())
    command = calls[0]
    assert command[command.index("-ss") + 1] == "598"
    assert command[command.index("-t") + 1] == "604"
    assert command[command.index("-protocol_whitelist") + 1] == "file,pipe"
    assert command[command.index("-ar") + 1] == "16000"
    assert command[command.index("-ac") + 1] == "1"
    assert not (tmp_path / "chunk.log").exists()


@pytest.mark.parametrize("timeout", [False, True])
def test_decoder_cancellation_terminates_and_reaps_only_owned_process(tmp_path, monkeypatch, timeout):
    state = SimpleNamespace(terminated=False, killed=False, waits=[])
    event = threading.Event()

    class Process:
        returncode = None

        def __init__(self, *args, **kwargs):
            event.set()

        def poll(self):
            return self.returncode

        def terminate(self):
            state.terminated = True

        def kill(self):
            state.killed = True

        def wait(self, timeout=None):
            state.waits.append(timeout)
            if timeout is not None and timeout_failure:
                raise subprocess.TimeoutExpired("ffmpeg", timeout)
            self.returncode = -1

    timeout_failure = timeout
    monkeypatch.setattr(module.subprocess, "Popen", Process)
    monkeypatch.setattr(module, "ffmpeg_exe", lambda: "ffmpeg")
    with pytest.raises(CancelledError):
        module._extract_audio(tmp_path / "source.mp4", 0, 10, tmp_path / "chunk.wav", event)
    assert state.terminated and state.killed == timeout
    assert state.waits == ([5, None] if timeout else [5])
    assert not (tmp_path / "chunk.log").exists()


def test_decoder_failure_is_explicit_and_log_is_cleaned(tmp_path, monkeypatch):
    class Process:
        returncode = 1

        def __init__(self, command, **kwargs):
            kwargs["stderr"].write(b"failed to decode source audio")
            kwargs["stderr"].flush()

        def poll(self):
            return self.returncode

    monkeypatch.setattr(module.subprocess, "Popen", Process)
    monkeypatch.setattr(module, "ffmpeg_exe", lambda: "ffmpeg")
    with pytest.raises(MediaError, match="failed to decode source audio"):
        module._extract_audio(tmp_path / "source.mp4", 0, 10, tmp_path / "chunk.wav",
                              threading.Event())
    assert not (tmp_path / "chunk.log").exists()

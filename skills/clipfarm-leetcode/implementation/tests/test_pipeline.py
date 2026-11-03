import subprocess
import time
from pathlib import Path

from fastapi.testclient import TestClient

from clipfarm.app import create_app
from clipfarm.media import ffmpeg_exe, probe, render
from clipfarm.models import Clip
from threading import Event
from clipfarm.transcripts import parse_transcript


def test_real_source_to_captioned_export(tmp_path):
    source = tmp_path / "original's source video.mp4"
    subprocess.run([
        ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24:duration=8",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=8",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(source),
    ], check=True, timeout=30)
    with TestClient(create_app(tmp_path / "studio data"), base_url="http://127.0.0.1") as client:
        imported = client.post("/api/projects/import", json={"path": str(source)})
        assert imported.status_code == 200, imported.text
        project = imported.json()
        route = f"/api/projects/{project['id']}"
        transcript = client.post(route + "/transcript", json={
            "filename": "captions.srt",
            "content": "1\n00:00:01,000 --> 00:00:03,000\nWhy this works.\n\n"
                       "2\n00:00:03,000 --> 00:00:05,000\nA second sentence.\n",
        })
        assert transcript.status_code == 200, transcript.text
        suggested = client.post(route + "/suggest", json={
            "min_duration": 2, "max_duration": 4, "count": 1,
        })
        assert suggested.status_code == 200, suggested.text
        project = suggested.json()
        clip = project["clips"][0]
        clip.update(start=2.2, end=4.2, layout="fit", captions=True)
        updated = client.patch(route, json={"revision": project["revision"], "clips": [clip]})
        assert updated.status_code == 200, updated.text
        started = client.post(route + "/jobs", json={"kind": "export", "clip_id": clip["id"]})
        assert started.status_code == 200, started.text
        job_id = started.json()["id"]
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            job = next(j for j in client.get(route + "/jobs").json() if j["id"] == job_id)
            if job["status"] not in ("queued", "running"):
                break
            time.sleep(0.15)
        assert job["status"] == "completed", job
        info = probe(Path(job["output"]))
        assert (info.width, info.height) == (1080, 1920)
        assert abs(info.fps - 30) < 0.1
        assert abs(info.duration - 2) < 0.15
        assert info.has_audio
        srt = client.get(f"/api/jobs/{job_id}/subtitles")
        assert srt.status_code == 200
        cues, _ = parse_transcript(srt.text, "result.srt", 2.2)
        assert cues[0].start == 0
        assert max(c.end for c in cues) <= 2.01
        assert "Why this works." in " ".join(c.text for c in cues)
        video = client.get(f"/api/jobs/{job_id}/video", headers={"Range": "bytes=0-63"})
        assert video.status_code == 206 and len(video.content) == 64
        assert client.get(f"/api/jobs/{job_id}/video?download=true").headers["content-disposition"].startswith("attachment")
        assert source.is_file()


def test_seek_near_end_of_two_hour_source(tmp_path):
    source = tmp_path / "two hour recording.mp4"
    subprocess.run([
        ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=blue:size=160x90:rate=1:duration=7200",
        "-c:v", "libx264", "-preset", "ultrafast", "-g", "30", "-pix_fmt", "yuv420p", str(source),
    ], check=True, timeout=90)
    info = probe(source)
    assert info.duration >= 7199
    output = tmp_path / "end of long recording.mp4"
    render(source, info, Clip(start=7100, end=7102, layout="fit", captions=False), [],
           output, True, lambda *_: None, Event())
    result = probe(output)
    assert abs(result.duration - 2) < 0.15
    assert (result.width, result.height) == (360, 640)

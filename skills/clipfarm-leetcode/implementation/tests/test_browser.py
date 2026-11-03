import os
import re
import socket
import subprocess
import threading
import time

import httpx
import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from clipfarm.app import create_app
from clipfarm.media import ffmpeg_exe, probe


@pytest.fixture
def live_studio(tmp_path):
    source = tmp_path / "browser recording.mp4"
    subprocess.run([
        ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=8",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(source),
    ], check=True, timeout=30)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    url = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(create_app(tmp_path / "browser data"), log_level="error",
                                         timeout_graceful_shutdown=5))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started, "Browser test server did not start."
    try:
        yield url, source, tmp_path
    finally:
        server.should_exit = True
        thread.join(timeout=25)
        listener.close()
        assert not thread.is_alive(), "Browser test server did not stop."


def test_studio_empty_state_and_mobile_layout(live_studio):
    url, _, root = live_studio
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=os.environ.get("CLIPFARM_BROWSER_CHANNEL", "msedge" if os.name == "nt" else "chromium"),
            headless=True,
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        expect(page).to_have_title(re.compile("ClipFarm", re.I))
        expect(page.locator("#health-label")).to_have_text("Local engine connected")
        expect(page.locator(".workspace-avatar")).to_have_count(0)
        expect(page.locator(".workspace-identity")).to_have_text("Your workspaceClipFarm Studio")
        assert page.locator("input[type=file]").count() >= 1
        theme = page.evaluate("""() => {
            const button = getComputedStyle(document.querySelector(".sidebar-import"));
            return {
                background: getComputedStyle(document.body).backgroundColor,
                accent: getComputedStyle(document.documentElement).getPropertyValue("--accent").trim(),
                buttonBackground: button.backgroundColor, buttonText: button.color,
                headerWidth: document.querySelector(".topbar").getBoundingClientRect().width
            };
        }""")
        assert theme["background"] == "rgb(0, 43, 54)"
        assert theme["accent"] == "#cd5c5c"
        assert theme["buttonBackground"] == "rgb(205, 92, 92)"
        assert theme["headerWidth"] == pytest.approx(1440, abs=1)

        def luminance(css_color):
            channels = [int(channel) / 255 for channel in re.findall(r"\d+", css_color)[:3]]
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
            return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

        assert (luminance(theme["buttonBackground"]) + 0.05) / (luminance(theme["buttonText"]) + 0.05) >= 4.5
        page.screenshot(path=str(root / "studio-desktop.png"), full_page=True)
        for width in (1280, 1024, 768, 760, 390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"), width
            expect(page.locator(".header-import")).to_be_visible()
            page.screenshot(path=str(root / f"studio-{width}.png"), full_page=True)
        page.locator(".header-import").click()
        expect(page.locator("#import-dialog")).to_be_visible()
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        page.keyboard.press("Escape")
        expect(page.locator("#import-dialog")).to_be_hidden()
        assert not errors, errors
        browser.close()


def test_browser_import_edit_analyze_preview_export_and_reopen(live_studio):
    url, source, root = live_studio
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=os.environ.get("CLIPFARM_BROWSER_CHANNEL", "msedge" if os.name == "nt" else "chromium"),
            headless=True,
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1100}, accept_downloads=True)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        expect(page.locator("#health-label")).to_have_text("Local engine connected")
        page.locator(".sidebar-import").click()
        page.locator("#path-tab").click()
        page.locator("#import-name").fill("Browser editing project")
        page.locator("#import-path").fill(str(source))
        page.locator("#path-submit").click()
        expect(page.locator("#workspace")).to_be_visible(timeout=30000)
        expect(page.locator("#project-name")).to_have_text("Browser editing project")
        expect(page.locator("#studio-navigation")).to_be_visible()
        page.locator("#studio-navigation").get_by_role("link", name="Transcript", exact=True).click()
        expect(page).to_have_url(re.compile(r"#transcript-title$"))
        expect(page.locator("#transcript-title")).to_be_in_viewport()
        page.wait_for_function("() => document.getElementById('source-video').videoWidth === 640")

        page.locator("#open-transcript").click()
        transcript = root / "transcript_granular.txt"
        transcript.write_text(
            "# Granular transcript\n"
            "00:00:00.000 Why this works.\n"
            "00:00:02.000 A complete thought.\n"
            "00:00:04.000 Another useful lesson.\n", encoding="utf-8"
        )
        assert ".txt" in page.locator("#transcript-file").get_attribute("accept")
        page.locator("#transcript-file").set_input_files(transcript)
        expect(page.locator("#transcript-filename")).to_have_value("transcript_granular.txt")
        expect(page.locator("#transcript-content")).to_have_value(transcript.read_text(encoding="utf-8"))
        page.locator("#transcript-submit").click()
        expect(page.locator("#cue-count")).to_have_text("3")
        page.locator("#open-suggest").click()
        page.locator("#suggest-min").fill("2")
        page.locator("#suggest-max").fill("4")
        page.locator("#suggest-count").fill("1")
        page.locator("#suggest-submit").click()
        expect(page.locator("#clip-count")).to_have_text("1")
        page.locator("#clip-title").fill("Browser reviewed clip")
        page.locator("#clip-start").fill("0.5")
        page.locator("#clip-end").fill("3")
        page.locator("#clip-layout").select_option("fit")
        page.locator("#caption-style").select_option("punchy")
        page.locator("#save-project").click()
        expect(page.locator("#save-project")).to_be_disabled()

        page.locator("#analyze-clip").click()
        expect(page.locator("#analysis-result")).to_be_visible(timeout=45000)
        page.locator("#clip-layout").select_option("split")
        for name, value in [("X", "0.1"), ("Y", "0.1"), ("width", "0.25"), ("height", "0.5")]:
            page.get_by_label(f"Face region {name}", exact=True).fill(value)
        for name, value in [("X", "0.4"), ("Y", "0"), ("width", "0.6"), ("height", "1")]:
            page.get_by_label(f"Content region {name}", exact=True).fill(value)
        page.locator("#clip-layout").select_option("leetcode")
        expect(page.locator("#subtitle-y")).to_have_value("0.82")
        expect(page.locator("#subtitle-y")).to_have_attribute("min", "0.77")
        expect(page.locator("#results-zoom-control")).to_be_visible()
        page.locator("#results-zoom").check()
        expect(page.locator("#results-zoom-control")).to_contain_text("camera and captions stay bright")
        expect(page.locator("#diagram-secondary-label")).to_have_text("RESULTS FOCUS")
        page.locator("#save-project").click()
        expect(page.locator("#save-project")).to_be_disabled()
        page.locator("#clip-layout").select_option("split")
        expect(page.locator("#subtitle-y")).to_have_value("0.6")
        expect(page.locator("#subtitle-y")).to_have_attribute("max", "0.63")
        expect(page.locator("#results-zoom-control")).to_be_hidden()
        expect(page.locator("#results-zoom")).not_to_be_checked()
        page.locator("#render-preview").click()
        expect(page.locator("#preview-video")).to_be_visible(timeout=60000)
        page.wait_for_function("() => document.getElementById('preview-video').videoWidth === 360")
        expect(page.locator("#analysis-result")).to_be_hidden()

        page.locator("#export-clip").click()
        export = page.locator(".job-row").filter(has=page.locator(".job-title", has_text="Export"))
        expect(export.locator(".job-status")).to_have_text("completed", timeout=60000)
        with page.expect_download() as event:
            export.get_by_role("link", name="Download MP4", exact=True).click()
        destination = root / "downloaded.mp4"
        event.value.save_as(destination)
        exported = probe(destination)
        assert (exported.width, exported.height) == (1080, 1920)
        assert abs(exported.duration - 2.5) < 0.15
        with page.expect_download() as event:
            export.get_by_role("link", name="Download SRT", exact=True).click()
        subtitles = root / "downloaded.srt"
        event.value.save_as(subtitles)
        assert "Why this works." in subtitles.read_text(encoding="utf-8")

        caption = page.locator(".cue-text").first
        caption.fill("Literal <img src=x onerror=window.injected=true> words.")
        page.locator("#save-project").click()
        expect(page.locator("#save-project")).to_be_disabled()
        expect(page.locator("#preview-status")).to_contain_text("Older render")
        assert page.evaluate("() => window.injected === undefined")
        page.screenshot(path=str(root / "studio-workspace.png"), full_page=True)
        for width in (1024, 760, 390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"), width
            expect(page.locator("#studio-navigation")).to_be_visible()
            page.screenshot(path=str(root / f"studio-workspace-{width}.png"), full_page=True)
        page.reload()
        page.get_by_role("button", name="Open Browser editing project", exact=True).click()
        expect(page.locator("#clip-title")).to_have_value("Browser reviewed clip")
        expect(page.locator(".cue-text").first).to_have_value("Literal <img src=x onerror=window.injected=true> words.")
        assert not errors, errors
        assert not page.locator("#error-banner").is_visible()
        browser.close()
    with httpx.Client(base_url=url) as client:
        project_id = client.get("/api/projects").json()[0]["id"]
        saved = client.get(f"/api/projects/{project_id}").json()
        assert saved["clips"][0]["analysis"] is None
        assert saved["clips"][0]["face_region"]["x"] == 0.1

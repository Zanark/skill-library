import html
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote

import pytest
from playwright.sync_api import expect, sync_playwright

from clipfarm import explorer, workflow

NAME = "session_20260927_174516_874000"
URI = f"clipfarm://open-session/{NAME}"


@pytest.fixture
def session(tmp_path):
    folder = tmp_path / NAME
    folder.mkdir()
    (folder / "index.html").write_text("<h1>Session</h1>", encoding="utf-8")
    return folder


def test_session_link_resolves_only_its_published_folder(session):
    assert explorer.session_folder(URI, session.parent) == session
    assert explorer.session_folder(URI + "/", session.parent) == session


@pytest.mark.parametrize("uri", [
    "file:///C:/Windows", "https://example.com", "clipfarm://open-session/../other",
    "clipfarm://open-session/%2e%2e", URI + "?path=C:\\Windows", URI + "#ignored",
    URI + '/file.mp4', URI + '" --results-dir C:\\Windows', URI + "\n",
    URI.replace("open-session", "open-session:80"), URI.replace("session_", "%73ession_"),
    "clipfarm://open-session/session_20260927_174516_874000/../../other",
])
def test_invalid_links_are_rejected_before_opening(session, uri):
    with pytest.raises(ValueError, match="Only clipfarm"):
        explorer.session_folder(uri, session.parent)


def test_missing_or_unpublished_session_is_not_opened(session):
    (session / "index.html").unlink()
    with pytest.raises(ValueError, match="no index"):
        explorer.session_folder(URI, session.parent)
    session.rmdir()
    with pytest.raises(FileNotFoundError):
        explorer.session_folder(URI, session.parent)
    with pytest.raises(ValueError, match="absolute"):
        explorer.session_folder(URI, Path("results"))


def test_redirected_session_is_rejected(session, tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    original = Path.resolve

    def redirected(path, *args, **kwargs):
        return outside if path == session else original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", redirected)
    with pytest.raises(ValueError, match="redirected"):
        explorer.session_folder(URI, session.parent)


def test_open_uses_native_folder_operation_not_a_shell(session, monkeypatch):
    calls = []
    monkeypatch.setattr(explorer.sys, "platform", "win32")
    monkeypatch.setattr(explorer.os, "startfile", lambda *args: calls.append(args), raising=False)
    assert explorer.open_session(URI, session.parent) == session
    assert calls == [(str(session), "explore")]


def test_unsupported_platform_and_native_failure_are_explicit(session, monkeypatch, capsys):
    monkeypatch.setattr(explorer.sys, "platform", "linux")
    with pytest.raises(ValueError, match="Windows"):
        explorer.open_session(URI, session.parent)
    monkeypatch.setattr(explorer.sys, "platform", "win32")

    def denied(*args):
        raise OSError("native launch denied")

    monkeypatch.setattr(explorer.os, "startfile", denied, raising=False)
    assert explorer.main(["open", "--results-dir", str(session.parent), "--", URI]) == 1
    assert "native launch denied" in capsys.readouterr().err


def test_registers_only_owned_per_user_protocol(session, monkeypatch):
    values = {}
    current_owner = None

    class Key:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def open_key(hive, path):
        if current_owner is None:
            raise FileNotFoundError(path)
        return Key(path)

    def query(key, name):
        return current_owner, 1

    def create(hive, path):
        assert hive == "CURRENT_USER"
        return Key(path)

    registry = SimpleNamespace(
        HKEY_CLASSES_ROOT="CLASSES_ROOT", HKEY_CURRENT_USER="CURRENT_USER", REG_SZ=1,
        OpenKey=open_key, QueryValueEx=query, CreateKey=create,
        SetValueEx=lambda key, name, unused, kind, value: values.update({(key.path, name): value}),
    )
    executable = session.parent / "python installation" / "python.exe"
    executable.parent.mkdir()
    executable.with_name("pythonw.exe").touch()
    monkeypatch.setattr(explorer.sys, "platform", "win32")
    monkeypatch.setattr(explorer.sys, "executable", str(executable))
    monkeypatch.setitem(sys.modules, "winreg", registry)
    command = explorer.install_protocol(session.parent)
    assert command.endswith('--from-browser -- "%1"')
    assert f'"{executable.with_name("pythonw.exe")}"' in command
    assert "-m clipfarm explorer open --results-dir" in command
    assert values[(explorer.PROTOCOL_KEY, "ClipFarmResultsRoot")] == str(session.parent)
    assert values[(explorer.PROTOCOL_KEY, "URL Protocol")] == ""
    assert values[(explorer.PROTOCOL_KEY + r"\shell\open\command", "")] == command
    current_owner = "Some other application"
    values.clear()
    with pytest.raises(ValueError, match="another application"):
        explorer.install_protocol(session.parent)
    assert not values
    current_owner = explorer.PROTOCOL_OWNER
    assert explorer.install_protocol(session.parent) == command


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("style_tag", ["style", "STYLE"])
def test_header_injection_preserves_script_and_other_csp_directives(ending, style_tag):
    css = "body{color:white}" + ending + "h1{color:red}"
    old_hash = explorer._css_hash(css)
    policy = f"default-src 'none'; style-src '{old_hash}'; script-src '{old_hash}'; connect-src 'none'"
    source = (
        f'<meta http-equiv="Content-Security-Policy" content="{html.escape(policy, quote=True)}">'
        f"<{style_tag}>{css}</{style_tag}><h1>Session</h1><main>Original cards</main><script>original()</script>"
    )
    output = explorer.add_explorer_button(source, NAME)
    assert '</h1><div class="session-explorer">' in output
    assert 'href="./" target="_blank" rel="noopener noreferrer"' in output
    assert f'data-session-name="{NAME}"' in output
    assert "Open session folder" in output and "clipfarm://" not in output
    assert "<main>Original cards</main><script>original()</script>" in output
    parser = explorer._Policies()
    parser.feed(output)
    result = parser.values[0][1]
    assert f"style-src '{explorer._css_hash(css + explorer.EXPLORER_CSS)}'" in result
    assert f"script-src '{old_hash}'" in result
    assert "default-src 'none'" in result and "connect-src 'none'" in result
    assert explorer.add_explorer_button(output, NAME) == output


def test_injection_handles_empty_styles_and_rejects_conflicting_or_blocked_pages():
    assert explorer.EXPLORER_CSS in explorer.add_explorer_button("<style></style><h1>Session</h1>", NAME)
    with pytest.raises(ValueError, match="heading"):
        explorer.add_explorer_button("<style></style>", NAME)
    with pytest.raises(ValueError, match="timestamped"):
        explorer.add_explorer_button("<style></style><h1>Session</h1>", "../other")
    with pytest.raises(ValueError, match="conflicts"):
        explorer.add_explorer_button('<h1>Session</h1><a id="open-session-explorer">Other</a>', NAME)
    source = '<meta http-equiv="Content-Security-Policy" content="style-src \'none\'"><style></style><h1>S</h1>'
    with pytest.raises(ValueError, match="CSP"):
        explorer.add_explorer_button(source, NAME)


@pytest.mark.parametrize("attribute", ['id="open-session-explorer"', "id='open-session-explorer'", "id=open-session-explorer"])
def test_existing_control_variations_are_not_duplicated(attribute):
    with pytest.raises(ValueError, match="conflicts"):
        explorer.add_explorer_button(f"<style></style><h1>Session</h1><a {attribute}>Other</a>", NAME)


def test_csp_without_style_restrictions_still_accepts_button():
    source = '<meta http-equiv="Content-Security-Policy" content="script-src \'none\'"><style></style><h1>S</h1>'
    assert 'href="./"' in explorer.add_explorer_button(source, NAME)


def test_legacy_header_is_upgraded_without_changing_any_other_bytes():
    legacy = (
        '<div class="session-explorer"><a id="open-session-explorer" '
        f'href="{URI}" '
        'title="Open this session folder using the local ClipFarm Windows handler">'
        'Open in Explorer</a><span>Windows may ask you to allow the local handler.</span></div>'
    )
    css = "body{color:white}" + explorer.EXPLORER_CSS
    prefix = (
        f'<meta http-equiv="Content-Security-Policy" content="style-src \'{explorer._css_hash(css)}\';script-src \'none\'">'
        f"<style>{css}</style><h1>Session</h1>"
    )
    suffix = '<main>Authored captions and credits</main><script>existing()</script>'
    output = explorer.add_explorer_button(prefix + legacy + suffix, NAME)
    assert output.startswith(prefix) and output.endswith(suffix)
    assert output.count(explorer.EXPLORER_CSS) == 1
    assert 'href="./" target="_blank" rel="noopener noreferrer"' in output
    assert "clipfarm://" not in output and "Windows may ask" not in output
    assert explorer.add_explorer_button(output, NAME) == output
    with pytest.raises(ValueError, match="conflicts"):
        explorer.add_explorer_button(prefix + legacy.replace(NAME, "session_20261001_002903_003000") + suffix, NAME)
    with pytest.raises(ValueError, match="conflicts"):
        explorer.add_explorer_button(output, "session_20261001_002903_003000")


def test_compact_csp_updates_only_the_stylesheet_source():
    css = "body{color:white}"
    policy = f"default-src 'none';style-src '{explorer._css_hash(css)}';script-src 'none'"
    source = f'<meta http-equiv="Content-Security-Policy" content="{policy}"><style>{css}</style><h1>S</h1>'
    output = explorer.add_explorer_button(source, NAME)
    parsed = explorer._Policies()
    parsed.feed(output)
    assert parsed.values[0][1] == policy.replace(explorer._css_hash(css), explorer._css_hash(css + explorer.EXPLORER_CSS))


def test_workflow_writes_button_only_for_session_galleries(tmp_path):
    public = tmp_path / NAME
    public.mkdir()
    document = workflow._write_gallery(public).read_text(encoding="utf-8")
    assert 'href="./" target="_blank" rel="noopener noreferrer"' in document
    assert '</h1><div class="session-explorer">' in document
    assert "open-session-explorer" not in workflow._write_gallery(tmp_path).read_text(encoding="utf-8")


@pytest.mark.parametrize("relative", [Path("."), Path("one-reel"), Path("v3") / "01-song", Path("..") / "other" / "reel"])
def test_export_folder_field_uses_real_name_and_relative_browser_link(tmp_path, relative):
    gallery = tmp_path / "session"
    folder = gallery / relative
    field = explorer.export_folder_field(folder, gallery)
    assert f'data-export-folder="{folder.name}"' in field
    assert f"<code>{folder.name}</code>" in field
    expected = relative.as_posix() + "/"
    assert f'href="{expected}" target="_blank" rel="noopener noreferrer"' in field
    assert "clipfarm:" not in field
    assert ("Relative location:" in field) == (relative.parent != Path("."))


def test_export_folder_field_escapes_labels_and_url_encodes_reserved_names(tmp_path):
    folder = tmp_path / "a & b #1"
    field = explorer.export_folder_field(folder, tmp_path)
    assert '<code>a &amp; b #1</code>' in field
    assert 'href="a%20%26%20b%20%231/"' in field
    assert unquote("a%20%26%20b%20%231/") == folder.name + "/"


def test_export_folder_sort_is_case_insensitive_and_uses_name_before_parent(tmp_path):
    paths = [tmp_path / "a-source" / "Zulu", tmp_path / "z-source" / "alpha",
             tmp_path / "b-source" / "Beta"]
    assert [p.name for p in sorted(paths, key=explorer.export_folder_sort_key)] == ["alpha", "Beta", "Zulu"]


def test_workflow_folder_labels_follow_export_directory_not_title_or_cut_id(tmp_path):
    for folder, title in (("z-last", "A title"), ("Alpha-first", "Z title"), ("beta-middle", "M title")):
        workflow.write_json(tmp_path / folder / "manifest.json", {
            "cut_id": "same-internal-id", "title": title, "category": "explanation",
            "duration": 12, "review_notes": "Fixture only",
        })
    document = workflow._write_gallery(tmp_path).read_text(encoding="utf-8")
    assert document.index('data-export-folder="Alpha-first"') < document.index('data-export-folder="beta-middle"')
    assert document.index('data-export-folder="beta-middle"') < document.index('data-export-folder="z-last"')
    assert document.count('class="export-folder"') == 3
    assert '<code>same-internal-id</code>' not in document
    assert explorer.EXPORT_FOLDER_CSS in document


def test_folder_styles_keep_hashed_csp_and_existing_copy_script():
    css = "body{color:white}"
    old_hash = explorer._css_hash(css)
    policy = f"default-src 'none';style-src '{old_hash}';script-src 'none'"
    source = f'<meta http-equiv="Content-Security-Policy" content="{policy}"><style>{css}</style><script>existing()</script>'
    document = explorer.append_gallery_css(source, explorer.EXPORT_FOLDER_CSS)
    parsed = explorer._Policies()
    parsed.feed(document)
    assert parsed.values[0][1] == policy.replace(old_hash, explorer._css_hash(css + explorer.EXPORT_FOLDER_CSS))
    assert "<script>existing()</script>" in document
    assert "'unsafe-inline'" not in document


def test_actual_export_folder_label_wraps_and_opens_exact_nested_directory(session):
    folder = session / "v3" / ("long-export-" + "name-" * 14 + "#1")
    folder.mkdir(parents=True)
    (folder / "clip.mp4").touch()
    css = "body{margin:20px}main{max-width:100%;min-width:0}"
    source = (
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\';style-src \'{explorer._css_hash(css)}\'">'
        f'<style>{css}</style><main>{explorer.export_folder_field(folder, session)}</main>'
    )
    gallery = session / "index.html"
    gallery.write_text(explorer.append_gallery_css(source, explorer.EXPORT_FOLDER_CSS), encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=os.environ.get("CLIPFARM_BROWSER_CHANNEL", "msedge" if os.name == "nt" else "chromium"),
            headless=True,
        )
        page = browser.new_page(viewport={"width": 320, "height": 800})
        errors = []
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.goto(gallery.as_uri())
        label = page.locator(".export-folder")
        expect(label.locator("a code")).to_have_text(folder.name)
        expect(label.locator(".export-folder-location code")).to_have_text(str(folder.relative_to(session)))
        assert label.evaluate("el=>getComputedStyle(el).backgroundColor") == "rgb(18, 59, 73)"
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        with page.expect_popup() as opened:
            label.locator("a").click()
        directory = opened.value
        expect(directory).to_have_url(folder.as_uri() + "/")
        expect(directory.get_by_role("link", name="clip.mp4", exact=True)).to_be_visible()
        assert directory.context is page.context and directory.evaluate("window.opener===null")
        assert not errors
        browser.close()


def test_explorer_cli_is_available_outside_repo(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "clipfarm", "explorer", "--help"],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "install" in result.stdout and "open" in result.stdout


@pytest.mark.parametrize("relocated", [False, True])
def test_actual_file_gallery_opens_directory_in_same_browser_new_tab(session, tmp_path, relocated):
    css = "body{background:#002b36;color:#eee8d5;margin:20px;font:15px system-ui}h1{font-size:24px}"
    policy = f"default-src 'none'; style-src '{explorer._css_hash(css)}'; script-src 'none'"
    source = (
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{html.escape(policy, quote=True)}">'
        f'<style>{css}</style><h1>Session fixture</h1><main>Existing clip cards</main>'
    )
    gallery = session / "index.html"
    gallery.write_text(explorer.add_explorer_button(source, NAME), encoding="utf-8")
    if relocated:
        folder = tmp_path / "Moved sessions" / NAME
        folder.mkdir(parents=True)
        moved_gallery = folder / "index.html"
        moved_gallery.write_bytes(gallery.read_bytes())
        session, gallery = folder, moved_gallery
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=os.environ.get("CLIPFARM_BROWSER_CHANNEL", "msedge" if os.name == "nt" else "chromium"),
            headless=True,
        )
        page = browser.new_page()
        errors = []
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.goto(gallery.as_uri())
        button = page.get_by_role("link", name="Open session folder", exact=True)
        expect(button).to_be_visible()
        expect(button).to_have_attribute("href", "./")
        expect(button).to_have_attribute("target", "_blank")
        expect(button).to_have_attribute("rel", "noopener noreferrer")
        for width in (1280, 390, 320):
            page.set_viewport_size({"width": width, "height": 800})
            heading = page.locator("h1").bounding_box()
            assert button.bounding_box()["y"] >= heading["y"] + heading["height"]
            assert button.bounding_box()["y"] + button.bounding_box()["height"] <= page.locator("main").bounding_box()["y"]
            assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth")
            assert button.evaluate("(el) => getComputedStyle(el).backgroundColor") == "rgb(205, 92, 92)"
        page.keyboard.press("Tab")
        expect(button).to_be_focused()
        with page.context.expect_page() as opened:
            button.click()
        directory = opened.value
        expect(directory).to_have_url(session.as_uri() + "/")
        expect(directory.get_by_role("link", name="index.html", exact=True)).to_be_visible()
        assert directory.context is page.context
        assert directory.evaluate("window.opener === null")
        assert page.url == gallery.as_uri()
        directory.close()
        assert not errors
        browser.close()

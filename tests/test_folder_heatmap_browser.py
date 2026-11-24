import json
from pathlib import Path
import tempfile
import unittest

from test_folder_heatmap import heatmap

try:
    from playwright.sync_api import Error as PlaywrightError, sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, "Optional Playwright is not installed.")
class FolderHeatmapBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(channel="msedge", headless=True)
        except PlaywrightError as exc:
            cls.playwright.stop()
            raise unittest.SkipTest(f"Optional Edge browser is unavailable: {exc}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "synthetic-root"
        self.root.mkdir()
        for name, sizes in [("folder-alpha", [1024, 1024]), ("folder-bravo", [1000]),
                            ("folder-charlie", [10] * 5), ("folder-empty", [])]:
            folder = self.root / name
            folder.mkdir()
            for i, size in enumerate(sizes):
                (folder / f"{i}.bin").write_bytes(b"x" * size)
        for name, size in [("a-big.bin", 1024**2), ("m-medium.bin", 950 * 1024),
                           ("z-small.bin", 900 * 1024)]:
            (self.root / name).write_bytes(b"x" * size)
        self.output = self.base / "report"
        self.data = heatmap.scan(self.root)
        heatmap.save(self.data, self.output)
        self.page = self.browser.new_page(viewport={"width": 1440, "height": 1000})
        self.addCleanup(self.page.close)
        self.errors = []
        self.external_requests = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.on("request", lambda r: self.external_requests.append(r.url)
                     if r.url.startswith(("http:", "https:")) else None)
        self.load()

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.assertEqual(self.external_requests, [])

    def load(self):
        self.page.goto((self.output / "index.html").as_uri())
        self.page.wait_for_selector("#map .tile")

    def names(self):
        return self.page.locator("#rows tr td:first-child").all_text_contents()

    def file_names(self):
        return [Path(name).name for name in
                self.page.locator("#fileRows tr td:first-child").all_text_contents()]

    def header(self, table, column):
        return self.page.locator(f'#{table} th button[data-sort="{column}"]')

    def test_all_folder_headers_first_ascending_second_descending(self):
        self.assertEqual(self.page.locator('#folderTable th[aria-sort="descending"]').count(), 1)
        self.assertTrue(self.names()[0].startswith("[Files directly"))
        self.page.locator("#filter").fill("folder-")
        a, b, c, e = ["folder-" + x for x in ["alpha", "bravo", "charlie", "empty"]]
        # Size starts descending, so its first click must be ascending as well.
        cases = [("size", [e, c, b, a]), ("name", [a, b, c, e]),
                 ("percent", [e, c, b, a]), ("files", [e, b, a, c])]
        for key, ascending in cases:
            with self.subTest(column=key):
                header = self.header("folderTable", key)
                header.click()
                self.assertEqual(self.names(), ascending)
                self.assertEqual(header.locator("..").get_attribute("aria-sort"), "ascending")
                header.click()
                self.assertEqual(self.names(), list(reversed(ascending)))
                self.assertEqual(header.locator("..").get_attribute("aria-sort"), "descending")

    def test_both_direct_file_headers_and_numeric_unit_sort(self):
        self.assertEqual(self.file_names(), ["a-big.bin", "m-medium.bin", "z-small.bin"])
        size = self.header("fileTable", "size")
        size.click()
        self.assertEqual(self.file_names(), ["z-small.bin", "m-medium.bin", "a-big.bin"])
        size.click()
        self.assertEqual(self.file_names(), ["a-big.bin", "m-medium.bin", "z-small.bin"])
        name = self.header("fileTable", "name")
        name.click()
        self.assertEqual(name.locator("..").get_attribute("aria-sort"), "ascending")
        self.assertEqual(self.file_names(), ["a-big.bin", "m-medium.bin", "z-small.bin"])
        name.click()
        self.assertEqual(self.file_names(), ["z-small.bin", "m-medium.bin", "a-big.bin"])

    def test_keyboard_navigation_filter_state_and_mobile_layout(self):
        name = self.header("folderTable", "name")
        name.focus()
        self.page.keyboard.press("Enter")
        self.assertEqual(name.locator("..").get_attribute("aria-sort"), "ascending")
        self.page.get_by_role("button", name="folder-alpha", exact=True).click()
        self.assertTrue(self.page.locator("#path").inner_text().endswith("folder-alpha"))
        self.assertEqual(name.locator("..").get_attribute("aria-sort"), "ascending")
        self.page.get_by_role("button", name="Up one folder", exact=True).click()
        self.page.locator("#filter").fill("folder-empty")
        self.assertEqual(self.names(), ["folder-empty"])
        self.page.get_by_role("button", name="Home", exact=True).click()
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.wait_for_timeout(150)
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))

    def test_all_folder_percent_sort_uses_each_own_parent(self):
        child = self.root / "folder-bravo" / "only-child"
        child.mkdir()
        (child / "value.bin").write_bytes(b"x" * 1000)
        self.data = heatmap.scan(self.root)
        heatmap.save(self.data, self.output)
        self.load()
        self.page.locator("#scope").select_option("all")
        self.header("folderTable", "percent").click()
        names = self.names()
        self.assertEqual(Path(names[0]).name, "folder-empty")
        self.assertGreater(names.index(str(child)), names.index(str(self.root / "folder-alpha")))
        self.header("folderTable", "percent").click()
        self.assertLess(self.names().index(str(child)), self.names().index(str(self.root / "folder-alpha")))

    def test_global_results_sort_before_limit(self):
        # Synthetic directory metadata exercises the UI limit without 1,000 disk writes.
        data = json.loads(json.dumps(self.data))
        for i in range(1005):
            data["nodes"][0]["children"].append(len(data["nodes"]))
            data["nodes"].append(dict(name=f"entry-{i:04}", parent=0, size=0,
                                      direct=0, files=0, directFiles=0, children=[], largest=[]))
        heatmap.save(data, self.output)
        self.load()
        self.page.locator("#scope").select_option("all")
        self.page.locator("#filter").fill("entry-")
        name = self.header("folderTable", "name")
        name.click()
        self.assertEqual(len(self.names()), 1000)
        self.assertTrue(self.names()[0].endswith("entry-0000"))
        name.click()
        self.assertTrue(self.names()[0].endswith("entry-1004"))
        self.assertTrue(self.names()[-1].endswith("entry-0005"))
        self.page.locator("#filter").fill("entry-0000")
        self.assertTrue(self.names()[0].endswith("entry-0000"))


if __name__ == "__main__":
    unittest.main()

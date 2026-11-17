"""Contract tests for the research-workflows hub pages."""
from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ["The problem", "The principle", "The workflow", "Where it fails", "A case", "Adapt it"]
NAV = ["Challenges", "Start here", "Principles", "Field guide", "Essays", "About"]
HUB_PAGES = [ROOT / "index.html", ROOT / "start-here" / "index.html", ROOT / "principles" / "index.html",
             *sorted((ROOT / "challenges").glob("*/index.html"))]
FORBIDDEN = ["sk-ant-", "/Users/", "Second-Brain", "lorem ipsum", "TODO", "—"]


class _Collect(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h2: list[str] = []
        self.nav: list[str] = []
        self.cards: list[str] = []
        self._in: str | None = None
        self._nav = False
        self._buf = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "nav" and a.get("aria-label") == "Primary":
            self._nav = True
        if tag == "h2" or (tag == "a" and self._nav):
            self._in, self._buf = tag, ""
        if tag == "a" and "challenge-card" in (a.get("class") or ""):
            self.cards.append(a.get("href", ""))

    def handle_data(self, data):
        if self._in:
            self._buf += data

    def handle_endtag(self, tag):
        if tag == self._in:
            text = " ".join(self._buf.split())
            (self.h2 if tag == "h2" else self.nav).append(text)
            self._in = None
        if tag == "nav":
            self._nav = False


def collect(path: Path) -> _Collect:
    c = _Collect()
    c.feed(path.read_text(encoding="utf-8"))
    return c


def section_problems(path: Path) -> list[str]:
    found = [h for h in (re.sub(r"^\d+\s*", "", x) for x in collect(path).h2) if h in SECTIONS]
    return [] if found == SECTIONS else [f"{path}: sections are {found}, expected {SECTIONS}"]


class HubTests(unittest.TestCase):
    def test_section_checker_reports_missing_and_misordered(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.html"
            p.write_text("".join(f"<h2>{s}</h2>" for s in SECTIONS if s != "Where it fails"), encoding="utf-8")
            self.assertTrue(section_problems(p))
            p.write_text("".join(f"<h2>{s}</h2>" for s in reversed(SECTIONS)), encoding="utf-8")
            self.assertTrue(section_problems(p))
            p.write_text("".join(f"<h2>{s}</h2>" for s in SECTIONS), encoding="utf-8")
            self.assertEqual(section_problems(p), [])

    def test_hub_pages_exist(self) -> None:
        for page in HUB_PAGES[:3]:
            self.assertTrue(page.is_file(), page)
        self.assertTrue(list((ROOT / "challenges").glob("*/index.html")))

    def test_every_challenge_page_has_the_six_sections_in_order(self) -> None:
        for page in sorted((ROOT / "challenges").glob("*/index.html")):
            self.assertEqual(section_problems(page), [])

    def test_home_has_no_card_without_page(self) -> None:
        cards = collect(ROOT / "index.html").cards
        self.assertTrue(cards)
        for href in cards:
            target = ROOT / href / "index.html"
            self.assertTrue(target.is_file(), href)
            self.assertEqual(section_problems(target), [])

    def test_navigation_is_identical_on_hub_pages(self) -> None:
        for page in HUB_PAGES:
            self.assertEqual(collect(page).nav, NAV, page)

    def test_diagram_has_static_fallback(self) -> None:
        for page in sorted((ROOT / "challenges").glob("*/index.html")):
            html = page.read_text(encoding="utf-8")
            for block in re.findall(r'<div class="workflow-diagram".*?</div>', html, re.S):
                self.assertRegex(block, r"<svg|<img")

    def test_about_links_all_four_books(self) -> None:
        about = (ROOT / "about.html").read_text(encoding="utf-8") + (ROOT / "script.js").read_text(encoding="utf-8")
        for book in sorted(ROOT.glob("book-*.html")):
            self.assertIn(book.name, about)

    def test_every_legacy_url_has_target(self) -> None:
        for line in (ROOT / "tools" / "legacy-urls.txt").read_text(encoding="utf-8").split("\n"):
            if line:
                self.assertTrue((ROOT / line).is_file(), line)

    def test_rtl_pages_declare_direction(self) -> None:
        pages = list(ROOT.glob("blog/*/he/index.html"))
        self.assertTrue(pages)
        for page in pages:
            self.assertRegex(page.read_text(encoding="utf-8"), r'<html lang="he" dir="rtl"')

    def test_hub_pages_contain_no_forbidden_strings(self) -> None:
        for page in HUB_PAGES:
            text = page.read_text(encoding="utf-8")
            for bad in FORBIDDEN:
                self.assertNotIn(bad, text, f"{page}: {bad!r}")

    def test_hub_pages_keep_side_gutter_and_viewport(self) -> None:
        for page in HUB_PAGES:
            self.assertIn('name="viewport"', page.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

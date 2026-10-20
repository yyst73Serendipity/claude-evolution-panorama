"""
验证 Claude 演进全景网页的数据边界、核心内容、交互控件、来源安全和单文件交付要求。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "work" / "build-page.py"
DATA_PATH = ROOT / "work" / "timeline-data.json"
OUTPUT_PATH = ROOT / "outputs" / "claude-evolution-panorama.html"


class AssetParser(HTMLParser):
    """收集外部样式、外部脚本和链接安全属性。"""

    def __init__(self) -> None:
        super().__init__()
        self.external_scripts: list[str] = []
        self.stylesheets: list[str] = []
        self.https_links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "script" and values.get("src"):
            self.external_scripts.append(values["src"])
        if tag == "link" and "stylesheet" in values.get("rel", ""):
            self.stylesheets.append(values.get("href", ""))
        if tag == "a" and values.get("href", "").startswith("https://"):
            self.https_links.append(values)


class ClaudeEvolutionPanoramaTest(unittest.TestCase):
    """覆盖网页构建的主要功能路径与日期边界。"""

    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(BUILD_SCRIPT)], cwd=ROOT, check=True, capture_output=True, text=True)
        cls.data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        cls.html = OUTPUT_PATH.read_text(encoding="utf-8")

    def test_output_exists_and_is_substantial(self) -> None:
        self.assertTrue(OUTPUT_PATH.exists())
        self.assertGreater(OUTPUT_PATH.stat().st_size, 80_000)

    def test_timeline_has_panorama_scale(self) -> None:
        self.assertGreaterEqual(len(self.data["events"]), 80)
        categories = {event["category"] for event in self.data["events"]}
        self.assertGreaterEqual(len(categories), 8)

    def test_all_event_dates_respect_cutoff(self) -> None:
        cutoff = date.fromisoformat(self.data["cutoff"])
        for event in self.data["events"]:
            with self.subTest(title=event["title"]):
                self.assertLessEqual(date.fromisoformat(event["date"]), cutoff)
        self.assertEqual(max(event["date"] for event in self.data["events"]), self.data["cutoff"])

    def test_required_sections_and_cutoff_are_present(self) -> None:
        for section_id in ("overview", "phases", "timeline", "models", "products", "plans", "api", "migration", "insights", "method", "sources"):
            self.assertIn(f'id="{section_id}"', self.html)
        self.assertIn(self.data["cutoff"], self.html)
        self.assertIn("该日期之后的信息不在当前快照范围内", self.html)

    def test_filter_controls_are_present(self) -> None:
        for control_id in ("query", "year-filter", "category-filter", "sort-order", "toggle-details", "reset-filters", "result-count"):
            self.assertIn(f'id="{control_id}"', self.html)

    def test_core_model_and_product_milestones_are_present(self) -> None:
        expected = (
            "Claude 2", "Claude 3", "Claude 3.7", "Claude 4", "Claude 5.x",
            "Claude Code", "MCP", "Cowork", "Fable", "Mythos", "Haiku 5.5",
            "Code Review 正式可用",
        )
        for phrase in expected:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.html)

    def test_current_prices_are_present(self) -> None:
        for phrase in ("$20/月", "$100 / $200", "$20/席/月 + 用量", "$4", "$20", "$2", "$10", "$0.10", "$0.50"):
            self.assertIn(phrase, self.html)
        self.assertIn("≤100K 输入", self.html)
        self.assertIn("&gt;100K 输入", self.html)

    def test_all_timeline_sources_are_https_official_domains(self) -> None:
        allowed = ("anthropic.com", "claude.com")
        for event in self.data["events"]:
            with self.subTest(url=event["sourceUrl"]):
                self.assertTrue(event["sourceUrl"].startswith("https://"))
                self.assertTrue(any(domain in event["sourceUrl"] for domain in allowed))

    def test_external_links_use_safe_new_window_attributes(self) -> None:
        parser = AssetParser()
        parser.feed(self.html)
        self.assertGreater(len(parser.https_links), 40)
        for attrs in parser.https_links:
            with self.subTest(href=attrs.get("href")):
                self.assertEqual(attrs.get("target"), "_blank")
                self.assertEqual(attrs.get("rel"), "noopener noreferrer")

    def test_page_has_no_external_css_or_javascript_dependencies(self) -> None:
        parser = AssetParser()
        parser.feed(self.html)
        self.assertEqual(parser.external_scripts, [])
        self.assertEqual(parser.stylesheets, [])
        self.assertNotRegex(self.html, re.compile(r"@import\s+url", re.IGNORECASE))
        self.assertNotIn("fonts.googleapis.com", self.html)
        self.assertNotIn("cdn.jsdelivr.net", self.html)
        self.assertNotIn("unpkg.com", self.html)

    def test_generated_page_exposes_automatic_update_status(self) -> None:
        self.assertIn("最后自动检查", self.html)
        self.assertIn("event.autoGenerated", self.html)
        self.assertIn("自动收录", self.html)

    def test_accessibility_basics_are_present(self) -> None:
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn("prefers-reduced-motion", self.html)
        self.assertIn("<noscript>", self.html)
        self.assertIn("@media print", self.html)


if __name__ == "__main__":
    unittest.main()

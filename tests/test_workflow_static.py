"""
静态检查 GitHub Actions 自动发布工作流的权限边界、Actions 固定版本和 Pages 构建步骤。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "update-claude-panorama.yml"


class WorkflowStaticTest(unittest.TestCase):
    """不依赖 YAML 第三方库，检查工作流的关键安全与发布约束。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_has_only_required_write_permissions(self) -> None:
        self.assertIn("contents: write", self.text)
        self.assertIn("pages: write", self.text)
        self.assertIn("id-token: write", self.text)
        self.assertNotIn("pull-requests: write", self.text)

    def test_every_action_reference_has_an_explicit_major_version(self) -> None:
        references = re.findall(r"uses:\s*([^\s]+)", self.text)
        self.assertGreaterEqual(len(references), 5)
        for reference in references:
            with self.subTest(reference=reference):
                self.assertRegex(reference, r"^[\w.-]+/[\w.-]+@v\d+$")

    def test_pages_artifact_contains_index_and_standalone_filename(self) -> None:
        self.assertIn("cp outputs/claude-evolution-panorama.html site/index.html", self.text)
        self.assertIn("cp outputs/claude-evolution-panorama.html site/claude-evolution-panorama.html", self.text)
        self.assertIn("touch site/.nojekyll", self.text)


if __name__ == "__main__":
    unittest.main()

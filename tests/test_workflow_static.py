"""
静态检查 Claude 官方资料更新与 GitHub Pages 发布工作流的权限、职责和步骤顺序。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "update-claude-panorama.yml"
DEPLOY_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-claude-pages.yml"


class UpdateWorkflowStaticTests(unittest.TestCase):
    """防止官方资料更新任务扩大权限、发布职责或提交范围。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = UPDATE_WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_only_daily_schedule_and_manual_trigger_are_enabled(self) -> None:
        self.assertIn('cron: "0 0 * * *"', self.workflow)
        self.assertRegex(self.workflow, r"(?m)^\s{2}workflow_dispatch:\s*$")
        self.assertNotRegex(self.workflow, r"(?m)^\s{2}push:\s*$")

    def test_update_job_has_only_contents_write_permission(self) -> None:
        update_job = self.workflow.split("  deploy-pages:", maxsplit=1)[0]
        self.assertIn("contents: write", update_job)
        self.assertNotIn("pages: write", update_job)
        self.assertNotIn("id-token: write", update_job)
        self.assertNotIn("pull-requests: write", self.workflow)
        self.assertIn("group: claude-panorama-update", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_update_pipeline_builds_and_runs_all_tests(self) -> None:
        for token in (
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "python3 work/update-claude-panorama.py",
            "python3 work/build-page.py",
            'python3 -m unittest discover -s tests -p "test_*.py" -v',
        ):
            self.assertIn(token, self.workflow)

    def test_external_actions_have_explicit_major_versions(self) -> None:
        references = [
            reference
            for reference in re.findall(r"uses:\s*([^\s]+)", self.workflow)
            if not reference.startswith("./")
        ]
        self.assertGreaterEqual(len(references), 2)
        for reference in references:
            with self.subTest(reference=reference):
                self.assertRegex(reference, r"^[\w.-]+/[\w.-]+@v\d+$")

    def test_commit_scope_is_explicit(self) -> None:
        self.assertNotRegex(self.workflow, r"git add\s+(?:-|--\s+)?[.]\s*(?:$|\n)")
        for path in (
            "work/timeline-data.json",
            "work/source-state.json",
            "outputs/claude-evolution-panorama.html",
            "CHANGELOG.md",
        ):
            self.assertIn(path, self.workflow)
        self.assertIn("更新: 同步 Claude 官方发布", self.workflow)

    def test_deploy_is_delegated_to_reusable_workflow(self) -> None:
        self.assertIn("uses: ./.github/workflows/deploy-claude-pages.yml", self.workflow)
        for token in (
            "actions/configure-pages@v5",
            "actions/upload-pages-artifact@v4",
            "actions/deploy-pages@v4",
            "site/index.html",
        ):
            self.assertNotIn(token, self.workflow)

    def test_update_step_order_matches_safe_pipeline(self) -> None:
        tokens = (
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "python3 work/update-claude-panorama.py",
            "python3 work/build-page.py",
            "python3 -m unittest discover",
            "git add",
            "uses: ./.github/workflows/deploy-claude-pages.yml",
        )
        positions = [self.workflow.index(token) for token in tokens]
        self.assertEqual(positions, sorted(positions))


class DeployWorkflowStaticTests(unittest.TestCase):
    """保证独立发布工作流只构建、验证并部署 Pages。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_main_push_manual_and_reusable_triggers_exist(self) -> None:
        self.assertRegex(self.workflow, r"(?s)push:\s+branches:\s+- main")
        self.assertRegex(self.workflow, r"(?m)^\s{2}workflow_dispatch:\s*$")
        self.assertRegex(self.workflow, r"(?m)^\s{2}workflow_call:\s*$")

    def test_permissions_are_minimal_for_pages(self) -> None:
        for permission in ("contents: read", "pages: write", "id-token: write"):
            self.assertIn(permission, self.workflow)
        for permission in ("contents: write", "pull-requests: write", "actions: write"):
            self.assertNotIn(permission, self.workflow)
        self.assertIn("group: claude-panorama-pages", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_update_and_git_write_commands_are_absent(self) -> None:
        for token in (
            "update-claude-panorama.py",
            "git add",
            "git commit",
            "git push",
            "更新: 同步 Claude 官方发布",
        ):
            self.assertNotIn(token, self.workflow)

    def test_runtime_build_and_full_verification_exist(self) -> None:
        self.assertRegex(self.workflow, r"python-version:\s*[\"']3\.12[\"']")
        self.assertIn("python3 work/build-page.py", self.workflow)
        self.assertIn('python3 -m unittest discover -s tests -p "test_*.py" -v', self.workflow)

    def test_pages_artifact_contains_both_entries_and_nojekyll(self) -> None:
        for token in (
            "site/index.html",
            "site/claude-evolution-panorama.html",
            "site/.nojekyll",
            "actions/configure-pages@v5",
            "actions/upload-pages-artifact@v4",
            "actions/deploy-pages@v4",
        ):
            self.assertIn(token, self.workflow)

    def test_deploy_step_order_matches_safe_pipeline(self) -> None:
        tokens = (
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "python3 work/build-page.py",
            "python3 -m unittest discover",
            "site/index.html",
            "actions/configure-pages@v5",
            "actions/upload-pages-artifact@v4",
            "actions/deploy-pages@v4",
        )
        positions = [self.workflow.index(token) for token in tokens]
        self.assertEqual(positions, sorted(positions))

    def test_every_action_reference_has_an_explicit_major_version(self) -> None:
        references = re.findall(r"uses:\s*([^\s]+)", self.workflow)
        self.assertGreaterEqual(len(references), 5)
        for reference in references:
            with self.subTest(reference=reference):
                self.assertRegex(reference, r"^[\w.-]+/[\w.-]+@v\d+$")


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


class DocsContractTest(unittest.TestCase):
    def test_readme_uses_project_root_commands(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("python3 engine/quiz_bot.py --format md next", readme)
        self.assertIn("python3 tools/bank_checklist.py", readme)
        self.assertNotIn("cd engine", readme)
        self.assertNotIn("cd tools", readme)

    def test_docs_state_sync_progress_does_not_create_empty_tracking(self):
        docs = Path("README.md").read_text(encoding="utf-8") + Path("docs/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("active-only", docs)
        self.assertIn("不会为题库中的未学习题创建空 tracking 记录", docs)

    def test_codex_quiz_trigger_guidance_exists(self):
        skill = Path(".agents/skills/ai-quiz-codex/SKILL.md").read_text(encoding="utf-8")
        agents = Path("AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("name: ai-quiz-codex", skill)
        self.assertIn("开始AI刷题", skill)
        self.assertIn("engine/quiz_bot.py --format md next", skill)
        self.assertIn("data/tracking/quiz_bot_state.json", skill)
        self.assertIn("开始AI刷题", agents)
        self.assertIn("ai-quiz-codex", agents)


if __name__ == "__main__":
    unittest.main()

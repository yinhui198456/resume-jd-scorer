import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".agents" / "skills" / "weekend-lunch-plan"


class CodexSkillLayoutTests(unittest.TestCase):
    def test_skill_uses_codex_discovery_layout(self):
        self.assertTrue(SKILL_DIR.is_dir())
        self.assertTrue((SKILL_DIR / "SKILL.md").is_file())
        self.assertTrue((SKILL_DIR / "scripts" / "recipe_preflight.py").is_file())
        self.assertTrue((SKILL_DIR / "templates" / "eval-chef.md").is_file())
        self.assertTrue((SKILL_DIR / "references" / "quality-checklist.md").is_file())

    def test_skill_metadata_can_implicitly_match_lunch_prompt(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = re.search(r"^---\n(.*?)\n---", text, re.S)
        self.assertIsNotNone(frontmatter)
        meta = frontmatter.group(1)
        self.assertIn("name: weekend-lunch-plan", meta)
        self.assertIn("description:", meta)
        self.assertIn("周末午餐建议", meta)
        self.assertIn("午餐方案", meta)

    def test_agents_md_guides_plain_prompt_trigger(self):
        agents = ROOT / "AGENTS.md"
        self.assertTrue(agents.is_file())
        text = agents.read_text(encoding="utf-8")
        self.assertIn("周末午餐建议", text)
        self.assertIn("$weekend-lunch-plan", text)
        self.assertIn(".agents/skills/weekend-lunch-plan/SKILL.md", text)


if __name__ == "__main__":
    unittest.main()

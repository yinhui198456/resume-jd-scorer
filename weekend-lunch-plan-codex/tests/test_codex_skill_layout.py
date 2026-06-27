import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
SKILL_DIR = ROOT / ".agents" / "skills" / "weekend-lunch-plan"
CANONICAL_SKILL_DIR = WORKSPACE / "skills" / "weekend-lunch-plan"


class CodexSkillLayoutTests(unittest.TestCase):
    def test_skill_uses_codex_discovery_layout(self):
        self.assertTrue(SKILL_DIR.is_symlink())
        self.assertEqual(SKILL_DIR.resolve(), CANONICAL_SKILL_DIR.resolve())
        self.assertTrue(SKILL_DIR.is_dir())
        self.assertTrue((SKILL_DIR / "SKILL.md").is_file())
        self.assertTrue((SKILL_DIR / "scripts" / "recipe_preflight.py").is_file())
        self.assertTrue((SKILL_DIR / "templates" / "eval-chef.md").is_file())
        self.assertTrue((SKILL_DIR / "templates" / "eval-breakfast-validator.md").is_file())
        self.assertTrue((SKILL_DIR / "references" / "quality-checklist.md").is_file())
        self.assertTrue((SKILL_DIR / "references" / "breakfast-checklist.md").is_file())
        self.assertTrue((SKILL_DIR / "references" / "breakfast-ideas.md").is_file())

    def test_workspace_skill_is_canonical_source(self):
        self.assertTrue(CANONICAL_SKILL_DIR.is_dir())
        self.assertTrue((CANONICAL_SKILL_DIR / "SKILL.md").is_file())
        self.assertFalse((WORKSPACE / "skills" / "weekend-lunch").is_dir() and not (WORKSPACE / "skills" / "weekend-lunch").is_symlink())
        self.assertEqual((WORKSPACE / "skills" / "weekend-lunch").resolve(), CANONICAL_SKILL_DIR.resolve())

    def test_skill_metadata_can_implicitly_match_lunch_prompt(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = re.search(r"^---\n(.*?)\n---", text, re.S)
        self.assertIsNotNone(frontmatter)
        meta = frontmatter.group(1)
        self.assertIn("name: weekend-lunch-plan", meta)
        self.assertIn("description:", meta)
        self.assertIn("周末午餐建议", meta)
        self.assertIn("周末早餐建议", meta)
        self.assertIn("早餐建议", meta)
        self.assertIn("午餐方案", meta)

    def test_breakfast_sop_references_quality_files(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/breakfast-checklist.md", text)
        self.assertIn("references/breakfast-ideas.md", text)
        self.assertIn("templates/eval-breakfast-validator.md", text)
        self.assertIn("recipe_review_gate.py --meal-type breakfast", text)
        self.assertIn("record_plan.py --meal-type breakfast", text)

    def test_breakfast_ideas_capture_user_fast_breakfast_preferences(self):
        text = (SKILL_DIR / "references" / "breakfast-ideas.md").read_text(encoding="utf-8")
        for keyword in ["叮咚买菜", "煎饺", "玉米卷", "肉粽", "烧麦", "窝窝头", "生煎", "汤包", "小笼包", "米酒", "花卷", "手抓饼"]:
            self.assertIn(keyword, text)
        for method in ["电蒸锅预约", "豆浆机预约", "煎锅快煎"]:
            self.assertIn(method, text)

    def test_agents_md_guides_plain_prompt_trigger(self):
        agents = ROOT / "AGENTS.md"
        self.assertTrue(agents.is_file())
        text = agents.read_text(encoding="utf-8")
        self.assertIn("周末午餐建议", text)
        self.assertIn("周末早餐建议", text)
        self.assertIn("早餐建议", text)
        self.assertIn("Skill主源", text)
        self.assertIn("/opt/personal-agent-workspace/skills/weekend-lunch-plan", text)
        self.assertIn("项目内 `.agents/skills/weekend-lunch-plan` 只能是指向主源目录的 symlink", text)


if __name__ == "__main__":
    unittest.main()

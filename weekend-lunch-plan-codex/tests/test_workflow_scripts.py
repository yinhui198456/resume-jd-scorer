import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".agents" / "skills" / "weekend-lunch-plan"


def run_script(script, *args, data_dir=None, stdin_data=None):
    env = os.environ.copy()
    if data_dir is not None:
        env["RECIPE_DATA_DIR"] = str(data_dir)
    return subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts" / script), *args],
        input=stdin_data,
        text=True,
        capture_output=True,
        cwd=SKILL_DIR,
        env=env,
        check=False,
    )


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_skill_script(name):
    path = SKILL_DIR / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkflowScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        write_json(self.data_dir / "history.json", [])
        write_json(self.data_dir / "inventory.json", [])
        write_json(self.data_dir / "wishlist.json", [])
        write_json(self.data_dir / "dish_feedback.json", [])

        self.plan = {
            "方案A": {
                "label": "方案A",
                "dishes": [
                    {"name": "清蒸多宝鱼", "category": "大荤", "time": "18分钟", "description": "【需采购】"},
                    {"name": "白灼鲜虾", "category": "大荤", "time": "12分钟", "description": "【需采购】"},
                    {"name": "上汤空心菜", "category": "【素】", "time": "10分钟", "description": "当季上汤做法。【需采购】"},
                    {"name": "冬瓜瑶柱汤", "category": "汤", "time": "25分钟", "description": "【需采购】"},
                    {"name": "杂粮饭", "category": "主食", "time": "30分钟", "description": "【需采购】"},
                ],
            }
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_plan_upserts_selected_plan_into_history(self):
        result = run_script(
            "record_plan.py",
            "--selected",
            "方案A",
            "--date",
            "2026-06-20",
            data_dir=self.data_dir,
            stdin_data=json.dumps(self.plan, ensure_ascii=False),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        history = json.loads((self.data_dir / "history.json").read_text(encoding="utf-8"))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["date"], "2026-06-20")
        self.assertEqual(history[0]["meal_type"], "lunch")
        self.assertEqual(
            history[0]["dishes"],
            ["清蒸多宝鱼", "白灼鲜虾", "上汤空心菜", "冬瓜瑶柱汤", "杂粮饭"],
        )

        result = run_script(
            "record_plan.py",
            "--selected",
            "方案A",
            "--date",
            "2026-06-20",
            data_dir=self.data_dir,
            stdin_data=json.dumps(self.plan, ensure_ascii=False),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        history = json.loads((self.data_dir / "history.json").read_text(encoding="utf-8"))
        self.assertEqual(len(history), 1)

    def test_record_plan_keeps_breakfast_and_lunch_separate_on_same_date(self):
        breakfast_plan = {
            "方案A": {
                "label": "方案A",
                "dishes": [
                    {"name": "虾仁蛋饼", "category": "主食"},
                    {"name": "水煮蛋", "category": "蛋白"},
                    {"name": "无糖豆浆", "category": "饮品"},
                    {"name": "小番茄", "category": "果蔬"},
                ],
            }
        }

        lunch = run_script(
            "record_plan.py",
            "--selected",
            "方案A",
            "--date",
            "2026-06-20",
            data_dir=self.data_dir,
            stdin_data=json.dumps(self.plan, ensure_ascii=False),
        )
        self.assertEqual(lunch.returncode, 0, lunch.stderr + lunch.stdout)

        breakfast = run_script(
            "record_plan.py",
            "--selected",
            "方案A",
            "--date",
            "2026-06-20",
            "--meal-type",
            "breakfast",
            data_dir=self.data_dir,
            stdin_data=json.dumps(breakfast_plan, ensure_ascii=False),
        )
        self.assertEqual(breakfast.returncode, 0, breakfast.stderr + breakfast.stdout)

        history = json.loads((self.data_dir / "history.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [(entry["date"], entry["meal_type"]) for entry in history],
            [("2026-06-20", "breakfast"), ("2026-06-20", "lunch")],
        )
        self.assertEqual(history[0]["dishes"], ["虾仁蛋饼", "水煮蛋", "无糖豆浆", "小番茄"])
        self.assertEqual(history[1]["dishes"], ["清蒸多宝鱼", "白灼鲜虾", "上汤空心菜", "冬瓜瑶柱汤", "杂粮饭"])

    def test_review_gate_accepts_breakfast_structure(self):
        breakfast_plan = {
            "方案A": {
                "label": "方案A",
                "meal_type": "breakfast",
                "dishes": [
                    {"name": "虾仁蛋饼", "category": "主食", "time": "12分钟", "description": "平底锅少油；【需采购】"},
                    {"name": "水煮蛋", "category": "蛋白", "time": "10分钟", "description": "高蛋白；【需采购】"},
                    {"name": "无糖豆浆", "category": "饮品", "time": "20分钟", "description": "豆浆机制作；【需采购】"},
                    {"name": "小番茄", "category": "果蔬", "time": "3分钟", "description": "清洗即食；【需采购】"},
                ],
            }
        }

        result = run_script(
            "recipe_review_gate.py",
            "--meal-type",
            "breakfast",
            data_dir=self.data_dir,
            stdin_data=json.dumps(breakfast_plan, ensure_ascii=False),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")

    def test_review_pipeline_uses_breakfast_history_blacklist_for_breakfast_plans(self):
        write_json(
            self.data_dir / "history.json",
            [{"date": "2026-06-18", "meal_type": "lunch", "dishes": ["虾仁蛋饼"]}],
        )
        breakfast_plan = {
            "方案A": {
                "label": "方案A",
                "meal_type": "breakfast",
                "dishes": [
                    {"name": "虾仁蛋饼", "category": "主食", "time": "12分钟", "description": "少油快手；【需采购】"},
                    {"name": "水煮蛋", "category": "蛋白", "time": "10分钟", "description": "高蛋白；【需采购】"},
                    {"name": "无糖豆浆", "category": "饮品", "time": "20分钟", "description": "豆浆机制作；【需采购】"},
                    {"name": "小番茄", "category": "果蔬", "time": "3分钟", "description": "清洗即食；【需采购】"},
                ],
            }
        }

        result = run_script(
            "review_pipeline.py",
            data_dir=self.data_dir,
            stdin_data=json.dumps(breakfast_plan, ensure_ascii=False),
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "NEEDS_EVAL")
        self.assertEqual(payload["gate"]["status"], "PASS")

    def test_record_feedback_and_reminder_close_the_loop(self):
        write_json(
            self.data_dir / "history.json",
            [{"date": "2026-06-20", "dishes": ["清蒸多宝鱼", "白灼鲜虾"]}],
        )

        result = run_script(
            "record_feedback.py",
            "--dish",
            "清蒸多宝鱼",
            "--rating",
            "love",
            "--date",
            "2026-06-21",
            "--note",
            "孩子喜欢",
            data_dir=self.data_dir,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        feedback = json.loads((self.data_dir / "dish_feedback.json").read_text(encoding="utf-8"))
        self.assertEqual(feedback[0]["dish_name"], "清蒸多宝鱼")
        self.assertEqual(feedback[0]["rating"], "love")

        result = run_script(
            "feedback_reminder.py",
            "--today",
            "2026-06-21",
            "--days",
            "7",
            data_dir=self.data_dir,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        reminder = json.loads(result.stdout)
        self.assertEqual(reminder["pending_count"], 1)
        self.assertEqual(reminder["pending"][0]["dish_name"], "白灼鲜虾")

    def test_review_pipeline_needs_evals_after_gate_passes(self):
        result = run_script(
            "review_pipeline.py",
            data_dir=self.data_dir,
            stdin_data=json.dumps(self.plan, ensure_ascii=False),
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "NEEDS_EVAL")
        self.assertEqual(payload["gate"]["status"], "PASS")
        self.assertEqual(len(payload["required_evaluators"]), 3)

    def test_review_pipeline_aggregates_evals_when_provided(self):
        evals_path = self.data_dir / "evals.json"
        write_json(
            evals_path,
            {
                "validator": {"status": "PASS"},
                "chef": {"status": "PASS"},
                "redteam": {"status": "PASS"},
            },
        )

        result = run_script(
            "review_pipeline.py",
            "--evals",
            str(evals_path),
            data_dir=self.data_dir,
            stdin_data=json.dumps(self.plan, ensure_ascii=False),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["gate"]["status"], "PASS")
        self.assertEqual(payload["aggregation"]["verdict"], "PASS")

    def test_review_gate_normalizes_confirmed_menu_ingredients(self):
        review_gate = load_skill_script("recipe_review_gate.py")
        self.assertEqual(review_gate.normalize_ingredient("咖喱牛肉"), "牛肉")
        self.assertEqual(review_gate.normalize_ingredient("咖喱牛腩"), "牛肉")
        self.assertEqual(review_gate.normalize_ingredient("盐葱牛小排"), "牛肉")
        self.assertEqual(review_gate.normalize_ingredient("冬瓜丸子汤"), "猪肉")

    def test_review_pipeline_allows_explicit_user_overrides_for_recent_ingredients(self):
        write_json(
            self.data_dir / "history.json",
            [{"date": "2026-06-18", "dishes": ["盐葱牛小排", "同安封肉"]}],
        )
        plan = {
            "方案A": {
                "label": "方案A",
                "explicit_overrides": ["咖喱牛腩", "冬瓜丸子汤"],
                "dishes": [
                    {"name": "咖喱牛腩", "category": "大荤", "time": "25分钟", "description": "用户确认；【需采购】"},
                    {"name": "蒜蓉粉丝蒸扇贝", "category": "大荤", "time": "12分钟", "description": "粉丝铺底，有仪式感；【需采购】"},
                    {"name": "腐乳炒空心菜", "category": "【素】", "time": "8分钟", "description": "空心菜当季；【需采购】"},
                    {"name": "冬瓜丸子汤", "category": "汤", "time": "18分钟", "description": "冬瓜当季；【需采购】"},
                    {"name": "南瓜饭", "category": "主食", "time": "30分钟", "description": "电饭煲制作；【需采购】"},
                ],
            }
        }

        result = run_script(
            "review_pipeline.py",
            data_dir=self.data_dir,
            stdin_data=json.dumps(plan, ensure_ascii=False),
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "NEEDS_EVAL")
        self.assertEqual(payload["gate"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

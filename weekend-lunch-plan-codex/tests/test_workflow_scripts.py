import json
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


if __name__ == "__main__":
    unittest.main()

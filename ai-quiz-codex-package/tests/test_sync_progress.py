import json
import tempfile
import unittest
from pathlib import Path

from tools.sync_progress import sync


class SyncProgressTest(unittest.TestCase):
    def test_sync_keeps_tracking_active_only(self):
        bank = {
            "modules": {
                "M01_Test": {
                    "questions": [
                        {"id": "Q-M01_Test01"},
                        {"id": "Q-M01_Test02"},
                    ]
                }
            }
        }
        progress = {
            "modules_progress": {
                "M01_Test": {"topics_done": 1, "total_topics": 0}
            },
            "question_tracking": {
                "Q-M01_Test01": {
                    "module": "M01_Test",
                    "first_learned": "2026-06-19",
                    "status": "learning",
                }
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            bank_path = Path(tmp) / "bank.json"
            progress_path = Path(tmp) / "progress.json"
            bank_path.write_text(json.dumps(bank), encoding="utf-8")
            progress_path.write_text(json.dumps(progress), encoding="utf-8")

            new_count, updated_modules = sync(bank_path, progress_path)

            synced = json.loads(progress_path.read_text(encoding="utf-8"))

        self.assertEqual(new_count, 0)
        self.assertEqual(updated_modules, 1)
        self.assertEqual(synced["modules_progress"]["M01_Test"]["total_topics"], 2)
        self.assertEqual(set(synced["question_tracking"]), {"Q-M01_Test01"})

    def test_sync_warns_about_tracking_records_missing_from_bank_without_pruning(self):
        bank = {
            "modules": {
                "M01_Test": {
                    "questions": [{"id": "Q-M01_Test01"}]
                }
            }
        }
        progress = {
            "modules_progress": {
                "M01_Test": {"topics_done": 1, "total_topics": 1}
            },
            "question_tracking": {
                "Q-M01_Test01": {"first_learned": "2026-06-19"},
                "Q-Missing01": {"first_learned": "2026-06-18"},
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            bank_path = Path(tmp) / "bank.json"
            progress_path = Path(tmp) / "progress.json"
            bank_path.write_text(json.dumps(bank), encoding="utf-8")
            progress_path.write_text(json.dumps(progress), encoding="utf-8")

            new_count, updated_modules = sync(bank_path, progress_path)

            synced = json.loads(progress_path.read_text(encoding="utf-8"))

        self.assertEqual(new_count, 0)
        self.assertEqual(updated_modules, 0)
        self.assertIn("Q-Missing01", synced["question_tracking"])


if __name__ == "__main__":
    unittest.main()

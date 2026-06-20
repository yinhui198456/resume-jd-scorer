import unittest

from tools.cleanup_ghost_records import cleanup_progress


class CleanupGhostRecordsTest(unittest.TestCase):
    def test_cleanup_removes_inactive_records_and_recomputes_topics_done(self):
        progress = {
            "modules_progress": {
                "M08_Agent架构": {"topics_done": 0, "total_topics": 88}
            },
            "question_tracking": {
                "Q-M08_Agent架构01": {
                    "first_learned": "2026-06-19",
                    "module": "M08_Agent架构",
                },
                "Q-M08_Agent架构02": {
                    "first_learned": None,
                    "module": "M08_Agent架构",
                },
                "Q-M08_Agent架构03": {
                    "first_learned": "2026-06-19",
                },
            },
        }

        cleaned, stats = cleanup_progress(progress)

        self.assertEqual(stats["ghost_count"], 1)
        self.assertEqual(stats["active_count"], 2)
        self.assertEqual(set(cleaned["question_tracking"]), {"Q-M08_Agent架构01", "Q-M08_Agent架构03"})
        self.assertEqual(cleaned["question_tracking"]["Q-M08_Agent架构03"]["module"], "M08_Agent架构")
        self.assertEqual(cleaned["modules_progress"]["M08_Agent架构"]["topics_done"], 2)


if __name__ == "__main__":
    unittest.main()

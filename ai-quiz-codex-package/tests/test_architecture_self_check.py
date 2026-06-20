import unittest
from unittest.mock import patch

from tools import architecture_self_check


class ArchitectureSelfCheckTest(unittest.TestCase):
    def test_missing_cron_config_is_skipped_for_migration_package(self):
        with patch.object(architecture_self_check.os.path, "exists", return_value=False):
            result = architecture_self_check.check_cron_health()

        self.assertEqual(result["study_reminder"]["status"], "skipped")
        self.assertEqual(result["bank_update"]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()

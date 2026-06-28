#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from report_pipeline import run_validation


class ReportPipelineTests(unittest.TestCase):
    def test_pipeline_runs_validators(self):
        docx = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "output",
            "常州市金坛第一人民医院数据指挥中心二期项目-工作周报-20260622-0626.docx",
        )
        if not os.path.exists(docx):
            self.skipTest(f"generated report not found: {docx}")

        result = run_validation(docx)

        self.assertIn("structure", result)
        self.assertIn("tone", result)
        self.assertIn(result["structure"]["status"], ("PASS", "WARN", "FAIL"))
        self.assertIn(result["tone"]["status"], ("PASS", "FAIL"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

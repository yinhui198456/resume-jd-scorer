import json
import tempfile
import unittest
from pathlib import Path

from tools.check_answer_exp_consistency_v2 import find_mismatches


class AnswerExplanationConsistencyTest(unittest.TestCase):
    def test_shared_concept_prefix_is_not_a_mismatch(self):
        bank = {
            "modules": {
                "M04_Context工程": {
                    "questions": [
                        {
                            "id": "Q-M04_Context工程48",
                            "question": "Context Engineering 与 Prompt Engineering 的核心区别是什么？",
                            "options": [
                                "Prompt Engineering 关注多轮对话记忆管理，Context Engineering 仅处理单次请求的模板设计",
                                "Prompt Engineering 关注单次指令措辞，Context Engineering 管理整个上下文窗口的内容组织和注入",
                                "Context Engineering 是 Prompt Engineering 的子集，仅优化系统提示词的编写质量",
                                "两者完全等价，只是不同厂商对同一概念的不同命名方式",
                            ],
                            "answer": "B.",
                            "explanation": "Context Engineering 的范围更广：它管理所有注入 LLM 上下文窗口的内容，Prompt Engineering 只是其中单次指令措辞的部分。",
                        }
                    ]
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            bank_path = Path(tmp) / "bank.json"
            bank_path.write_text(json.dumps(bank), encoding="utf-8")

            mismatches = find_mismatches(bank_path)

        self.assertEqual(mismatches, [])

    def test_verbatim_non_answer_at_explanation_start_is_a_mismatch(self):
        bank = {
            "modules": {
                "M01_Test": {
                    "questions": [
                        {
                            "id": "Q-M01_Test01",
                            "question": "测试题？",
                            "options": [
                                "正确答案文本足够长",
                                "错误答案文本足够长，包含足够多的独特内容",
                                "另一个错误答案文本",
                                "第四个错误答案文本",
                            ],
                            "answer": "A",
                            "explanation": "错误答案文本足够长，包含足够多的独特内容，因为这里错误地解释了 B 选项。",
                        }
                    ]
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            bank_path = Path(tmp) / "bank.json"
            bank_path.write_text(json.dumps(bank), encoding="utf-8")

            mismatches = find_mismatches(bank_path)

        self.assertEqual([m["id"] for m in mismatches], ["Q-M01_Test01"])


if __name__ == "__main__":
    unittest.main()

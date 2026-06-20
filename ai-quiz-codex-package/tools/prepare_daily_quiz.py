#!/usr/bin/env python3
"""
prepare_daily_quiz.py — 确定性出题脚本

职责：
1. 读取 progress.json，计算今日到期复习题
2. 从 bank.json 读取完整题目（题干+options+answer+explanation）
3. 打乱选项顺序，同步更新 answer 字母
4. 输出 JSON 供 cron prompt 格式化推送

LLM 只负责教学/判题/反馈，绝不允许自行编造题目。

调用方式：
  python3 scripts/prepare_daily_quiz.py [progress.json路径] [bank.json路径] [日期(可选)] [复习题数(可选)] [新题数(可选)]

输出：stdout 输出 JSON，供 cron prompt 直接消费
"""

import json
import sys
import os
import random
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BANK_PATH = None
PROGRESS_PATH = None
STUDY_LOGS_DIR = None

def resolve_paths(progress_json=None, bank_json=None):
    """根据调用环境解析路径（支持 cron 调用和独立调用）"""
    global BANK_PATH, PROGRESS_PATH, STUDY_LOGS_DIR

    if bank_json and os.path.exists(bank_json):
        BANK_PATH = bank_json
    else:
        # 尝试多种可能的路径
        candidates = [
            os.path.join(ROOT_DIR, "data", "question-bank", "bank.json"),
        ]
        for c in candidates:
            if os.path.exists(c):
                BANK_PATH = c
                break

    if progress_json and os.path.exists(progress_json):
        PROGRESS_PATH = progress_json
    else:
        candidates = [
            os.path.join(ROOT_DIR, "data", "tracking", "progress.json"),
        ]
        for c in candidates:
            if os.path.exists(c):
                PROGRESS_PATH = c
                break

    if not BANK_PATH or not PROGRESS_PATH:
        print(json.dumps({"error": f"找不到文件: bank={BANK_PATH}, progress={PROGRESS_PATH}", "questions": []}, ensure_ascii=False))
        sys.exit(0)

    # 推导 study-logs 目录
    STUDY_LOGS_DIR = os.path.join(os.path.dirname(PROGRESS_PATH), "..", "study-logs")


def get_due_review_questions(progress_data, today, count=4):
    """从 progress.json 选出今日到期需要复习的题目"""
    today_str = today.strftime("%Y-%m-%d")
    due = []

    tracking = progress_data.get("question_tracking", {})
    for qid, record in tracking.items():
        if not record.get("first_learned"):
            continue
        next_review = record.get("next_review")
        if next_review and next_review <= today_str:
            due.append({
                "qid": qid,
                "module": record.get("module", ""),
                "review_count": record.get("review_count", 0),
                "confidence": record.get("confidence", 3),
            })

    # 按 review_count 升序排（积压优先），取指定数量
    due.sort(key=lambda x: x["review_count"])
    return due[:count]


def get_new_question(progress_data, bank_data, count=1):
    """选择尚未学习的新题，按模块优先级"""
    tracking = progress_data.get("question_tracking", {})
    learned_qids = set(tracking.keys())

    # 模块优先级（skill 中定义的）
    module_order = [
        "M04_Context工程", "M05_FunctionCalling", "M06_MCP", "M07_Skills",
        "M08_Agent架构", "M09_框架选型", "M11_RAG", "M13_安全评估",
        "M14_推理部署", "M15_成本优化", "M16_AgenticCoding", "M17_工程化",
        "M01_LLM基础", "M02_Transformer", "M03_Prompt工程",
        "M10_MultiAgent", "M12_Memory", "M18_系统设计",
    ]

    new_questions = []
    modules = bank_data.get("modules", {})

    for mod_name in module_order:
        if mod_name not in modules:
            continue
        for q in modules[mod_name].get("questions", []):
            qid = q["id"]
            if qid not in learned_qids:
                new_questions.append({"qid": qid, "module": mod_name, "question": q})
                if len(new_questions) >= count:
                    return new_questions

    return new_questions


def shuffle_question(q_data):
    """打乱选项顺序，同步更新 answer 字母"""
    options = list(q_data["options"])
    answer_raw = q_data["answer"].strip().rstrip(".")

    # 找到正确答案的索引
    correct_idx = ord(answer_raw) - ord("A")
    if correct_idx < 0 or correct_idx >= len(options):
        # answer 越界，返回原始数据（不崩溃）
        return q_data

    correct_text = options[correct_idx]

    # 打乱选项
    indices = list(range(len(options)))
    random.shuffle(indices)

    new_options = [options[i] for i in indices]

    # 找到正确答案在新数组中的位置
    new_answer_idx = indices.index(correct_idx)
    new_answer = chr(ord("A") + new_answer_idx)

    return {
        "id": q_data["id"],
        "module": q_data.get("module", ""),
        "question": q_data["question"],
        "options": new_options,
        "answer": new_answer + ".",
        "explanation": q_data.get("explanation", ""),
        "key_concepts": q_data.get("key_concepts", ""),
        "difficulty": q_data.get("difficulty", 1),
    }


def find_question_by_id(bank_data, qid):
    """从 bank.json 中精确查找指定 QID 的题目"""
    modules = bank_data.get("modules", {})
    for mod_name, mod_data in modules.items():
        for q in mod_data.get("questions", []):
            if q.get("id") == qid:
                return {**q, "module": mod_name}
    return None


def validate_answer_consistency(q_data):
    """检查 answer 和 explanation 是否一致（防 answer 标签错误）"""
    answer_raw = q_data.get("answer", "").strip().rstrip(".")
    explanation = q_data.get("explanation", "")

    if not answer_raw or not explanation:
        return True  # 无法验证，放行

    options = q_data.get("options", [])
    correct_idx = ord(answer_raw) - ord("A")
    if correct_idx < 0 or correct_idx >= len(options):
        return False  # answer 越界

    correct_text = options[correct_idx]

    # 检查 explanation 中是否包含对正确选项的正面描述
    # 简单启发式：explanation 不应包含否定正确答案的关键词
    negation_patterns = ["是错误的", "不正确", "不应该", "无法解决", "不是", "错误的做法"]
    for pattern in negation_patterns:
        if pattern in explanation and correct_text[:10] in explanation:
            return False

    return True


def main():
    args = sys.argv[1:]

    # 解析参数
    progress_json = args[0] if len(args) > 0 else None
    bank_json = args[1] if len(args) > 1 else None
    date_str = args[2] if len(args) > 2 else datetime.now().strftime("%Y-%m-%d")
    review_count = int(args[3]) if len(args) > 3 else 4
    new_count = int(args[4]) if len(args) > 4 else 1

    today = datetime.strptime(date_str, "%Y-%m-%d")
    resolve_paths(progress_json, bank_json)

    # 设置随机种子（保证同一天输出一致）
    random.seed(42)

    # 读取数据
    with open(BANK_PATH, "r", encoding="utf-8") as f:
        bank_data = json.load(f)

    with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
        progress_data = json.load(f)

    # 1. 选复习题
    due_review = get_due_review_questions(progress_data, today, review_count)
    review_questions = []
    for item in due_review:
        q = find_question_by_id(bank_data, item["qid"])
        if q:
            shuffled = shuffle_question(q)
            review_questions.append(shuffled)

    # 2. 选新题
    new_items = get_new_question(progress_data, bank_data, new_count)
    new_questions = []
    for item in new_items:
        q = item["question"]
        shuffled = shuffle_question({**q, "module": item["module"]})
        new_questions.append(shuffled)

    # 3. 验证一致性
    all_questions = review_questions + new_questions
    warnings = []
    for q in all_questions:
        if not validate_answer_consistency(q):
            warnings.append(f"⚠️ {q['id']} answer/explanation 可能不一致，请人工检查")

    # 4. 输出 JSON
    output = {
        "date": date_str,
        "review_questions": review_questions,
        "new_questions": new_questions,
        "warnings": warnings,
        "metadata": {
            "bank_path": BANK_PATH,
            "progress_path": PROGRESS_PATH,
            "review_due": len(due_review),
            "review_selected": len(review_questions),
            "new_selected": len(new_questions),
        }
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

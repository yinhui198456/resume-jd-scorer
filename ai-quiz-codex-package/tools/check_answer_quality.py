#!/usr/bin/env python3
"""Check answer quality in bank.json.

Detects:
1. Multiple correct answers (explanation positively validates non-answer options)
2. Obvious distractors (absolute negatives, irrelevant content, placeholder patterns)
3. Length bias (correct answer disproportionately longer than distractors)

Usage: python3 scripts/check_answer_quality.py [bank.json_path]
"""

import json
import sys
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BANK_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    ROOT_DIR / "data" / "question-bank" / "bank.json"
)

# Patterns indicating obviously wrong distractors
OBVIOUS_WRONG_PATTERNS = [
    r"完全不", r"绝对不", r"从不", r"没有任何", r"毫无",
    r"以上都不是", r"以上都不对", r"以上说法均错误",
    r"无关", r"没有关系", r"不影响",
    r"占位", r"placeholder", r"TODO",
    r"工程实践表明", r"经验表明.*?实际上",  # Placeholder distractors
]

# Length bias threshold
LENGTH_RATIO_THRESHOLD = 1.8  # If correct answer is 1.8x longer than avg distractor


def check_multiple_correct(q):
    """Check if explanation positively validates non-answer options,
    suggesting multiple correct answers exist."""
    issues = []
    qid = q.get("id", "?")
    opts = q.get("options", [])
    answer = q.get("answer", "").strip().rstrip(".")
    explanation = q.get("explanation", "")
    labels = ["A", "B", "C", "D"]

    if answer not in labels or len(opts) != 4:
        return issues

    answer_idx = labels.index(answer)

    for i, opt in enumerate(opts):
        if i == answer_idx or len(opt) < 8:
            continue

        # Check if non-answer option text appears in explanation
        opt_key = opt[:20]
        if opt_key in explanation:
            # Check if it's validated (not negated)
            context_start = max(0, explanation.find(opt_key) - 30)
            context_end = min(len(explanation), explanation.find(opt_key) + len(opt_key) + 30)
            context = explanation[context_start:context_end].lower()

            neg_words = ["不正确", "错误", "不是", "不应该", "无法", "但", "不过",
                        "仅适用于", "这种理解来源于", "混淆了", "误解", "片面",
                        "不准确", "有误", "不成立"]

            if not any(nw in context for nw in neg_words):
                issues.append({
                    "type": "multiple_correct",
                    "qid": qid,
                    "detail": f"explanation 正面提及非答案选项 {labels[i]}: {opt[:50]}..."
                })

    return issues


def check_obvious_distractors(q):
    """Check if distractors contain obviously wrong patterns."""
    issues = []
    qid = q.get("id", "?")
    opts = q.get("options", [])
    answer = q.get("answer", "").strip().rstrip(".")
    labels = ["A", "B", "C", "D"]

    if answer not in labels or len(opts) != 4:
        return issues

    answer_idx = labels.index(answer)

    for i, opt in enumerate(opts):
        if i == answer_idx:
            continue

        # Check for absolute negative patterns
        for pattern in OBVIOUS_WRONG_PATTERNS:
            if re.search(pattern, opt):
                issues.append({
                    "type": "obvious_distractor",
                    "qid": qid,
                    "detail": f"选项 {labels[i]} 含明显错误模式: {pattern} → {opt[:50]}..."
                })
                break

        # Check if distractor is suspiciously short (<30% of correct answer length)
        if answer_idx < len(opts):
            answer_len = len(opts[answer_idx])
            if answer_len > 20 and len(opt) < answer_len * 0.3:
                issues.append({
                    "type": "obvious_distractor",
                    "qid": qid,
                    "detail": f"选项 {labels[i]} 过短 ({len(opt)} vs 答案 {answer_len} 字符)"
                })

    return issues


def check_length_bias(q):
    """Check if correct answer is disproportionately longer than distractors."""
    issues = []
    qid = q.get("id", "?")
    opts = q.get("options", [])
    answer = q.get("answer", "").strip().rstrip(".")
    labels = ["A", "B", "C", "D"]

    if answer not in labels or len(opts) != 4:
        return issues

    answer_idx = labels.index(answer)
    answer_len = len(opts[answer_idx])
    distractor_lens = [len(opts[i]) for i in range(4) if i != answer_idx]
    avg_distractor_len = sum(distractor_lens) / len(distractor_lens)

    if avg_distractor_len > 0 and answer_len / avg_distractor_len > LENGTH_RATIO_THRESHOLD:
        issues.append({
            "type": "length_bias",
            "qid": qid,
            "detail": f"答案长度是干扰项的 {answer_len/avg_distractor_len:.1f}x ({answer_len} vs 平均 {avg_distractor_len:.0f})"
        })

    return issues


def main():
    with open(BANK_PATH) as f:
        bank = json.load(f)

    all_issues = []
    total = 0
    stats = {"multiple_correct": 0, "obvious_distractor": 0, "length_bias": 0}

    for mod_name, mod in bank["modules"].items():
        for q in mod.get("questions", []):
            total += 1
            all_issues.extend(check_multiple_correct(q))
            all_issues.extend(check_obvious_distractors(q))
            all_issues.extend(check_length_bias(q))

    for issue in all_issues:
        stats[issue["type"]] += 1

    print(f"总题数: {total}")
    print(f"发现问题: {len(all_issues)}")
    print(f"  - 多个正确答案: {stats['multiple_correct']}")
    print(f"  - 干扰项过于明显: {stats['obvious_distractor']}")
    print(f"  - 长度偏见: {stats['length_bias']}")

    if all_issues:
        print("\n--- 详情 ---")
        for issue in all_issues:
            print(f"  [{issue['type']}] {issue['qid']}: {issue['detail']}")

    return len(all_issues)


if __name__ == "__main__":
    exit(main())

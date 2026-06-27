#!/usr/bin/env python3
"""recipe_eval_aggregator.py v1.0 — SOP 1.5 聚合裁决脚本

输入：3 个角色的 JSON 评估结果（通过 stdin 或 --validator/--chef/--redteam 参数）
输出：最终裁决 (PASS/FAIL/FALLBACK) + 合并问题 + 改进指令

裁决规则：
- 全部 ✅ → PASS
- 任一 ❌ → FAIL（需修正后重跑，最多3次）
- 3 个中有 2+ 个失败（超时/解析错误）→ FALLBACK（主 agent 自行审核）

退出码：0=PASS, 1=FAIL, 2=FALLBACK
"""

import json
import sys
import argparse


def parse_eval_result(role, data):
    """解析单个角色的评估结果。"""
    if data is None:
        return {"role": role, "status": "ERROR", "issues": ["无评估结果"], "passed": False}

    # 标准格式：{status: "PASS"|"FAIL", issues: [...], suggestions: [...]}
    status = data.get("status", data.get("verdict", "UNKNOWN")).upper()
    issues = data.get("issues", [])
    suggestions = data.get("suggestions", [])

    if status == "PASS" or status == "✅" or "✅" in status:
        return {"role": role, "status": "PASS", "issues": [], "suggestions": suggestions, "passed": True}
    elif status == "FAIL" or status == "❌" or "❌" in status:
        return {"role": role, "status": "FAIL", "issues": issues, "suggestions": suggestions, "passed": False}
    else:
        return {"role": role, "status": "ERROR", "issues": [f"无法解析 {role} 结果：{status}"], "passed": False}


def aggregate(results):
    """聚合 3 个角色的结果，产出最终裁决。"""
    passed_count = sum(1 for r in results if r["passed"])
    error_count = sum(1 for r in results if r["status"] == "ERROR")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")

    # 合并所有问题和改进建议
    all_issues = []
    all_suggestions = []
    for r in results:
        for issue in r.get("issues", []):
            all_issues.append(f"[{r['role']}] {issue}")
        for sug in r.get("suggestions", []):
            all_suggestions.append(f"[{r['role']}] {sug}")

    # 裁决
    if error_count >= 2:
        # 2+ subagent 失败 → FALLBACK
        verdict = "FALLBACK"
        exit_code = 2
        instruction = "subagent 评估不可用（{}个失败），请主 agent 自行按 quality-checklist.md 全量审核".format(error_count)
    elif fail_count == 0 and error_count == 0:
        # 全部通过 → PASS
        verdict = "PASS"
        exit_code = 0
        instruction = "全部审核通过，方案可交付给用户"
    else:
        # 任一不通过 → FAIL
        verdict = "FAIL"
        exit_code = 1
        instruction = "发现 {} 个问题，修正全部不合格项后重新跑审核（最多3次循环）".format(len(all_issues))

    return {
        "verdict": verdict,
        "exit_code": exit_code,
        "instruction": instruction,
        "summary": {
            "validator": results[0]["status"] if len(results) > 0 else "N/A",
            "chef": results[1]["status"] if len(results) > 1 else "N/A",
            "redteam": results[2]["status"] if len(results) > 2 else "N/A",
        },
        "passed_count": passed_count,
        "fail_count": fail_count,
        "error_count": error_count,
        "issues": all_issues,
        "suggestions": all_suggestions,
        "total_issues": len(all_issues),
    }


def main():
    parser = argparse.ArgumentParser(description="聚合菜谱评估结果")
    parser.add_argument("--validator", type=str, help="校验官 JSON 结果文件路径")
    parser.add_argument("--chef", type=str, help="厨师 JSON 结果文件路径")
    parser.add_argument("--redteam", type=str, help="红队 JSON 结果文件路径")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取 JSON（格式：{validator:..., chef:..., redteam:...}）")
    args = parser.parse_args()

    results = []

    if args.stdin:
        raw = sys.stdin.read()
        if not raw.strip():
            result = aggregate([
                {"role": "validator", "status": "ERROR", "issues": ["无输入"], "passed": False},
                {"role": "chef", "status": "ERROR", "issues": ["无输入"], "passed": False},
                {"role": "redteam", "status": "ERROR", "issues": ["无输入"], "passed": False},
            ])
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(2)
        data = json.loads(raw)
        results.append(parse_eval_result("校验官", data.get("validator")))
        results.append(parse_eval_result("厨师", data.get("chef")))
        results.append(parse_eval_result("红队", data.get("redteam")))
    else:
        for role, path in [("校验官", args.validator), ("厨师", args.chef), ("红队", args.redteam)]:
            if path:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = None
            results.append(parse_eval_result(role, data))

    final = aggregate(results)
    print(json.dumps(final, ensure_ascii=False, indent=2))
    sys.exit(final["exit_code"])


if __name__ == "__main__":
    main()

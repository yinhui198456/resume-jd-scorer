#!/usr/bin/env python3
"""Run the local review gate and optionally aggregate subagent evals."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_EVALUATORS = [
    {"role": "validator", "label": "校验官", "template": "templates/eval-validator.md"},
    {"role": "chef", "label": "厨师", "template": "templates/eval-chef.md"},
    {"role": "redteam", "label": "红队", "template": "templates/eval-redteam.md"},
]


def read_plan(args):
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            return f.read()
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("无输入方案 JSON")
    json.loads(raw)
    return raw


def run_json_command(command, stdin_data):
    completed = subprocess.run(
        command,
        input=stdin_data,
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=os.environ.copy(),
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {
            "status": "ERROR",
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
        }
    return completed.returncode, payload


def template_status():
    status = []
    for item in REQUIRED_EVALUATORS:
        path = ROOT / item["template"]
        status.append({
            **item,
            "path": str(path),
            "exists": path.exists(),
        })
    return status


def main():
    parser = argparse.ArgumentParser(description="执行自动审核门，并可聚合三方审核 JSON")
    parser.add_argument("--input", help="方案 JSON 文件；省略时从 stdin 读取")
    parser.add_argument("--evals", help="三方审核结果 JSON 文件；省略时输出待审核说明")
    args = parser.parse_args()

    try:
        plan_raw = read_plan(args)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "stage": "input", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    gate_code, gate = run_json_command([sys.executable, str(ROOT / "scripts" / "recipe_review_gate.py")], plan_raw)
    if gate_code != 0:
        print(json.dumps({
            "status": "FAIL",
            "stage": "gate",
            "gate": gate,
            "required_evaluators": template_status(),
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    if not args.evals:
        print(json.dumps({
            "status": "NEEDS_EVAL",
            "stage": "subagent_eval",
            "gate": gate,
            "required_evaluators": template_status(),
            "next_step": "分别使用 3 个模板完成审核，并将 JSON 结果传给 --evals",
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    try:
        evals_raw = Path(args.evals).read_text(encoding="utf-8")
        json.loads(evals_raw)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "stage": "evals", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    agg_code, aggregation = run_json_command(
        [sys.executable, str(ROOT / "scripts" / "recipe_eval_aggregator.py"), "--stdin"],
        evals_raw,
    )
    verdict = aggregation.get("verdict", "ERROR")
    print(json.dumps({
        "status": verdict,
        "stage": "aggregation",
        "gate": gate,
        "aggregation": aggregation,
        "required_evaluators": template_status(),
    }, ensure_ascii=False, indent=2))
    sys.exit(agg_code)


if __name__ == "__main__":
    main()

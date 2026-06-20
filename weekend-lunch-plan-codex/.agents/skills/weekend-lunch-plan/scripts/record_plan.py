#!/usr/bin/env python3
"""Record a confirmed lunch plan into history.json.

Input plan format matches recipe_review_gate.py:
{ "方案A": {"label": "方案A", "dishes": [{"name": "..."}] } }
or { "方案A": [{"name": "..."}] }.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(os.environ.get("RECIPE_DATA_DIR", os.path.expanduser("~/.hermes/profiles/life/data")))
HISTORY_FILE = DATA_DIR / "history.json"


def load_json(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_plan(args):
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            return json.load(f)
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("无输入方案 JSON")
    return json.loads(raw)


def select_plan(plan_data, selected):
    if not isinstance(plan_data, dict) or not plan_data:
        raise ValueError("方案 JSON 必须是非空对象")

    if selected:
        if selected not in plan_data:
            raise ValueError(f"未找到选中方案：{selected}")
        plan = plan_data[selected]
        label = selected
    elif len(plan_data) == 1:
        label, plan = next(iter(plan_data.items()))
    else:
        raise ValueError("存在多套方案时必须提供 --selected")

    if isinstance(plan, list):
        dishes = plan
    elif isinstance(plan, dict):
        dishes = plan.get("dishes", [])
        label = plan.get("label", label)
    else:
        raise ValueError("选中方案必须是数组或包含 dishes 的对象")

    names = []
    seen = set()
    for dish in dishes:
        name = dish.get("name") if isinstance(dish, dict) else str(dish)
        if name and name not in seen:
            names.append(name)
            seen.add(name)
    if not names:
        raise ValueError("选中方案没有可记录的菜名")

    return label, names


def upsert_history(history, date, dishes):
    next_history = []
    replaced = False
    for entry in history:
        if entry.get("date") == date:
            next_history.append({"date": date, "dishes": dishes})
            replaced = True
        else:
            next_history.append(entry)
    if not replaced:
        next_history.append({"date": date, "dishes": dishes})
    next_history.sort(key=lambda x: x.get("date", ""))
    return next_history, replaced


def main():
    parser = argparse.ArgumentParser(description="记录已确认菜单到 history.json")
    parser.add_argument("--input", help="方案 JSON 文件；省略时从 stdin 读取")
    parser.add_argument("--selected", help="选中的方案 key，例如 方案A")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="记录日期，默认今天")
    args = parser.parse_args()

    try:
        plan_data = read_plan(args)
        label, dishes = select_plan(plan_data, args.selected)
        history = load_json(HISTORY_FILE)
        updated, replaced = upsert_history(history, args.date, dishes)
        save_json(HISTORY_FILE, updated)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    print(json.dumps({
        "status": "PASS",
        "date": args.date,
        "selected": label,
        "dishes": dishes,
        "dish_count": len(dishes),
        "history_file": str(HISTORY_FILE),
        "operation": "updated" if replaced else "created",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

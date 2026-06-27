#!/usr/bin/env python3
"""Record dish feedback into dish_feedback.json."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(os.environ.get("RECIPE_DATA_DIR", os.path.expanduser("~/.hermes/profiles/life/data")))
FEEDBACK_FILE = DATA_DIR / "dish_feedback.json"


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


def upsert_feedback(feedback, dish_name, rating, date, note):
    entry = {
        "dish_name": dish_name,
        "rating": rating,
        "date": date,
    }
    if note:
        entry["note"] = note

    updated = []
    replaced = False
    for item in feedback:
        if item.get("dish_name") == dish_name:
            updated.append(entry)
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(entry)
    updated.sort(key=lambda x: (x.get("date", ""), x.get("dish_name", "")))
    return updated, replaced


def main():
    parser = argparse.ArgumentParser(description="记录菜品反馈到 dish_feedback.json")
    parser.add_argument("--dish", required=True, help="菜名")
    parser.add_argument("--rating", required=True, choices=["love", "dislike", "neutral"], help="反馈评级")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="反馈日期，默认今天")
    parser.add_argument("--note", default="", help="可选备注")
    args = parser.parse_args()

    try:
        feedback = load_json(FEEDBACK_FILE)
        updated, replaced = upsert_feedback(feedback, args.dish, args.rating, args.date, args.note)
        save_json(FEEDBACK_FILE, updated)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    print(json.dumps({
        "status": "PASS",
        "dish_name": args.dish,
        "rating": args.rating,
        "date": args.date,
        "feedback_file": str(FEEDBACK_FILE),
        "operation": "updated" if replaced else "created",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

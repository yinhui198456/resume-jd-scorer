#!/usr/bin/env python3
"""List recent dishes that still need feedback."""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


DATA_DIR = Path(os.environ.get("RECIPE_DATA_DIR", os.path.expanduser("~/.hermes/profiles/life/data")))
HISTORY_FILE = DATA_DIR / "history.json"
FEEDBACK_FILE = DATA_DIR / "dish_feedback.json"


def load_json(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def build_pending(history, feedback, today, days):
    today_date = parse_date(today)
    since = today_date - timedelta(days=days)
    feedback_dishes = {item.get("dish_name") for item in feedback if item.get("dish_name")}

    pending = []
    seen = set()
    for entry in sorted(history, key=lambda x: x.get("date", "")):
        date_text = entry.get("date", "")
        try:
            cooked_date = parse_date(date_text)
        except ValueError:
            continue
        if cooked_date < since or cooked_date > today_date:
            continue
        for dish_name in entry.get("dishes", []):
            key = (date_text, dish_name)
            if dish_name in feedback_dishes or key in seen:
                continue
            pending.append({"date": date_text, "dish_name": dish_name})
            seen.add(key)
    return pending


def main():
    parser = argparse.ArgumentParser(description="输出近期待反馈菜品")
    parser.add_argument("--today", default=datetime.now().strftime("%Y-%m-%d"), help="今天日期，默认系统日期")
    parser.add_argument("--days", type=int, default=7, help="回看天数，默认 7")
    args = parser.parse_args()

    try:
        history = load_json(HISTORY_FILE)
        feedback = load_json(FEEDBACK_FILE)
        pending = build_pending(history, feedback, args.today, args.days)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    print(json.dumps({
        "status": "PASS",
        "today": args.today,
        "days": args.days,
        "pending_count": len(pending),
        "pending": pending,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

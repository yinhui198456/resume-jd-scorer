import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from digest.config import load_config
from digest.learn.models import LearningPlanCandidate
from digest.learn.sheets import FeishuSheetsClient
from digest.learn.tracker import plan_learning_write


def build_sheets_client(config):
    return FeishuSheetsClient(config.feishu_app_id, config.feishu_app_secret)


def _resolve_sheet_id(sheets: list[dict[str, object]], title: str) -> str:
    for sheet in sheets:
        if sheet.get("title") == title:
            return str(sheet["sheet_id"])
    raise ValueError("LEARNING_PLAN_SHEET_NOT_FOUND")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record a Daily AI Digest interest into Feishu learning plan")
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--source-date", required=True)
    parser.add_argument("--intent", required=True)
    parser.add_argument("--section", default="生产力项目")
    parser.add_argument("--stars", type=int)
    parser.add_argument("--now")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[3]
    config = load_config(root)
    client = build_sheets_client(config)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(ZoneInfo(config.schedule.get("timezone", "Asia/Shanghai")))
    candidate = LearningPlanCandidate(
        source_date=args.source_date,
        title=args.title,
        summary=args.summary,
        url=args.url,
        section=args.section,
        stars=args.stars,
        user_intent=args.intent,
    )

    sheet_id = _resolve_sheet_id(
        client.get_sheets(config.learning_plan_spreadsheet_token),
        config.learning_plan_sheet_title,
    )
    values = client.read_values(config.learning_plan_spreadsheet_token, sheet_id, "A1:I225")
    plan = plan_learning_write(values, candidate, now)
    payload = {"mode": "apply" if args.apply else "preview", "sheet_id": sheet_id, "plan": asdict(plan)}

    if args.apply:
        if plan.action == "append":
            result = client.append_values(config.learning_plan_spreadsheet_token, sheet_id, plan.range_name, plan.values)
        elif plan.action == "update":
            result = client.update_values(config.learning_plan_spreadsheet_token, sheet_id, plan.range_name, plan.values)
        else:
            raise ValueError(f"unknown action: {plan.action}")
        payload["result"] = result

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

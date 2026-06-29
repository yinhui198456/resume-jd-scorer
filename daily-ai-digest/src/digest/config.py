import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from digest.models import AppConfig


REQUIRED_ENVIRONMENT = (
    "MINIMAX_API_KEY",
    "MINIMAX_BASE_URL",
    "MINIMAX_MODEL",
    "CTI_FEISHU_APP_ID",
    "CTI_FEISHU_APP_SECRET",
    "DAILY_AI_DIGEST_FEISHU_CHAT_ID",
)


def load_config(root: Path) -> AppConfig:
    load_dotenv(root.parent / ".env", override=False)
    load_dotenv(Path.home() / ".claude-to-im" / "config.env", override=False)
    documents = {
        name: yaml.safe_load(
            (root / "configs" / f"{name}.yml").read_text(encoding="utf-8")
        )
        or {}
        for name in ("sources", "filters", "topics", "schedule")
    }
    values = {name: os.environ.get(name, "") for name in REQUIRED_ENVIRONMENT}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ValueError(f"missing environment variables: {','.join(missing)}")

    weights = documents["filters"].get("weights", {})
    if weights and abs(sum(float(value) for value in weights.values()) - 1.0) > 1e-9:
        raise ValueError("filter weights must sum to 1.0")

    learning_plan_spreadsheet_token = os.environ.get(
        "DAILY_AI_DIGEST_LEARNING_PLAN_SPREADSHEET_TOKEN",
        "R4LAsRmQKhfMXYtV7UacSeaGngg",
    )
    learning_plan_sheet_title = os.environ.get(
        "DAILY_AI_DIGEST_LEARNING_PLAN_SHEET_TITLE",
        "主任务",
    )

    return AppConfig(
        root=str(root),
        sources=documents["sources"],
        filters=documents["filters"],
        topics=documents["topics"],
        schedule=documents["schedule"],
        minimax_api_key=values["MINIMAX_API_KEY"],
        minimax_base_url=values["MINIMAX_BASE_URL"],
        minimax_model=values["MINIMAX_MODEL"],
        feishu_app_id=values["CTI_FEISHU_APP_ID"],
        feishu_app_secret=values["CTI_FEISHU_APP_SECRET"],
        feishu_chat_id=values["DAILY_AI_DIGEST_FEISHU_CHAT_ID"],
        learning_plan_spreadsheet_token=learning_plan_spreadsheet_token,
        learning_plan_sheet_title=learning_plan_sheet_title,
    )

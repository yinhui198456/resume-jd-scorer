import json
import re


REQUIRED_GENERATION_FIELDS = {"chinese_title", "summary", "why_it_matters"}


def parse_generation(text: str) -> dict[str, str]:
    if not isinstance(text, str):
        raise ValueError("invalid generation response")
    cleaned = re.sub(r"^\s*<think>.*?</think>\s*", "", text, count=1, flags=re.DOTALL)
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, count=1, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned, count=1)
    try:
        value = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("invalid generation response") from error
    if set(value) != REQUIRED_GENERATION_FIELDS or not all(
        isinstance(value[key], str) and value[key].strip()
        for key in REQUIRED_GENERATION_FIELDS
    ):
        raise ValueError("invalid generation response")
    return value


def fallback_generation(title: str, body: str, language: str) -> dict[str, str]:
    return {
        "chinese_title": title.strip(),
        "summary": " ".join(body.split())[:160],
        "why_it_matters": "该条目来自已验证的官方或发布来源，建议查看原文。",
        "translation_status": "pending" if language == "en" else "not_required",
    }

import json
import os
import logging

from anthropic import Anthropic

from models import (
    DimensionScore,
    EvaluationResult,
    FollowUpQuestion,
    Recommendation,
)

logger = logging.getLogger(__name__)

# ---- 评分规则常量（单一数据源） ----

DIMENSION_CONFIG = {
    "hard_requirement": {"max_score": 40, "weight": 0.4, "label": "硬性要求匹配度"},
    "skill_match": {"max_score": 30, "weight": 0.3, "label": "技能匹配度"},
    "experience_match": {"max_score": 20, "weight": 0.2, "label": "经验匹配度"},
    "bonus_potential": {"max_score": 10, "weight": 0.1, "label": "潜力/加分项"},
}

THRESHOLD_INTERVIEW = 75
THRESHOLD_BACKUP = 50

# ---- LLM 客户端（模块级单例） ----

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(
            api_key=os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
            base_url=os.environ.get("ANTHROPIC_BASE_URL", ""),
        )
    return _client


# ---- Prompt ----

def _build_system_prompt() -> str:
    """动态构建 system prompt，从 DIMENSION_CONFIG 读取，避免规则重复。"""
    dim_rows = "\n".join(
        f"| {cfg['label']} | {key} | {cfg['max_score']} | 见 config |"
        for key, cfg in DIMENSION_CONFIG.items()
    )
    return f"""你是一个专业的招聘评估专家。请根据提供的 JD（职位描述）和简历，给出结构化评估。

## 评分维度（总分 100）
| 维度 | key | 满分 | 说明 |
|------|-----|------|------|
{dim_rows}

## 建议规则
- 总分 ≥ {THRESHOLD_INTERVIEW} → "INTERVIEW"
- 总分 {THRESHOLD_BACKUP}-{THRESHOLD_INTERVIEW - 1} → "BACKUP"
- 总分 < {THRESHOLD_BACKUP} → "REJECT"

## 要求
1. 每个维度必须有 evidence，若简历中未体现则得分=0，evidence="未体现"
2. strengths 至少写 1 条；weaknesses 若无明显短板写 ["无明显短板"]
3. 追问问题：INTERVIEW 写 3-5 个，BACKUP 写 2-4 个，REJECT 写 0-2 个
4. dimension 字段只能是：{" / ".join(DIMENSION_CONFIG.keys())}
5. total_score 必须等于四个维度 score 之和
6. 只输出 JSON，不要输出任何其他文字

## 输出 JSON 格式
{{
  "total_score": 0,
  "recommendation": "INTERVIEW|BACKUP|REJECT",
  "dimensions": {{
    {json.dumps({key: {"score": 0, "max_score": cfg["max_score"], "weight": cfg["weight"], "evidence": ""}
                 for key, cfg in DIMENSION_CONFIG.items()}, indent=4)}
  }},
  "strengths": [],
  "weaknesses": [],
  "follow_up_questions": [
    {{"question": "", "dimension": "", "intent": ""}}
  ],
  "summary": ""
}}
"""


SYSTEM_PROMPT = _build_system_prompt()


def build_user_prompt(jd_text: str, resume_text: str) -> str:
    return f"""请评估以下候选人：

## JD（职位描述）
{jd_text}

## 简历
{resume_text}

请按评分规则输出 JSON 评估结果。"""


# ---- 核心逻辑 ----

def _recommendation_from_score(total: int) -> Recommendation:
    if total >= THRESHOLD_INTERVIEW:
        return Recommendation.INTERVIEW
    if total >= THRESHOLD_BACKUP:
        return Recommendation.BACKUP
    return Recommendation.REJECT


def _validate_and_fix(raw: dict) -> EvaluationResult:
    """对 LLM 输出做校验和自动修正，确保可被 Pydantic 校验通过。"""
    dims = raw.get("dimensions", {})
    validated_dims = {}
    computed_total = 0

    for key, cfg in DIMENSION_CONFIG.items():
        dim_data = dims.get(key, {})
        score = dim_data.get("score", 0)
        max_s = cfg["max_score"]
        # 钳位
        score = max(0, min(score, max_s))
        evidence = dim_data.get("evidence", "").strip()
        if not evidence:
            evidence = "未体现"
        validated_dims[key] = DimensionScore(
            score=score, max_score=max_s, weight=cfg["weight"], evidence=evidence,
        )
        computed_total += score

    # strengths / weaknesses 兜底
    strengths = raw.get("strengths", [])
    if not strengths:
        strengths = ["无明显优势"]
    weaknesses = raw.get("weaknesses", [])
    if not weaknesses:
        weaknesses = ["无明显短板"]

    # follow_up_questions 截断到 5
    follow_ups = raw.get("follow_up_questions", [])[:5]

    # recommendation 以总分为准
    total_score = raw.get("total_score", computed_total)
    recommendation = _recommendation_from_score(total_score)

    return EvaluationResult(
        total_score=total_score,
        recommendation=recommendation,
        dimensions=validated_dims,
        strengths=strengths,
        weaknesses=weaknesses,
        follow_up_questions=[FollowUpQuestion(**q) for q in follow_ups],
        summary=raw.get("summary", "评估完成"),
    )


def _extract_text_from_response(resp) -> str:
    """从 Anthropic 响应中提取纯文本，跳过 ThinkingBlock。"""
    for block in resp.content:
        if hasattr(block, "text") and block.text:
            return block.text.strip()
    return ""


def _extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON，支持 markdown code block 包裹。"""
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(text)


def evaluate(jd_text: str, resume_text: str, max_retries: int = 2) -> EvaluationResult:
    """调用 LLM 进行评估，失败时重试，并对结果做校验修正。"""
    client = _get_client()
    model = os.environ.get("ANTHROPIC_MODEL", "qwen3.6-plus")

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.messages.create(
                model=model,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": build_user_prompt(jd_text, resume_text)},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            content = _extract_text_from_response(resp)
            logger.debug("LLM response length (attempt %d): %d chars", attempt, len(content))

            raw = _extract_json(content)
            result = _validate_and_fix(raw)
            return result

        except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError) as e:
            last_error = e
            logger.warning("LLM output parse failed (attempt %d): %s", attempt, e)
        except Exception as e:
            last_error = e
            logger.error("LLM call failed (attempt %d): %s", attempt, e)

    raise RuntimeError(f"LLM 评估失败，已重试 {max_retries} 次: {last_error}")

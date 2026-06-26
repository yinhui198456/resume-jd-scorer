#!/usr/bin/env python3
"""LLM 简历 JD 评估脚本。从环境变量读取 JD 和简历文本，输出 JSON 评估结果。

用法：
    JD_TEXT="..." CV_TEXT="..." python3 evaluate.py

输出：JSON 格式评估结果（stdout）
"""

import json
import os
import sys
import logging

from anthropic import Anthropic

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
logger = logging.getLogger(__name__)

# ---- 评分规则常量 ----

DIMENSION_CONFIG = {
    "hard_requirement": {"max_score": 40, "weight": 0.4, "label": "硬性要求匹配度"},
    "skill_match": {"max_score": 30, "weight": 0.3, "label": "技能匹配度"},
    "experience_match": {"max_score": 20, "weight": 0.2, "label": "经验匹配度"},
    "bonus_potential": {"max_score": 10, "weight": 0.1, "label": "潜力/加分项"},
}

# 可信度系数（基于红旗信号数量/严重程度）
CREDIBILITY_TIERS = {
    "none": {"multiplier": 1.0, "label": "无明显疑点"},
    "minor": {"multiplier": 0.9, "label": "轻微疑虑（1个轻度红旗）"},
    "moderate": {"multiplier": 0.75, "label": "中度疑虑（培训痕迹/项目存疑/技能过度）"},
    "severe": {"multiplier": 0.6, "label": "严重疑虑（职责夸张+培训痕迹+岗位错位）"},
    "critical": {"multiplier": 0.5, "label": "极严重（时间线矛盾+多项造假嫌疑）"},
}

THRESHOLD_INTERVIEW = 75
THRESHOLD_BACKUP = 50

# ---- Prompt ----

SYSTEM_PROMPT = """你是一个专业的招聘评估专家。请根据提供的 JD（职位描述）和简历，给出结构化评估。

**当前时间：2026 年 6 月 26 日。判断"未来日期"时以此为准（2026-07 及之后才算未来）。**

## 两阶段评分法

### 第一阶段：基础匹配分（100分）
| 维度 | key | 满分 | 说明 |
|------|-----|------|------|
| 硬性要求匹配度 | hard_requirement | 40 | 学历、年限、语言能力等 |
| 技能匹配度 | skill_match | 30 | 硬技能/工具/框架覆盖度 |
| 经验匹配度 | experience_match | 20 | 过往业务场景与JD职责匹配度 |
| 潜力/加分项 | bonus_potential | 10 | 开源/大厂背景/跨领域能力 |

### 第二阶段：可信度系数（必须评估）

根据红旗信号确定系数，**最终得分 = 基础分 × 系数**：

| 可信度等级 | 系数 | 判定标准 |
|-----------|------|---------|
| 无 | 1.0 | 无明显疑点 |
| 轻微 | 0.9 | 1个轻度红旗 |
| 中度 | 0.75 | 培训痕迹/项目存疑/技能过度 |
| 严重 | 0.6 | 职责夸张+培训痕迹+岗位错位 |
| 极严重 | 0.5 | 时间线矛盾+多项造假嫌疑 |

**系数判定规则：**
- 同时出现"培训痕迹"+"职责夸张"→ 至少 0.6
- 同时出现"时间线矛盾"+"项目存疑"→ 至少 0.5
- 仅"技能描述过度"→ 0.75
- 无任何红旗→ 1.0

**排除规则（出现以下情况不扣分）：**
- 简历头部年限明显笔误（如"1年经验"但履历覆盖10年+），以实际履历为准
- PDF解析产生的乱码水印字符串（如`dd12b1e34f370bd21HF92Ny8FVpXxIq3UfqcWOelmv7WPxBh`），这是解析噪声
- 团队项目中候选人仅负责其中一部分，以"个人职责"描述为准，不苛求覆盖整个项目

## 建议规则（基于最终得分）
- 最终得分 ≥ 75 → "INTERVIEW"
- 最终得分 50-74 → "BACKUP"
- 最终得分 < 50 → "REJECT"

## 追问设计原则
- 对 flagged 的技能/项目必须设计 **验证性追问**
- 追问要求候选人提供 **具体场景、数据、决策过程**，而非概念性回答
- 例："K8s 有哪些组件" → "你管理的集群规模多大？遇到过最棘手的 Pod 调度问题是什么？"

## 要求
1. 每个维度必须有 evidence
2. strengths 至少 1 条；weaknesses 必须包含真实性分析
3. 必须输出 credibility_tier 和 credibility_multiplier
4. final_score = round(base_score × multiplier)
5. 追问：INTERVIEW 4-6个（至少2个验证），BACKUP 3-4个，REJECT 1-2个
6. 只输出 JSON

## 输出 JSON 格式
{
  "base_score": 0,
  "credibility_tier": "none|minor|moderate|severe|critical",
  "credibility_multiplier": 1.0,
  "final_score": 0,
  "recommendation": "INTERVIEW|BACKUP|REJECT",
  "dimensions": {
    "hard_requirement": {"score": 0, "max_score": 40, "weight": 0.4, "evidence": ""},
    "skill_match": {"score": 0, "max_score": 30, "weight": 0.3, "evidence": ""},
    "experience_match": {"score": 0, "max_score": 20, "weight": 0.2, "evidence": ""},
    "bonus_potential": {"score": 0, "max_score": 10, "weight": 0.1, "evidence": ""}
  },
  "strengths": [],
  "weaknesses": [],
  "red_flags": [],
  "follow_up_questions": [
    {
      "question": "",
      "dimension": "",
      "intent": "",
      "type": "technical|verification|scenario|comprehensive",
      "reference_answer": ""
    }
  ],

**强制要求：follow_up_questions 必须包含以下类型，缺一不可：**
- 至少 3 题 type="verification"（验证简历疑点）
- 至少 4 题 type="technical"（覆盖JD技术要求）
- 至少 3 题 type="scenario"（驻场/运维/上手场景）
- 至少 3 题 type="comprehensive"（沟通/出差/对客/强度/文档）
- 总数 15-20 题
  "summary": ""
}
"""


def _recommendation_from_score(total: int) -> str:
    if total >= THRESHOLD_INTERVIEW:
        return "INTERVIEW"
    if total >= THRESHOLD_BACKUP:
        return "BACKUP"
    return "REJECT"


def _validate_and_fix(raw: dict) -> dict:
    """校验和修正 LLM 输出。"""
    dims = raw.get("dimensions", {})
    validated_dims = {}
    computed_total = 0

    for key, cfg in DIMENSION_CONFIG.items():
        dim_data = dims.get(key, {})
        score = dim_data.get("score", 0)
        max_s = cfg["max_score"]
        score = max(0, min(score, max_s))
        evidence = (dim_data.get("evidence") or "").strip()
        if not evidence:
            evidence = "未体现"
        validated_dims[key] = {
            "score": score,
            "max_score": max_s,
            "weight": cfg["weight"],
            "evidence": evidence,
        }
        computed_total += score

    strengths = raw.get("strengths") or ["无明显优势"]
    weaknesses = raw.get("weaknesses") or ["无明显短板"]
    follow_ups = (raw.get("follow_up_questions") or [])[:6]

    # 基础分 = 四个维度之和
    base_score = computed_total

    # 兼容旧格式：如果 LLM 返回 total_score 而非 base_score
    if "total_score" in raw and "base_score" not in raw:
        # 旧格式：直接使用 total_score 作为 base_score，无可信度调整
        base_score = raw["total_score"]
        multiplier = 1.0
    else:
        # 新格式：可信度系数
        multiplier = raw.get("credibility_multiplier", 1.0)
        multiplier = max(0.5, min(1.0, multiplier))  # 限制在 0.5-1.0

    # 最终得分 = 基础分 × 系数
    final_score = round(base_score * multiplier)
    recommendation = _recommendation_from_score(final_score)

    return {
        "base_score": base_score,
        "credibility_tier": raw.get("credibility_tier", "none"),
        "credibility_multiplier": multiplier,
        "final_score": final_score,
        "recommendation": recommendation,
        "dimensions": validated_dims,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "red_flags": raw.get("red_flags", []),
        "follow_up_questions": follow_ups,
        "summary": raw.get("summary") or "评估完成",
    }


def _extract_text_from_response(resp) -> str:
    for block in resp.content:
        if hasattr(block, "text") and block.text:
            return block.text.strip()
    return ""


def _extract_json(text: str) -> dict:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(text)


def evaluate(jd_text: str, resume_text: str, max_retries: int = 2) -> dict:
    client = Anthropic(
        api_key=os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
        base_url=os.environ.get("ANTHROPIC_BASE_URL", ""),
    )
    model = os.environ.get("ANTHROPIC_MODEL", "qwen3.6-plus")

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.messages.create(
                model=model,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": f"请评估以下候选人：\n\n## JD\n{jd_text}\n\n## 简历\n{resume_text}"},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            content = _extract_text_from_response(resp)
            raw = _extract_json(content)
            return _validate_and_fix(raw)

        except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError) as e:
            last_error = e
            logger.warning("Parse failed (attempt %d): %s", attempt, e)
        except Exception as e:
            last_error = e
            logger.error("LLM call failed (attempt %d): %s", attempt, e)

    raise RuntimeError(f"评估失败，已重试 {max_retries} 次: {last_error}")


def main():
    jd_text = os.environ.get("JD_TEXT", "").strip()
    cv_text = os.environ.get("CV_TEXT", "").strip()

    if not jd_text:
        print("错误：JD_TEXT 环境变量为空", file=sys.stderr)
        sys.exit(1)
    if not cv_text:
        print("错误：CV_TEXT 环境变量为空", file=sys.stderr)
        sys.exit(1)

    try:
        result = evaluate(jd_text, cv_text)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

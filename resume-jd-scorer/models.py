from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Recommendation(str, Enum):
    INTERVIEW = "INTERVIEW"
    BACKUP = "BACKUP"
    REJECT = "REJECT"


class DimensionScore(BaseModel):
    score: int = Field(ge=0, description="该维度得分")
    max_score: int = Field(ge=1, description="该维度满分")
    weight: float = Field(description="权重，0.1-0.4")
    evidence: str = Field(min_length=1, description="评分依据；缺失时填'未体现'")

    @model_validator(mode="after")
    def _check_score_in_range(self) -> "DimensionScore":
        if self.score > self.max_score:
            raise ValueError(f"score ({self.score}) 不能超过 max_score ({self.max_score})")
        return self


class FollowUpQuestion(BaseModel):
    question: str = Field(min_length=1, description="追问问题")
    dimension: str = Field(
        description="关联维度：hard_requirement|skill_match|experience_match|bonus_potential"
    )
    intent: str = Field(min_length=1, description="追问意图")
    question_type: str = Field(
        default="technical",
        description="问题类型：technical(技术考察) | verification(真实性验证)"
    )


class EvaluationResult(BaseModel):
    base_score: int = Field(ge=0, le=100, description="基础匹配分（四维之和）")
    credibility_tier: str = Field(
        default="none",
        description="可信度等级：none|minor|moderate|severe|critical"
    )
    credibility_multiplier: float = Field(
        default=1.0, ge=0.5, le=1.0,
        description="可信度系数（0.5-1.0）"
    )
    final_score: int = Field(ge=0, le=100, description="最终得分（基础分×系数）")
    recommendation: Recommendation = Field(description="面试建议")
    dimensions: dict[str, DimensionScore] = Field(
        description="各维度评分"
    )
    strengths: list[str] = Field(min_length=1, description="候选人优势点列表")
    weaknesses: list[str] = Field(
        default_factory=list,
        description="候选人短板/缺失项列表"
    )
    red_flags: list[str] = Field(
        default_factory=list,
        description="真实性红旗信号列表（年限不符、项目存疑等）"
    )
    follow_up_questions: list[FollowUpQuestion] = Field(
        default_factory=list,
        max_length=20,
        description="面试追问问题列表"
    )
    summary: str = Field(min_length=1, description="一段话总结评估结论")

    @model_validator(mode="after")
    def _check_final_score_consistency(self) -> "EvaluationResult":
        computed_base = sum(d.score for d in self.dimensions.values())
        if self.base_score != computed_base:
            object.__setattr__(self, "base_score", computed_base)
        expected_final = round(self.base_score * self.credibility_multiplier)
        if self.final_score != expected_final:
            object.__setattr__(self, "final_score", expected_final)
        return self


class EvaluationRequest(BaseModel):
    jd_text: str = Field(min_length=1, max_length=20000, description="职位描述文本")
    resume_text: str = Field(min_length=1, max_length=20000, description="简历文本")


class EvaluationResponse(BaseModel):
    success: bool
    result: Optional[EvaluationResult] = None
    error: Optional[str] = None


class AnswersRequest(BaseModel):
    jd_text: str = Field(min_length=1, max_length=20000, description="职位描述文本")
    resume_text: str = Field(min_length=1, max_length=20000, description="简历文本")
    questions: list[str] = Field(min_length=1, description="面试问题列表")


class AnswersResponse(BaseModel):
    answers: list[str] = Field(default_factory=list, description="建议答案列表")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")


class HistoryRecord(BaseModel):
    id: Optional[str] = Field(default=None, description="记录ID")
    jd_text: Optional[str] = Field(default=None, max_length=20000, description="职位描述文本")
    resume_text: Optional[str] = Field(default=None, max_length=20000, description="简历文本")
    candidate_name: str = Field(default="未知候选人", description="候选人姓名")
    resume_filename: str = Field(default="", description="简历文件名")
    result: Optional[EvaluationResult] = Field(default=None, description="评估结果")
    created_at: Optional[str] = Field(default=None, description="创建时间")

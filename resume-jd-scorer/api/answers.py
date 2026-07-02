from fastapi import APIRouter

from answer_generator import generate_suggested_answers
from models import AnswersRequest, AnswersResponse

router = APIRouter()


@router.post("/answers", response_model=AnswersResponse)
def post_answers(req: AnswersRequest):
    try:
        answers = generate_suggested_answers(
            req.jd_text,
            req.resume_text,
            req.questions,
        )
        return AnswersResponse(answers=answers)
    except Exception:
        return AnswersResponse(answers=[], success=False, error="建议答案生成失败")

from fastapi import APIRouter, HTTPException

from models import EvaluationRequest, EvaluationResponse
from scorer import evaluate

router = APIRouter()


@router.post("/evaluate", response_model=EvaluationResponse)
def post_evaluate(req: EvaluationRequest):
    try:
        result = evaluate(req.jd_text, req.resume_text)
        return EvaluationResponse(success=True, result=result)
    except Exception:
        return EvaluationResponse(success=False, error="评估服务暂时不可用，请稍后重试")

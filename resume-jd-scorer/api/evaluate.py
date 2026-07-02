import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from json_store import JsonStore
from models import EvaluationRequest, EvaluationResponse, PairEvaluationRequest
from scorer import evaluate

logger = logging.getLogger(__name__)

router = APIRouter()

JD_STORE_PATH = Path(__file__).parent.parent / "data" / "jds.json"
RESUME_STORE_PATH = Path(__file__).parent.parent / "data" / "resumes.json"


def get_jd_store() -> JsonStore:
    return JsonStore(JD_STORE_PATH)


def get_resume_store() -> JsonStore:
    return JsonStore(RESUME_STORE_PATH)


@router.post("/evaluate", response_model=EvaluationResponse)
def post_evaluate(req: EvaluationRequest):
    try:
        result = evaluate(req.jd_text, req.resume_text)
        return EvaluationResponse(success=True, result=result)
    except Exception:
        logger.exception("Evaluation failed")
        return EvaluationResponse(success=False, error="评估服务暂时不可用，请稍后重试")


@router.post("/evaluate/pair", response_model=EvaluationResponse)
def post_evaluate_pair(
    req: PairEvaluationRequest,
    jd_store: JsonStore = Depends(get_jd_store),
    resume_store: JsonStore = Depends(get_resume_store),
):
    jd_record = jd_store.get(req.jd_id)
    if not jd_record:
        raise HTTPException(status_code=404, detail="JD not found")
    resume_record = resume_store.get(req.resume_id)
    if not resume_record:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        result = evaluate(jd_record["content"], resume_record["content"])
        return EvaluationResponse(success=True, result=result)
    except Exception:
        logger.exception("Pair evaluation failed")
        return EvaluationResponse(success=False, error="评估服务暂时不可用，请稍后重试")

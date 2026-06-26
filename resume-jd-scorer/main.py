import logging

from fastapi import FastAPI, HTTPException

from models import EvaluationRequest, EvaluationResponse, EvaluationResult
from scorer import evaluate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="简历 JD 评估服务",
    description="基于 JD 对简历进行评估打分的 MVP 服务",
    version="0.1.0",
)


@app.post("/evaluate", response_model=EvaluationResponse)
def post_evaluate(req: EvaluationRequest):
    """接收 JD 和简历文本，返回 100 分制评估结果。"""
    try:
        result = evaluate(req.jd_text, req.resume_text)
        return EvaluationResponse(success=True, result=result)
    except Exception as e:
        logger.exception("Evaluation failed")
        # 不暴露内部异常细节给客户端
        return EvaluationResponse(success=False, error="评估服务暂时不可用，请稍后重试")


@app.get("/health")
def health():
    return {"status": "ok"}

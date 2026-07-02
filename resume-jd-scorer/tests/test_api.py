import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.evaluate import router as evaluate_router
from main import app
from models import EvaluationResult, Recommendation, EvaluationResponse

client = TestClient(app)

# ---- fixtures ----

@pytest.fixture
def client_fixture():
    return TestClient(app)

# ---- fixtures: 样例数据 ----

JD_SENIOR_JAVA = """
职位：高级 Java 后端工程师
要求：
- 5 年+ Java 开发经验
- 熟练掌握 Spring Boot、MySQL、Redis
- 熟悉分布式系统设计
- 本科及以上计算机相关专业
- 有电商或支付系统经验优先
"""

RESUME_STRONG = """
张三 | 5 年 Java 后端开发
学历：本科 计算机科学与技术
经历：
- 某大厂电商平台，负责订单系统和支付网关开发
- 熟练使用 Spring Boot、MySQL、Redis、Kafka
- 主导微服务拆分，QPS 从 5k 提升至 30k
- 技术博客作者，GitHub 开源项目 Star 200+
- 英语 CET-6
"""

RESUME_WEAK = """
李四 | 1 年 Go + 3 年前端开发
学历：本科 视觉设计
经历：
- 前端开发 3 年，使用 Vue.js 和 React
- 近 1 年学习 Go，用 gin 开发过一个内部工具
- 无微服务经验，未使用过 Kubernetes
- 无英语等级证书
"""

# 边界分数：恰好 75 分
MOCK_RESULT_75 = {
    "base_score": 75,
    "credibility_tier": "none",
    "credibility_multiplier": 1.0,
    "final_score": 75,
    "recommendation": "INTERVIEW",
    "dimensions": {
        "hard_requirement": {"score": 30, "max_score": 40, "weight": 0.4, "evidence": "本科计算机"},
        "skill_match": {"score": 25, "max_score": 30, "weight": 0.3, "evidence": "熟悉核心技能"},
        "experience_match": {"score": 12, "max_score": 20, "weight": 0.2, "evidence": "有一定后端经验"},
        "bonus_potential": {"score": 8, "max_score": 10, "weight": 0.1, "evidence": "有开源贡献"},
    },
    "strengths": ["技术基础扎实"],
    "weaknesses": ["项目规模较小"],
    "follow_up_questions": [
        {"question": "Q1", "dimension": "experience_match", "intent": "验证"}
    ],
    "summary": "边界候选人",
}

# 边界分数：恰好 49 分
MOCK_RESULT_49 = {
    "base_score": 49,
    "credibility_tier": "none",
    "credibility_multiplier": 1.0,
    "final_score": 49,
    "recommendation": "REJECT",
    "dimensions": {
        "hard_requirement": {"score": 10, "max_score": 40, "weight": 0.4, "evidence": "未体现"},
        "skill_match": {"score": 15, "max_score": 30, "weight": 0.3, "evidence": "基础了解"},
        "experience_match": {"score": 14, "max_score": 20, "weight": 0.2, "evidence": "有限相关经验"},
        "bonus_potential": {"score": 10, "max_score": 10, "weight": 0.1, "evidence": "学习能力强"},
    },
    "strengths": ["学习意愿强"],
    "weaknesses": ["经验严重不足"],
    "follow_up_questions": [],
    "summary": "不匹配",
}


def _mock_evaluate(*args, **kwargs):
    """Mock evaluate() 返回固定的 EvaluationResult。"""
    return EvaluationResult(**MOCK_RESULT_75)


# ---- 测试 ----

def test_schema_model_validate():
    """测试 EvaluationResult 模型校验通过。"""
    data = {
        "base_score": 88,
        "credibility_tier": "none",
        "credibility_multiplier": 1.0,
        "final_score": 88,
        "recommendation": "INTERVIEW",
        "dimensions": {
            "hard_requirement": {"score": 38, "max_score": 40, "weight": 0.4, "evidence": "本科计算机，5年经验"},
            "skill_match": {"score": 27, "max_score": 30, "weight": 0.3, "evidence": "熟悉Spring Boot/MySQL/Redis"},
            "experience_match": {"score": 15, "max_score": 20, "weight": 0.2, "evidence": "电商订单和支付经验"},
            "bonus_potential": {"score": 8, "max_score": 10, "weight": 0.1, "evidence": "大厂背景+开源"},
        },
        "strengths": ["5年Java经验", "有大厂背景"],
        "weaknesses": ["Kafka实战不足"],
        "follow_up_questions": [
            {"question": "如何处理高并发库存扣减？", "dimension": "experience_match", "intent": "验证实战深度"}
        ],
        "summary": "候选人匹配度高，建议面试。",
    }
    result = EvaluationResult(**data)
    assert result.base_score == 88
    assert result.recommendation == Recommendation.INTERVIEW
    assert len(result.dimensions) == 4


def test_schema_total_score_auto_fix():
    """测试 total_score 与维度之和不一致时自动修正。"""
    data = {
        "base_score": 88,  # 在 0-100 范围内，但与维度之和(70)不一致
        "credibility_tier": "none",
        "credibility_multiplier": 1.0,
        "final_score": 88,
        "recommendation": "INTERVIEW",
        "dimensions": {
            "hard_requirement": {"score": 30, "max_score": 40, "weight": 0.4, "evidence": "test"},
            "skill_match": {"score": 20, "max_score": 30, "weight": 0.3, "evidence": "test"},
            "experience_match": {"score": 15, "max_score": 20, "weight": 0.2, "evidence": "test"},
            "bonus_potential": {"score": 5, "max_score": 10, "weight": 0.1, "evidence": "test"},
        },
        "strengths": ["test"],
        "weaknesses": [],
        "follow_up_questions": [],
        "summary": "test",
    }
    result = EvaluationResult(**data)
    assert result.base_score == 70  # 30+20+15+5 = 70，自动修正


@patch("api.evaluate.evaluate")
def test_evaluate_high_match(mock_evaluate):
    """测试高分候选人调用 /api/evaluate 接口返回 INTERVIEW 建议（使用 mock 避免 LLM 波动）。"""
    mock_evaluate.return_value = EvaluationResult(**MOCK_RESULT_75)
    resp = client.post("/api/evaluate", json={
        "jd_text": JD_SENIOR_JAVA,
        "resume_text": RESUME_STRONG,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["result"]["final_score"] >= 75
    assert body["result"]["recommendation"] == "INTERVIEW"
    assert len(body["result"]["dimensions"]) == 4
    assert len(body["result"]["follow_up_questions"]) >= 1


def test_evaluate_low_match():
    """测试低分候选人调用 /api/evaluate 接口返回 REJECT 或 BACKUP 建议。"""
    resp = client.post("/api/evaluate", json={
        "jd_text": JD_SENIOR_JAVA,
        "resume_text": RESUME_WEAK,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["result"]["final_score"] < 75
    assert body["result"]["recommendation"] in ("BACKUP", "REJECT")
    assert len(body["result"]["dimensions"]) == 4


def test_empty_input_rejected():
    """测试空输入被 Pydantic 校验拒绝，返回 422。"""
    resp = client.post("/api/evaluate", json={"jd_text": "", "resume_text": "some resume"})
    assert resp.status_code == 422

    resp = client.post("/api/evaluate", json={"jd_text": "some jd", "resume_text": ""})
    assert resp.status_code == 422


def test_missing_field_rejected():
    """测试缺少必填字段返回 422。"""
    resp = client.post("/api/evaluate", json={"jd_text": JD_SENIOR_JAVA})
    assert resp.status_code == 422


@patch("api.evaluate.evaluate")
def test_llm_failure_returns_error(mock_evaluate):
    """测试 LLM 调用失败时返回 success=False + 通用错误消息。"""
    mock_evaluate.side_effect = RuntimeError("LLM 评估失败")
    resp = client.post("/api/evaluate", json={
        "jd_text": JD_SENIOR_JAVA,
        "resume_text": RESUME_STRONG,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "评估服务暂时不可用" in body["error"]
    # 确认不泄露内部异常细节
    assert "RuntimeError" not in body["error"]


@patch("api.evaluate.evaluate")
def test_boundary_score_75_is_interview(mock_evaluate):
    """测试恰好 75 分时 recommendation 为 INTERVIEW。"""
    mock_evaluate.return_value = EvaluationResult(**MOCK_RESULT_75)
    resp = client.post("/api/evaluate", json={
        "jd_text": JD_SENIOR_JAVA,
        "resume_text": RESUME_STRONG,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["final_score"] == 75
    assert body["result"]["recommendation"] == "INTERVIEW"


@patch("api.evaluate.evaluate")
def test_boundary_score_49_is_reject(mock_evaluate):
    """测试恰好 49 分时 recommendation 为 REJECT。"""
    mock_evaluate.return_value = EvaluationResult(**MOCK_RESULT_49)
    resp = client.post("/api/evaluate", json={
        "jd_text": JD_SENIOR_JAVA,
        "resume_text": RESUME_WEAK,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["final_score"] == 49
    assert body["result"]["recommendation"] == "REJECT"


def test_health_check():
    """测试 /health 返回 ok。"""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


@patch("scorer._get_client")
def test_missing_api_key_returns_error(mock_get_client):
    """测试 API key 缺失时返回通用错误。"""
    mock_get_client.side_effect = RuntimeError("API key not configured")
    resp = client.post("/api/evaluate", json={
        "jd_text": JD_SENIOR_JAVA,
        "resume_text": RESUME_STRONG,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "评估服务暂时不可用" in body["error"]


@patch("api.evaluate.evaluate")
def test_concurrent_evaluate(mock_evaluate):
    """测试并发请求不互相干扰（使用 mock 避免多次 LLM 调用）。"""
    import concurrent.futures

    mock_evaluate.return_value = EvaluationResult(**MOCK_RESULT_75)

    def _request():
        return client.post("/api/evaluate", json={
            "jd_text": JD_SENIOR_JAVA,
            "resume_text": RESUME_STRONG,
        })

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(_request) for _ in range(3)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    for resp in responses:
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["result"]["final_score"] == 75


def test_oversized_input_rejected():
    """测试输入超过最大长度时返回 422。"""
    resp = client.post("/api/evaluate", json={
        "jd_text": "A" * 25000,
        "resume_text": RESUME_WEAK,
    })
    assert resp.status_code == 422

    resp = client.post("/api/evaluate", json={
        "jd_text": JD_SENIOR_JAVA,
        "resume_text": "B" * 25000,
    })
    assert resp.status_code == 422


# ---- Task 12: New integration tests for parse, answers, history ----

def test_parse_txt_file(client_fixture: TestClient, tmp_path):
    txt = tmp_path / "resume.txt"
    txt.write_text("姓名：李四\n", encoding="utf-8")
    with open(txt, "rb") as f:
        response = client_fixture.post("/api/parse", files={"file": ("resume.txt", f, "text/plain")})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["type"] == "text/plain"
    assert data["name"].endswith(".txt")
    assert "李四" in data["text"]
    assert data["error"] is None


def test_parse_unsupported_type(client_fixture: TestClient, tmp_path):
    bad = tmp_path / "resume.exe"
    bad.write_bytes(b"\x00\x01\x02\x03")
    with open(bad, "rb") as f:
        response = client_fixture.post("/api/parse", files={"file": ("resume.exe", f, "application/octet-stream")})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error"]


def test_answers_endpoint(client_fixture: TestClient, monkeypatch):
    def mock_generate(jd_text, resume_text, questions):
        return ["answer1", "answer2"]

    monkeypatch.setattr("api.answers.generate_suggested_answers", mock_generate)
    response = client_fixture.post("/api/answers", json={
        "jd_text": "JD",
        "resume_text": "RESUME",
        "questions": ["q1", "q2"],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["answers"] == ["answer1", "answer2"]


def test_history_crud(client_fixture: TestClient):
    record = {
        "candidate_name": "测试",
        "resume_filename": "test.pdf",
        "jd_text": "JD",
        "resume_text": "RESUME",
        "result": {
            "base_score": 80,
            "credibility_tier": "none",
            "credibility_multiplier": 1.0,
            "final_score": 80,
            "recommendation": "INTERVIEW",
            "dimensions": {
                "hard_requirement": {"score": 32, "max_score": 40, "weight": 0.4, "evidence": "匹配"},
                "skill_match": {"score": 24, "max_score": 30, "weight": 0.3, "evidence": "匹配"},
                "experience_match": {"score": 16, "max_score": 20, "weight": 0.2, "evidence": "匹配"},
                "bonus_potential": {"score": 8, "max_score": 10, "weight": 0.1, "evidence": "匹配"},
            },
            "strengths": ["优势"],
            "weaknesses": ["无明显短板"],
            "red_flags": [],
            "follow_up_questions": [],
            "summary": "测试总结",
        },
    }
    response = client_fixture.post("/api/history", json=record)
    assert response.status_code == 200
    saved = response.json()["record"]
    assert saved["id"] is not None

    response = client_fixture.get("/api/history")
    assert response.status_code == 200
    assert len(response.json()["records"]) >= 1

    response = client_fixture.delete(f"/api/history/{saved['id']}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from models import EvaluationResult


@pytest.fixture
def client_fixture():
    return TestClient(app)


@pytest.fixture
def sample_resume():
    return {
        "name": "张三",
        "content": "张三，5 年 Java 后端开发，熟悉 Spring Boot、MySQL、Redis",
        "filename": "zhangsan.pdf",
        "contact": "13800138000",
        "work_years": "5 年",
    }


def test_resume_crud(client_fixture: TestClient, sample_resume):
    # create
    resp = client_fixture.post("/api/resumes", json=sample_resume)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    saved = data["record"]
    assert saved["id"]
    assert saved["name"] == sample_resume["name"]

    # list
    resp = client_fixture.get("/api/resumes")
    assert resp.status_code == 200
    records = resp.json()["records"]
    assert any(r["id"] == saved["id"] for r in records)

    # get
    resp = client_fixture.get(f"/api/resumes/{saved['id']}")
    assert resp.status_code == 200
    assert resp.json()["record"]["id"] == saved["id"]

    # update
    resp = client_fixture.put(f"/api/resumes/{saved['id']}", json={"contact": "13900139000"})
    assert resp.status_code == 200
    assert resp.json()["record"]["contact"] == "13900139000"

    # delete
    resp = client_fixture.delete(f"/api/resumes/{saved['id']}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_resume_not_found(client_fixture: TestClient):
    resp = client_fixture.get("/api/resumes/non-existent-id")
    assert resp.status_code == 404


def test_resume_validation(client_fixture: TestClient):
    resp = client_fixture.post("/api/resumes", json={"name": "", "content": "resume"})
    assert resp.status_code == 422

    resp = client_fixture.post("/api/resumes", json={"name": "resume", "content": ""})
    assert resp.status_code == 422


MOCK_RESULT = {
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
}


@patch("api.evaluate.evaluate")
def test_evaluate_pair(mock_evaluate, client_fixture: TestClient):
    mock_evaluate.return_value = EvaluationResult(**MOCK_RESULT)

    jd_resp = client_fixture.post("/api/jds", json={
        "name": "Java JD",
        "content": "Java 后端要求",
        "tags": [],
    })
    jd_id = jd_resp.json()["record"]["id"]

    resume_resp = client_fixture.post("/api/resumes", json={
        "name": "张三",
        "content": "Java 后端经验",
        "filename": "zs.pdf",
    })
    resume_id = resume_resp.json()["record"]["id"]

    resp = client_fixture.post("/api/evaluate/pair", json={
        "jd_id": jd_id,
        "resume_id": resume_id,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["result"]["final_score"] == 80


def test_evaluate_pair_missing_ids(client_fixture: TestClient):
    resp = client_fixture.post("/api/evaluate/pair", json={
        "jd_id": "missing",
        "resume_id": "missing",
    })
    assert resp.status_code == 404

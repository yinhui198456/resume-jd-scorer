import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client_fixture():
    return TestClient(app)


@pytest.fixture
def sample_jd():
    return {
        "name": "高级 Java 后端",
        "content": "5 年+ Java 经验，熟悉 Spring Boot、MySQL、Redis",
        "tags": ["后端", "Java"],
    }


def test_jd_crud(client_fixture: TestClient, sample_jd):
    # create
    resp = client_fixture.post("/api/jds", json=sample_jd)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    saved = data["record"]
    assert saved["id"]
    assert saved["name"] == sample_jd["name"]
    assert saved["tags"] == sample_jd["tags"]

    # list
    resp = client_fixture.get("/api/jds")
    assert resp.status_code == 200
    records = resp.json()["records"]
    assert any(r["id"] == saved["id"] for r in records)

    # get
    resp = client_fixture.get(f"/api/jds/{saved['id']}")
    assert resp.status_code == 200
    assert resp.json()["record"]["id"] == saved["id"]

    # update
    resp = client_fixture.put(f"/api/jds/{saved['id']}", json={"name": "资深 Java 后端"})
    assert resp.status_code == 200
    assert resp.json()["record"]["name"] == "资深 Java 后端"

    # delete
    resp = client_fixture.delete(f"/api/jds/{saved['id']}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    resp = client_fixture.get(f"/api/jds/{saved['id']}")
    assert resp.status_code == 404


def test_jd_not_found(client_fixture: TestClient):
    resp = client_fixture.get("/api/jds/non-existent-id")
    assert resp.status_code == 404

    resp = client_fixture.put("/api/jds/non-existent-id", json={"name": "x"})
    assert resp.status_code == 404


def test_jd_validation(client_fixture: TestClient):
    resp = client_fixture.post("/api/jds", json={"name": "", "content": "JD"})
    assert resp.status_code == 422

    resp = client_fixture.post("/api/jds", json={"name": "JD", "content": ""})
    assert resp.status_code == 422

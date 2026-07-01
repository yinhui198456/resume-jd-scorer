import json
import tempfile
from pathlib import Path

from history_store import HistoryStore


def test_save_and_load_record():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        path = f.name

    store = HistoryStore(path)
    record = store.save({
        "candidate_name": "张三",
        "resume_filename": "张三.pdf",
        "jd_text": "JD",
        "resume_text": "RESUME",
        "result": {"final_score": 80},
    })

    assert record["id"]
    assert record["created_at"]
    assert record["candidate_name"] == "张三"

    records = store.load()
    assert len(records) == 1
    assert records[0]["candidate_name"] == "张三"

    Path(path).unlink()


def test_capacity_limit():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        path = f.name

    store = HistoryStore(path)
    for i in range(60):
        store.save({"candidate_name": f"候选人{i}"})

    records = store.load()
    assert len(records) == 50
    assert records[0]["candidate_name"] == "候选人59"

    Path(path).unlink()

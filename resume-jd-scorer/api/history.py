from fastapi import APIRouter

from history_store import HistoryStore
from models import HistoryRecord
from resume_info import extract_name

router = APIRouter()
store = HistoryStore()


@router.get("/history")
def get_history():
    return {"success": True, "records": store.load()}


@router.post("/history")
def post_history(record: HistoryRecord):
    data = record.model_dump()
    if not data.get("candidate_name"):
        data["candidate_name"] = extract_name(data.get("resume_text", "")) or "未知候选人"
    # Ensure id and created_at are not None so setdefault works
    if data.get("id") is None:
        del data["id"]
    if data.get("created_at") is None:
        del data["created_at"]
    saved = store.save(data)
    return {"success": True, "record": saved}


@router.delete("/history/{record_id}")
def delete_history(record_id: str):
    deleted = store.delete(record_id)
    return {"success": True, "deleted": deleted}

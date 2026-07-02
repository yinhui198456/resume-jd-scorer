from fastapi import APIRouter, Depends

from history_store import HistoryStore
from models import HistoryRecord
from resume_info import extract_name

router = APIRouter()


def get_history_store() -> HistoryStore:
    return HistoryStore()


@router.get("/history")
def get_history(store: HistoryStore = Depends(get_history_store)):
    return {"success": True, "records": store.load()}


@router.post("/history")
def post_history(record: HistoryRecord, store: HistoryStore = Depends(get_history_store)):
    data = record.model_dump(exclude_none=True)
    if not data.get("candidate_name"):
        data["candidate_name"] = extract_name(data.get("resume_text", "")) or "未知候选人"
    saved = store.save(data)
    return {"success": True, "record": saved}


@router.delete("/history/{record_id}")
def delete_history(record_id: str, store: HistoryStore = Depends(get_history_store)):
    deleted = store.delete(record_id)
    return {"success": True, "deleted": deleted}

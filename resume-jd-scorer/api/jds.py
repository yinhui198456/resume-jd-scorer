from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from json_store import JsonStore
from models import JDCreate, JDRecord, JDUpdate

router = APIRouter()

JD_STORE_PATH = Path(__file__).parent.parent / "data" / "jds.json"


def get_jd_store() -> JsonStore:
    return JsonStore(JD_STORE_PATH)


@router.get("/jds")
def list_jds(store: JsonStore = Depends(get_jd_store)):
    return {"success": True, "records": store.list()}


@router.get("/jds/{jd_id}")
def get_jd(jd_id: str, store: JsonStore = Depends(get_jd_store)):
    record = store.get(jd_id)
    if not record:
        raise HTTPException(status_code=404, detail="JD not found")
    return {"success": True, "record": record}


@router.post("/jds")
def create_jd(jd: JDCreate, store: JsonStore = Depends(get_jd_store)):
    data = jd.model_dump(exclude_none=True)
    saved = store.save(data)
    return {"success": True, "record": saved}


@router.put("/jds/{jd_id}")
def update_jd(jd_id: str, jd: JDUpdate, store: JsonStore = Depends(get_jd_store)):
    existing = store.get(jd_id)
    if not existing:
        raise HTTPException(status_code=404, detail="JD not found")
    update_data = {k: v for k, v in jd.model_dump(exclude_none=True).items() if v is not None}
    existing.update(update_data)
    saved = store.save(existing)
    return {"success": True, "record": saved}


@router.delete("/jds/{jd_id}")
def delete_jd(jd_id: str, store: JsonStore = Depends(get_jd_store)):
    deleted = store.delete(jd_id)
    return {"success": True, "deleted": deleted}

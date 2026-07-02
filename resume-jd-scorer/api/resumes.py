from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from json_store import JsonStore
from models import ResumeCreate, ResumeRecord, ResumeUpdate

router = APIRouter()

RESUME_STORE_PATH = Path(__file__).parent.parent / "data" / "resumes.json"


def get_resume_store() -> JsonStore:
    return JsonStore(RESUME_STORE_PATH)


@router.get("/resumes")
def list_resumes(store: JsonStore = Depends(get_resume_store)):
    return {"success": True, "records": store.list()}


@router.get("/resumes/{resume_id}")
def get_resume(resume_id: str, store: JsonStore = Depends(get_resume_store)):
    record = store.get(resume_id)
    if not record:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"success": True, "record": record}


@router.post("/resumes")
def create_resume(resume: ResumeCreate, store: JsonStore = Depends(get_resume_store)):
    data = resume.model_dump(exclude_none=True)
    saved = store.save(data)
    return {"success": True, "record": saved}


@router.put("/resumes/{resume_id}")
def update_resume(
    resume_id: str,
    resume: ResumeUpdate,
    store: JsonStore = Depends(get_resume_store),
):
    existing = store.get(resume_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Resume not found")
    update_data = {k: v for k, v in resume.model_dump(exclude_none=True).items() if v is not None}
    existing.update(update_data)
    saved = store.save(existing)
    return {"success": True, "record": saved}


@router.delete("/resumes/{resume_id}")
def delete_resume(resume_id: str, store: JsonStore = Depends(get_resume_store)):
    deleted = store.delete(resume_id)
    return {"success": True, "deleted": deleted}

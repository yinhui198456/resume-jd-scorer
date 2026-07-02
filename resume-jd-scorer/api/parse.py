import os
import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

# Make skill scripts importable
_SKILL_SCRIPTS = Path("/opt/personal-agent-workspace/skills/resume-jd-scorer/scripts")
if str(_SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SKILL_SCRIPTS))

from parse_file import parse_resume

router = APIRouter()

MAX_UPLOAD_SIZE = 10 * 1024 * 1024


@router.post("/parse")
def parse_upload(file: UploadFile = File(...)):
    content = file.file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        return {"success": False, "type": None, "name": None, "text": None, "error": "文件大小超过 10MB 限制"}
    suffix = Path(file.filename or "resume.bin").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = parse_resume(tmp_path)
        return {"success": True, "type": result.get("type"), "name": result.get("name"), "text": result.get("text"), "error": None}
    except ValueError as e:
        return {"success": False, "type": None, "name": None, "text": None, "error": str(e)}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

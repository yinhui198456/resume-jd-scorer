"""Local JSON persistence for evaluation history."""

from __future__ import annotations

import fcntl
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_HISTORY_PATH = Path(__file__).parent / "data" / "evaluations.json"
MAX_RECORDS = 50


class HistoryStore:
    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = Path(path or DEFAULT_HISTORY_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "records": []}
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"version": 1, "records": []}

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, "r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                f.seek(0)
                content = f.read()
                if not content:
                    return []
                data = json.loads(content)
            except json.JSONDecodeError:
                data = {"version": 1, "records": []}
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        records = data.get("records", [])
        records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return records[:MAX_RECORDS]

    def save(self, record: dict[str, Any]) -> dict[str, Any]:
        complete = dict(record)
        complete.setdefault("id", str(uuid.uuid4()))
        complete.setdefault("created_at", datetime.now(timezone.utc).isoformat())

        # Ensure file exists before opening r+
        if not self.path.exists():
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "records": []}, f, ensure_ascii=False, indent=2)

        with open(self.path, "r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                content = f.read()
                if content:
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        data = {"version": 1, "records": []}
                else:
                    data = {"version": 1, "records": []}
                f.seek(0)
                f.truncate()

                records = data.get("records", [])
                records = [r for r in records if r.get("created_at")]
                records.insert(0, complete)
                records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
                data["records"] = records[:MAX_RECORDS]
                json.dump(data, f, ensure_ascii=False, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return complete

    def delete(self, record_id: str) -> bool:
        if not self.path.exists():
            return False
        with open(self.path, "r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                content = f.read()
                if content:
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        data = {"version": 1, "records": []}
                else:
                    data = {"version": 1, "records": []}
                f.seek(0)
                f.truncate()

                before = len(data.get("records", []))
                data["records"] = [r for r in data.get("records", []) if r.get("id") != record_id]
                after = len(data["records"])
                json.dump(data, f, ensure_ascii=False, indent=2)
                return before != after
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

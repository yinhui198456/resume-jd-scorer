"""Generic local JSON persistence with file locking.

Follows the same pattern as history_store.py but generalized for any entity.
"""

from __future__ import annotations

import fcntl
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonStore:
    """Thread/process-safe JSON store using fcntl.flock.

    Data shape on disk: {"version": 1, "records": [...]}
    Records are dicts; save() will set id and created_at if missing.
    """

    def __init__(
        self,
        path: str | os.PathLike[str],
        max_records: int | None = None,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_records = max_records

    def _ensure_file(self) -> None:
        if not self.path.exists():
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "records": []}, f, ensure_ascii=False, indent=2)

    def _load_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "records": []}
        with open(self.path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content:
                return {"version": 1, "records": []}
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"version": 1, "records": []}

    def list(self) -> list[dict[str, Any]]:
        """Return all records sorted by created_at descending."""
        data = self._load_raw()
        records = data.get("records", [])
        records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        if self.max_records is not None:
            records = records[: self.max_records]
        return records

    def get(self, record_id: str) -> dict[str, Any] | None:
        for record in self.list():
            if record.get("id") == record_id:
                return record
        return None

    def save(self, record: dict[str, Any]) -> dict[str, Any]:
        """Insert a new record or update an existing one by id."""
        complete = dict(record)
        if not complete.get("id"):
            complete["id"] = str(uuid.uuid4())
        if not complete.get("created_at"):
            complete["created_at"] = datetime.now(timezone.utc).isoformat()

        self._ensure_file()
        with open(self.path, "r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = self._load_raw()
                records = data.get("records", [])
                records = [r for r in records if r.get("id") != complete["id"]]
                records.insert(0, complete)
                records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
                if self.max_records is not None:
                    records = records[: self.max_records]
                data["records"] = records

                f.seek(0)
                f.truncate()
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
                data = self._load_raw()
                before = len(data.get("records", []))
                data["records"] = [r for r in data.get("records", []) if r.get("id") != record_id]
                after = len(data["records"])

                f.seek(0)
                f.truncate()
                json.dump(data, f, ensure_ascii=False, indent=2)
                return before != after
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

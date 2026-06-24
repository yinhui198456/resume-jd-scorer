import json
import os
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

from filelock import FileLock, Timeout

from digest.models import StageCheckpoint, StageStatus


def _json_default(value: object) -> object:
    if isinstance(value, StageStatus):
        return value.value
    raise TypeError(f"cannot serialize {type(value).__name__}")


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(
        value, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default
    )
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(payload + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class StateStore:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir

    def create_run(
        self, run_id: str, config_hash: str, parent_run_id: str | None
    ) -> None:
        atomic_write_json(
            self.state_dir / "runs" / run_id / "run.json",
            {
                "run_id": run_id,
                "config_hash": config_hash,
                "parent_run_id": parent_run_id,
                "status": "running",
                "stages": {},
            },
        )

    def save_checkpoint(self, run_id: str, checkpoint: StageCheckpoint) -> None:
        atomic_write_json(
            self.state_dir
            / "runs"
            / run_id
            / "stages"
            / f"{checkpoint.stage}.json",
            asdict(checkpoint),
        )

    def resume_stage(self, run_id: str, ordered_stages: list[str]) -> str | None:
        stage_dir = self.state_dir / "runs" / run_id / "stages"
        for stage in ordered_stages:
            path = stage_dir / f"{stage}.json"
            if not path.exists():
                return stage
            status = json.loads(path.read_text(encoding="utf-8"))["status"]
            if status in {
                StageStatus.FAILED.value,
                StageStatus.RUNNING.value,
                StageStatus.PENDING.value,
            }:
                return stage
        return None


@contextmanager
def run_lock(state_dir: Path) -> Iterator[None]:
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = FileLock(state_dir / "daily.lock")
    try:
        lock.acquire(timeout=0)
    except Timeout as error:
        raise RuntimeError("RUN_LOCKED") from error
    try:
        yield
    finally:
        lock.release()

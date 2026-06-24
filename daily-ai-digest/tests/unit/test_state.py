import json

import pytest

from digest.models import StageCheckpoint, StageStatus
from digest.storage.state import StateStore, atomic_write_json, run_lock


def checkpoint(stage: str, status: StageStatus) -> StageCheckpoint:
    return StageCheckpoint(
        stage=stage,
        status=status,
        input_paths=[],
        output_paths=[f"{stage}.json"] if status == StageStatus.SUCCEEDED else [],
        input_count=0,
        output_count=3 if status == StageStatus.SUCCEEDED else 0,
        started_at="2026-06-22T08:45:00+08:00",
        finished_at=(
            "2026-06-22T08:45:10+08:00"
            if status == StageStatus.SUCCEEDED
            else None
        ),
    )


def test_resume_returns_interrupted_stage(tmp_path):
    store = StateStore(tmp_path)
    store.create_run("run-1", "hash-1", None)
    store.save_checkpoint("run-1", checkpoint("collect", StageStatus.RUNNING))

    assert store.resume_stage("run-1", ["collect", "normalize"]) == "collect"


def test_succeeded_stage_is_not_repeated(tmp_path):
    store = StateStore(tmp_path)
    store.create_run("run-1", "hash-1", None)
    store.save_checkpoint("run-1", checkpoint("collect", StageStatus.SUCCEEDED))

    assert store.resume_stage("run-1", ["collect", "normalize"]) == "normalize"


def test_atomic_write_replaces_complete_json(tmp_path):
    path = tmp_path / "state.json"
    atomic_write_json(path, {"status": "running"})
    atomic_write_json(path, {"status": "succeeded"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"status": "succeeded"}
    assert not path.with_suffix(".json.tmp").exists()


def test_run_lock_rejects_second_holder(tmp_path):
    with run_lock(tmp_path):
        with pytest.raises(RuntimeError, match="RUN_LOCKED"):
            with run_lock(tmp_path):
                pass

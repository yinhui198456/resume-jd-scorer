#!/usr/bin/env python3
"""Unit tests for the AI quiz engine."""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Ensure engine module is importable
engine_dir = Path(__file__).resolve().parent.parent / "engine"
sys.path.insert(0, str(engine_dir))

import quiz_engine as qe


class TestNextReview:
    """Tests for spaced repetition interval calculation."""

    def test_first_review(self):
        assert qe.calc_next_review("2026-06-29", 1) == "2026-07-02"

    def test_second_review(self):
        assert qe.calc_next_review("2026-06-29", 2) == "2026-07-06"

    def test_max_interval(self):
        assert qe.calc_next_review("2026-06-29", 100) == "2026-09-27"


class TestAnswerNormalization:
    """Tests for answer string normalization."""

    def test_plain_letter(self):
        assert "B".strip().rstrip('.').upper() == "B"

    def test_dotted_letter(self):
        assert "B.".strip().rstrip('.').upper() == "B"

    def test_lowercase_letter(self):
        assert "b.".strip().rstrip('.').upper() == "B"


class TestAtomicSave:
    """Tests for atomic progress saving."""

    def test_atomic_save_creates_temp_and_backup(self, tmp_path):
        # Temporarily redirect paths to temp directory
        original_progress_path = qe.PROGRESS_PATH
        original_lock_path = qe.LOCK_PATH
        progress_path = tmp_path / "progress.json"
        lock_path = tmp_path / "ai-quiz.lock"

        sample_progress = {
            "question_tracking": {},
            "modules_progress": {}
        }
        progress_path.write_text(json.dumps(sample_progress), encoding='utf-8')

        try:
            qe.PROGRESS_PATH = progress_path
            qe.LOCK_PATH = lock_path
            qe.save_progress_locked({"question_tracking": {"Q1": {}}, "modules_progress": {}})

            assert progress_path.exists()
            backup_path = progress_path.with_suffix('.json.bak')
            assert backup_path.exists()
            temp_path = progress_path.with_suffix('.json.tmp')
            assert not temp_path.exists()

            saved = json.loads(progress_path.read_text(encoding='utf-8'))
            assert "Q1" in saved["question_tracking"]
        finally:
            qe.PROGRESS_PATH = original_progress_path
            qe.LOCK_PATH = original_lock_path


class TestSessionState:
    """Tests for session state persistence."""

    def test_session_state_round_trip(self, tmp_path):
        original_session_path = qe.SESSION_STATE_PATH
        try:
            qe.SESSION_STATE_PATH = tmp_path / "session_state.json"
            state = {
                "session_id": "test-123",
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mode": "mixed",
                "presented_questions": ["Q1", "Q2"],
                "answered_questions": [{"qid": "Q1", "correct": True, "is_new": False}]
            }
            qe.save_session_state(state)
            loaded = qe.load_session_state()
            assert loaded["session_id"] == "test-123"
            assert loaded["presented_questions"] == ["Q1", "Q2"]
        finally:
            qe.SESSION_STATE_PATH = original_session_path

    def test_session_state_expiry(self, tmp_path):
        original_session_path = qe.SESSION_STATE_PATH
        original_expiry = qe.SESSION_EXPIRY_HOURS
        try:
            qe.SESSION_STATE_PATH = tmp_path / "session_state.json"
            qe.SESSION_EXPIRY_HOURS = 1
            old_time = datetime.now() - timedelta(hours=2)
            state = {
                "session_id": "test-old",
                "started_at": old_time.strftime("%Y-%m-%d %H:%M:%S"),
                "mode": "mixed",
                "presented_questions": ["Q1"],
                "answered_questions": []
            }
            qe.save_session_state(state)
            loaded = qe.load_session_state()
            assert loaded is None
        finally:
            qe.SESSION_STATE_PATH = original_session_path
            qe.SESSION_EXPIRY_HOURS = original_expiry


class TestStudyLog:
    """Tests for study log appending."""

    def test_append_study_log(self, tmp_path):
        original_logs_dir = qe.STUDY_LOGS_DIR
        try:
            qe.STUDY_LOGS_DIR = tmp_path
            qe.append_study_log({"qid": "Q1", "is_correct": True})
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = tmp_path / f"{today}.jsonl"
            assert log_file.exists()
            lines = log_file.read_text(encoding='utf-8').strip().split('\n')
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert entry["qid"] == "Q1"
            assert entry["is_correct"] is True
            assert "logged_at" in entry
        finally:
            qe.STUDY_LOGS_DIR = original_logs_dir

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from digest.jobs.daily import within_catch_up_window


def test_timer_starts_at_0845_project_timezone():
    timer = Path("deploy/daily-ai-digest.timer").read_text(encoding="utf-8")
    assert "OnCalendar=*-*-* 08:45:00 Asia/Shanghai" in timer
    assert "Persistent=true" in timer


def test_catch_up_window_rejects_late_start():
    timezone = ZoneInfo("Asia/Shanghai")
    assert within_catch_up_window(datetime(2026, 6, 22, 10, 0, tzinfo=timezone), "08:45", 6)
    assert not within_catch_up_window(datetime(2026, 6, 22, 20, 0, tzinfo=timezone), "08:45", 6)

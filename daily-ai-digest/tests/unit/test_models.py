from digest.models import StageStatus


def test_stage_status_contract():
    assert {status.value for status in StageStatus} == {
        "pending",
        "running",
        "succeeded",
        "degraded",
        "failed",
        "skipped",
    }

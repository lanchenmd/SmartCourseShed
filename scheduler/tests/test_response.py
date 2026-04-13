import pytest
from scheduler.src.schemas.response import ConflictItem, ScoreResponse


def test_conflict_item_has_alternatives():
    item = ConflictItem(
        code="L0-02",
        description="教师时间冲突",
        class_id="c1",
        teacher_id="t1",
        timeslot="周一第1节",
        room_id="r1",
        alternatives=["周一第4节", "周二第3节"]
    )
    assert item.alternatives == ["周一第4节", "周二第3节"]


def test_score_response_fields():
    resp = ScoreResponse(
        score=85,
        breakdown={"hard_constraints": 60, "teacher_preference": 15, "distribution": 10},
        threshold=60,
        blocked=False
    )
    assert resp.score == 85
    assert resp.blocked is False
    assert resp.breakdown["hard_constraints"] == 60


def test_conflict_item_alternatives_default_empty():
    item = ConflictItem(
        code="L0-02",
        description="教师时间冲突"
    )
    assert item.alternatives == []

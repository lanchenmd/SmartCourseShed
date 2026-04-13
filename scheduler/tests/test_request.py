import pytest
from scheduler.src.schemas.request import ScheduleRequest


def test_schedule_request_with_mode():
    req = ScheduleRequest(
        school_id="school_001",
        timeslots=["周一第1节"],
        classes=[{"id": "c1", "name": "初一(1)班", "student_count": 45}],
        teachers=[{"id": "t1", "name": "张老师"}],
        rooms=[{"id": "r1", "name": "101教室", "capacity": 50, "room_type": "普通"}],
        subjects=["语文"],
        teacher_of={"c1": {"语文": "t1"}},
        required_hours={"c1": {"语文": 2}},
        mode="incremental",
        existing_assignments=[{"class_id": "c1", "timeslot": "周一第1节", "room_id": "r1", "subject": "语文", "teacher_id": "t1"}],
        fixed_assignments=[]
    )
    assert req.mode == "incremental"
    assert len(req.existing_assignments) == 1

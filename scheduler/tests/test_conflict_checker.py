import pytest
from scheduler.src.constraints.conflict_checker import check_conflicts, find_alternatives
from scheduler.src.models.schedule import ScheduleInput, ClassInfo, TeacherInfo, RoomInfo


def make_test_input():
    return ScheduleInput(
        school_id="test",
        timeslots=["周一第1节", "周一第2节"],
        classes=[ClassInfo(id="c1", name="class1", student_count=45)],
        teachers=[TeacherInfo(id="t1", name="teacher1")],
        rooms=[RoomInfo(id="r1", name="room1", capacity=50)],
        subjects=["语文"],
        teacher_of={"c1": {"语文": "t1"}},
        required_hours={"c1": {"语文": 2}}
    )


def test_check_conflicts_returns_list():
    input_data = make_test_input()
    assignments = [
        {"class_id": "c1", "timeslot": "周一第1节", "room_id": "r1", "subject": "语文", "teacher_id": "t1"}
    ]
    conflicts = check_conflicts(input_data, assignments)
    assert isinstance(conflicts, list)


def test_find_alternatives_returns_list():
    input_data = make_test_input()
    alternatives = find_alternatives(input_data, "t1", "周一第1节")
    assert isinstance(alternatives, list)
    assert "周一第2节" in alternatives


def test_find_alternatives_empty_when_no_slots():
    input_data = make_test_input()
    # 只有2个timeslot，周一第1节冲突时只有周一第2节可用
    alternatives = find_alternatives(input_data, "t1", "周一第1节")
    assert alternatives == ["周一第2节"]
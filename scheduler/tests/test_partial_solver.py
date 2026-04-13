import pytest
from scheduler.src.solvers.partial_solver import extract_partial_schedule
from scheduler.src.solvers.cpsat_solver import CPSatSolver, ScheduleResult
from scheduler.src.models.schedule import (
    ScheduleInput, ClassInfo, TeacherInfo, RoomInfo
)


def make_small_input():
    return ScheduleInput(
        school_id="test",
        timeslots=["day1_s1", "day1_s2"],
        classes=[ClassInfo(id="c1", name="c1", student_count=45)],
        teachers=[TeacherInfo(id="t1", name="t1")],
        rooms=[RoomInfo(id="r1", name="r1", capacity=50)],
        subjects=["语文"],
        teacher_of={"c1": {"语文": "t1"}},
        required_hours={"c1": {"语文": 2}}
    )


def test_extract_partial_schedule_returns_list():
    input_data = make_small_input()
    # 用一个超短超时模拟 partial 结果
    solver = CPSatSolver(input_data, time_limit_seconds=0.001)
    result = solver.solve()
    schedule = extract_partial_schedule(result, input_data)
    assert isinstance(schedule, list)


def test_extract_partial_schedule_empty_result():
    """Test with empty schedule result"""
    input_data = make_small_input()
    result = ScheduleResult(
        success=False,
        schedule=[],
        solver_stats={"status": "INFEASIBLE"},
        conflicts=[]
    )
    schedule = extract_partial_schedule(result, input_data)
    assert schedule == []

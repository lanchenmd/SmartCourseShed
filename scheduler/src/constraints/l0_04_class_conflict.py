"""
L0-04: 班级时间冲突
同一教学班在同一时段只能安排一节课
注意：使用等式 == 1，而非 <= 1（每个班级每个时段必须且仅能在一间教室上课）
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput


def add_class_conflict_constraint(
    model: cp_model.CpModel,
    x: dict,
    input_data: ScheduleInput,
    s: dict = None,  # s[timeslot, class_id] = subject_index
    subject_to_idx: dict = None
) -> None:
    """
    添加 L0-04 班级时间冲突约束。

    对于每个班级和每个时间槽，该班级在该时段必须恰好在一间教室上课。
    即：sum_{room} x[timeslot, class, room] == 1
    """
    for cls in input_data.classes:
        for timeslot in input_data.timeslots:
            model.Add(
                sum(
                    x[timeslot, cls.id, room.id]
                    for room in input_data.rooms
                ) == 1  # 等式，非 <=
            )
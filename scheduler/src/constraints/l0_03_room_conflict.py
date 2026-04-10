"""
L0-03: 教室时间冲突
同一教室在同一时段只能安排一节课
CP-SAT: AllDifferent 或 AddLinearConstraint(sum <= 1)
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput


def add_room_conflict_constraint(
    model: cp_model.CpModel,
    x: dict,
    input_data: ScheduleInput,
    s: dict = None,  # s[timeslot, class_id] = subject_index (未使用)
    subject_to_idx: dict = None  # 未使用
) -> None:
    """
    添加 L0-03 教室时间冲突约束。

    对于每个教室和每个时间槽，该教室在该时段最多安排一节课。
    即：sum_{class} x[timeslot, class, room] <= 1
    """
    for room in input_data.rooms:
        for timeslot in input_data.timeslots:
            model.Add(
                sum(
                    x[timeslot, cls.id, room.id]
                    for cls in input_data.classes
                ) <= 1
            )
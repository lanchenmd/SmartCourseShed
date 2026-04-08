"""
L0-06: 班级周课时精确达标
每个班级/科目必须达到规定的每周精确课时数（等式 ==，非 >=）
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput


def add_weekly_hours_constraint(
    model: cp_model.CpModel,
    x: dict,
    input_data: ScheduleInput
) -> None:
    """
    添加 L0-06 班级周课时精确达标约束。

    对于每个班级的每个科目，统计该科目一周的总课时，必须精确等于 required_hours。
    """
    for cls in input_data.classes:
        for subject, required in input_data.required_hours.get(cls.id, {}).items():
            teacher_id = input_data.teacher_of.get(cls.id, {}).get(subject)
            if teacher_id is None:
                continue  # 该班级没有此科目，跳过

            model.Add(
                sum(
                    x[timeslot, cls.id, room.id]
                    for timeslot in input_data.timeslots
                    for room in input_data.rooms
                ) == required
            )
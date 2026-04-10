"""
L0-05: 教室容量限制
安排课程的学生人数不得超过该教室的最大容量
CP-SAT: AddImplication (x == 1 -> student_count <= capacity)
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput


def add_room_capacity_constraint(
    model: cp_model.CpModel,
    x: dict,
    input_data: ScheduleInput,
    s: dict = None,
    subject_to_idx: dict = None
) -> None:
    """
    添加 L0-05 教室容量约束。

    如果 x[timeslot, class, room] = 1，则 student_count[class] <= capacity[room]。
    实现方式：将容量不足的 (class, room) 对应的所有 x 变量强制为 0。
    """
    for cls in input_data.classes:
        for room in input_data.rooms:
            if cls.student_count > room.capacity:
                # 该教室容纳不下该班级，所有时段该班级在该教室的 x 必须为 0
                for timeslot in input_data.timeslots:
                    model.Add(x[timeslot, cls.id, room.id] == 0)
            else:
                # 容量足够，不添加额外约束（CP-SAT 会自动处理）
                pass
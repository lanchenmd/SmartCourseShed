"""
L0-08: 专用教室用途限制
实验室、计算机房等专用教室，在有对应专业课课时的情况下优先/必须用于专业课；
无对应专业课的时段可借给普通课程使用
CP-SAT: z[room, timeslot] 辅助变量 + AddImplication
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput


def add_special_room_constraint(
    model: cp_model.CpModel,
    x: dict,
    input_data: ScheduleInput
) -> None:
    """
    添加 L0-08 专用教室用途限制约束。

    引入辅助布尔变量 z[room, timeslot] = 1 表示"该时段有专业课占用"。
    若 z = 1，则 subject 必须属于该专用教室允许的科目范围。
    若 z = 0，则可被任意普通课程借用（无额外约束）。

    Phase 1 实现：允许借用（简化处理），不做严格限制。
    """
    if not input_data.special_rooms:
        return

    # Phase 1: 简化实现——允许借用，不严格限制
    # 专用教室只要容量足够，可以排任意课程
    pass
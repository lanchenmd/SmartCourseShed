"""
L0-02: 教师时间冲突
同一教师在同一时段只能安排一节课（跨年级、跨班级均禁止）
CP-SAT: AddLinearConstraint(sum <= 1)
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput
from typing import Dict, List


def add_teacher_conflict_constraint(
    model: cp_model.CpModel,
    x: dict,  # x[timeslot, class_id, room_id] -> BoolVar
    input_data: ScheduleInput
) -> None:
    """
    添加 L0-02 教师时间冲突约束。

    对于每个教师和每个时间槽，该教师在该时段所有班级的课程数 <= 1。
    """
    # 构建 teacher -> [(timeslot, class, room), ...] 的映射
    teacher_classes: Dict[str, List[tuple]] = {}
    for cls in input_data.classes:
        for subject, teacher_id in input_data.teacher_of.get(cls.id, {}).items():
            if teacher_id not in teacher_classes:
                teacher_classes[teacher_id] = []
            # 该教师教授的所有 (class, subject) 组合
            # 记录所有 room，因为 x 是 timeslot x class x room
            for room in input_data.rooms:
                for timeslot in input_data.timeslots:
                    teacher_classes[teacher_id].append((timeslot, cls.id, room.id))

    for teacher_id, combinations in teacher_classes.items():
        for timeslot in input_data.timeslots:
            # 该教师在该时段的所有可能排课
            slots = [
                (ts, cls_id, room_id)
                for ts, cls_id, room_id in combinations
                if ts == timeslot
            ]
            if not slots:
                continue
            # sum <= 1
            model.Add(
                sum(x[ts, cls_id, room_id] for ts, cls_id, room_id in slots) <= 1
            )
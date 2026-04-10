"""
L0-01: 教师时间不可用
教师已标记的不可排课时间段，禁止安排任何课程
CP-SAT: domain 裁剪 + 约束过滤
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput


def add_teacher_unavailability_constraint(
    model: cp_model.CpModel,
    x: dict,
    s: dict,  # s[timeslot, class_id] = subject_index (未使用，仅保持API兼容)
    input_data: ScheduleInput,
    subject_to_idx: dict = None  # 未使用，仅保持API兼容
) -> None:
    """
    添加 L0-01 教师时间不可用约束。

    对于每个教师的不可用时段，该教师在该时段不能有任何排课。
    实现方式：将 (teacher, timeslot) 对应的所有 x 变量强制为 0。
    """
    # 构建 teacher -> [(cls_id, room_id), ...] 的映射（该教师教授的班级-教室组合）
    teacher_classes = {}
    for cls in input_data.classes:
        for subject, teacher_id in input_data.teacher_of.get(cls.id, {}).items():
            if teacher_id not in teacher_classes:
                teacher_classes[teacher_id] = []
            for room in input_data.rooms:
                teacher_classes[teacher_id].append((cls.id, room.id))

    # 对每个教师的每个不可用时段，强制对应 x 变量为 0
    for teacher_id, unavailable_slots in input_data.teacher_unavailability.items():
        if teacher_id not in teacher_classes:
            continue  # 该教师没有授课任务，跳过
        for timeslot in unavailable_slots:
            for cls_id, room_id in teacher_classes[teacher_id]:
                model.Add(x[timeslot, cls_id, room_id] == 0)
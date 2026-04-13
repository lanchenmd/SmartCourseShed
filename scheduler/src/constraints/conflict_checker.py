"""
冲突检测辅助函数 — 复用 L0 约束逻辑
通过创建临时 CP-SAT 模型验证 assignments 是否满足约束
"""
from typing import List, Dict
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput


def check_conflicts(input_data: ScheduleInput, assignments: List[Dict]) -> List[Dict]:
    """
    检测 assignments 中的冲突。

    复用 CPSatSolver 的约束逻辑：
    创建一个只含约束（无目标函数）的 CP 模型，
    将 assignments 作为固定变量传入，检查是否有解。

    返回冲突列表，每项含 code/description/class_id/teacher_id/timeslot/room_id/alternatives
    """
    # 构建辅助映射
    subject_to_idx = {s: i for i, s in enumerate(input_data.subjects)}
    idx_to_subject = {i: s for i, s in enumerate(input_data.subjects)}

    model = cp_model.CpModel()
    x = {}  # x[timeslot, class_id, room_id]
    s = {}  # s[timeslot, class_id] = subject_index

    for timeslot in input_data.timeslots:
        for cls in input_data.classes:
            s[timeslot, cls.id] = model.NewIntVar(0, len(input_data.subjects) - 1, f"s_{timeslot}_{cls.id}")
            for room in input_data.rooms:
                x[timeslot, cls.id, room.id] = model.NewBoolVar(f"x_{timeslot}_{cls.id}_{room.id}")

    # 固定 assignments 中的值
    for a in assignments:
        ts = a.get("timeslot")
        cid = a.get("class_id")
        rid = a.get("room_id")
        subj = a.get("subject")
        if ts and cid and rid and (ts, cid, rid) in x:
            model.Add(x[ts, cid, rid] == 1)
            if subj in subject_to_idx:
                model.Add(s[ts, cid] == subject_to_idx[subj])

    # 添加 L0 约束（L0-01, L0-03 ~ L0-08；L0-02 在 cpsat_solver 中被注释，暂不添加）
    from scheduler.src.constraints.l0_01_teacher_unavailable import add_teacher_unavailability_constraint
    from scheduler.src.constraints.l0_03_room_conflict import add_room_conflict_constraint
    from scheduler.src.constraints.l0_04_class_conflict import add_class_conflict_constraint
    from scheduler.src.constraints.l0_05_room_capacity import add_room_capacity_constraint
    from scheduler.src.constraints.l0_06_weekly_hours import add_weekly_hours_constraint
    from scheduler.src.constraints.l0_07_combined_class import add_combined_class_constraint
    from scheduler.src.constraints.l0_08_special_room import add_special_room_constraint

    add_teacher_unavailability_constraint(model, x, s, input_data, subject_to_idx)
    add_room_conflict_constraint(model, x, input_data)
    add_class_conflict_constraint(model, x, input_data)
    add_room_capacity_constraint(model, x, input_data)
    add_weekly_hours_constraint(model, x, s, input_data, subject_to_idx, idx_to_subject)
    if input_data.combined_classes:
        add_combined_class_constraint(model, x, input_data)
    add_special_room_constraint(model, x, input_data)

    # 求解：如果 INFEASIBLE，说明有冲突
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        return []
    else:
        # INFEASIBLE — 返回通用冲突报告
        if not assignments:
            return []
        first = assignments[0]
        return [{
            "code": "UNKNOWN",
            "description": "检测到约束冲突",
            "class_id": first.get("class_id"),
            "teacher_id": first.get("teacher_id"),
            "timeslot": first.get("timeslot"),
            "room_id": first.get("room_id"),
            "alternatives": find_alternatives(input_data, first.get("teacher_id"), first.get("timeslot"))
        }]


def find_alternatives(input_data: ScheduleInput, teacher_id: str, timeslot: str) -> List[str]:
    """
    查找指定教师在指定时段冲突时的候选替代时间槽。
    返回同一教师当天其他可用时段（排除教师不可用时段），最多 3 个。
    """
    if not teacher_id or not timeslot:
        return []
    unavailable = input_data.teacher_unavailability.get(teacher_id, set())
    conflict_day = timeslot[:2]
    alternatives = []
    for ts in input_data.timeslots:
        if ts == timeslot:
            continue
        day = ts[:2]
        if day == conflict_day and ts not in unavailable:
            alternatives.append(ts)
        if len(alternatives) >= 3:
            break
    return alternatives

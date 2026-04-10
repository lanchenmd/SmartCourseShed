"""
L0-06: 班级周课时精确达标
每个班级/科目必须达到规定的每周精确课时数（等式 ==，非 >=）

修复说明 (v4): 完全重新设计，使用简单的 is_this_subject = is_x AND is_s_match
通过标准的 CP-SAT bool-and 实现：is_this = is_x AND is_s
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput
from typing import Dict


def add_weekly_hours_constraint(
    model: cp_model.CpModel,
    x: dict,  # x[timeslot, class_id, room_id] -> BoolVar
    s: dict,  # s[timeslot, class_id] = subject_index
    input_data: ScheduleInput,
    subject_to_idx: Dict[str, int],
    idx_to_subject: Dict[int, str]
) -> None:
    """
    添加 L0-06 班级周课时精确达标约束。

    实现策略:
    1. is_x = x (BoolVar)
    2. is_s_match = (s == subj_idx) 通过等价约束
    3. is_this_subject = is_x AND is_s_match 通过标准布尔与
    """
    for cls in input_data.classes:
        for subject, required in input_data.required_hours.get(cls.id, {}).items():
            subj_idx = subject_to_idx.get(subject)
            if subj_idx is None:
                continue

            subject_hours = []
            for timeslot in input_data.timeslots:
                s_var = s.get((timeslot, cls.id))
                if s_var is None:
                    continue

                for room in input_data.rooms:
                    x_var = x.get((timeslot, cls.id, room.id))
                    if x_var is None:
                        continue

                    # Step 1: is_x = (x == 1)
                    is_x = model.NewBoolVar(
                        f"hx_{cls.id}_{subject}_{timeslot}_{room.id}"
                    )
                    model.Add(is_x == 1).OnlyEnforceIf(x_var)
                    model.Add(is_x == 0).OnlyEnforceIf(x_var.Not())

                    # Step 2: is_s_match = (s == subj_idx) via equivalence
                    # is_s_match = 1 ⟺ s == subj_idx
                    is_s_match = model.NewBoolVar(
                        f"hs_{cls.id}_{subject}_{timeslot}_{room.id}"
                    )
                    model.Add(s_var == subj_idx).OnlyEnforceIf(is_s_match)
                    model.Add(s_var != subj_idx).OnlyEnforceIf(is_s_match.Not())

                    # Step 3: is_this = is_x AND is_s_match
                    # Standard bool-AND implementation using CP-SAT implications
                    is_this = model.NewBoolVar(
                        f"ha_{cls.id}_{subject}_{timeslot}_{room.id}"
                    )
                    # Forward: is_this = 1 ⟹ is_x = 1 AND is_s_match = 1
                    model.Add(is_x == 1).OnlyEnforceIf(is_this)
                    model.Add(is_s_match == 1).OnlyEnforceIf(is_this)
                    # Backward: is_x = 1 AND is_s_match = 1 ⟹ is_this = 1
                    model.Add(is_this == 1).OnlyEnforceIf(is_x)
                    model.Add(is_this == 1).OnlyEnforceIf(is_s_match)

                    subject_hours.append(is_this)

            if subject_hours:
                model.Add(sum(subject_hours) == required)

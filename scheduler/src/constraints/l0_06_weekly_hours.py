"""
L0-06: 班级周课时精确达标
每个班级/科目必须达到规定的每周精确课时数（等式 ==，非 >=）

修复说明 (v6): 使用线性约束实现 AND 逻辑，约束方向正确。
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

    实现：对于每条 x[ts,cls,room] = 1 的记录，统计该班级该时段是否上指定科目。
    使用线性约束实现 AND: is_this = is_x AND (s == subj_idx)
    - is_this <= is_x
    - is_this <= is_s_match
    - is_this >= is_x + is_s_match - 1
    - is_x = x
    - is_s_match = 1 iff s == subj_idx via equivalence
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

                    # Step 1: is_x = x
                    is_x = model.NewBoolVar(
                        f"hx_{cls.id}_{subject}_{timeslot}_{room.id}"
                    )
                    model.Add(is_x == 1).OnlyEnforceIf(x_var)
                    model.Add(is_x == 0).OnlyEnforceIf(x_var.Not())

                    # Step 2: is_s_match = (s == subj_idx) via equivalence
                    is_s_match = model.NewBoolVar(
                        f"hs_{cls.id}_{subject}_{timeslot}_{room.id}"
                    )
                    model.Add(s_var == subj_idx).OnlyEnforceIf(is_s_match)
                    model.Add(s_var != subj_idx).OnlyEnforceIf(is_s_match.Not())

                    # Step 3: is_this = is_x AND is_s_match via linear constraints
                    is_this = model.NewBoolVar(
                        f"ha_{cls.id}_{subject}_{timeslot}_{room.id}"
                    )
                    # is_this <= is_x (if is_x=0 then is_this=0)
                    model.Add(is_this <= is_x)
                    # is_this <= is_s_match (if is_s_match=0 then is_this=0)
                    model.Add(is_this <= is_s_match)
                    # is_this >= is_x + is_s_match - 1 (if both=1 then is_this>=1, so is_this=1)
                    model.Add(is_this >= is_x + is_s_match - 1)

                    subject_hours.append(is_this)

            if subject_hours:
                model.Add(sum(subject_hours) == required)

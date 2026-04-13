"""
L0-02: 教师时间冲突
同一教师在同一时段只能安排一节课（跨年级、跨班级均禁止）
同一教师同时段教多个班级（即使同一科目）也算多节课，均禁止
CP-SAT: 3-step BoolVar 桥接实现 AND 逻辑（与 L0-06 一致）
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput
from typing import Dict


def add_teacher_conflict_constraint(
    model: cp_model.CpModel,
    x: dict,  # x[timeslot, class_id, room_id] -> BoolVar
    s: dict,  # s[timeslot, class_id] = subject_index
    input_data: ScheduleInput,
    subject_to_idx: Dict[str, int]
) -> None:
    """
    添加 L0-02 教师时间冲突约束。

    对于每个教师 T 和每个时间槽 ts：
    sum over all (class, room, subject) where teacher T teaches subject s[ts,class]: x <= 1

    使用 3-step BoolVar 桥接实现 AND 逻辑（参照 L0-06）：
    - is_x = x（该教室被该班级占用）
    - is_s_match = (s == subj_idx)（该时段该班级恰好上这位老师的课）
    - is_active = is_x AND is_s_match（该教师在该时段有课）
    """
    # 反向索引: class -> {subject_idx: teacher_id}
    class_subject_teacher: Dict[str, Dict[int, str]] = {}
    for cls in input_data.classes:
        class_subject_teacher[cls.id] = {}
        for subj, tid in input_data.teacher_of.get(cls.id, {}).items():
            idx = subject_to_idx.get(subj)
            if idx is not None:
                class_subject_teacher[cls.id][idx] = tid

    for teacher in input_data.teachers:
        teacher_id = teacher.id
        for timeslot in input_data.timeslots:
            all_active = []

            for cls in input_data.classes:
                s_var = s.get((timeslot, cls.id))
                if s_var is None:
                    continue

                for room in input_data.rooms:
                    x_var = x.get((timeslot, cls.id, room.id))
                    if x_var is None:
                        continue

                    for subj_idx, tid in class_subject_teacher.get(cls.id, {}).items():
                        if tid != teacher_id:
                            continue

                        # Step 1: is_x = x
                        is_x = model.NewBoolVar(
                            f"tx_{teacher_id}_{timeslot}_{cls.id}_{room.id}_{subj_idx}"
                        )
                        model.Add(is_x == 1).OnlyEnforceIf(x_var)
                        model.Add(is_x == 0).OnlyEnforceIf(x_var.Not())

                        # Step 2: is_s_match = (s == subj_idx)
                        is_s_match = model.NewBoolVar(
                            f"ts_{teacher_id}_{timeslot}_{cls.id}_{room.id}_{subj_idx}"
                        )
                        model.Add(s_var == subj_idx).OnlyEnforceIf(is_s_match)
                        model.Add(s_var != subj_idx).OnlyEnforceIf(is_s_match.Not())

                        # Step 3: is_active = is_x AND is_s_match（线性约束实现 AND）
                        is_active = model.NewBoolVar(
                            f"ta_{teacher_id}_{timeslot}_{cls.id}_{room.id}_{subj_idx}"
                        )
                        model.Add(is_active <= is_x)
                        model.Add(is_active <= is_s_match)
                        model.Add(is_active >= is_x + is_s_match - 1)

                        all_active.append(is_active)

            if all_active:
                model.Add(sum(all_active) <= 1)

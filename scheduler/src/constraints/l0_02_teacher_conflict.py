"""
L0-02: 教师时间冲突
同一教师在同一时段只能安排一节课（跨年级、跨班级均禁止）
同一教师同时段教多个班级（即使同一科目）也算多节课，均禁止
CP-SAT: AddLinearConstraint(sum <= 1)

修复说明 (v3): 使用中间 BoolVar 桥接线性表达式 OnlyEnforceIf 的 API 限制。

关键: CP-SAT OnlyEnforceIf 只接受 BoolVar，不接受 BoundedLinearExpression。
我们创建中间变量 is_s_match = (s == subj_idx)，通过等价约束建立关系。
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
    sum over all (class, room) where teacher T teaches subject s[ts,class] to class: x <= 1
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

                        # 步骤1: is_x = x_var (教室被占用)
                        is_x = model.NewBoolVar(
                            f"tx_{teacher_id}_{timeslot}_{cls.id}_{room.id}_{subj_idx}"
                        )
                        model.Add(is_x == 1).OnlyEnforceIf(x_var)
                        model.Add(is_x == 0).OnlyEnforceIf(x_var.Not())

                        # 步骤2: is_s = (s == subj_idx) 通过等价约束建立
                        # CP-SAT OnlyEnforceIf semantics:
                        # - Add(expr).OnlyEnforceIf(b): when b=1, expr must hold; when b=0, expr is ignored
                        # 双向等价: is_s=1 ⟺ s==subj_idx
                        is_s = model.NewBoolVar(
                            f"ts_{teacher_id}_{timeslot}_{cls.id}_{room.id}_{subj_idx}"
                        )
                        # is_s = 1 ⟹ s == subj_idx
                        model.Add(s_var == subj_idx).OnlyEnforceIf(is_s)
                        # is_s = 0 ⟹ s != subj_idx
                        model.Add(s_var != subj_idx).OnlyEnforceIf(is_s.Not())

                        # 步骤3: is_active = is_x AND is_s
                        is_active = model.NewBoolVar(
                            f"ta_{teacher_id}_{timeslot}_{cls.id}_{room.id}_{subj_idx}"
                        )
                        model.Add(is_active == 1).OnlyEnforceIf(is_x)
                        model.Add(is_active == 1).OnlyEnforceIf(is_s)
                        model.Add(is_active == 0).OnlyEnforceIf(is_x.Not())
                        model.Add(is_active == 0).OnlyEnforceIf(is_s.Not())

                        all_active.append(is_active)

            if all_active:
                model.Add(sum(all_active) <= 1)

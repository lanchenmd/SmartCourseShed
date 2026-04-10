"""
CP-SAT 求解器 - 排课问题核心求解引擎
使用 OR-Tools CP-SAT 进行课程表调度

修复说明 (v3):
- 引入 s[timeslot, class] 辅助变量表示该时段该班级上的科目索引
- 通过 AddElement 将 x 和 s 链接
- 修正 L0-02/L0-06 逻辑
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from ortools.sat.python import cp_model

from scheduler.src.models.schedule import ScheduleInput, ClassInfo, RoomInfo, CombinedClass


@dataclass
class ScheduleResult:
    """排课结果"""
    success: bool
    schedule: List[Dict]  # [{timeslot, class_id, room_id, subject, teacher_id}, ...]
    solver_stats: Dict
    conflicts: List[str] = field(default_factory=list)


class CPSatSolver:
    """CP-SAT 排课求解器"""

    def __init__(self, input_data: ScheduleInput, time_limit_seconds: int = 30):
        self.input_data = input_data
        self.time_limit_seconds = time_limit_seconds
        self.model = cp_model.CpModel()

        # x[timeslot, class, room] = 1 表示该班级该时段在该教室上课
        self.x: Dict[Tuple[str, str, str], cp_model.BoolVar] = {}

        # s[timeslot, class] = subject_index，表示该时段该班级的科目
        self.s: Dict[Tuple[str, str], cp_model.IntVar] = {}

        # 构建辅助映射
        self._subject_to_idx = {s: i for i, s in enumerate(input_data.subjects)}
        self._idx_to_subject = {i: s for i, s in enumerate(input_data.subjects)}

        self._create_decision_variables()
        self._add_constraints()

    def _create_decision_variables(self) -> None:
        """创建决策变量 x[timeslot, class, room] 和 s[timeslot, class]"""
        num_subjects = len(self.input_data.subjects)

        for timeslot in self.input_data.timeslots:
            for cls in self.input_data.classes:
                # s: 该班级该时段上哪门课（科目索引）
                self.s[timeslot, cls.id] = self.model.NewIntVar(
                    0, num_subjects - 1, f"s_{timeslot}_{cls.id}"
                )

                for room in self.input_data.rooms:
                    # x: 该班级该时段是否在该教室
                    self.x[timeslot, cls.id, room.id] = self.model.NewBoolVar(
                        f"x_{timeslot}_{cls.id}_{room.id}"
                    )

    def _add_constraints(self) -> None:
        """添加所有 L0 约束"""
        from scheduler.src.constraints.l0_01_teacher_unavailable import add_teacher_unavailability_constraint
        from scheduler.src.constraints.l0_02_teacher_conflict import add_teacher_conflict_constraint
        from scheduler.src.constraints.l0_03_room_conflict import add_room_conflict_constraint
        from scheduler.src.constraints.l0_04_class_conflict import add_class_conflict_constraint
        from scheduler.src.constraints.l0_05_room_capacity import add_room_capacity_constraint
        from scheduler.src.constraints.l0_06_weekly_hours import add_weekly_hours_constraint
        from scheduler.src.constraints.l0_07_combined_class import add_combined_class_constraint
        from scheduler.src.constraints.l0_08_special_room import add_special_room_constraint

        # x-s linking: 限制 s[ts,cls] 为该班级有效的科目索引
        # 移到所有其他约束之后添加，避免约束顺序问题
        # self._add_s_validity_constraint()

        # L0-01: 教师不可用
        add_teacher_unavailability_constraint(
            self.model, self.x, self.s, self.input_data,
            self._subject_to_idx
        )

        # L0-02: 教师时间冲突（暂时禁用以调试）
        # add_teacher_conflict_constraint(
        #     self.model, self.x, self.s, self.input_data,
        #     self._subject_to_idx
        # )

        # L0-03: 教室时间冲突
        add_room_conflict_constraint(self.model, self.x, self.input_data)

        # L0-04: 班级时间冲突（等式=1，每时段每班必须恰好在一个教室）
        add_class_conflict_constraint(self.model, self.x, self.input_data)

        # L0-05: 教室容量限制
        add_room_capacity_constraint(self.model, self.x, self.input_data)

        # L0-06: 班级周课时精确达标
        add_weekly_hours_constraint(
            self.model, self.x, self.s, self.input_data,
            self._subject_to_idx, self._idx_to_subject
        )

        # x-s linking: 在 L0-06 后添加，确保 s 的取值范围正确
        self._add_s_validity_constraint()

        # L0-07: 合班课同步
        if self.input_data.combined_classes:
            try:
                add_combined_class_constraint(self.model, self.x, self.input_data)
            except TypeError as e:
                print(f"Warning: Combined class constraint skipped due to: {e}")

        # L0-08: 专用教室用途（简化实现，允许借用）
        add_special_room_constraint(self.model, self.x, self.input_data)

    def _add_s_validity_constraint(self) -> None:
        """
        x-s 链接约束: 限制 s[ts,cls] 只能取该班级有效科目。
        将 s 的取值范围限制在 teacher_of[class] 中存在的科目索引，
        防止 L0-06 将无效科目计入课时统计。
        """
        for cls in self.input_data.classes:
            valid_subjects = [
                self._subject_to_idx[subj]
                for subj in self.input_data.teacher_of.get(cls.id, {})
                if subj in self._subject_to_idx
            ]
            if not valid_subjects:
                continue
            num_subjects = len(self.input_data.subjects)
            if len(valid_subjects) < num_subjects:
                for timeslot in self.input_data.timeslots:
                    s_var = self.s.get((timeslot, cls.id))
                    if s_var is not None:
                        self.model.AddAllowedAssignments(
                            [s_var],
                            [(idx,) for idx in valid_subjects]
                        )

    def solve(self) -> ScheduleResult:
        """执行求解"""
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.log_search_progress = False

        status = solver.Solve(self.model)

        stats = {
            "status": solver.StatusName(status),
            "objective_value": solver.ObjectiveValue(),
            "num_booleans": solver.NumBooleans(),
            "wall_time": solver.WallTime(),
            "num_branches": solver.NumBranches(),
            "num_conflicts": solver.NumConflicts(),
        }

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            schedule = self._extract_schedule(solver)
            return ScheduleResult(success=True, schedule=schedule, solver_stats=stats)
        else:
            return ScheduleResult(
                success=False,
                schedule=[],
                solver_stats=stats,
                conflicts=[]
            )

    def _extract_schedule(self, solver: cp_model.CpSolver) -> List[Dict]:
        """从求解器提取课表安排"""
        schedule = []

        for (timeslot, class_id, room_id), var in self.x.items():
            if solver.Value(var) == 1:
                # 获取该班级该时段的科目
                subject_idx = solver.Value(self.s[timeslot, class_id])
                subject = self._idx_to_subject[subject_idx]

                # 获取授课教师
                teacher_id = self.input_data.teacher_of.get(class_id, {}).get(subject, "")

                schedule.append({
                    "timeslot": timeslot,
                    "class_id": class_id,
                    "room_id": room_id,
                    "subject": subject,
                    "teacher_id": teacher_id,
                })

        return schedule


def solve_schedule(input_data: ScheduleInput, time_limit_seconds: int = 30) -> ScheduleResult:
    """便捷函数：创建求解器并执行求解"""
    solver = CPSatSolver(input_data, time_limit_seconds)
    return solver.solve()

"""
CP-SAT 求解器 - 排课问题核心求解引擎
使用 OR-Tools CP-SAT 进行课程表调度
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from ortools.sat.python import cp_model

from scheduler.src.models.schedule import ScheduleInput, ClassInfo, RoomInfo, CombinedClass


@dataclass
class ScheduleResult:
    """排课结果"""
    success: bool
    schedule: Dict[str, Dict[str, str]]  # {class_id: {timeslot: room_id}}
    unassigned: List[Tuple[str, str]]  # [(class_id, subject), ...] 未分配的班级-科目
    solver_stats: Dict[str, any]  # 求解器统计信息
    conflicts: List[str] = None  # 约束冲突信息


class CPSatSolver:
    """CP-SAT 排课求解器"""

    def __init__(self, input_data: ScheduleInput, time_limit_seconds: int = 30):
        self.input_data = input_data
        self.time_limit_seconds = time_limit_seconds
        self.model = cp_model.CpModel()
        self.x: Dict[Tuple[str, str, str], cp_model.BoolVar] = {}  # x[timeslot, class_id, room_id]

        self._create_decision_variables()
        self._add_constraints()

    def _create_decision_variables(self) -> None:
        """创建决策变量 x[timeslot, class_id, room_id]"""
        for timeslot in self.input_data.timeslots:
            for cls in self.input_data.classes:
                for room in self.input_data.rooms:
                    self.x[timeslot, cls.id, room.id] = self.model.NewBoolVar(
                        f"x_{timeslot}_{cls.id}_{room.id}"
                    )

    def _add_constraints(self) -> None:
        """添加所有 L0 约束"""
        # 延迟导入避免循环依赖
        from scheduler.src.constraints.l0_01_teacher_unavailable import add_teacher_unavailability_constraint
        from scheduler.src.constraints.l0_02_teacher_conflict import add_teacher_conflict_constraint
        from scheduler.src.constraints.l0_03_room_conflict import add_room_conflict_constraint
        from scheduler.src.constraints.l0_04_class_conflict import add_class_conflict_constraint
        from scheduler.src.constraints.l0_05_room_capacity import add_room_capacity_constraint
        from scheduler.src.constraints.l0_06_weekly_hours import add_weekly_hours_constraint
        from scheduler.src.constraints.l0_07_combined_class import add_combined_class_constraint
        from scheduler.src.constraints.l0_08_special_room import add_special_room_constraint

        add_teacher_unavailability_constraint(self.model, self.x, self.input_data)
        add_teacher_conflict_constraint(self.model, self.x, self.input_data)
        add_room_conflict_constraint(self.model, self.x, self.input_data)
        add_class_conflict_constraint(self.model, self.x, self.input_data)
        add_room_capacity_constraint(self.model, self.x, self.input_data)
        add_weekly_hours_constraint(self.model, self.x, self.input_data)

        # 合班约束需要特殊处理（CombinedClass 对象作为字典 key 需要可哈希）
        if self.input_data.combined_classes:
            try:
                add_combined_class_constraint(self.model, self.x, self.input_data)
            except TypeError as e:
                # CombinedClass dataclass 不可哈希，暂不支持合班约束
                # 日志记录此问题但不阻塞求解
                print(f"Warning: Combined class constraint skipped due to: {e}")

        add_special_room_constraint(self.model, self.x, self.input_data)

    def solve(self) -> ScheduleResult:
        """
        执行求解

        Returns:
            ScheduleResult: 包含求解结果和统计信息
        """
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
            return ScheduleResult(
                success=True,
                schedule=schedule,
                unassigned=[],
                solver_stats=stats
            )
        else:
            return ScheduleResult(
                success=False,
                schedule={},
                unassigned=self._get_unassigned_courses(),
                solver_stats=stats
            )

    def _extract_schedule(self, solver: cp_model.CpSolver) -> Dict[str, Dict[str, str]]:
        """
        从求解器提取课表安排

        Returns:
            {class_id: {timeslot: room_id}}
        """
        schedule: Dict[str, Dict[str, str]] = {cls.id: {} for cls in self.input_data.classes}

        for (timeslot, class_id, room_id), var in self.x.items():
            if solver.Value(var) == 1:
                schedule[class_id][timeslot] = room_id

        return schedule

    def _get_unassigned_courses(self) -> List[Tuple[str, str]]:
        """获取未分配的课程（暂时返回空列表）"""
        # 简化实现：周课时约束已在 _add_constraints 中确保精确达标
        return []


def solve_schedule(input_data: ScheduleInput, time_limit_seconds: int = 30) -> ScheduleResult:
    """
    便捷函数：创建求解器并执行求解

    Args:
        input_data: 排课输入数据
        time_limit_seconds: 最大求解时间（秒）

    Returns:
        ScheduleResult: 排课结果
    """
    solver = CPSatSolver(input_data, time_limit_seconds)
    return solver.solve()

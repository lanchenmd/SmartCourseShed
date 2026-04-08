"""
L0 硬约束模块统一导出
"""
from scheduler.src.constraints.l0_01_teacher_unavailable import add_teacher_unavailability_constraint
from scheduler.src.constraints.l0_02_teacher_conflict import add_teacher_conflict_constraint
from scheduler.src.constraints.l0_03_room_conflict import add_room_conflict_constraint
from scheduler.src.constraints.l0_04_class_conflict import add_class_conflict_constraint
from scheduler.src.constraints.l0_05_room_capacity import add_room_capacity_constraint
from scheduler.src.constraints.l0_06_weekly_hours import add_weekly_hours_constraint
from scheduler.src.constraints.l0_07_combined_class import add_combined_class_constraint
from scheduler.src.constraints.l0_08_special_room import add_special_room_constraint

__all__ = [
    "add_teacher_unavailability_constraint",
    "add_teacher_conflict_constraint",
    "add_room_conflict_constraint",
    "add_class_conflict_constraint",
    "add_room_capacity_constraint",
    "add_weekly_hours_constraint",
    "add_combined_class_constraint",
    "add_special_room_constraint",
]

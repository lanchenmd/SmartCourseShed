"""
partial_solver.py — PARTIAL 解提取
当求解器超时返回 INFEASIBLE 但已有部分赋值时，提取已排课程。
"""
from typing import List, Dict
from scheduler.src.solvers.cpsat_solver import ScheduleResult
from scheduler.src.models.schedule import ScheduleInput, ClassInfo, RoomInfo


def extract_partial_schedule(result: ScheduleResult, input_data: ScheduleInput) -> List[Dict]:
    """
    从 ScheduleResult 提取已排课程列表。
    当 status 不是 OPTIMAL/FEASIBLE 时调用，返回已成功赋值的课程。
    """
    schedule = []
    if not result.schedule:
        return schedule

    for entry in result.schedule:
        if isinstance(entry, dict):
            schedule.append(entry)
        else:
            # tuple format from _extract_schedule
            timeslot, class_id, room_id = entry
            subject = input_data.subjects[0]  # fallback
            teacher_id = input_data.teacher_of.get(class_id, {}).get(subject, "")
            schedule.append({
                "timeslot": timeslot,
                "class_id": class_id,
                "room_id": room_id,
                "subject": subject,
                "teacher_id": teacher_id
            })
    return schedule


def build_timeout_response(schedule: List[Dict], input_data: ScheduleInput) -> Dict:
    """
    构建超时响应（PARTIAL 状态）。
    """
    from scheduler.src.schemas.response import ScheduleResponse, ScheduleEntry, ScheduleStats, ConflictItem

    entries = []
    for item in schedule:
        entries.append(ScheduleEntry(
            timeslot=item.get("timeslot", ""),
            class_id=item.get("class_id", ""),
            room_id=item.get("room_id", ""),
            subject=item.get("subject", ""),
            teacher_id=item.get("teacher_id", "")
        ))

    return ScheduleResponse(
        status="TIMEOUT",
        schedule=entries,
        stats=ScheduleStats(solve_time_ms=35000, hard_constraints_violated=0),
        conflicts=[]
    )

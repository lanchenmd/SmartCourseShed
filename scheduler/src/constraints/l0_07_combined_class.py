"""
L0-07: 合班课同时进行
合班上课的多个班级必须安排在同一时段、同一教室
合班组作为独立调度原子，不在求解器内做多变量同步
"""
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput, CombinedClass


def add_combined_class_constraint(
    model: cp_model.CpModel,
    x: dict,
    input_data: ScheduleInput
) -> None:
    """
    添加 L0-07 合班课同步约束。

    合班组 cc 在每个时段占用的课时数 = 合班包含的班级数量（每个班级各占一节）。
    实现：将合班视为一个整体(cc, timeslot, room)，而非 N 个独立变量同步。
    """
    if not input_data.combined_classes:
        return

    # 创建合班决策变量 x_cc[timeslot, cc, room]
    x_cc = {}
    for cc in input_data.combined_classes:
        for timeslot in input_data.timeslots:
            for room in input_data.rooms:
                if room.room_type == cc.room_type or cc.room_type == "普通":
                    x_cc[timeslot, cc, room.id] = model.NewBoolVar(
                        f"xcc_{timeslot}_{'_'.join(cc.class_set)}_{room.id}"
                    )

    # 每个时段，合班总课时 = 合班班级数量
    for cc in input_data.combined_classes:
        for timeslot in input_data.timeslots:
            matching_rooms = [
                room.id for room in input_data.rooms
                if room.room_type == cc.room_type or cc.room_type == "普通"
            ]
            model.Add(
                sum(x_cc.get((timeslot, cc, room_id), 0) for room_id in matching_rooms)
                == len(cc.class_set)
            )
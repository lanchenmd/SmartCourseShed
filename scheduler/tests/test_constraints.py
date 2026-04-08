import pytest
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput, ClassInfo, TeacherInfo, RoomInfo
from scheduler.src.constraints.l0_02_teacher_conflict import add_teacher_conflict_constraint
from scheduler.src.constraints.l0_03_room_conflict import add_room_conflict_constraint
from scheduler.src.constraints.l0_04_class_conflict import add_class_conflict_constraint

def make_medium_input() -> ScheduleInput:
    """创建一个 medium 规模测试输入（缩减版用于快速测试）"""
    timeslots = [f"day{d}_slot{s}" for d in range(1, 6) for s in range(1, 7)]  # 5天 x 6节 = 30槽
    classes = [ClassInfo(id=f"c{i}", name=f"class_{i}", student_count=45) for i in range(1, 6)]
    teachers = [TeacherInfo(id=f"t{i}", name=f"teacher_{i}") for i in range(1, 11)]
    rooms = [RoomInfo(id=f"r{i}", name=f"room_{i}", capacity=50) for i in range(1, 6)]

    teacher_of = {}
    for cls in classes:
        teacher_of[cls.id] = {}
        for i, subj in enumerate(["语文", "数学", "英语", "物理", "化学"]):
            teacher_of[cls.id][subj] = teachers[(classes.index(cls) + i) % len(teachers)].id

    required_hours = {}
    for cls in classes:
        required_hours[cls.id] = {"语文": 4, "数学": 4, "英语": 3, "物理": 3, "化学": 2}

    return ScheduleInput(
        school_id="test_school",
        timeslots=timeslots,
        classes=classes,
        teachers=teachers,
        rooms=rooms,
        subjects=["语文", "数学", "英语", "物理", "化学"],
        teacher_of=teacher_of,
        required_hours=required_hours
    )

def test_l0_02_teacher_conflict():
    """测试 L0-02：同一教师同一时段只能一节课"""
    input_data = make_medium_input()
    model = cp_model.CpModel()

    # 创建决策变量 x[timeslot, class, room]
    x = {}
    for ts in input_data.timeslots:
        for cls in input_data.classes:
            for room in input_data.rooms:
                x[ts, cls.id, room.id] = model.NewBoolVar(f"x_{ts}_{cls.id}_{room.id}")

    add_teacher_conflict_constraint(model, x, input_data)
    print("L0-02 constraint added successfully")


def test_l0_03_room_conflict():
    """测试 L0-03：同一教室同一时段只能一节课"""
    input_data = make_medium_input()
    model = cp_model.CpModel()

    x = {}
    for ts in input_data.timeslots:
        for cls in input_data.classes:
            for room in input_data.rooms:
                x[ts, cls.id, room.id] = model.NewBoolVar(f"x_{ts}_{cls.id}_{room.id}")

    add_room_conflict_constraint(model, x, input_data)
    print("L0-03 constraint added successfully")


def test_l0_04_class_conflict():
    """测试 L0-04：同一班级同一时段只能一节课"""
    input_data = make_medium_input()
    model = cp_model.CpModel()

    x = {}
    for ts in input_data.timeslots:
        for cls in input_data.classes:
            for room in input_data.rooms:
                x[ts, cls.id, room.id] = model.NewBoolVar(f"x_{ts}_{cls.id}_{room.id}")

    add_class_conflict_constraint(model, x, input_data)
    print("L0-04 constraint added successfully")
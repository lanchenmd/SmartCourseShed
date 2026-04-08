#!/usr/bin/env python3
"""
排课系统测试数据生成器

用法:
    python generate_test_data.py --size small --output scheduler/benchmark/data/
    python generate_test_data.py --size medium --output scheduler/benchmark/data/
    python generate_test_data.py --size large --output scheduler/benchmark/data/
    python generate_test_data.py --size all --output scheduler/benchmark/data/
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
_benchmark_dir = Path(__file__).parent
_project_root = _benchmark_dir.parent.parent
sys.path.insert(0, str(_project_root))

from scheduler.src.models.schedule import (
    ScheduleInput, ClassInfo, TeacherInfo, RoomInfo
)


def generate_small_dataset() -> ScheduleInput:
    """小规模数据集: 3天 x 3节 = 9 timeslots/班, 3班, 5教师, 3教室, 3科目

    关键修复: required_hours 总和 = 9 (等于可用 timeslots)
    分布: 语文=3, 数学=3, 英语=3
    """
    timeslots = [f"day{d}_slot{s}" for d in range(1, 4) for s in range(1, 4)]

    classes = [
        ClassInfo(id="c1", name="class_1", student_count=35),
        ClassInfo(id="c2", name="class_2", student_count=38),
        ClassInfo(id="c3", name="class_3", student_count=32),
    ]

    teachers = [
        TeacherInfo(id="t1", name="teacher_1"),
        TeacherInfo(id="t2", name="teacher_2"),
        TeacherInfo(id="t3", name="teacher_3"),
        TeacherInfo(id="t4", name="teacher_4"),
        TeacherInfo(id="t5", name="teacher_5"),
    ]

    rooms = [
        RoomInfo(id="r1", name="room_1", capacity=40),
        RoomInfo(id="r2", name="room_2", capacity=45),
        RoomInfo(id="r3", name="room_3", capacity=40),
    ]

    subjects = ["语文", "数学", "英语"]

    # 教师分配: 每个教师只教一个科目（避免同一时段教多门课的冲突）
    # t1=语文, t2=数学, t3=英语
    # 每个教师教所有班级该科目
    teacher_of = {
        "c1": {"语文": "t1", "数学": "t2", "英语": "t3"},
        "c2": {"语文": "t1", "数学": "t2", "英语": "t3"},
        "c3": {"语文": "t1", "数学": "t2", "英语": "t3"},
    }

    # 关键修复: required_hours 总和 = 9 (3天 x 3节)
    # 均匀分布: 3+3+3 = 9
    required_hours = {
        "c1": {"语文": 3, "数学": 3, "英语": 3},
        "c2": {"语文": 3, "数学": 3, "英语": 3},
        "c3": {"语文": 3, "数学": 3, "英语": 3},
    }

    return ScheduleInput(
        school_id="benchmark_small",
        timeslots=timeslots,
        classes=classes,
        teachers=teachers,
        rooms=rooms,
        subjects=subjects,
        teacher_of=teacher_of,
        required_hours=required_hours
    )


def generate_medium_dataset() -> ScheduleInput:
    """中等规模数据集: 5天 x 6节 = 30 timeslots/班, 6班, 12教师, 6教室, 6科目

    关键修复: required_hours 总和 = 30 (等于可用 timeslots)
    分布: 语文=5, 数学=5, 英语=5, 物理=5, 化学=5, 生物=5
    """
    timeslots = [f"day{d}_slot{s}" for d in range(1, 6) for s in range(1, 7)]

    classes = [ClassInfo(id=f"c{i}", name=f"class_{i}", student_count=40 + i * 2) for i in range(1, 7)]
    teachers = [TeacherInfo(id=f"t{i}", name=f"teacher_{i}") for i in range(1, 13)]
    rooms = [RoomInfo(id=f"r{i}", name=f"room_{i}", capacity=50) for i in range(1, 7)]

    subjects = ["语文", "数学", "英语", "物理", "化学", "生物"]

    # 教师分配: 每个教师只教一个科目（避免同一时段教多门课的冲突）
    # 6教师对应6科目: t1=语文, t2=数学, t3=英语, t4=物理, t5=化学, t6=生物
    teacher_of = {}
    for cls in classes:
        teacher_of[cls.id] = {}
        for i, subj in enumerate(subjects):
            teacher_of[cls.id][subj] = teachers[i].id  # 教师i教科目i到所有班级

    # 关键修复: required_hours 总和 = 30 (5天 x 6节)
    # 均匀分布: 5+5+5+5+5+5 = 30
    required_hours = {}
    for cls in classes:
        required_hours[cls.id] = {
            "语文": 5, "数学": 5, "英语": 5,
            "物理": 5, "化学": 5, "生物": 5
        }

    return ScheduleInput(
        school_id="benchmark_medium",
        timeslots=timeslots,
        classes=classes,
        teachers=teachers,
        rooms=rooms,
        subjects=subjects,
        teacher_of=teacher_of,
        required_hours=required_hours
    )


def generate_large_dataset() -> ScheduleInput:
    """大规模数据集: 5天 x 6节 = 30 timeslots/班, 12班, 24教师, 12教室, 9科目

    关键修复: required_hours 总和 = 30 (等于可用 timeslots)
    分布: 语文=4, 数学=4, 英语=4, 物理=3, 化学=3, 生物=3, 历史=3, 地理=3, 政治=3
    总计: 4+4+4+3+3+3+3+3+3 = 30
    """
    timeslots = [f"day{d}_slot{s}" for d in range(1, 6) for s in range(1, 7)]

    classes = [ClassInfo(id=f"c{i}", name=f"class_{i}", student_count=38 + (i % 5) * 3) for i in range(1, 13)]
    teachers = [TeacherInfo(id=f"t{i}", name=f"teacher_{i}") for i in range(1, 10)]  # 9 teachers = 9 subjects
    rooms = [RoomInfo(id=f"r{i}", name=f"room_{i}", capacity=50) for i in range(1, 13)]

    subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治"]

    # 教师分配: 每个教师只教一个科目（避免同一时段教多门课的冲突）
    # 9教师对应9科目: t1=语文, t2=数学, t3=英语, t4=物理, t5=化学, t6=生物, t7=历史, t8=地理, t9=政治
    teacher_of = {}
    for cls in classes:
        teacher_of[cls.id] = {}
        for i, subj in enumerate(subjects):
            teacher_of[cls.id][subj] = teachers[i].id  # 教师i教科目i到所有班级

    # 关键修复: required_hours 总和 = 30 (5天 x 6节)
    # 分布: 语文=4, 数学=4, 英语=4, 物理=3, 化学=3, 生物=3, 历史=3, 地理=3, 政治=3
    # 总计: 4+4+4+3+3+3+3+3+3 = 30
    required_hours = {}
    for cls in classes:
        required_hours[cls.id] = {
            "语文": 4, "数学": 4, "英语": 4,
            "物理": 3, "化学": 3, "生物": 3,
            "历史": 3, "地理": 3, "政治": 3
        }

    return ScheduleInput(
        school_id="benchmark_large",
        timeslots=timeslots,
        classes=classes,
        teachers=teachers,
        rooms=rooms,
        subjects=subjects,
        teacher_of=teacher_of,
        required_hours=required_hours
    )


def schedule_input_to_dict(input_data: ScheduleInput) -> dict:
    """将 ScheduleInput 转换为可序列化的字典"""
    return {
        "school_id": input_data.school_id,
        "timeslots": input_data.timeslots,
        "classes": [vars(c) for c in input_data.classes],
        "teachers": [vars(t) for t in input_data.teachers],
        "rooms": [vars(r) for r in input_data.rooms],
        "subjects": input_data.subjects,
        "teacher_of": input_data.teacher_of,
        "required_hours": input_data.required_hours,
        "combined_classes": [vars(cc) for cc in input_data.combined_classes],
        "special_rooms": input_data.special_rooms,
        "teacher_unavailability": {k: list(v) for k, v in input_data.teacher_unavailability.items()}
    }


def validate_dataset(input_data: ScheduleInput) -> bool:
    """验证数据集的合理性

    关键验证: 每个班的 required_hours 总和必须等于可用 timeslots 数
    否则 CP-SAT 求解器会返回 INFEASIBLE
    """
    num_timeslots = len(input_data.timeslots)

    for cls in input_data.classes:
        total_required = sum(input_data.required_hours[cls.id].values())
        if total_required > num_timeslots:
            print(f"[ERROR] Class {cls.id}: required_hours={total_required} > available_timeslots={num_timeslots}")
            return False
        if total_required < num_timeslots:
            print(f"[WARNING] Class {cls.id}: required_hours={total_required} < available_timeslots={num_timeslots} (will have empty slots)")

    print(f"[OK] Dataset validated: {len(input_data.classes)} classes, {num_timeslots} timeslots each")
    return True


def main():
    parser = argparse.ArgumentParser(description="排课系统测试数据生成器")
    parser.add_argument(
        "--size",
        type=str,
        default="all",
        choices=["small", "medium", "large", "all"],
        help="数据集规模 (default: all)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scheduler/benchmark/data/",
        help="输出目录 (default: scheduler/benchmark/data/)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="只验证现有数据文件，不生成"
    )

    args = parser.parse_args()

    generators = {
        "small": generate_small_dataset,
        "medium": generate_medium_dataset,
        "large": generate_large_dataset,
    }

    if args.size == "all":
        sizes = ["small", "medium", "large"]
    else:
        sizes = [args.size]

    output_dir = Path(args.output)
    if not args.validate_only:
        output_dir.mkdir(parents=True, exist_ok=True)

    for size in sizes:
        json_file = output_dir / f"{size}.json"

        if args.validate_only:
            if json_file.exists():
                print(f"\n=== Validating {size}.json ===")
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                input_data = ScheduleInput.from_request(data)
                validate_dataset(input_data)
            else:
                print(f"[SKIP] {size}.json not found")
            continue

        print(f"Generating {size} dataset...", file=sys.stderr)
        input_data = generators[size]()

        # Validate before saving
        if not validate_dataset(input_data):
            print(f"[ERROR] Dataset validation failed for {size}", file=sys.stderr)
            sys.exit(1)

        # Save to JSON
        data_dict = schedule_input_to_dict(input_data)
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=2)

        print(f"[OK] Saved {json_file}", file=sys.stderr)


if __name__ == "__main__":
    main()

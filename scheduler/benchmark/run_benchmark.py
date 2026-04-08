#!/usr/bin/env python3
"""
排课算法 Benchmark CLI
用法:
    python run_benchmark.py --dataset small --runs 3 --timeout 60
"""
import argparse
import json
import time
import statistics
import sys
import os
from pathlib import Path

# Add SmartCourseShed to path so we can use scheduler.src imports
_benchmark_dir = Path(__file__).parent  # benchmark/
_project_root = _benchmark_dir.parent.parent   # SmartCourseShed/
sys.path.insert(0, str(_project_root))
# Don't chdir - run from SmartCourseShed root so scheduler.src imports work

from scheduler.src.models.schedule import (
    ScheduleInput, ClassInfo, TeacherInfo, RoomInfo
)
from scheduler.src.solvers.cpsat_solver import solve_schedule, ScheduleResult


def generate_small_dataset() -> ScheduleInput:
    """生成小规模测试数据集（3天 x 3节 = 9槽，3班，5教师，3教室）"""
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

    teacher_of = {
        "c1": {"语文": "t1", "数学": "t2", "英语": "t3"},
        "c2": {"语文": "t2", "数学": "t1", "英语": "t3"},
        "c3": {"语文": "t3", "数学": "t2", "英语": "t1"},
    }

    required_hours = {
        "c1": {"语文": 2, "数学": 2, "英语": 1},
        "c2": {"语文": 2, "数学": 2, "英语": 1},
        "c3": {"语文": 2, "数学": 2, "英语": 1},
    }

    return ScheduleInput(
        school_id="benchmark_small",
        timeslots=timeslots,
        classes=classes,
        teachers=teachers,
        rooms=rooms,
        subjects=["语文", "数学", "英语"],
        teacher_of=teacher_of,
        required_hours=required_hours
    )


def generate_medium_dataset() -> ScheduleInput:
    """生成中等规模测试数据集（5天 x 6节 = 30槽，6班，12教师，6教室）"""
    timeslots = [f"day{d}_slot{s}" for d in range(1, 6) for s in range(1, 7)]
    classes = [ClassInfo(id=f"c{i}", name=f"class_{i}", student_count=40 + i * 2) for i in range(1, 7)]
    teachers = [TeacherInfo(id=f"t{i}", name=f"teacher_{i}") for i in range(1, 13)]
    rooms = [RoomInfo(id=f"r{i}", name=f"room_{i}", capacity=50) for i in range(1, 7)]

    subjects = ["语文", "数学", "英语", "物理", "化学", "生物"]

    teacher_of = {}
    for cls in classes:
        teacher_of[cls.id] = {}
        for i, subj in enumerate(subjects):
            teacher_of[cls.id][subj] = teachers[(classes.index(cls) + i) % len(teachers)].id

    required_hours = {}
    for cls in classes:
        required_hours[cls.id] = {
            "语文": 4, "数学": 4, "英语": 3, "物理": 3, "化学": 2, "生物": 2
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
    """生成大规模测试数据集（5天 x 6节 = 30槽，12班，24教师，12教室）"""
    timeslots = [f"day{d}_slot{s}" for d in range(1, 6) for s in range(1, 7)]
    classes = [ClassInfo(id=f"c{i}", name=f"class_{i}", student_count=38 + (i % 5) * 3) for i in range(1, 13)]
    teachers = [TeacherInfo(id=f"t{i}", name=f"teacher_{i}") for i in range(1, 25)]
    rooms = [RoomInfo(id=f"r{i}", name=f"room_{i}", capacity=50) for i in range(1, 13)]

    subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治"]

    teacher_of = {}
    for cls in classes:
        teacher_of[cls.id] = {}
        for i, subj in enumerate(subjects):
            teacher_of[cls.id][subj] = teachers[(classes.index(cls) + i) % len(teachers)].id

    required_hours = {}
    for cls in classes:
        required_hours[cls.id] = {
            "语文": 4, "数学": 4, "英语": 3, "物理": 3,
            "化学": 2, "生物": 2, "历史": 2, "地理": 1, "政治": 1
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


def load_dataset(name: str) -> ScheduleInput:
    """加载或生成数据集"""
    data_dir = Path(__file__).parent / "data"

    # Check if data file exists
    json_file = data_dir / f"{name}.json"
    if json_file.exists():
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ScheduleInput.from_request(data)

    # Generate dataset if file doesn't exist
    generators = {
        "small": generate_small_dataset,
        "medium": generate_medium_dataset,
        "large": generate_large_dataset,
    }

    if name not in generators:
        raise ValueError(f"Unknown dataset: {name}. Available: {list(generators.keys())}")

    print(f"[Benchmark] Dataset '{name}' not found in {data_dir}, generating...", file=sys.stderr)
    return generators[name]()


def run_single_benchmark(input_data: ScheduleInput, timeout: int) -> dict:
    """运行单次 benchmark"""
    start_time = time.perf_counter()
    result = solve_schedule(input_data, time_limit_seconds=timeout)
    wall_time = time.perf_counter() - start_time

    # Calculate assignment rate
    total_slots_needed = sum(sum(hours.values()) for hours in input_data.required_hours.values())
    total_slots_assigned = sum(len(class_schedule) for class_schedule in result.schedule.values())
    assignment_rate = total_slots_assigned / total_slots_needed if total_slots_needed > 0 else 0

    return {
        "success": result.success,
        "status": result.solver_stats.get("status", "UNKNOWN"),
        "wall_time": wall_time,
        "solver_wall_time": result.solver_stats.get("wall_time", 0),
        "num_booleans": result.solver_stats.get("num_booleans", 0),
        "num_branches": result.solver_stats.get("num_branches", 0),
        "num_conflicts": result.solver_stats.get("num_conflicts", 0),
        "assignment_rate": assignment_rate,
        "unassigned_count": len(result.unassigned),
    }


def format_results(results: list, dataset_name: str) -> str:
    """格式化 benchmark 结果"""
    if not results:
        return "No results"

    wall_times = [r["wall_time"] for r in results]
    solver_times = [r["solver_wall_time"] for r in results]
    booleans = [r["num_booleans"] for r in results]
    branches = [r["num_branches"] for r in results]
    conflicts = [r["num_conflicts"] for r in results]
    success_count = sum(1 for r in results if r["success"])

    lines = [
        f"=== Benchmark Results: {dataset_name} ===",
        f"Runs: {len(results)} | Success: {success_count} | Failed: {len(results) - success_count}",
        "",
        f"{'Metric':<20} {'Mean':>10} {'Std':>10} {'Min':>10} {'Max':>10}",
        "-" * 62,
        f"{'Wall Time (s)':<20} {statistics.mean(wall_times):>10.3f} {statistics.stdev(wall_times) if len(wall_times) > 1 else 0:>10.3f} {min(wall_times):>10.3f} {max(wall_times):>10.3f}",
        f"{'Solver Time (s)':<20} {statistics.mean(solver_times):>10.3f} {statistics.stdev(solver_times) if len(solver_times) > 1 else 0:>10.3f} {min(solver_times):>10.3f} {max(solver_times):>10.3f}",
        f"{'Num Booleans':<20} {statistics.mean(booleans):>10.0f} {'-':>10} {min(booleans):>10.0f} {max(booleans):>10.0f}",
        f"{'Num Branches':<20} {statistics.mean(branches):>10.0f} {'-':>10} {min(branches):>10.0f} {max(branches):>10.0f}",
        f"{'Num Conflicts':<20} {statistics.mean(conflicts):>10.0f} {'-':>10} {min(conflicts):>10.0f} {max(conflicts):>10.0f}",
    ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="排课算法 Benchmark CLI")
    parser.add_argument(
        "--dataset",
        type=str,
        default="small",
        choices=["small", "medium", "large"],
        help="数据集规模 (default: small)"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="运行次数 (default: 1)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="单次求解超时（秒）(default: 60)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式结果"
    )

    args = parser.parse_args()

    # Load dataset
    input_data = load_dataset(args.dataset)

    print(f"[Benchmark] Dataset: {args.dataset}", file=sys.stderr)
    print(f"[Benchmark] Problem size: {len(input_data.classes)} classes, "
          f"{len(input_data.teachers)} teachers, {len(input_data.rooms)} rooms, "
          f"{len(input_data.timeslots)} timeslots", file=sys.stderr)
    print(f"[Benchmark] Running {args.runs} run(s) with timeout={args.timeout}s", file=sys.stderr)
    print("-" * 60, file=sys.stderr)

    # Run benchmarks
    results = []
    for i in range(args.runs):
        print(f"[Run {i+1}/{args.runs}] Starting...", file=sys.stderr)
        result = run_single_benchmark(input_data, args.timeout)
        results.append(result)
        status_str = "SUCCESS" if result["success"] else "FAILED"
        print(f"[Run {i+1}/{args.runs}] {status_str} - "
              f"Wall: {result['wall_time']:.3f}s, "
              f"Solver: {result['solver_wall_time']:.3f}s, "
              f"Status: {result['status']}", file=sys.stderr)

    # Output results
    if args.json:
        import json
        print(json.dumps({
            "dataset": args.dataset,
            "runs": args.runs,
            "timeout": args.timeout,
            "results": results
        }, indent=2))
    else:
        print("\n" + format_results(results, args.dataset))


if __name__ == "__main__":
    main()

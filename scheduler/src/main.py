"""
FastAPI HTTP 接口
Phase 1 简化版本，用于联调验证
"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from scheduler.src.schemas.request import ScheduleRequest
from scheduler.src.schemas.response import ScheduleResponse, ScheduleEntry, ScheduleStats, ConflictItem
from scheduler.src.models.schedule import ScheduleInput, ClassInfo, TeacherInfo, RoomInfo, CombinedClass
from scheduler.src.solvers.cpsat_solver import CPSatSolver
from scheduler.src.constraints.conflict_checker import check_conflicts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: solver created on-demand per request
    yield
    # shutdown: nothing to cleanup


app = FastAPI(
    title="排课算法服务",
    description="OR-Tools CP-SAT 排课求解器 HTTP API",
    version="1.0.0",
    lifespan=lifespan
)


def _build_schedule_input(request: dict) -> ScheduleInput:
    """Build ScheduleInput from request dict, reusing ScheduleRequest.to_schedule_input()"""
    req = ScheduleRequest(
        school_id=request["school_id"],
        timeslots=request.get("timeslots", []),
        classes=request.get("classes", []),
        teachers=request.get("teachers", []),
        rooms=request.get("rooms", []),
        subjects=request.get("subjects", []),
        teacher_of=request.get("teacher_of", {}),
        required_hours=request.get("required_hours", {}),
        combined_classes=request.get("combined_classes", []),
        special_rooms=request.get("special_rooms", {}),
        teacher_unavailability={k: set(v) for k, v in request.get("teacher_unavailability", {}).items()}
    )
    return req.to_schedule_input()


def build_response(schedule_result, solve_time_ms: int) -> ScheduleResponse:
    """将 ScheduleResult 转换为 ScheduleResponse"""
    # 构建 schedule entries
    entries = []
    for class_id, timeslot_room_map in schedule_result.schedule.items():
        for timeslot, room_id in timeslot_room_map.items():
            # 简化：Phase 1 不填充 subject/teacher_id
            entries.append(ScheduleEntry(
                timeslot=timeslot,
                class_id=class_id,
                room_id=room_id,
                subject="",
                teacher_id=""
            ))

    # 确定状态
    status_map = {
        "OPTIMAL": "SUCCESS",
        "FEASIBLE": "SUCCESS",
        "INFEASIBLE": "INFEASIBLE",
        "UNKNOWN": "TIMEOUT",
    }
    status = status_map.get(schedule_result.solver_stats.get("status", "UNKNOWN"), "TIMEOUT")

    return ScheduleResponse(
        status=status,
        schedule=entries,
        stats=ScheduleStats(
            solve_time_ms=solve_time_ms,
            hard_constraints_violated=len(schedule_result.conflicts) if schedule_result.conflicts else 0
        ),
        conflicts=[
            ConflictItem(code="", description=c) for c in (schedule_result.conflicts or [])
        ]
    )


@app.post("/api/v1/schedule/generate", response_model=ScheduleResponse)
def generate_schedule(request: ScheduleRequest) -> ScheduleResponse:
    """
    生成课表。

    输入：学校排课配置（班级、教师、教室、时间槽、约束等）
    输出：课表安排或冲突报告
    """
    try:
        # 转换请求为 ScheduleInput
        input_data = request.to_schedule_input()

        # 创建求解器并求解
        solver = CPSatSolver(input_data, time_limit_seconds=35)
        start = time.time()
        result = solver.solve()
        solve_time_ms = int((time.time() - start) * 1000)

        return build_response(result, solve_time_ms)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/schedule/check-conflict")
def check_conflict(request: dict):
    """冲突检测 — 复用 CPSatSolver 约束验证"""
    input_data = _build_schedule_input(request)

    conflicts = check_conflicts(input_data, request.get("assignments", []))
    return {
        "status": "CONFLICT" if conflicts else "SUCCESS",
        "conflicts": conflicts,
        "score": None
    }


@app.get("/api/v1/schedule/modes")
def get_modes():
    """返回三种排课模式说明"""
    return {
        "modes": [
            {"id": "full", "name": "全量排课", "description": "清空现有课表，从头生成完整课表"},
            {"id": "incremental", "name": "增量排课", "description": "保留已有课程，只排空缺槽"},
            {"id": "auto-fill", "name": "手动+自动填充", "description": "固定手动课程，自动填补剩余"}
        ]
    }


@app.post("/api/v1/schedule/score")
def score_schedule(request: dict):
    """满意度评分 — Phase 1 返回固定基础分"""
    assignments = request.get("assignments", [])
    threshold = request.get("threshold", 60)

    if request.get("school_id"):
        input_data = _build_schedule_input(request)
        conflicts = check_conflicts(input_data, assignments)
        score = 0 if conflicts else 60
    else:
        score = 60

    return {
        "score": score,
        "breakdown": {"hard_constraints": score, "teacher_preference": 0, "distribution": 0},
        "threshold": threshold,
        "blocked": (score < threshold)
    }


@app.post("/api/v1/schedule/validate")
def validate_schedule(request: dict):
    """课表完整性校验"""
    assignments = request.get("assignments", [])
    required_hours = request.get("required_hours", {})

    class_hours = {}
    for a in assignments:
        cid = a.get("class_id")
        if cid:
            class_hours[cid] = class_hours.get(cid, 0) + 1

    missing = []
    for cid, hours in required_hours.items():
        total_required = sum(hours.values()) if isinstance(hours, dict) else 0
        actual = class_hours.get(cid, 0)
        if actual < total_required:
            missing.append({"class_id": cid, "expected": total_required, "actual": actual})

    return {
        "status": "VALID" if not missing else "INCOMPLETE",
        "missing": missing
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
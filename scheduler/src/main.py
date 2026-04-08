"""
FastAPI HTTP 接口
Phase 1 简化版本，用于联调验证
"""
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from scheduler.src.schemas.request import ScheduleRequest
from scheduler.src.schemas.response import ScheduleResponse, ScheduleEntry, ScheduleStats, ConflictItem
from scheduler.src.models.schedule import ScheduleInput, ClassInfo, TeacherInfo, RoomInfo, CombinedClass
from scheduler.src.solvers.cpsat_solver import CPSatSolver


app = FastAPI(
    title="排课算法服务",
    description="OR-Tools CP-SAT 排课求解器 HTTP API",
    version="1.0.0"
)

# 全局求解器实例
_scheduler: CPSatSolver = None


@app.on_event("startup")
def startup():
    pass  # 求解器在请求时按需创建


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


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

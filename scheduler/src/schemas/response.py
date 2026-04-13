from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class ScheduleEntry(BaseModel):
    timeslot: str = Field(..., description="时间槽")
    class_id: str = Field(..., description="班级ID")
    room_id: str = Field(..., description="教室ID")
    subject: str = Field(..., description="科目")
    teacher_id: str = Field(..., description="教师ID")


class ConflictItem(BaseModel):
    code: str = Field(..., description="约束代码，如 L0-02")
    description: str = Field(..., description="冲突描述")
    class_id: Optional[str] = Field(None, description="相关班级ID")
    teacher_id: Optional[str] = Field(None, description="相关教师ID")
    timeslot: Optional[str] = Field(None, description="相关时间槽")
    room_id: Optional[str] = Field(None, description="相关教室ID")
    alternatives: List[str] = Field(default=[], description="候选替代时间槽列表")


class ScheduleStats(BaseModel):
    solve_time_ms: int = Field(..., description="求解耗时，毫秒")
    hard_constraints_violated: int = Field(default=0, description="硬约束冲突数")
    avg_objective_score: Optional[float] = Field(None, description="目标函数分，Phase 1 始终为 null")


class ScoreResponse(BaseModel):
    score: int = Field(..., ge=0, le=100, description="满意度评分 0-100")
    breakdown: Dict[str, int] = Field(default={}, description="评分明细")
    threshold: int = Field(default=60, description="当前阈值")
    blocked: bool = Field(default=False, description="是否低于阈值被阻止")


class ScheduleResponse(BaseModel):
    status: str = Field(..., description="SUCCESS | INFEASIBLE | TIMEOUT | PARTIAL")
    schedule: List[ScheduleEntry] = Field(default=[], description="课表安排")
    stats: ScheduleStats = Field(..., description="统计信息")
    conflicts: List[ConflictItem] = Field(default=[], description="冲突列表")

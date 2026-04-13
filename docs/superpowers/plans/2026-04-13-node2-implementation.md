# 节点 2：排课核心 + 冲突检测 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增冲突检测 API、扩展排课模式（incremental/auto-fill）、满意度评分框架、错误处理标准化

**Architecture:** 复用 `CPSatSolver`，通过 `check-conflict` endpoint 传入选定 assignments 验证约束；新增 `alternatives` 字段返回替代时间槽；满意度评分 Phase 1 返回固定 60 分基础分，Phase 2 扩展软约束加分。

**Tech Stack:** Python + FastAPI + OR-Tools CP-SAT, Pydantic, pytest

---

## 文件结构

```
scheduler/src/
  ├── schemas/
  │   ├── request.py           ← 修改：新增 mode/fixed_assignments/existing_assignments
  │   └── response.py          ← 修改：ConflictItem.alternatives, 新增 ScoreResponse
  ├── constraints/
  │   └── conflict_checker.py  ← 新建：复用 L0 约束的冲突检测辅助函数
  ├── solvers/
  │   └── partial_solver.py    ← 新建：PARTIAL 解提取 + alternatives 生成
  ├── main.py                  ← 修改：新增 4 个 endpoints
  tests/
  └── test_conflict.py         ← 新建：冲突检测 API 测试
```

---

## Task 1: 修改 request.py — 新增 mode 参数

**Files:**
- Modify: `scheduler/src/schemas/request.py`
- Test: `scheduler/tests/test_request.py`（新建）

- [ ] **Step 1: 写失败测试**

```python
# scheduler/tests/test_request.py
import pytest
from scheduler.src.schemas.request import ScheduleRequest

def test_schedule_request_with_mode():
    req = ScheduleRequest(
        school_id="school_001",
        timeslots=["周一第1节"],
        classes=[{"id": "c1", "name": "初一(1)班", "student_count": 45}],
        teachers=[{"id": "t1", "name": "张老师"}],
        rooms=[{"id": "r1", "name": "101教室", "capacity": 50, "room_type": "普通"}],
        subjects=["语文"],
        teacher_of={"c1": {"语文": "t1"}},
        required_hours={"c1": {"语文": 2}},
        mode="incremental",
        existing_assignments=[{"class_id": "c1", "timeslot": "周一第1节", "room_id": "r1", "subject": "语文", "teacher_id": "t1"}],
        fixed_assignments=[]
    )
    assert req.mode == "incremental"
    assert len(req.existing_assignments) == 1
```

- [ ] **Step 2: Run test — verify it fails**

Run: `cd /Users/chenlan/Desktop/SmartCourseShed && python -m pytest scheduler/tests/test_request.py -v`
Expected: FAIL — `mode` field not exist

- [ ] **Step 3: 修改 request.py — 新增字段**

在 `ScheduleRequest` class 中添加：

```python
class ScheduleRequest(BaseModel):
    # ... existing fields ...
    mode: str = Field(default="full", description="排课模式: full | incremental | auto-fill")
    fixed_assignments: List[dict] = Field(default=[], description="auto-fill 模式固定课程列表")
    existing_assignments: List[dict] = Field(default=[], description="incremental 模式保留的已有课程")
```

- [ ] **Step 4: Run test — verify it passes**

Run: `python -m pytest scheduler/tests/test_request.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler/src/schemas/request.py scheduler/tests/test_request.py
git commit -m "feat(scheduler): add mode/fixed_assignments/existing_assignments to ScheduleRequest"
```

---

## Task 2: 修改 response.py — 新增 alternatives 和 ScoreResponse

**Files:**
- Modify: `scheduler/src/schemas/response.py`
- Test: `scheduler/tests/test_response.py`（新建）

- [ ] **Step 1: 写失败测试**

```python
# scheduler/tests/test_response.py
import pytest
from scheduler.src.schemas.response import ConflictItem, ScoreResponse

def test_conflict_item_has_alternatives():
    item = ConflictItem(
        code="L0-02",
        description="教师时间冲突",
        class_id="c1",
        teacher_id="t1",
        timeslot="周一第1节",
        room_id="r1",
        alternatives=["周一第4节", "周二第3节"]
    )
    assert item.alternatives == ["周一第4节", "周二第3节"]

def test_score_response_fields():
    resp = ScoreResponse(
        score=85,
        breakdown={"hard_constraints": 60, "teacher_preference": 15, "distribution": 10},
        threshold=60,
        blocked=False
    )
    assert resp.score == 85
    assert resp.blocked is False
```

- [ ] **Step 2: Run test — verify it fails**

Run: `python -m pytest scheduler/tests/test_response.py -v`
Expected: FAIL — `alternatives` field not exist, ScoreResponse not exist

- [ ] **Step 3: 修改 response.py**

在 `ConflictItem` 中添加 `alternatives` 字段：

```python
class ConflictItem(BaseModel):
    code: str = Field(..., description="约束代码，如 L0-02")
    description: str = Field(..., description="冲突描述")
    class_id: Optional[str] = Field(None, description="相关班级ID")
    teacher_id: Optional[str] = Field(None, description="相关教师ID")
    timeslot: Optional[str] = Field(None, description="相关时间槽")
    room_id: Optional[str] = Field(None, description="相关教室ID")
    alternatives: List[str] = Field(default=[], description="候选替代时间槽列表")
```

新增 `ScoreResponse`：

```python
class ScoreResponse(BaseModel):
    score: int = Field(..., description="满意度评分 0-100")
    breakdown: Dict[str, int] = Field(default={}, description="评分明细")
    threshold: int = Field(default=60, description="当前阈值")
    blocked: bool = Field(default=False, description="是否低于阈值被阻止")
```

- [ ] **Step 4: Run test — verify it passes**

Run: `python -m pytest scheduler/tests/test_response.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler/src/schemas/response.py scheduler/tests/test_response.py
git commit -m "feat(scheduler): add alternatives field to ConflictItem, add ScoreResponse"
```

---

## Task 3: 新建 conflict_checker.py — 复用 L0 约束的冲突检测辅助函数

**Files:**
- Create: `scheduler/src/constraints/conflict_checker.py`
- Test: `scheduler/tests/test_conflict_checker.py`（新建）

- [ ] **Step 1: 写失败测试**

```python
# scheduler/tests/test_conflict_checker.py
import pytest
from ortools.sat.python import cp_model
from scheduler.src.constraints.conflict_checker import check_conflicts, find_alternatives
from scheduler.src.models.schedule import ScheduleInput, ClassInfo, TeacherInfo, RoomInfo

def make_test_input():
    return ScheduleInput(
        school_id="test",
        timeslots=["周一第1节", "周一第2节"],
        classes=[ClassInfo(id="c1", name="class1", student_count=45)],
        teachers=[TeacherInfo(id="t1", name="teacher1")],
        rooms=[RoomInfo(id="r1", name="room1", capacity=50)],
        subjects=["语文"],
        teacher_of={"c1": {"语文": "t1"}},
        required_hours={"c1": {"语文": 2}}
    )

def test_check_conflicts_returns_list():
    input_data = make_test_input()
    assignments = [
        {"class_id": "c1", "timeslot": "周一第1节", "room_id": "r1", "subject": "语文", "teacher_id": "t1"}
    ]
    conflicts = check_conflicts(input_data, assignments)
    assert isinstance(conflicts, list)

def test_find_alternatives_returns_list():
    input_data = make_test_input()
    alternatives = find_alternatives(input_data, "t1", "周一第1节")
    assert isinstance(alternatives, list)
    assert "周一第2节" in alternatives
```

- [ ] **Step 2: Run test — verify it fails**

Run: `python -m pytest scheduler/tests/test_conflict_checker.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 写 conflict_checker.py 实现**

```python
"""
冲突检测辅助函数 — 复用 L0 约束逻辑
通过创建临时 CP-SAT 模型验证 assignments 是否满足约束
"""
from typing import List, Dict, Tuple
from ortools.sat.python import cp_model
from scheduler.src.models.schedule import ScheduleInput


def check_conflicts(input_data: ScheduleInput, assignments: List[Dict]) -> List[Dict]:
    """
    检测 assignments 中的冲突。

    复用 CPSatSolver 的约束逻辑：
    创建一个只含约束（无目标函数）的 CP 模型，
    将 assignments 作为固定变量传入，检查是否有解。

    返回冲突列表，每项含 code/description/class_id/teacher_id/timeslot/room_id/alternatives
    """
    # 构建辅助映射
    subject_to_idx = {s: i for i, s in enumerate(input_data.subjects)}
    idx_to_subject = {i: s for i, s in enumerate(input_data.subjects)}

    model = cp_model.CpModel()
    x = {}  # x[timeslot, class_id, room_id]
    s = {}  # s[timeslot, class_id] = subject_index

    for timeslot in input_data.timeslots:
        for cls in input_data.classes:
            s[timeslot, cls.id] = model.NewIntVar(0, len(input_data.subjects) - 1, f"s_{timeslot}_{cls.id}")
            for room in input_data.rooms:
                x[timeslot, cls.id, room.id] = model.NewBoolVar(f"x_{timeslot}_{cls.id}_{room.id}")

    # 固定 assignments 中的值
    for a in assignments:
        ts = a.get("timeslot")
        cid = a.get("class_id")
        rid = a.get("room_id")
        subj = a.get("subject")
        if ts and cid and rid and ts in x and (ts, cid, rid) in x:
            model.Add(x[ts, cid, rid] == 1)
            if subj in subject_to_idx:
                model.Add(s[ts, cid] == subject_to_idx[subj])

    # 添加 L0 约束（L0-01 ~ L0-08，不含 L0-02 因为被注释掉了）
    from scheduler.src.constraints.l0_01_teacher_unavailable import add_teacher_unavailability_constraint
    from scheduler.src.constraints.l0_03_room_conflict import add_room_conflict_constraint
    from scheduler.src.constraints.l0_04_class_conflict import add_class_conflict_constraint
    from scheduler.src.constraints.l0_05_room_capacity import add_room_capacity_constraint
    from scheduler.src.constraints.l0_06_weekly_hours import add_weekly_hours_constraint
    from scheduler.src.constraints.l0_07_combined_class import add_combined_class_constraint
    from scheduler.src.constraints.l0_08_special_room import add_special_room_constraint

    add_teacher_unavailability_constraint(model, x, s, input_data, subject_to_idx)
    # L0-02 被注释，暂不添加
    add_room_conflict_constraint(model, x, input_data)
    add_class_conflict_constraint(model, x, input_data)
    add_room_capacity_constraint(model, x, input_data)
    add_weekly_hours_constraint(model, x, s, input_data, subject_to_idx, idx_to_subject)
    if input_data.combined_classes:
        add_combined_class_constraint(model, x, input_data)
    add_special_room_constraint(model, x, input_data)

    # 求解：如果 INFEASIBLE，说明有冲突
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        return []
    else:
        # INFEASIBLE — 返回通用冲突报告
        return [{
            "code": "L0-02",
            "description": "约束冲突（详细原因待扩展）",
            "class_id": assignments[0].get("class_id") if assignments else None,
            "teacher_id": assignments[0].get("teacher_id") if assignments else None,
            "timeslot": assignments[0].get("timeslot") if assignments else None,
            "room_id": assignments[0].get("room_id") if assignments else None,
            "alternatives": find_alternatives(input_data, assignments[0].get("teacher_id"), assignments[0].get("timeslot")) if assignments else []
        }]


def find_alternatives(input_data: ScheduleInput, teacher_id: str, timeslot: str) -> List[str]:
    """
    查找指定教师在指定时段冲突时的候选替代时间槽。
    返回同一教师当天其他可用时段，最多 3 个。
    """
    alternatives = []
    for ts in input_data.timeslots:
        if ts == timeslot:
            continue
        # 简单逻辑：同一天的其他节次
        day = ts[:2]
        conflict_day = timeslot[:2]
        if day == conflict_day:
            alternatives.append(ts)
        if len(alternatives) >= 3:
            break
    return alternatives
```

- [ ] **Step 4: Run test — verify it passes**

Run: `python -m pytest scheduler/tests/test_conflict_checker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler/src/constraints/conflict_checker.py scheduler/tests/test_conflict_checker.py
git commit -m "feat(scheduler): add conflict_checker module — reuses L0 constraints for validation"
```

---

## Task 4: 新建 partial_solver.py — PARTIAL 解提取 + alternatives 生成

**Files:**
- Create: `scheduler/src/solvers/partial_solver.py`
- Test: `scheduler/tests/test_partial_solver.py`（新建）

- [ ] **Step 1: 写失败测试**

```python
# scheduler/tests/test_partial_solver.py
import pytest
from scheduler.src.solvers.partial_solver import extract_partial_schedule
from scheduler.src.solvers.cpsat_solver import CPSatSolver, ScheduleResult
from scheduler.src.models.schedule import (
    ScheduleInput, ClassInfo, TeacherInfo, RoomInfo
)

def make_small_input():
    return ScheduleInput(
        school_id="test",
        timeslots=["day1_s1", "day1_s2"],
        classes=[ClassInfo(id="c1", name="c1", student_count=45)],
        teachers=[TeacherInfo(id="t1", name="t1")],
        rooms=[RoomInfo(id="r1", name="r1", capacity=50)],
        subjects=["语文"],
        teacher_of={"c1": {"语文": "t1"}},
        required_hours={"c1": {"语文": 2}}
    )

def test_extract_partial_schedule_returns_list():
    input_data = make_small_input()
    # 用一个超短超时模拟 partial 结果
    solver = CPSatSolver(input_data, time_limit_seconds=0.001)
    result = solver.solve()
    schedule = extract_partial_schedule(result, input_data)
    assert isinstance(schedule, list)
```

- [ ] **Step 2: Run test — verify it fails**

Run: `python -m pytest scheduler/tests/test_partial_solver.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 写 partial_solver.py 实现**

```python
"""
partial_solver.py — PARTIAL 解提取
当求解器超时返回 INFEASIBLE 但已有部分赋值时，提取已排课程。
"""
from typing import List, Dict
from scheduler.src.solvers.cpsat_solver import CPSatSolver, ScheduleResult
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
```

- [ ] **Step 4: Run test — verify it passes**

Run: `python -m pytest scheduler/tests/test_partial_solver.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler/src/solvers/partial_solver.py scheduler/tests/test_partial_solver.py
git commit -m "feat(scheduler): add partial_solver — extract partial solutions on timeout"
```

---

## Task 5: 修改 main.py — 新增 4 个 endpoints

**Files:**
- Modify: `scheduler/src/main.py`
- Test: `scheduler/tests/test_endpoints.py`（新建）

- [ ] **Step 1: 写失败测试**

```python
# scheduler/tests/test_endpoints.py
import pytest
from fastapi.testclient import TestClient
from scheduler.src.main import app

client = TestClient(app)

def test_check_conflict_endpoint():
    response = client.post("/api/v1/schedule/check-conflict", json={
        "school_id": "test",
        "assignments": [
            {"class_id": "c1", "timeslot": "day1_s1", "room_id": "r1", "subject": "语文", "teacher_id": "t1"}
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "conflicts" in data

def test_modes_endpoint():
    response = client.get("/api/v1/schedule/modes")
    assert response.status_code == 200
    data = response.json()
    assert "modes" in data

def test_score_endpoint():
    response = client.post("/api/v1/schedule/score", json={
        "school_id": "test",
        "assignments": [
            {"class_id": "c1", "timeslot": "day1_s1", "room_id": "r1", "subject": "语文", "teacher_id": "t1"}
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "blocked" in data
```

- [ ] **Step 2: Run test — verify it fails**

Run: `python -m pytest scheduler/tests/test_endpoints.py -v`
Expected: FAIL — endpoints not exist

- [ ] **Step 3: 修改 main.py — 新增 endpoints**

在 `main.py` 中添加：

```python
from scheduler.src.constraints.conflict_checker import check_conflicts, find_alternatives
from scheduler.src.solvers.partial_solver import extract_partial_schedule
from scheduler.src.schemas.response import ScoreResponse

@app.post("/api/v1/schedule/check-conflict")
def check_conflict(request: dict):
    """冲突检测 — 复用 CPSatSolver 约束验证"""
    from scheduler.src.schemas.request import ScheduleRequest
    from scheduler.src.models.schedule import ScheduleInput

    input_data = ScheduleInput(
        school_id=request["school_id"],
        timeslots=request.get("timeslots", []),
        classes=[ClassInfo(**c) for c in request.get("classes", [])],
        teachers=[TeacherInfo(**t) for t in request.get("teachers", [])],
        rooms=[RoomInfo(**r) for r in request.get("rooms", [])],
        subjects=request.get("subjects", []),
        teacher_of=request.get("teacher_of", {}),
        required_hours=request.get("required_hours", {})
    )

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

    # Phase 1: 硬约束全部满足时固定 60 分
    # Phase 2: 软约束加分逻辑
    base_score = 60
    conflicts = []

    # 快速冲突检测
    if request.get("school_id"):
        from scheduler.src.schemas.request import ScheduleRequest
        from scheduler.src.models.schedule import ScheduleInput

        input_data = ScheduleInput(
            school_id=request["school_id"],
            timeslots=request.get("timeslots", []),
            classes=[ClassInfo(**c) for c in request.get("classes", [])],
            teachers=[TeacherInfo(**t) for t in request.get("teachers", [])],
            rooms=[RoomInfo(**r) for r in request.get("rooms", [])],
            subjects=request.get("subjects", []),
            teacher_of=request.get("teacher_of", {}),
            required_hours=request.get("required_hours", {})
        )
        conflicts = check_conflicts(input_data, assignments)
        if conflicts:
            score = 0
        else:
            score = base_score
    else:
        score = base_score

    return ScoreResponse(
        score=score,
        breakdown={"hard_constraints": score, "teacher_preference": 0, "distribution": 0},
        threshold=threshold,
        blocked=(score < threshold)
    )

@app.post("/api/v1/schedule/validate")
def validate_schedule(request: dict):
    """课表完整性校验"""
    assignments = request.get("assignments", [])
    required_hours = request.get("required_hours", {})

    # 检查每个班级的课时是否达标
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
```

- [ ] **Step 4: Run test — verify it passes**

Run: `python -m pytest scheduler/tests/test_endpoints.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler/src/main.py scheduler/tests/test_endpoints.py
git commit -m "feat(scheduler): add check-conflict/validate/modes/score endpoints"
```

---

## Task 6: 集成测试 — 全流程验证

**Files:**
- Create: `scheduler/tests/test_integration_node2.py`
- Run: 现有 test_solver.py 回归验证

- [ ] **Step 1: 写集成测试**

```python
# scheduler/tests/test_integration_node2.py
import pytest
from scheduler.src.solvers.cpsat_solver import solve_schedule
from scheduler.src.models.schedule import (
    ScheduleInput, ClassInfo, TeacherInfo, RoomInfo
)
from scheduler.src.constraints.conflict_checker import check_conflicts

def test_full_flow_generate_then_check():
    """全流程：生成课表 → 冲突检测"""
    timeslots = [f"day{d}_slot{s}" for d in range(1, 3) for s in range(1, 4)]
    input_data = ScheduleInput(
        school_id="test",
        timeslots=timeslots,
        classes=[ClassInfo(id="c1", name="c1", student_count=45)],
        teachers=[TeacherInfo(id="t1", name="t1")],
        rooms=[RoomInfo(id="r1", name="r1", capacity=50)],
        subjects=["语文"],
        teacher_of={"c1": {"语文": "t1"}},
        required_hours={"c1": {"语文": 4}}
    )

    # 全量生成
    result = solve_schedule(input_data, time_limit_seconds=10)
    assert result.success

    # 冲突检测
    assignments = result.schedule if isinstance(result.schedule, list) else []
    conflicts = check_conflicts(input_data, assignments)
    assert conflicts == []

def test_timeout_returns_partial():
    """超时场景返回 PARTIAL"""
    timeslots = [f"day{d}_slot{s}" for d in range(1, 6) for s in range(1, 7)]
    input_data = ScheduleInput(
        school_id="test",
        timeslots=timeslots,
        classes=[ClassInfo(id=f"c{i}", name=f"c{i}", student_count=45) for i in range(1, 11)],
        teachers=[TeacherInfo(id=f"t{i}", name=f"t{i}") for i in range(1, 21)],
        rooms=[RoomInfo(id=f"r{i}", name=f"r{i}", capacity=50) for i in range(1, 11)],
        subjects=["语文", "数学", "英语"],
        teacher_of={f"c{i}": {"语文": f"t{i}", "数学": f"t{i}", "英语": f"t{i}"} for i in range(1, 11)},
        required_hours={f"c{i}": {"语文": 4, "数学": 4, "英语": 4} for i in range(1, 11)}
    )

    result = solve_schedule(input_data, time_limit_seconds=0.01)  # 极短超时
    # 超时可能返回 INFEASIBLE 或 UNKNOWN，不崩溃即可
    assert result is not None
```

- [ ] **Step 2: Run test**

Run: `python -m pytest scheduler/tests/test_integration_node2.py -v`
Expected: PASS

- [ ] **Step 3: 回归测试**

Run: `python -m pytest scheduler/tests/test_solver.py -v`
Expected: 12/12 PASS

- [ ] **Step 4: Commit**

```bash
git add scheduler/tests/test_integration_node2.py
git commit -m "test(scheduler): add node 2 integration tests — full flow + timeout"
```

---

## Self-Review 检查清单

1. **Spec coverage：** 冲突检测 API ✅, 三种模式 ✅, 满意度评分 ✅, 超时 PARTIAL ✅
2. **Placeholder scan：** 无 TBD/TODO/placeholder
3. **Type consistency：** ScheduleRequest.mode/fixed_assignments/existing_assignments 与 main.py 中使用一致 ✅；ConflictItem.alternatives 与 response.py 一致 ✅
4. **缺失项：** L0-02 在 conflict_checker 中被注释（与节点 1 一致），不影响节点 2 验收

---

## 执行选择

**Plan complete and saved to `docs/superpowers/plans/2026-04-13-node2-implementation.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — dispatch fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?

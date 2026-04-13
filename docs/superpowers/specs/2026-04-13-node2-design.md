# 节点 2：排课核心 + 冲突检测 — 设计文档

## Context

节点 2 在节点 1 基础上扩展排课服务能力，新增冲突检测 API、三种排课模式、满意度评分系统。节点 1 已实现 `POST /api/v1/schedule/generate` 全量排课接口。

**输入文档：**
- `中小学排课系统_多Agent协作开发框架.md`
- `docs/chenlan-main-design-20260407.md`（已批准设计基线）
- `scheduler/docs/PHASE1_LESSONS_LEARNED.md`

---

## 新增 API Endpoints

```
现有：
POST /api/v1/schedule/generate   ← 节点 1 已实现，全量排课

新增（节点 2）：
POST /api/v1/schedule/check-conflict   ← 冲突检测
POST /api/v1/schedule/validate        ← 课表完整性校验
GET  /api/v1/schedule/modes           ← 三种模式说明
POST /api/v1/schedule/score           ← 满意度评分
```

---

## 1. 冲突检测 API

### POST /api/v1/schedule/check-conflict

**触发方式：** 前端拖拽课程卡松开后，300ms debounce 调用。

**请求：**
```json
{
  "school_id": "string",
  "assignments": [
    {
      "class_id": "string",
      "timeslot": "string",
      "room_id": "string",
      "subject": "string",
      "teacher_id": "string"
    }
  ],
  "check_mode": "single" | "batch"  // single=单条检测，batch=批量检测
}
```

**响应：**
```json
{
  "status": "SUCCESS" | "CONFLICT" | "INFEASIBLE",
  "conflicts": [
    {
      "code": "L0-02",
      "description": "教师时间冲突",
      "class_id": "c1",
      "teacher_id": "t1",
      "timeslot": "周一第1节",
      "room_id": "r1",
      "alternatives": ["周一第4节", "周二第3节"]
    }
  ],
  "score": 85
}
```

**实现方式：** 复用 `CPSatSolver`，传入选定的 assignments，让求解器验证约束是否满足。约束逻辑完全复用 L0-01~08，不单独写检测逻辑。

**替代方案生成逻辑：** 检测到冲突后，遍历该教师/教室/班级在同时段的所有可用时间槽，返回候选列表。最多返回 3 个。

---

## 2. 三种排课模式

### POST /api/v1/schedule/generate（扩展 mode 参数）

**新增 mode 参数：**

```json
{
  "mode": "full" | "incremental" | "auto-fill",
  "fixed_assignments": [...],  // 手动排课已固定的课程，auto-fill 模式必传
  "school_id": "string",
  "timeslots": [...],
  "classes": [...],
  "teachers": [...],
  "rooms": [...],
  "subjects": [...],
  "teacher_of": {...},
  "required_hours": {...},
  "combined_classes": [...],
  "special_rooms": {...},
  "teacher_unavailability": {...}
}
```

### 模式行为

| mode | 行为 |
|------|------|
| `full` | 清空现有课表，从头生成完整课表（节点 1 行为） |
| `incremental` | 保留数据库中已确认的 assignments，只排空缺槽 |
| `auto-fill` | `fixed_assignments` 固定不动，剩余由求解器自动填补 |

### 实现说明

- `incremental`：传入时附加 `existing_assignments` 字段（已排课程列表），求解器在创建决策变量时将这些 slots 的 x 变量固定为 1。
- `auto-fill`：`fixed_assignments` 作为硬约束输入，求解器只填充剩余 slots。

---

## 3. 满意度评分系统

### POST /api/v1/schedule/score

**请求：**
```json
{
  "school_id": "string",
  "assignments": [...]
}
```

**响应：**
```json
{
  "score": 85,
  "breakdown": {
    "hard_constraints": 60,  // 硬约束基础分（全部满足=60，有违反=0）
    "teacher_preference": 15,  // 教师偏好加分（Phase 2 实现）
    "distribution": 10          // 分布均匀性加分（Phase 2 实现）
  },
  "threshold": 60,  // 当前阈值（从数据库/配置读取）
  "blocked": false  // 是否低于阈值被阻止
}
```

### 评分规则（Phase 1）

Phase 1 软约束未完整实现，评分框架：

| 条件 | 分数 |
|------|------|
| 硬约束有任一违反 | `score: 0` |
| 硬约束全部满足 | `score: 60`（固定基础分）|
| `blocked: true` when `score < threshold` | 前端阻止发布 |

Phase 2 补充：
- 连堂偏好加分（+10）
- 教师时间偏好加分（+10）
- 课程分布均匀性加分（+10）

---

## 4. 错误处理标准化

### 超时响应（PARTIAL）

```
status: "TIMEOUT"
schedule: [...partial assignments...]  // 已排课程保留
conflicts: [...]
score: null
```

说明：
- 超时（>35s）不等同于 INFEASIBLE，可能是约束太紧或规模大
- 返回部分解，管理员可手动补充未排课程
- 前端区分显示："完整解" vs "部分解（超时）"

### 5xx 错误

- 超时或 5xx：自动重试 1 次
- 重试仍然失败：返回 `{ "status": "ERROR", "message": "..." }`

### INFEASIBLE（确认无解）

- 约束条件互相矛盾，确认无法排课
- 返回冲突约束清单（最多 10 条）
- `status: "INFEASIBLE"`, `score: 0`

---

## 5. 数据模型扩展

### ScheduleRequest 新增字段

```python
class ScheduleRequest(BaseModel):
    # 现有字段...
    mode: str = "full"  # "full" | "incremental" | "auto-fill"
    fixed_assignments: List[dict] = []  # auto-fill 模式使用
    existing_assignments: List[dict] = []  # incremental 模式使用
```

### ConflictItem 新增 alternatives 字段

```python
class ConflictItem(BaseModel):
    code: str
    description: str
    class_id: Optional[str] = None
    teacher_id: Optional[str] = None
    timeslot: Optional[str] = None
    room_id: Optional[str] = None
    alternatives: List[str] = []  # 新增：候选替代时间槽
```

### ScoreResponse 新增字段

```python
class ScoreResponse(BaseModel):
    score: int
    breakdown: dict
    threshold: int
    blocked: bool
```

---

## 6. API 路由设计

```
/api/v1/schedule/
  ├── generate    POST   ← 扩展 mode 参数
  ├── check-conflict  POST  ← 新增
  ├── validate        POST  ← 新增
  ├── score           POST  ← 新增
  └── modes           GET   ← 新增（返回三种模式说明）
```

---

## 7. 文件变更

```
scheduler/src/
  ├── main.py                      ← 新增 endpoints
  ├── schemas/request.py           ← 新增字段
  ├── schemas/response.py          ← 新增 ConflictItem.alternatives, ScoreResponse
  ├── solvers/
  │   ├── cpsat_solver.py          ← 支持 incremental/auto-fill 模式
  │   └── partial_solver.py        ← 新增：支持 partial 解提取
  └── constraints/
      └── l0_conflict_checker.py   ← 新增：复用 L0 约束的冲突检测辅助函数
```

---

## 8. 验收标准

- [ ] 冲突检测 API 可检测 L0-02/L0-03/L0-04 三维冲突，不漏报
- [ ] 冲突响应包含 alternatives（替代时间槽列表）
- [ ] 三种模式（full/incremental/auto-fill）均可正常调用
- [ ] 满意度评分可显示，分数低于阈值时前端阻止发布
- [ ] 超时返回 PARTIAL + 部分课表，非空课表
- [ ] Benchmark（small/medium）仍在 30s 内

---

## 9. 未完成项（Phase 2）

- 软约束权重体系（teacher_preference、distribution 加分）
- 替代方案算法优化（当前返回最多 3 个候选）
- 调课/代课/请假审批流
- Excel 批量导入

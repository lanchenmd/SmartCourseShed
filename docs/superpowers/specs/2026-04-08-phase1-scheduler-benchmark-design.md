# Phase 1 设计方案：环境搭建 + OR-Tools Benchmark

**版本：** v1.0
**日期：** 2026-04-08
**状态：** 已确认

---

## 1. 概述

### 1.1 目标

完成 Phase 1 的环境搭建和 OR-Tools Benchmark 验证，确认 CP-SAT 求解器在规定时间内能为中等规模学校（20 班 + 50 教师 + 20 教室）生成可行课表。

### 1.2 交付物

- Python OR-Tools 排课服务（`scheduler/`）
- CLI 基准测试脚本（`benchmark/run_benchmark.py`）
- 三套测试数据集（small / medium / large）
- HTTP REST 接口（Phase 1 联调验证用）
- Benchmark 验收通过

---

## 2. 技术架构

### 2.1 项目目录结构

```
project-root/
├── backend/                   # Node.js + Hono（Phase 2+）
├── scheduler/                 # Python + OR-Tools（Phase 1 重点）
│   ├── src/
│   │   ├── __init__.py
│   │   ├── constraints/        # L0/L1 约束实现
│   │   │   ├── __init__.py
│   │   │   ├── l0_*.py        # 8 条 L0 硬约束
│   │   │   └── l1_*.py        # L1 可配置硬约束（Phase 2）
│   │   ├── models/            # 数据模型
│   │   │   ├── __init__.py
│   │   │   └── schedule.py    # 课表数据模型
│   │   ├── solvers/           # CP-SAT 求解器封装
│   │   │   ├── __init__.py
│   │   │   └── cpsat_solver.py
│   │   ├── schemas/           # pydantic 请求/响应 schema
│   │   │   ├── __init__.py
│   │   │   ├── request.py
│   │   │   └── response.py
│   │   └── main.py            # FastAPI 入口
│   ├── benchmark/
│   │   ├── __init__.py
│   │   ├── data/              # 测试数据集 JSON
│   │   │   ├── small_10c_20t.json
│   │   │   ├── medium_20c_50t.json
│   │   │   └── large_40c_80t.json
│   │   ├── run_benchmark.py   # CLI 基准测试（验收标准）
│   │   └── generate_test_data.py  # 测试数据生成脚本
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_constraints.py
│   │   └── test_solver.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── docker-compose.yml
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-08-phase1-scheduler-benchmark-design.md
```

### 2.2 技术栈

| 组件 | 选择 | 说明 |
|------|------|------|
| 求解器 | OR-Tools CP-SAT | `ortools.sat.python.cp_model` |
| Python | 3.11+ | |
| Web 框架 | FastAPI | Phase 1 简化，不使用 uvicorn 独立部署 |
| 数据验证 | pydantic | |
| 通信协议 | HTTP/REST | Phase 1 简化，不使用 gRPC |

### 2.3 决策变量（3D + Index 方案）

```
x[timeslot, class, room] ∈ {0, 1}
表示：时段 timeslot，班级 class，在教室 room 上课

teacher_of[class_id][subject_id] → teacher_id（查表，非决策变量）
```

变量数估算：30 时隙/天 × 5 天 × 20 班 × 20 室 = 60,000，实际因 domain 裁剪更少。

---

## 3. 约束实现（Phase 1 完整 8 条 L0）

### 3.1 L0 硬约束清单

| 代码 | 名称 | CP-SAT 实现 |
|------|------|------------|
| L0-01 | 教师时间不可用 | domain 裁剪 + 约束过滤 |
| L0-02 | 教师时间冲突 | `AddLinearConstraint(sum ≤ 1)` |
| L0-03 | 教室时间冲突 | `AllDifferent` |
| L0-04 | 班级时间冲突 | `AllDifferent`（等式 =1） |
| L0-05 | 教室容量限制 | `AddImplication` |
| L0-06 | 班级周课时精确达标 | `AddLinearConstraint`（等式 ==） |
| L0-07 | 合班课同步 | 合班组作为原子调度单元 |
| L0-08 | 专用教室用途限制 | `z[room,timeslot]` 辅助变量 + `AddImplication` |

### 3.2 CP-SAT 实现要点

**L0-02 教师时间冲突：**
```python
for teacher in teachers:
    for timeslot in timeslots:
        sum_constraint = sum(
            x[timeslot, cls, room]
            for cls in classes
            for room in rooms
            if teacher_of[cls][subject_of(cls, timeslot)] == teacher
        )
        model.Add(sum_constraint <= 1)
```

**L0-04 班级时间冲突（等式 =1）：**
```python
for cls in classes:
    for timeslot in timeslots:
        sum_constraint = sum(x[timeslot, cls, room] for room in rooms)
        model.Add(sum_constraint == 1)  # 等式，非 ≤
```

**L0-06 班级周课时精确达标：**
```python
for cls in classes:
    for subject in subjects:
        required = required_hours[cls][subject]
        model.Add(
            sum(x[ts, cls, room]
                for ts in timeslots
                for room in rooms
                if teacher_of[cls][subject] == teacher_of[cls][subject])
            == required
        )
```

**L0-07 合班作为原子调度单元：**
```python
# 合班组 cc = (class_set, teacher, subject, room_type)
# 每个合班班级各占一节，总课时 = 合班班级数量
for cc in combined_classes:
    for timeslot in timeslots:
        model.Add(
            sum(x[timeslot, cc, room] for room in rooms) == len(cc.class_set)
        )
```

**L0-08 专用教室条件借用：**
```python
z = {}
for room in special_rooms:
    for timeslot in timeslots:
        z[room, timeslot] = model.NewBoolVar(f'z_{room}_{timeslot}')
        # z = 1 当且仅当此时段有专业课占用
        model.Add(
            sum(x[timeslot, cls, room] for cls in classes) == 1
        ).OnlyEnforceIf(z[room, timeslot])
        # 若 z = 1，则 subject 必须在允许范围内
        # 若 z = 0，可借给任意普通课程
```

---

## 4. 目标函数（Phase 1）

### 4.1 决策：Option A — 纯可行性验证

Phase 1 **不调用** `model.Minimize()`，仅验证可行性。

```python
# Phase 1：仅求解，不优化
response = model.Solve(cp_model.CpSolverParameters())
# 不使用：model.Minimize(any_expression)
```

### 4.2 输出格式

```json
{
  "status": "SUCCESS | INFEASIBLE | TIMEOUT | PARTIAL",
  "schedule": [
    {
      "timeslot": "周一第1节",
      "class_id": "class_001",
      "room_id": "room_101",
      "subject": "数学",
      "teacher_id": "teacher_zhang"
    }
  ],
  "stats": {
    "solve_time_ms": 12340,
    "hard_constraints_violated": 0,
    "avg_objective_score": null
  },
  "conflicts": []
}
```

**状态说明：**
- `SUCCESS`：找到可行解，硬约束冲突 = 0
- `INFEASIBLE`：无可行解，`conflicts` 填充冲突约束清单
- `TIMEOUT`：30s 内未找到可行解（Phase 2 返回近似解）
- `PARTIAL`：部分成功（Phase 2 实现）

---

## 5. Benchmark 规格

### 5.1 测试数据集

| 数据集 | 班级 | 教师 | 教室 | 时隙/天 | 周总时隙 | 约束项估算 |
|--------|------|------|------|---------|----------|-----------|
| small | 10 | 20 | 10 | 10 | 50 | ~500 |
| **medium** | 20 | 50 | 20 | 30 | 150 | **~2,500-3,000** |
| large | 40 | 80 | 30 | 30 | 150 | ~5,000+ |

### 5.2 验收标准

**主轨：CLI 基准测试**
```bash
python benchmark/run_benchmark.py --dataset medium --runs 5
```

| 指标 | 目标值 |
|------|--------|
| avg_time | ≤ 25 秒 |
| success_rate | ≥ 80%（5 次中至少 4 次成功） |
| worst_case | ≤ 35 秒 |
| hard_constraints_violated | = 0（成功时） |

**辅轨：HTTP 接口**
```
POST /api/v1/schedule/generate
```
- 验证求解器在 HTTP 服务模式下工作正常
- 使用 medium 数据集，验收标准同 CLI

**成功标准：** 两轨均达标才算 Phase 1 Benchmark 完成

### 5.3 超时策略

- 硬超时：35 秒
- 超时后：返回 `status: TIMEOUT`，不返回近似解（Phase 2 实现近似求解）

### 5.4 冲突约束清单格式（INFEASIBLE 时）

```json
{
  "status": "INFEASIBLE",
  "conflicts": [
    {"code": "L0-06", "class": "初二(1)班", "subject": "数学", "required_hours": 4},
    {"code": "L0-02", "teacher": "张老师", "timeslot": "周一第3节"}
  ]
}
```

注：`available_slots` 为后处理计算值，非 CP-SAT 直接输出。

---

## 6. 测试数据生成

### 6.1 生成脚本

```bash
python benchmark/generate_test_data.py --size medium --output benchmark/data/
```

### 6.2 生成方式：Option C

半随机生成 + 规则注入 + 验证保存：
1. 随机生成基础数据（班级、教师、教室、时间槽）
2. 注入有效课时配置（确保可达）
3. 随机标记教师不可用时段（控制比例）
4. `validate_and_save.py` 验证数据一致性后保存为固定 JSON

### 6.3 数据质量要求

- 课时配置可满足（不会出现必然 INFEASIBLE）
- 教师不可用时段比例 ≤ 20%
- 合班配置至少包含 1 组两班合场景

---

## 7. API 设计（Phase 1）

### 7.1 HTTP 端点

```
POST /api/v1/schedule/generate
Content-Type: application/json

{
  "school_id": "school_001",
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

Response 200:
{
  "status": "SUCCESS",
  "schedule": [...],
  "stats": {...}
}
```

### 7.2 内部调用（CLI）

```python
from scheduler.solvers.cpsat_solver import CpsatScheduler

scheduler = CpsatScheduler()
result = scheduler.solve(input_data)
```

---

## 8. 关键设计决策汇总

| 决策项 | 选择 | 原因 |
|--------|------|------|
| Benchmark 验证方式 | 双重验证（CLI 主轨 + HTTP 辅轨） | CLI 适合自动化，HTTP 适合联调 |
| 目标函数 | Option A（纯可行性，null） | Phase 1 聚焦验证，不引入优化复杂度 |
| 测试数据生成 | Option C（半随机 + 验证保存） | 保证可满足性，避免必然失败 |
| 通信协议 | HTTP/REST | 简化 Phase 1，不使用 gRPC |
| Warm-start | 不实现 | Phase 2 再做 |
| 超时近似解 | 不实现 | Phase 2 再做 |
| 合班处理 | 原子调度单元 | 避免多变量同步复杂性 |
| L0-08 借用 | 允许（条件占用） | 资源充分利用 |

---

## 9. 依赖项

```
# requirements.txt
ortools>=9.10
pydantic>=2.0
fastapi>=0.110
uvicorn>=0.27
pytest>=8.0
```

---

## 10. 下一步

1. 搭建 `scheduler/` 目录结构
2. 实现 pydantic 数据模型（`schemas/`）
3. 实现 8 条 L0 约束（`constraints/`）
4. 实现 CP-SAT 求解器（`solvers/cpsat_solver.py`）
5. 实现 `main.py` HTTP 接口
6. 实现测试数据生成脚本
7. 实现 CLI Benchmark 脚本
8. 运行 Benchmark 验收

---

**文档状态：** 已确认，等待实现

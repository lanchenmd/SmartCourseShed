# SmartCourseShed — 中小学排课Agent系统

> 基于 OR-Tools CP-SAT 的智能排课引擎，支持三维冲突检测（教师/教室/班级）、实时冲突提示与替代方案推荐。

## 项目背景与挑战

排课是学校里最具挑战性的管理工作之一。一个班级的课程表背后涉及教师、教室、时间槽、科目等多维约束，每次调整都可能引发连锁冲突。

### 核心挑战

**硬约束必须满足，但需求天天变。**

开学前一周，教务主任面临这样的局面：物理李老师请假一周、初二3班换教室、音乐教室被占用——每个变化都需要在全科室层面重新检查冲突。手工逐行检查容易遗漏，一旦开学发现问题就得重新调整。

**排课的复杂性在于：**

- **多维约束耦合**：调整一个时间槽，可能同时影响教师、教室、班级三个维度的可用性
- **硬约束与软约束交织**：教室容量（硬）、连堂偏好（软）、教师时间偏好（软），不同约束有不同的优先级
- **变化响应要快**：学校需求变化频繁，但现有商业软件"改一次需求要等很久"，手工处理又容易出错

**我们的目标：** 在满足所有硬约束（L0）的前提下，让排课调整"快、准、狠"——冲突检测实时、替代方案明确、手动调整后自动验证。

## 核心特色

| 特色 | 说明 |
|------|------|
| **极致冲突检测** | 三维（教师/教室/班级）实时检测，拖拽课程卡后 300ms debounce 即出结果 |
| **超快排课速度** | OR-Tools CP-SAT 求解器，Medium 数据集（6班/12教师/6教室/30时段）平均 1.8 秒，远超 25 秒验收标准 |
| **替代方案推荐** | 冲突时自动推荐可用时间槽，减少手动试错 |
| **三种排课模式** | 全量排课 / 增量排课 / 手动+自动填充，适配不同工作流 |
| **配置驱动** | 硬约束（L0）+ 软约束（L1/L2）通过配置驱动，非硬编码 |
| **满意度评分** | 0-100 分数值化课表质量，低于阈值自动阻止发布 |

## 技术架构

```
┌─────────────┐     HTTP/REST      ┌─────────────────────┐
│  前端/小程序  │ ────────────────→  │  排课服务 (Python)    │
│  Next.js /  │ ←───────────────   │  FastAPI + OR-Tools  │
│  Taro       │    JSON Response  │  CP-SAT 求解器       │
└─────────────┘                   └─────────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
              ┌─────▼─────┐           ┌────────▼────────┐        ┌──────▼──────┐
              │  L0-01    │           │  L0-02          │        │  L0-03      │
              │  教师不可用 │           │  教师时间冲突    │        │  教室时间冲突 │
              └───────────┘           └─────────────────┘        └─────────────┘
                    │                          │                          │
              ┌─────▼─────┐           ┌────────▼────────┐        ┌──────▼──────┐
              │  L0-04    │           │  L0-05          │        │  L0-06      │
              │  班级冲突  │           │  教室容量限制    │        │  周课时达标   │
              └───────────┘           └─────────────────┘        └─────────────┘
                    │
              ┌─────▼─────┐           ┌─────────────────┐
              │  L0-07    │           │  L0-08          │
              │  合班同步  │           │  专用教室限制    │
              └───────────┘           └─────────────────┘
```

### 决策变量设计（3D + Index 方案）

```
x[timeslot, class, room] ∈ {0, 1}
表示：时段 timeslot，班级 class，在教室 room 上课

s[timeslot, class] ∈ SUBJECTS
表示：该时段该班级上什么科目（通过 teacher_of 查表确定授课教师）
```

**优势：** 变量数减少约 500 倍（5D → 3D），subject 不作为独立决策变量，正确性由数据模型保证。

## 约束模型

排课系统的核心是**约束层次**：硬约束（L0）必须满足，否则排课方案无效；软约束（L1/L2）尽量满足，决定课表质量分数。

### L0 硬约束（必须满足，缺一不可）

| 约束 | 代码 | 说明 |
|------|------|------|
| 教师时间不可用 | L0-01 | 教师标记的不可排课时段，禁止安排任何课程 |
| 教师时间冲突 | L0-02 | 同一教师同一时段只能上一节课（跨班级均禁止） |
| 教室时间冲突 | L0-03 | 同一教室同一时段只能安排一节课 |
| 班级时间冲突 | L0-04 | 同一班级同一时段必须在且仅在一间教室（等式 =1） |
| 教室容量限制 | L0-05 | 班级人数不能超过教室最大容量 |
| 班级周课时达标 | L0-06 | 每个班级每科目必须达到规定课时数（等式 ==） |
| 合班课同步 | L0-07 | 合班必须同时、同教室、同教师上课（原子调度） |
| 专用教室限制 | L0-08 | 实验室等专用教室有条件借用规则 |

### 软约束（L1/L2，Phase 2 实现）

| 约束层级 | 示例 | 说明 |
|---------|------|------|
| L1 可配置硬约束 | 某个班级必须上午上数学 | 通过 Schema 的 `is_hard` 开关控制 |
| L2 软约束权重 | 教师连堂偏好 +10 分、课程分布均匀 +10 分 | 影响满意度评分，但不阻塞发布 |

## API 接口

```
POST /api/v1/schedule/generate    # 生成课表（全量/增量/手动+自动填充）
POST /api/v1/schedule/check-conflict   # 冲突检测（实时）
POST /api/v1/schedule/validate    # 课表完整性校验
POST /api/v1/schedule/score       # 满意度评分
GET  /api/v1/schedule/modes       # 三种模式说明
GET  /health                      # 健康检查
```

## 阶段性目标

| 节点 | 内容 | 状态 |
|------|------|------|
| 节点 0 | 约束模型规格定义：CP-SAT 3D+Index方案 + 8条L0硬约束 | ✅ 已完成 |
| 节点 1 | 环境搭建 + OR-Tools Benchmark 验证 | ✅ 已完成 |
| 节点 2 | 排课核心 + 冲突检测 + 三种模式 + 满意度评分 | ✅ 已完成 |
| 节点 3 | 日历 UI + 冲突解决 UX | 待开始 |
| 节点 4 | 基础权限 + 用户认证 + Redis 乐观锁 | 待开始 |
| 节点 5 | 优化与收尾 | 待开始 |

## 当前进展

### 节点 1 — Benchmark 验证（✅ 完成）

| Dataset | Status | Success Rate | Avg Time |
|---------|--------|--------------|----------|
| Small   | ✅ PASS | 3/3 (100%)   | 0.037s   |
| Medium  | ✅ PASS | 5/5 (100%)   | 1.878s   |
| Large   | ✅ PASS | 3/3 (100%)   | 6.761s   |

**验收标准（Medium）：** avg ≤25s, success_rate ≥80%
**实际结果：** avg 1.878s, success_rate 100% — **大幅超越标准**

### 节点 2 — 排课核心 + 冲突检测（✅ 完成）

- `POST /api/v1/schedule/check-conflict` — 冲突检测（复用 L0 约束）
- `POST /api/v1/schedule/validate` — 课表完整性校验
- `GET  /api/v1/schedule/modes` — 三种模式说明
- `POST /api/v1/schedule/score` — 满意度评分（Phase 1 固定 60 分基础分）
- `conflict_checker.py` — 复用 L0 约束的冲突检测辅助函数
- `partial_solver.py` — PARTIAL 解提取
- **测试：** 31 passed, 0 failed

## 项目结构

```
SmartCourseShed/
├── scheduler/                    # 排课算法服务（Python）
│   ├── src/
│   │   ├── solvers/
│   │   │   ├── cpsat_solver.py       # CP-SAT 求解器
│   │   │   └── partial_solver.py     # PARTIAL 解提取
│   │   ├── constraints/
│   │   │   ├── l0_01_teacher_unavailable.py
│   │   │   ├── l0_02_teacher_conflict.py
│   │   │   ├── l0_03_room_conflict.py
│   │   │   ├── l0_04_class_conflict.py
│   │   │   ├── l0_05_room_capacity.py
│   │   │   ├── l0_06_weekly_hours.py
│   │   │   ├── l0_07_combined_class.py
│   │   │   ├── l0_08_special_room.py
│   │   │   └── conflict_checker.py   # 冲突检测辅助函数
│   │   ├── models/
│   │   │   └── schedule.py           # 数据模型
│   │   ├── schemas/
│   │   │   ├── request.py            # 请求 schema
│   │   │   └── response.py           # 响应 schema
│   │   └── main.py                   # FastAPI HTTP 接口
│   ├── benchmark/
│   │   └── run_benchmark.py          # CLI 基准测试
│   ├── tests/                        # pytest 测试套件
│   └── docs/                         # 文档
│       ├── PHASE1_BENCHMARK_STATUS.md
│       ├── PHASE1_LESSONS_LEARNED.md
│       └── PHASE1_TESTING_GUIDE.md
├── docs/                            # 设计文档
│   ├── chenlan-main-design-20260407.md   # 已批准设计基线
│   └── superpowers/
│       ├── specs/                    # 设计规格
│       └── plans/                    # 实施计划
└── CLAUDE.md                        # 项目核心指令
```

## 快速开始

### 1. 运行测试

```bash
cd /Users/chenlan/Desktop/SmartCourseShed

# 运行全部测试
python -m pytest scheduler/tests/ -v

# 运行 Benchmark
python -m scheduler.benchmark.run_benchmark --dataset medium --runs 5 --timeout 60
```

### 2. 启动排课服务

```bash
cd /Users/chenlan/Desktop/SmartCourseShed/scheduler
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001
```

### 3. 调用 API

```bash
# 冲突检测
curl -X POST http://localhost:8001/api/v1/schedule/check-conflict \
  -H "Content-Type: application/json" \
  -d '{
    "school_id": "school_001",
    "timeslots": ["周一第1节", "周一第2节"],
    "classes": [{"id": "c1", "name": "初一(1)班", "student_count": 45}],
    "teachers": [{"id": "t1", "name": "张老师"}],
    "rooms": [{"id": "r1", "name": "101教室", "capacity": 50, "room_type": "普通"}],
    "subjects": ["语文"],
    "teacher_of": {"c1": {"语文": "t1"}},
    "required_hours": {"c1": {"语文": 2}},
    "assignments": [
      {"class_id": "c1", "timeslot": "周一第1节", "room_id": "r1", "subject": "语文", "teacher_id": "t1"}
    ]
  }'

# 满意度评分
curl -X POST http://localhost:8001/api/v1/schedule/score \
  -H "Content-Type: application/json" \
  -d '{"school_id": "test", "assignments": [...], "threshold": 60}'
```

## 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 排课求解器 | Python + OR-Tools CP-SAT | 约束规划求解 |
| HTTP 接口 | FastAPI + Pydantic | 高性能 REST API |
| 单元测试 | pytest | 31 个测试用例 |
| 前端 | Next.js 14 + React 18 + Ant Design 5 + FullCalendar | 日历拖拽 UI |
| 小程序 | Taro 4 | 微信小程序端（待开发） |
| 后端主服务 | Node.js + Hono | 主 API 服务（待开发） |
| 数据库 | PostgreSQL 16 | 多租户预留（school_id） |
| 缓存 | Redis | 乐观锁（待开发） |

## 关键设计决策

### 1. 为什么用 OR-Tools CP-SAT？

排课本质是**约束满足问题（Constraint Satisfaction Problem）**而非线性规划。每个硬约束都是一个条件，多个约束叠加后形成巨大的搜索空间。CP-SAT 在这个问题上比传统 SAT/SMT 求解器快 10-100 倍，适合中等规模（<100 变量）的教育场景。

### 2. 3D + Index 方案 vs 5D 方案

| 方案 | 变量数（Medium 数据集） | 优点 | 缺点 |
|------|------------------------|------|------|
| 5D: x[ts, cls, room, subj, teacher] | 32,400 | 天然耦合 | 变量数爆炸 |
| **3D + Index: x + s** | **~810** | **变量数少 40 倍** | subject 通过查表确定 |

### 3. required_hours 总和 = timeslots

这是 L0-06 约束快速收敛的关键。当课时要求覆盖所有时间槽时，`s[ts, cls]` 与 `x[ts, cls, room]` 强耦合，求解器搜索空间大幅减少。

## 下一步

节点 3 — 日历 UI + 冲突解决 UX：
- FullCalendar 周/月视图
- 课程卡片拖拽（换节、换天）
- 冲突红框高亮 + 替代方案提示

---

**文档更新日期：** 2026-04-14

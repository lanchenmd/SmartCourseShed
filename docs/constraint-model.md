# 约束模型规格定义

**版本：** v1.1
**日期：** 2026-04-08
**阶段：** 阶段 0 — 准备阶段
**状态：** Engineering Review 后修订，已确认

---

## 1. 概述

### 1.1 目标

本文档定义中小学排课系统的**约束模型规格**，为 OR-Tools 约束求解器提供完整的形式化输入。

本文档是**排课算法开发的唯一真相来源**，所有约束规则必须通过配置驱动，禁止在业务代码中硬编码。

### 1.2 求解器选型

| 项目 | 选择 |
|------|------|
| 求解器 | **OR-Tools CP-SAT** (`ortools.sat.python.cp_model`) |
| 原因 | 速度快、工业级、大规模支持好；软硬约束集成天然；Python 原生 |

> 注：若 OR-Tools 不可用，备选为自定义回溯 + 启发式算法（Phase 1 快速验证用）。

### 1.3 约束分层架构

```
┌─────────────────────────────────────────────────────────────┐
│ L0 硬约束（权重 10000，Schema 固定不可配置，Phase 1 实现）      │
│   无可行解 → 返回 INFEASIBLE + 冲突约束清单                    │
├─────────────────────────────────────────────────────────────┤
│ L1 可配置硬约束（Schema 预留 is_hard 开关，Phase 2 实现）       │
│   学校可单独关闭某 L1 约束，关闭后降为 L2                       │
├─────────────────────────────────────────────────────────────┤
│ L2 软约束（权重 1-10，Phase 2 实现）                          │
│   连堂偏好、教师时间偏好、课程分布均匀性                        │
└─────────────────────────────────────────────────────────────┘
```

**策略决策：**
- Phase 1 采用**策略一（严格模式）**：L0 硬约束绝对不可违反，无解则报错
- **策略三（分级仲裁）**预留：约束实体 Schema 预留 `priority` 字段占位
- **策略二（自动降级）**不实现：静默违反硬约束风险大于收益

---

## 2. L0 硬约束规格

每条约束包含：**代码、名称、定义、业务意义、CP-SAT 实现**。

### L0-01：教师时间不可用

| 字段 | 内容 |
|------|------|
| **代码** | `L0-01` |
| **名称** | Teacher Unavailability |
| **定义** | 教师已明确标记的不可排课时间段，禁止安排任何课程 |
| **业务意义** | 必须尊重教师实际可用性（会议、培训、外出等） |
| **CP-SAT 实现** | 通过 `teacher_of` 查表确定教师，决策变量 `x[t,c,r]` 的 domain 裁剪 + 约束过滤 |

**数学形式化（3D 模型）：**

```
∀ teacher ∈ T, ∀ timeslot ∈ U[teacher]:
  Σ_{class ∈ C, room ∈ R, subject ∈ S where teacher_of[class, subject] = teacher} x[timeslot, class, room] = 0
即：teacher_of 映射到该教师的 (class, subject) 组合，在该时段的所有 x[t,c,r] 必须为 0
```

---

### L0-02：教师时间冲突

| 字段 | 内容 |
|------|------|
| **代码** | `L0-02` |
| **名称** | Teacher Time Conflict |
| **定义** | 同一教师在同一时段只能安排一节课（跨年级、跨班级均禁止） |
| **业务意义** | 核心资源约束，教师不能同时在多个地点授课 |
| **CP-SAT 实现** | `AddLinearConstraint(sum ≤ 1)`，教师由 `teacher_of` 查表确定 |

**数学形式化（3D 模型）：**

```
∀ teacher ∈ T, ∀ timeslot ∈ TS:
  Σ_{class ∈ C, room ∈ R, subject ∈ S where teacher_of[class, subject] = teacher} x[timeslot, class, room] ≤ 1
```

> **澄清（L0-02）：** 若同一教师在同一时段教授两个不同班级的同一科目（如张三同时给初一(1)班和初一(2)班上数学），这构成**两节**课节，均计入 Σ。L0-02 的 sum ≤ 1 正确禁止此行为。

---

### L0-03：教室时间冲突

| 字段 | 内容 |
|------|------|
| **代码** | `L0-03` |
| **名称** | Room Time Conflict |
| **定义** | 同一教室在同一时段只能安排一节课 |
| **业务意义** | 防止教室双重预定 |
| **CP-SAT 实现** | `AllDifferent` 或 `AddLinearConstraint(sum ≤ 1)` |

**数学形式化（3D 模型）：**

```
∀ room ∈ R, ∀ timeslot ∈ TS:
  Σ_{class ∈ C} x[timeslot, class, room] ≤ 1
```

---

### L0-04：班级时间冲突

| 字段 | 内容 |
|------|------|
| **代码** | `L0-04` |
| **名称** | Class Time Conflict |
| **定义** | 同一教学班/行政班在同一时段只能安排一节课（学生不能同时上两门课） |
| **业务意义** | 学生课表最基本合理性 |
| **CP-SAT 实现** | `AllDifferent` 或 `AddLinearConstraint(sum = 1)` |

**数学形式化（3D 模型）：**

```
∀ class ∈ CLASSES, ∀ timeslot ∈ TS:
  Σ_{room ∈ R} x[timeslot, class, room] = 1
  注：每个班级每个时段必须在且仅在一个教室（等式 =1，而非 ≤1）
```

---

### L0-05：教室容量限制

| 字段 | 内容 |
|------|------|
| **代码** | `L0-05` |
| **名称** | Classroom Capacity |
| **定义** | 安排课程的学生人数不得超过该教室的最大容量 |
| **业务意义** | 避免超员 |
| **CP-SAT 实现** | `AddLinearConstraint` |

**数学形式化（3D 模型）：**

```
∀ timeslot ∈ TS, ∀ class ∈ CLASSES, ∀ room ∈ R:
  x[timeslot, class, room] = 1 → student_count[class] ≤ capacity[room]
  实现为：x[timeslot, class, room] = 1 时触发检查，否则不约束
```

---

### L0-06：班级周课时精确达标

| 字段 | 内容 |
|------|------|
| **代码** | `L0-06` |
| **名称** | Class Weekly Hours |
| **定义** | 每个班级/科目必须达到规定的每周精确课时数 |
| **业务意义** | 满足教学计划要求 |
| **CP-SAT 实现** | `AddLinearConstraint` 等式约束 |

**数学形式化（3D 模型）：**

```
∀ class ∈ CLASSES, ∀ subject ∈ SUBJECTS:
  Σ_{timeslot ∈ TS, room ∈ R where teacher_of[class, subject] 的教师可用的room} x[timeslot, class, room]
  = required_hours[class, subject]

  即：统计所有 (timeslot, room) 中该班级上该科目的课时数（通过 teacher_of 确定教师身份），
  结果必须精确等于规定课时数。
```

> **精确化：** 使用等式 `==` 而非 `>=`。多排会挤压其他科目时间槽，实际操作中无学校主动多排。

---

### L0-07：合班课同时进行

| 字段 | 内容 |
|------|------|
| **代码** | `L0-07` |
| **名称** | Combined Class Sync |
| **定义** | 合班上课的多个班级必须安排在同一时段、同一教室，由同一教师授课，不可拆分 |
| **业务意义** | 实验课、体育课、选修合班等场景 |
| **CP-SAT 实现** | 合班组作为独立调度原子，不在求解器内做多变量同步 |

**数学形式化（3D 模型 — 合班作为原子调度单元）：**

```
定义合班组元组：
  COMBINED_CLASS cc = (class_set = {class_a, class_b, ...}, teacher, subject, room_type)

约束：
  ∀ cc ∈ COMBINED_CLASSES, ∀ timeslot ∈ TS:
    Σ_{room ∈ R where room_type_fits(room, cc.room_type)} x[timeslot, cc, room] = |cc.class_set|
    即：合班在此时段占用的课时数 = 合班包含的班级数量（每个班级各占一节）

  辅助变量 x[timeslot, cc, room] 维度：合班组 × 时段 × 教室
```

> **精确化（1C 修正）：** 合班不再作为 N 个独立班级变量强制同步，而是将合班组本身作为调度原子（`cc`）。teacher 和 subject 在合班定义时就固定，不作为求解器内的变量。Phase 1 先验证两班合场景。

---

### L0-08：专用教室用途限制

| 字段 | 内容 |
|------|------|
| **代码** | `L0-08` |
| **名称** | Special Room Purpose |
| **定义** | 实验室、计算机房、音乐教室、体育馆、美术室等专用教室有对应专业课时，优先保障专业课；无对应专业课的时段，允许借给普通课程使用 |
| **业务意义** | 在保障专用教室用途的前提下，充分利用闲置资源 |
| **CP-SAT 实现** | `AddAllowedAssignments` + `AddImplication`（条件占用约束） |

**数学形式化（3D 模型 — 条件借用约束）：**

```
∀ room ∈ SPECIAL_ROOMS, ∀ timeslot ∈ TS:
  引入辅助布尔变量 z[room, timeslot] = 1 表示"该时段有专业课占用"

  z[room, timeslot] = 1 ⟺ Σ_{class ∈ CLASSES} x[timeslot, class, room] = 1
                                              且 teacher_of[class, subject_of(class,timeslot)] ∈ ALLOWED_TEACHERS[room]
  （即该教室此时段有课，且授课教师属于该专用教室允许的教师范围）

  约束：
    若 z[room, timeslot] = 1：
      subject_of(class, timeslot) ∈ ALLOWED_SUBJECTS[room]
    若 z[room, timeslot] = 0：
      该教室可被任意普通课程借用（subject 无限制）
```

> **精确化（1B 修正）：** "无对应专业课时可借用"的条件判断通过辅助布尔变量 `z` + CP-SAT `AddImplication` 实现，而非 `AddAllowedAssignments` 的简单枚举。这是因为"是否有专业课"本身依赖于求解结果，需要条件约束。
>
> **修正（2026-04-08）：** 允许借用，而非严格禁止。专用教室在无对应专业课时段空置是资源浪费，应允许普通课程借用。

---

## 3. 冲突解决策略

### 3.1 Phase 1 策略：严格模式

```
有可行解时 → 返回最优解
无可行解时 → 返回 INFEASIBLE + 冲突约束清单（具体是哪几条 L0 约束无法同时满足）
```

**冲突约束清单格式建议：**

```json
{
  "status": "INFEASIBLE",
  "conflicts": [
    {"code": "L0-06", "class": "初二(1)班", "subject": "数学", "required_hours": 4},
    {"code": "L0-02", "teacher": "张老师", "timeslot": "周一第3节"}
  ]
}
```

> **注意（1D 修正）：** `required_hours` 是输入数据，可直接显示。`available_slots`（如需显示）是**后处理计算值**——CP-SAT 返回 INFEASIBLE 后，实现时需额外计算：遍历该班级+科目的所有可能排课时间槽，过滤被 L0-01/L0-02/L0-03 占据的，剩余数量即为 `available_slots`。这不是 CP-SAT 的直接输出。

### 3.2 策略三预留：priority 字段

约束实体 Schema 中预留 `priority` 字段（Phase 1 填 null）：

```json
{
  "id": "constraint_l0_01",
  "type": "硬约束",
  "code": "L0-01",
  "priority": null,
  "penalty_weight": null,
  "is_active": true,
  "school_id": "school_001"
}
```

> Phase 2 积累真实冲突案例后，再定义合理的优先级顺序（预期：L0-01 > L0-06 > L0-05 > 其他）。

---

## 4. 数据模型与查表结构

### 4.1 teacher_of 查表（核心数据映射）

```json
{
  "teacher_of": {
    "class_id": {
      "subject_id": "teacher_id"
    }
  },
  "example": {
    "class_001": {
      "math": "teacher_zhang",
      "chinese": "teacher_wang",
      "english": "teacher_li"
    }
  }
}
```

> **说明：** `(class, subject) → teacher` 是排课前的预定义数据，不是求解器的决策变量。这使得 3D 决策变量 `x[timeslot, class, room]` 成为可能。

### 4.2 约束实体 Schema

```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "description": "唯一标识，如 constraint_l0_01"
    },
    "type": {
      "type": "enum",
      "enum": ["硬约束", "软约束"],
      "description": "约束分类"
    },
    "code": {
      "type": "string",
      "description": "标准代码，如 L0-01, L1-01, L2-01"
    },
    "priority": {
      "type": ["integer", "null"],
      "description": "优先级（策略三用），Phase 1 硬约束全部填 null"
    },
    "penalty_weight": {
      "type": ["integer", "null"],
      "description": "惩罚权重（L2 软约束用），Phase 1 填 null"
    },
    "is_active": {
      "type": "boolean",
      "description": "是否启用"
    },
    "school_id": {
      "type": "string",
      "description": "多租户隔离字段"
    }
  },
  "required": ["id", "type", "code", "is_active", "school_id"]
}
```

### 4.3 L1/L2 约束预留槽位

| 层级 | 预留约束代码 | 说明 |
|------|-------------|------|
| L1-01 | 同一教师同一时段最多一节课 | 由 L0-02 覆盖，Phase 2 可能降级 |
| L1-02 | 合班课容量检查 | 由 L0-05 覆盖 |
| L2-01 | 连堂偏好 | 同一科目尽量连排 |
| L2-02 | 教师时间偏好 | 教师倾向于某些时间段 |
| L2-03 | 课程分布均匀性 | 同一科目一天内不排太密 |

---

## 5. OR-Tools CP-SAT 模型草图

### 5.1 决策变量（3D + Index 方案）

```
# 主体决策变量（3维）
x[timeslot, class, room] ∈ {0, 1}
表示：时段 timeslot，班级 class，在教室 room 上课（科目由 teacher_of 查表确定）

# 合班决策变量（独立维度）
x[timeslot, combined_class, room] ∈ {0, 1}
表示：合班组作为一个原子整体被调度
```

> **方案选择理由：** 3D 方案比原 5D 方案变量数减少约 500 倍（6M → 12K），
> 且 subject 不再作为求解器决策变量，正确性由数据模型 `teacher_of` 保证。

### 5.2 辅助变量

```
s[timeslot, class] ∈ SUBJECTS   # 时段 timeslot，班级 class 上什么科目
                                  # 实现：CP-SAT Element 变量或枚举域变量

z[room, timeslot] ∈ {0, 1}       # 专用教室该时段是否被专业课占用（用于 L0-08）
```

### 5.3 目标函数（Phase 1）

Phase 1 目标函数：**最小化 L2 软约束违反数**（Phase 2 再引入加权）。

```
Minimize: Σ L2_violations
```

> 注：若 L0 硬约束存在冲突（INFEASIBLE），目标函数无意义，直接返回错误。

### 5.4 完整约束形式化（3D 模型）

```
# 基础约束：每班级每时段在且仅在一个教室（L0-04 等式的副产品）
∀ class ∈ CLASSES, ∀ timeslot ∈ TS:
  Σ_{room ∈ R} x[timeslot, class, room] = 1

# L0-01: 教师时间不可用
# 先计算每时段各教师的占用状态，再过滤不可用时段
∀ teacher ∈ T, ∀ timeslot ∈ U[teacher]:
  Σ_{class ∈ C, room ∈ R where teacher_of[class, subject_of(class,timeslot)] = teacher} x[timeslot, class, room] = 0

# L0-02: 教师时间冲突
∀ teacher ∈ T, ∀ timeslot ∈ TS:
  Σ_{class ∈ C, room ∈ R where teacher_of[class, subject_of(class,timeslot)] = teacher} x[timeslot, class, room] ≤ 1

# L0-03: 教室时间冲突
∀ room ∈ R, ∀ timeslot ∈ TS:
  Σ_{class ∈ C} x[timeslot, class, room] ≤ 1

# L0-05: 教室容量
∀ timeslot ∈ TS, ∀ class ∈ CLASSES, ∀ room ∈ R where x[timeslot, class, room] = 1:
  student_count[class] ≤ capacity[room]
  实现为：x[timeslot, class, room] = 1 → student_count[class] ≤ capacity[room]

# L0-06: 班级周课时精确达标
∀ class ∈ CLASSES, ∀ subject ∈ SUBJECTS:
  Σ_{timeslot ∈ TS, room ∈ R where subject_of(class, timeslot) = subject} x[timeslot, class, room]
  = required_hours[class, subject]

# L0-07: 合班课同步（合班作为原子调度单元）
∀ combined_class ∈ COMBINED_CLASSES, ∀ timeslot ∈ TS:
  Σ_{room ∈ R} x[timeslot, combined_class, room] = |combined_class.class_set|
  （每个班级各占一节，合班总课时 = 合班班级数量）

# L0-08: 专用教室用途限制（条件借用）
# z[room, timeslot] = 1 表示"此时段有专业课占用"
∀ room ∈ SPECIAL_ROOMS, ∀ timeslot ∈ TS:
  z[room, timeslot] ⟺ Σ_{class ∈ CLASSES} x[timeslot, class, room] = 1
                                          且 teacher_of[class, subject_of(class,timeslot)] ∈ ALLOWED_TEACHERS[room]

  若 z[room, timeslot] = 1：
    subject_of(class, timeslot) ∈ ALLOWED_SUBJECTS[room]
  若 z[room, timeslot] = 0：
    无额外约束（可借给任意普通课程）
```

---

## 6. OR-Tools Benchmark 规格（Phase 1）

### 6.1 基准目标

| 指标 | 目标值 |
|------|--------|
| 学校规模 | 20 班级 + 50 教师 + 20 教室 + 30 时间槽/天 × 5 天/周 |
| 约束项数量 | 参照 §6.2 定义 |
| 求解时间 | ≤ 30 秒 |
| 解质量 | 返回可接受课表（INFEASIBLE 时输出冲突约束清单） |

### 6.2 "约束项"定义

**"约束项"指 CP-SAT 求解器内的约束实例数量（constraint instances），即 8 条 L0 硬约束模板在特定学校规模下展开的实际约束条数。**

以 20 班 + 50 教师 + 20 教室 + 30 槽/天 × 5 天为参考基准：

| 约束模板 | 实例数估算 | 说明 |
|---------|-----------|------|
| L0-02 教师时间冲突 | ~1,500 | 50教师 × 30时隙/天 |
| L0-03 教室时间冲突 | ~600 | 20教室 × 30时隙/天 |
| L0-04 班级时间冲突 | ~600 | 20班 × 30时隙/天 |
| L0-06 班级周课时达标 | ~200 | 20班 × 平均10科目 |
| L0-01/05/07/08 | ~100-300 | 配置相关 |
| **合计** | **约 2,500-3,000** | |

> **说明：** 设计文档中"100 约束项"为初期参考基准的概称，不代表 Phase 1 必须恰好达到 100 条。实际 Phase 1 Benchmark 以"≤ 30 秒内求解"为验收标准，约束项数量取决于具体学校配置。

### 6.3 超时策略

若 30 秒内无法得到可行解：
1. 返回近似最优解（软约束违反数次优）
2. 标记 `status: partial`
3. 输出未满足的约束清单，供管理员手动调整

---

## 7. 未解决项清单（Phase 2）

以下内容**不属于 Phase 1 范围**，仅作记录：

| 项 | 说明 | 依赖 |
|----|------|------|
| L1 可配置硬约束 | Schema 的 `is_hard` 开关逻辑，关闭后降为 L2 | 需要真实学校使用数据 |
| L2 软约束权重体系 | 连堂偏好、教师时间偏好等权重（1-10）| 需要真实偏好数据 |
| 走班制数据结构预留 | 班级实体加 `type:行政班|走班组` 字段 | Phase 2 实现 |
| 分层教学数据结构预留 | 课程拆分为"课程类型"和"课程实例"两层 | Phase 2 实现 |
| 策略三分级仲裁 | 真实优先级顺序定义（需积累冲突案例） | Phase 2 实现 |

---

## 8. 附录：数学符号对照表

| 符号 | 含义 |
|------|------|
| `T` | 教师集合 |
| `C` | 班级集合 |
| `CLASSES` | 所有班级（含合班组） |
| `S` | 科目集合 |
| `R` | 教室集合（含 SPECIAL_ROOMS 子集） |
| `TS` | 时间槽集合 |
| `U[t]` | 教师 `t` 的不可用时间槽集合 |
| `teacher_of[c,s]` | 查表：班级 `c` 科目 `s` 的授课教师 |
| `ALLOWED_SUBJECTS[r]` | 专用教室 `r` 允许的科目集合 |
| `ALLOWED_TEACHERS[r]` | 专用教室 `r` 允许的授课教师集合 |
| `required_hours[c,s]` | 班级 `c` 科目 `s` 的规定周课时数 |
| `student_count[c]` | 班级 `c` 的学生人数 |
| `capacity[r]` | 教室 `r` 的最大容量 |
| `COMBINED_CLASSES` | 合班组集合 |
| `z[room, timeslot]` | 辅助布尔：专用教室该时段是否被专业课占用 |

---

## 9. Engineering Review 修订记录

| 版本 | 日期 | 修订内容 | 关联 Issue |
|------|------|----------|-----------|
| v1.0 | 2026-04-08 | 初始版本 | — |
| v1.1 | 2026-04-08 | 决策变量从 5D 改为 3D + Index（`teacher_of` 查表） | 1A |
| v1.1 | 2026-04-08 | L0-07 合班改为原子调度单元（COMBINED_CLASS） | 1C |
| v1.1 | 2026-04-08 | L0-08 形式化加注 big-M/Implication 实现说明 | 1B |
| v1.1 | 2026-04-08 | 冲突报告注明 `available_slots` 为后处理字段 | 1D |
| v1.1 | 2026-04-08 | L0-02 加同一教师同节多班授课澄清注释 | 1E |
| v1.1 | 2026-04-08 | L0-08 允许借用修正（非严格禁止） | 用户修正 |

---

**下一步：用户最终确认 → 进入阶段 1（环境搭建 + OR-Tools Benchmark）**

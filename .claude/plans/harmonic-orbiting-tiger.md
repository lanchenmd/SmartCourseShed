# 节点 0：约束模型规格定义 — 执行计划

## Context

节点 0 是中小学排课系统的准备节点，在编码前必须完成约束模型的 formal规格定义。
输出文档：`docs/constraint-model.md`

此节点的核心输入来自：
- `中小学排课系统_多Agent协作开发框架.md`（需求文档）
- `design_baseline.md`（已批准的设计基线）
- 上述 brainstorming 对话中的所有决策

---

## 已确认的设计决策

### 1. 求解器选型
- **CP-SAT**（OR-Tools `CP-SAT` solver）
- 原因：速度快、支持大规模工业级求解、软硬约束集成天然

### 2. 约束分层架构（Phase 1）

```
L0 硬约束（权重 10000，Schema 固定不可配置）
  ├── L0-01: 教师时间不可用（Teacher Unavailability）
  ├── L0-02: 教师时间冲突（同一教师同时段只能一节课）
  ├── L0-03: 教室时间冲突（同一教室同时段只能一节课）
  ├── L0-04: 班级时间冲突（同一班级同时段只能一节课）
  ├── L0-05: 教室容量限制（学生数 ≤ 教室容量）
  ├── L0-06: 班级周课时精确达标（Σ课时 == 规定课时，等式约束）
  ├── L0-07: 合班课同时进行（2-N 个班同时段同教室）
  └── L0-08: 专用教室用途限制（实验室等仅用于对应科目）

L1 可配置硬约束（Schema 预留 `is_hard` 开关，Phase 1 全部开启，暂不实现逻辑降级）
  └── Phase 2 再实现 L1 约束组

L2 软约束（Phase 2 实现）
  └── 连堂偏好、教师时间偏好、课程分布均匀性

注：策略二（自动降级）整体不建议实现，不在 Phase 1 范围
```

### 3. 冲突解决策略（Phase 1）
- **策略一（严格模式）**：L0 硬约束不可违反，无可行解则返回 INFEASIBLE + 冲突约束清单
- **策略三（分级仲裁）**：Schema 预留 `priority` 字段占位，Phase 1 全部硬约束填同一值，Phase 2 再定义优先级顺序
- **策略选择不做配置化**：Phase 1 固定为策略一

### 4. CP-SAT 实现细节（从 L0 约束推导）

| 约束 | CP-SAT 实现 | 约束类型 |
|------|-------------|---------|
| L0-02/03/04 时间冲突 | `for_each(var in time_slots): sum(assignments) <= 1` | `AllDifferent` 或 `AddLinearConstraint` |
| L0-01 教师不可用 | 决策变量 domain 直接排除不可用时段 | domain 裁剪 |
| L0-05 容量 | `student_count <= room_capacity` | `AddLinearConstraint` |
| L0-06 课时精确达标 | `sum(weekly_slots for class/subject) == required_hours` | `AddLinearConstraint` 等式 |
| L0-07 合班同步 | 所有合班班级共享同一个 `room_id` 和 `time_slot` | 辅助变量同步约束 |
| L0-08 专用教室 | `allowed_subjects[room_id]` 白名单检查 | `AddAllowedAssignments` 或 `AddForbiddenAssignments` |

### 5. 关键措辞精确化（文档中须明确）
- L0-06：精确达标（等式 `==`，非 `>=`）
- L0-07：支持 2-N 班合班，Phase 1 验证两班合场景
- L0-08：严格禁止借用（无对应专业课时，专用教室空置，不借给普通课程）

### 6. 约束实体 Schema（为策略三预留扩展点）

```json
{
  "id": "string",
  "type": "enum(硬约束 | 软约束)",
  "code": "string (如 L0-01)",
  "priority": "int | null",      // 预留，Phase 1 全部填 null
  "penalty_weight": "int | null", // 软约束用，Phase 1 全部填 null
  "is_active": "boolean",
  "school_id": "string (多租户隔离)"
}
```

---

## 步骤 0（前置）：更新项目记忆和 CLAUDE.md

**此步骤在 Plan Mode 退出后立即执行（Plan Mode 期间无法编辑其他文件）：**

### 0.1 更新记忆文件 `memory/design_baseline.md`
追加以下决策：
- CP-SAT 求解器选型
- L0 硬约束完整清单（8条，含精确化说明）
- 约束分层架构（L0/L1/L2）
- 冲突策略（策略一 + 策略三预留）
- L0-06 等式约束、 L0-07 两班合验证、L0-08 严格禁止借用

### 0.2 更新项目 `CLAUDE.md`
在"实施计划摘要"节点 0 中补充约束模型完成状态

### 0.3 更新 `memory/project_overview.md`（如需要）
补充约束模型决策对技术栈的影响说明

---

## 执行步骤（续 Step 1-3）

### Step 1: 写入 `docs/constraint-model.md`

文档结构：

```
1. 概述
   - 约束模型目标
   - CP-SAT 求解器选型说明
   - 约束分层架构图

2. L0 硬约束规格（8条）
   - 每条包含：代码、名称、定义、CP-SAT 实现方式、数学形式化

3. 冲突解决策略
   - Phase 1 策略一（严格模式）
   - 策略三预留（priority 字段）
   - 策略二（不实现）

4. 约束实体定义
   - JSON Schema
   - 字段说明（含 priority 扩展点注释）

5. OR-Tools CP-SAT 模型草图
   - 决策变量定义
   - 目标函数（Phase 1 最小化软约束违反数）
   - 约束形式化（每条 L0 的数学表达）

6. 未解决项清单（Phase 2）
   - L1 可配置硬约束
   - L2 软约束权重体系
   - 走班制/分层教学数据结构预留
```

### Step 2: 自审（Spec Self-Review）
- 检查无 TBD/TODO 占位
- 检查数学形式化与代码实现描述一致
- 检查 L0-06 等式 vs 不等式措辞一致

### Step 3: 提交用户 Review
- 用户阅读 `docs/constraint-model.md`
- 用户确认后 → 进入节点 1

---

## Critical Files

- 输出文件：`docs/constraint-model.md`（新建）
- 参考文档：`中小学排课系统_多Agent协作开发框架.md`（已有）
- 参考文档：`~/.gstack/projects/SmartCourseShed/chenlan-main-design-20260407.md`（已有）

---

## Verification

- [ ] 文档写入 `docs/constraint-model.md`
- [ ] 自审通过：无占位符、无歧义
- [ ] 用户 review 并确认
- [ ] Commit 到 git

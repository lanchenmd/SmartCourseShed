# 中小学排课 SaaS 系统 — 实施计划

## Context

这是一个面向中小学的排课 SaaS 系统，核心差异化是"能自我进化的排课系统"。MVP（Phase 1）聚焦配置驱动的排课核心，解决学校当前"手工排课 + 冲突检测效率低"的核心痛点。

**已完成：**
- 需求澄清（/office-hours）
- 设计文档（已批准，8/10）

**设计基线：** `~/.gstack/projects/SmartCourseShed/chenlan-main-design-20260407.md`

---

## MVP 实施范围（Phase 1）

### 核心模块（精简后）

| 模块 | 功能点 | 优先级 |
|------|--------|--------|
| 排课核心 | OR-Tools 全量排课、增量排课、手动排 + 自动填充 | P0 |
| 约束系统 | 硬约束（教师/教室/班级三维冲突）、软约束（满意度评分 0-100） | P0 |
| 冲突检测 | 实时冲突检测、冲突原因提示、冲突红框高亮 | P0 |
| 日历界面 | 周/月视图、FullCalendar 拖拽、换节/换天 | P0 |
| 基础数据 | 班级、教师、课程、教室、时间槽 CRUD | P0 |
| 用户权限 | 两级角色（管理员 + 普通用户）+ JWT 双 Token | P0 |

**砍掉（Phase 2）：**
- 调课/代课/请假审批流
- Excel 导入
- 超级管理员（Phase 2 再做）
- 微信小程序端（Phase 2 再做）

### 技术架构

```
前端: Next.js 14 (App Router) + React 18 + Ant Design 5 + FullCalendar
后端主服务: Node.js + Hono (JavaScript/TypeScript)
排课算法服务: Python + OR-Tools (独立服务)
数据库: PostgreSQL 16
缓存: Redis
部署: Docker Compose (单租户 SaaS)
```

**技术架构说明：**
- Node.js + Hono：后端主服务，处理 API 请求、业务逻辑
- Python + OR-Tools：排课核心算法，以独立服务形式部署，通过 **HTTP/REST** 与主服务通信
- 原因：OR-Tools 是 Python 库，无法直接集成到 Node.js；Phase 1 优先简单性，HTTP/REST 更易调试和快速迭代

**技术栈变更原因：** Bun + Elysia 生产案例少，生态不成熟。Node.js + Hono 同样支持 TypeScript，但更稳定、招人更容易、问题排查更容易。

### 关键文件路径（待创建）

| 类型 | 路径 | 说明 |
|------|------|------|
| 前端 | `frontend/` | Next.js 14 应用 |
| 后端主服务 | `backend/` | Node.js + Hono API 服务 |
| 排课算法服务 | `scheduler/` | Python + OR-Tools 独立服务 |
| 数据库 | `backend/db/` | PostgreSQL Schema + Flyway 迁移 |
| AI 抽象层 | `backend/ai/provider.ts` | LLM 调用抽象（Phase 2-3 使用） |

---

## MVP 差异化定位（Phase 1）

**Phase 1 主打差异化：** 极致的冲突检测体验 + 超快的排课速度

- 国内现有排课软件冲突检测普遍做得差（只能检测部分冲突）
- 我们的目标：100% 硬约束冲突检测，一个不漏
- 排课速度：30 秒内生成可接受课表（竞品通常需要 5 分钟+）

**Phase 1 核心价值：** 让教务主任从"手工检查冲突 1-2 天"变成"一键生成，2 小时内完成"

---

## 实施节点

### 节点 0: 约束模型规格定义（准备节点，并行于环境搭建）

**目标：** 在编码前定义机器可读的约束规格，作为 OR-Tools 求解器的输入

**任务：**
1. **定义硬约束（必须满足）：**
   - 教师冲突：同一教师同一时间只能在一个班级
   - 教室冲突：同一教室同一时间只能分配给一个班级
   - 班级冲突：同一班级同一时间只能有一门课程
   - 课时数约束：每门课程每周必须达到指定课时数

2. **定义软约束（影响满意度评分）：**
   - 教师时间偏好（如不希望排在上午第一节）
   - 课程连排偏好（如体育课不要连排）
   - 科目分布均匀性（如语文不要集中在上午）
   - 教室容量约束

3. **输出：**
   - `docs/constraint-model.md` — 机器可读的约束规格文档
   - OR-Tools Benchmark 基准数据文件

**验收标准：** 约束模型文档化，PM 确认无误后方可开始 Phase 1 编码

### 节点 1: 环境搭建 + OR-Tools Benchmark（第 1 周）

**目标：** 验证 OR-Tools 在 30 秒内能为目标规模生成可接受课表

**任务：**
0. **设计 PostgreSQL Schema（含 school_id 多租户预留）**
   - 创建 Flyway 迁移脚本
   - 核心表：schools, classes, teachers, courses, classrooms, time_slots, schedules, constraints, users
   - 所有表预留 `school_id` 字段（多租户扩展性）
1. 搭建开发环境：Node.js + Hono + Next.js + PostgreSQL + Redis
2. 实现基础数据模型（班级、教师、课程、时间槽）
3. 用 OR-Tools 实现基础排课算法
4. **Benchmark 测试：** 20 班级 + 50 教师 + 100 约束项，求解时间必须 ≤ 30 秒
5. 若超时，调整算法策略（近似求解 + 分步求解）

**验收标准：** OR-Tools Benchmark 通过（30 秒内返回可接受解）

---

### 节点 2: 排课核心 + 冲突检测（第 2-3 周）

**目标：** 完成配置驱动的排课核心

**任务：**
1. 实现约束配置系统（硬约束 + 软约束可配置）
2. 实现冲突检测 API（三维冲突：教师、教室、班级）
3. 实现满意度评分系统（0-100 分）
4. 实现三种排课模式（全量/增量/手动+自动填充）
5. 集成排课算法与冲突检测
6. **Python 服务错误处理策略：**
   - 超时：35 秒（30s Benchmark + 5s buffer）
   - 重试：超时/5xx 自动重试 1 次
   - 错误响应：返回结构化错误（code + message）
   - 部分失败：若求解器返回部分解，标记 `status: partial`

**验收标准：**
- 硬约束冲突 100% 检测，不漏报
- 满意度评分可量化显示

---

### 节点 3: 日历 UI（第 4-5 周）

**目标：** 完成日历拖拽界面 + 冲突解决 UX

**任务：**
1. 集成 FullCalendar（周/月视图）
2. 实现课程卡片拖拽（换节、换天）
3. 拖拽时实时调用冲突检测 API
4. **冲突解决 UX（新增）：**
   - 冲突红框高亮 + 冲突原因提示
   - 冲突时显示可用的替代时间槽列表
   - 用户选择替代方案后自动更新
   - 无法解决时标记为"待手动调整"状态
5. 日历叠加信息：公历日期（农历/天气暂不做）

**验收标准：**
- 日历视图流畅切换
- 拖拽操作 < 100ms 响应（冲突检测有延迟）
- 冲突实时检测无延迟
- 用户能理解冲突原因并选择解决方案

---

### 节点 4: 基础权限 + 用户认证（第 6 周）

**目标：** 完成两级权限 + JWT 双 Token

**任务：**
1. 实现用户注册 / 登录（账号密码）
2. 实现两级权限（管理员 + 普通用户）
   - 管理员：排课操作、审核调课/代课/请假
   - 普通用户：查看本人课表、提交调课/代课/请假申请
3. 实现 JWT Access Token + Refresh Token 双 Token 机制
4. 实现 Redis Token 黑名单（登出失效）
5. 实现 Redis 乐观锁（课表写操作并发保护）

**砍掉：** 超级管理员（Phase 2 实现）

**验收标准：**
- 两级权限隔离，无越权访问
- Token 刷新机制正常

---

### 节点 5: 优化与收尾（第 7-8 周）

**目标：** 完善 Phase 1 核心功能，修复 bug

**任务：**
1. 全流程集成测试
2. 性能优化（OR-Tools 求解时间、数据库查询优化）
3. Bug 修复
4. 用户体验优化

**砍掉（Phase 2）：**
- 调课/代课/请假审批流
- Excel 批量导入
- 超级管理员
- 微信小程序端

---

## 强制工作流（CLAUDE_RULES.md）

**每个任务开始前必须：**
1. 执行 brainstorming（/brainstorming skill）
2. 创建失败测试用例（先写测试，再写实现）
3. 任务完成后对照验收标准逐条确认

**每个模块完成后必须：**
1. 执行 /review（工程质量审查）
2. 执行 /cso（安全审计，JWT + 权限模块）
3. 执行 /qa（功能验收）

---

## 验证方法

### 单元测试
- 排课算法：硬约束 100% 通过
- 冲突检测：已知冲突用例 100% 检出
- 权限控制：越权访问 100% 拦截

### 集成测试
- 全流程排课：生成可接受课表（硬约束 0 冲突 + 满意度 ≥ 60）

### 端到端验收（/qa）
1. 管理员登录 → 配置约束 → 生成课表
2. 日历拖拽调整 → 冲突实时检测

### OR-Tools Benchmark
- 目标：20 班级 + 50 教师 + 100 约束项，≤ 30 秒
- 基准数据：见 `docs/benchmark-data.md`

---

## 当前状态

- [x] 需求澄清（/office-hours）
- [x] 设计文档（已批准，8/10）
- [x] CEO Review（3 项建议已接受）
- [x] Engineering Review（5 architecture issues resolved, 3 outside voice recommendations accepted）
- [ ] 节点 0: 约束模型规格定义
- [ ] 节点 1: 环境搭建 + OR-Tools Benchmark

**下一步：** 节点 0: 约束模型规格定义（准备节点）

---

## GSTACK REVIEW REPORT

| Review | Trigger | Runs | Status | Findings |
|--------|---------|------|--------|----------|
| CEO Review | `/plan-ceo-review` | 1 | ✅ CLEAR | 3 strategic recommendations accepted |
| Eng Review | `/plan-eng-review` | 1 | ✅ CLEAR | 5 architecture issues resolved; 3 outside voice recommendations accepted (Phase 0 added, HTTP kept, conflict UX added) |
| Design Review | — | 0 | — | Pending implementation |

**VERDICT:** CEO + ENG CLEARED — ready to proceed to implementation

---

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale |
|---|-------|----------|-----------|-----------|----------|
| 1 | CEO | Bun+Elysia → Node.js+Hono | Auto | P5 (explicit over clever) | 成熟生态，更易招人、排障 |
| 2 | CEO | 添加差异化定位 | Auto | P1 (completeness) | Phase 1 需要明确的核心价值主张 |
| 3 | CEO | 砍调课/请假/Excel/超级管理员 | Auto | P2 (boil lakes) | 聚焦核心，减少不确定性 |
| 4 | Eng | gRPC → HTTP/REST | Auto | Simplicity | Phase 1 优先简单性，HTTP 更易调试 |
| 5 | Eng | 添加约束模型规格定义（Phase 0） | Auto | Completeness | 编码前必须定义机器可读约束规格 |
| 6 | Eng | PostgreSQL Schema 含 school_id | Auto | Multi-tenancy | 所有表预留多租户字段 |
| 7 | Eng | Redis 乐观锁（并发保护） | Auto | Data integrity | 多管理员并发写保护 |
| 8 | Eng | Python 错误处理策略（35s 超时/重试/partial） | Auto | Reliability | 防止超时和数据丢失 |
| 9 | Eng | 冲突解决 UX（替代方案列表） | Auto | UX | 用户能理解冲突并自主解决 |
| 10 | Outside Voice | 约束模型规格前置 | Accepted | Prerequisites | 约束规格是后续开发的基础 |
| 11 | Outside Voice | 保持 HTTP/REST | Accepted | Simplicity | Phase 1 接受限制，后续可升级 |
| 12 | Outside Voice | 冲突解决 UX | Accepted | UX completeness | 核心用户流程必须定义 |
# CLAUDE.md — 中小学排课系统 项目核心指令

本项目的需求可参考./中小学排课系统_多Agent协作开发框架.md文档。

本项目所有 Claude Code 行为规范、Superpowers 强制工作流、gstack 角色切换规则、Subagent 使用规则及全部特殊约定，**完整定义在 `./CLAUDE_RULES.md` 中**。

**Claude Code 必须永久遵守以下规则：**

- 你必须将 `./CLAUDE_RULES.md` 的全部内容视为本文件（CLAUDE.md）的**不可分割的一部分**，拥有完全相同的最高优先级和约束力。
- 每次对话开始、每次新任务、每次思考前，你都必须先确认已完整加载并严格执行 CLAUDE_RULES.md 中的所有条款。
- 若本文件与 CLAUDE_RULES.md 出现任何冲突，以 CLAUDE_RULES.md 为准。

（本文件后续仅用于增加全局说明或临时重点，不会再放入具体工作流规则）

---

## 项目设计基线

**已批准的设计文档：** `~/.gstack/projects/SmartCourseShed/chenlan-main-design-20260407.md`

设计基线包含：

- MVP 术语表（冲突定义、满意度评分、可接受课表标准）
- 角色权限映射（管理员/普通用户两级，节点2实现超级管理员（节点1砍掉））
- 调课/代课/请假流程（节点2实现）
- 三个关键前提（P1/P2/P3）
- 差异化定位（极致冲突检测 + 超快排课速度）

**记忆体系：** `~/.claude/projects/-Users-chenlan-Desktop-SmartCourseShed/memory/`

- 项目概述、技术栈、节点划分
- 设计基线摘要
- 市场需求与用户画像

---

## 实施计划摘要


| 节点   | 内容                                                                      | 状态            |
| ---- | ----------------------------------------------------------------------- | ------------- |
| 节点 0 | 约束模型规格定义（准备节点）：CP-SAT 3D+Index方案 + 8条L0硬约束 + 策略一 + Engineering Review完成 | **已完成（v1.1）** |
| 节点 1 | 环境搭建 + OR-Tools Benchmark                                               | **✅ 已完成**     |
| 节点 2 | 排课核心 + 冲突检测                                                             | 待开始           |
| 节点 3 | 日历 UI + 冲突解决 UX                                                         | 待开始           |
| 节点 4 | 基础权限 + 用户认证 + Redis 乐观锁                                                 | 待开始           |
| 节点 5 | 优化与收尾                                                                   | 待开始           |


**节点1 已解决问题：**

- L0-02 OnlyEnforceIf TypeError：改用 3-step BoolVar 桥接
- L0-06 线性AND方向错误：改为正确的不等式方向
- run_benchmark.py 数据不一致（核心）：required_hours 总和调整为 = timeslots
- Stale JSON 数据文件：每次运行重新生成
- Room 容量不足：capacity 50 → 60

**节点1 砍掉，节点2实现：** 调课/代课/请假审批流、Excel 导入、超级管理员、微信小程序端、需求沟通 Agent + 校对 Agent

**下一步：** 进入节点2 — 排课核心 + 冲突检测

**节点1 文档：**

- `scheduler/docs/PHASE1_BENCHMARK_STATUS.md` — Benchmark 状态报告
- `scheduler/docs/PHASE1_LESSONS_LEARNED.md` — 踩坑总结
- `scheduler/docs/PHASE1_TESTING_GUIDE.md` — 测试指南


## gstack (REQUIRED — global install)

**Before doing ANY work, verify gstack is installed:**

```bash
test -d ~/.claude/skills/gstack/bin && echo "GSTACK_OK" || echo "GSTACK_MISSING"
```

If GSTACK_MISSING: STOP. Do not proceed. Tell the user:

> gstack is required for all AI-assisted work in this repo.
> Install it:
> ```bash
> git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
> cd ~/.claude/skills/gstack && ./setup --team
> ```
> Then restart your AI coding tool.

Do not skip skills, ignore gstack errors, or work around missing gstack.

Using gstack skills: After install, skills like /qa, /ship, /review, /investigate,
and /browse are available. Use /browse for all web browsing.
Use ~/.claude/skills/gstack/... for gstack file paths (the global path).

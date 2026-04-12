# Phase 1 踩坑总结

**日期：** 2026-04-11
**状态：** 已解决

---

## 1. 问题总览

| # | 问题 | 严重程度 | 根因 | 状态 |
|---|------|----------|------|------|
| 1 | L0-02 OnlyEnforceIf TypeError | 高 | CP-SAT API 理解错误 | ✅ 已修复 |
| 2 | L0-06 线性AND方向错误 | 高 | 布尔逻辑理解错误 | ✅ 已修复 |
| 3 | run_benchmark.py 数据不一致 | **极高** | 数据定义与文档不一致 | ✅ 已修复 |
| 4 | Stale JSON 数据文件 | 中 | 缓存问题 | ✅ 已修复 |
| 5 | Room 容量不足 | 中 | 数据配置错误 | ✅ 已修复 |

---

## 2. 坑 1：L0-02 OnlyEnforceIf TypeError

### 2.1 错误代码

```python
# 错误实现：直接将 x 变量用于 OnlyEnforceIf
model.Add(sum_vars <= 1).OnlyEnforceIf(x[timeslot, cls.id, room.id])
```

**错误信息：**
```
TypeError: OnlyEnforceIf expects a BoolVar or its negation, not BoundedLinearExpression
```

### 2.2 根因

CP-SAT 的 `OnlyEnforceIf()` 只接受 `BoolVar` 类型，不接受线性表达式（如 `x <= 1`）。

### 2.3 解决方案

使用 3-step BoolVar 桥接：

```python
# Step 1: is_x = x (x 是 BoolVar，直接等价)
is_x = model.NewBoolVar(f"ix_{timeslot}_{cls.id}_{room.id}")
model.Add(is_x == 1).OnlyEnforceIf(x[timeslot, cls.id, room.id])
model.Add(is_x == 0).OnlyEnforceIf(x[timeslot, cls.id, room.id].Not())

# Step 2: is_s_match = (s == subj_idx) via equivalence
is_s_match = model.NewBoolVar(f"is_{timeslot}_{cls.id}_{room.id}")
model.Add(s_var == subj_idx).OnlyEnforceIf(is_s_match)
model.Add(s_var != subj_idx).OnlyEnforceIf(is_s_match.Not())

# Step 3: is_active = is_x AND is_s_match via linear constraints
is_active = model.NewBoolVar(f"ia_{timeslot}_{cls.id}_{room.id}")
model.Add(is_active <= is_x)
model.Add(is_active <= is_s_match)
model.Add(is_active >= is_x + is_s_match - 1)
```

### 2.4 与设计目标的差距

**设计文档说：** L0-02 使用 `AddLinearConstraint(sum <= 1)`
**实际情况：** CP-SAT 的 `OnlyEnforceIf` 不能直接用在线性约束上，需要布尔桥接

---

## 3. 坑 2：L0-06 线性AND方向错误

### 3.1 错误代码

```python
# 错误：使用 1 - is_x 而不是 is_x
model.Add(is_this <= 1 - is_x)  # 错误！
model.Add(is_this <= is_s_match)
model.Add(is_this >= is_x + is_s_match - 1)
```

### 3.2 根因

布尔逻辑 AND 的线性约束实现方向错误：

- `is_this <= 1 - is_x`：当 `is_x = 1` 时，`is_this <= 0`，错误地强制 `is_this = 0`
- 正确：`is_this <= is_x`，当 `is_x = 0` 时自然 `is_this = 0`

### 3.3 解决方案

```python
# 正确的 AND 线性化：
# is_this = is_x AND is_s_match
# is_this <= is_x          (if is_x=0 then is_this=0)
# is_this <= is_s_match     (if is_s_match=0 then is_this=0)
# is_this >= is_x + is_s_match - 1  (if both=1 then is_this>=1, so is_this=1)
model.Add(is_this <= is_x)
model.Add(is_this <= is_s_match)
model.Add(is_this >= is_x + is_s_match - 1)
```

### 3.4 与设计目标的差距

**设计文档说：** 使用等式 `==` 精确约束
**实际情况：** 需要先将 AND 逻辑线性化，再使用等式约束课时总数

---

## 4. 坑 3：run_benchmark.py 数据不一致（核心问题）

### 4.1 错误代码

```python
# run_benchmark.py 中的错误定义
required_hours = {
    "c1": {"语文": 4, "数学": 4, "英语": 3, "物理": 3, "化学": 2, "生物": 2}
    # 总和 = 18，但 timeslots = 30！
}
```

```python
# generate_test_data.py 中的正确定义（与设计文档一致）
required_hours = {
    "c1": {"语文": 5, "数学": 5, "英语": 5, "物理": 5, "化学": 5, "生物": 5}
    # 总和 = 30，等于 timeslots
}
```

### 4.2 症状

```
=== Benchmark Results: medium ===
Runs: 1 | Success: 0 | Failed: 1
Wall Time (s): 60.425
Status: UNKNOWN (timeout)
```

- 单独 L0-03 + L0-04：OPTIMAL (0.028s)
- L0-03 + L0-04 + L0-06：60秒超时

### 4.3 根因分析

**L0-06 的语义假设：**
- 每个 timeslot 的 room 赋值都贡献到一个 subject
- `s[ts, cls]` subject 跟随 `x[ts, cls, room]` room 赋值

**实际问题：**
- `required_hours` 总和 = 18/30 = 60%
- 40% 的 room 赋值不应该关联到任何 subject
- 但 `s[ts, cls]` 不受 `x[ts, cls, room]` 约束，是**自由变量**
- 当 `s` 可以自由取值时，`is_s_match = (s == subj_idx)` 导致搜索空间爆炸

**验证实验：**
```python
# 当 required_hours = 30/30 (100% 覆盖) 时
Status: OPTIMAL, Time: 1.727s  # 快速求解！

# 当 required_hours = 18/30 (60% 覆盖) 时
Status: UNKNOWN, Time: 60.067s  # 超时！
```

### 4.4 解决方案

修正 `run_benchmark.py`，使其与 `generate_test_data.py` 和设计文档一致：

```python
# Medium dataset：required_hours 总和 = 30
required_hours = {
    "c1": {"语文": 5, "数学": 5, "英语": 5, "物理": 5, "化学": 5, "生物": 5}
}

# Large dataset：required_hours 总和 = 30
required_hours = {
    "c1": {
        "语文": 4, "数学": 4, "英语": 4,
        "物理": 3, "化学": 3, "生物": 3,
        "历史": 3, "地理": 3, "政治": 3
    }
}
```

### 4.5 与设计目标的差距

**设计文档说：** `required_hours` 总和应等于可用 timeslots（确保可达）
**实际情况：** Benchmark 数据生成脚本与主脚本不一致，导致不可达

---

## 5. 坑 4：Stale JSON 数据文件

### 5.1 问题

```bash
# 每次运行 benchmark 前需要手动删除缓存
rm -rf scheduler/benchmark/data/*.json
```

### 5.2 解决方案

在 `load_dataset()` 中检查数据文件是否存在，如果存在则重新生成：

```python
def load_dataset(name: str) -> ScheduleInput:
    data_dir = Path(__file__).parent / "data"
    json_file = data_dir / f"{name}.json"

    if json_file.exists():
        # 始终重新生成，避免 stale 数据
        json_file.unlink()

    # 重新生成...
```

### 5.3 与设计目标的差距

**设计文档说：** 固定 JSON 数据集
**实际情况：** 需要每次重新生成以保证数据一致性

---

## 6. 坑 5：Room 容量不足

### 6.1 问题

```python
# 原配置：room capacity = 50
rooms = [RoomInfo(id=f"r{i}", name=f"room_{i}", capacity=50) for i in range(1, 7)]

# 但 class c6 有 52 学生
classes = [ClassInfo(id=f"c{i}", name=f"class_{i}", student_count=40 + i * 2) for i in range(1, 7)]
# c6: student_count = 40 + 6*2 = 52 > 50
```

### 6.2 解决方案

```python
# 修正 room capacity
rooms = [RoomInfo(id=f"r{i}", name=f"room_{i}", capacity=60) for i in range(1, 7)]
```

### 6.3 与设计目标的差距

**设计文档说：** 教室容量应能容纳最大班级
**实际情况：** 生成数据时未检查容量约束

---

## 7. 总结：与设计目标的差距

| 设计目标 | 实际实现 | 差距说明 |
|---------|---------|---------|
| required_hours 总和 = timeslots | 数据脚本不一致 | 需要手动对齐 |
| CP-SAT OnlyEnforceIf 直接使用 | 需要 BoolVar 桥接 | API 细节差异 |
| L0-06 精确等式约束 | 需要 AND 线性化 | 实现复杂度高于预期 |
| 固定 JSON 数据集 | 每次重新生成 | 数据一致性优先 |
| 教室容量覆盖最大班级 | 生成时未校验 | 需要后添加验证 |

---

## 8. 经验教训

1. **数据一致性是关键**：Benchmark 数据生成脚本和运行脚本必须使用相同的约束定义，否则会出现"设计可达但运行不可达"的问题

2. **CP-SAT API 有细节约束**：`OnlyEnforceIf` 不能直接用于线性约束，需要布尔桥接

3. **L0-06 的语义需要满足**：`required_hours` 必须与 timeslots 成正比，否则求解器无法快速收敛

4. **测试数据必须验证**：生成的数据应该包含基本的可达性检查

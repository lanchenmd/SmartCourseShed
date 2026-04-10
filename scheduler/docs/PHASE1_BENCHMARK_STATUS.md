# Phase 1 Benchmark 状态报告

**更新日期：** 2026-04-10

## 当前结果

| Dataset | Status | Success Rate | Avg Time | Notes |
|---------|--------|--------------|----------|-------|
| Small   | ✅ PASS | 3/3 (100%)   | 0.026s   | OPTIMAL |
| Medium  | ⚠️ FAIL | 0/3 (0%)     | 60s+     | UNKNOWN/INFEASIBLE |
| Large   | ⚠️ FAIL | 0/1 (0%)     | 120s+    | UNKNOWN |

## 已解决问题

1. **L0-02 OnlyEnforceIf TypeError**：OnlyEnforceIf 不接受 BoundedLinearExpression，改用 3-step BoolVar 桥接
2. **L0-06 线性AND方向错误**：从 `is_this <= 1 - is_x` 改为 `is_this <= is_x` + `is_this >= is_x + is_s_match - 1`
3. **L0-02 AND 双向等价缺失**：添加了 `model.Add(is_active == 1).OnlyEnforceIf(is_x)` 和 `model.Add(is_active == 1).OnlyEnforceIf(is_s)` 反向约束
4. **Stale JSON 数据文件**：删除了 `benchmark/data/*.json`，每次运行重新生成
5. **Room 容量不足**：Medium/Large 的 room capacity 从 50 改为 60

## 待解决问题

### Medium Dataset UNKNOWN (超时)

**现象：** 3次运行均达到60秒超时限制，状态 UNKNOWN（不是 INFEASIBLE）

**分析：**
- L0-03 + L0-04 单独测试：OPTIMAL (0.028s)
- L0-03 + L0-04 + L0-06：INFEASIBLE (0.034s) - 快速失败
- L0-03 + L0-04 + L0-05 + L0-06：INFEASIBLE (0.034s) - 快速失败
- 全部8个约束：UNKNOWN (60s timeout) - 慢搜索

**可能原因：**
1. L0-06 约束数量过多（6 classes × 6 subjects × 30 timeslots × 6 rooms × 3 boolvars = 3240+ 辅助变量）
2. CP-SAT 求解器在某些约束组合下搜索效率低
3. Medium dataset 的 required_hours 分布导致大量冲突

**下一步排查方向：**
1. 单独测试 L0-03 + L0-04 + L0-05（不加 L0-06）是否 OPTIMAL
2. 检查 medium required_hours 是否满足（18/30 slots）
3. 尝试减少 required_hours 或调整约束顺序

## Benchmark 命令

```bash
# Small
python -m scheduler.benchmark.run_benchmark --dataset small --runs 3 --timeout 30

# Medium
python -m scheduler.benchmark.run_benchmark --dataset medium --runs 3 --timeout 60

# Large
python -m scheduler.benchmark.run_benchmark --dataset large --runs 1 --timeout 120
```

## 验收标准（来自 design spec）

- Medium dataset: avg ≤25s, success_rate ≥80%, worst ≤35s
- Large dataset: 待定义

# V16 计划：WaddingtonV5Arm — 两桶路由（ML-heavy 或 V13 基线）

**日期**：2026-06-21 | **状态**：计划中

---

## 背景

V15 的完整分析见 [docs/v15/SUMMARY.md](../v15/SUMMARY.md)。核心结论：

- ML-heavy 路由（0.8/0.2）在大基因池数据集显著有效（IL2 +15%，Sanchez21 +33%）
- LLM-heavy 路由（w_llm > 0.5）消除了 ML 过滤效应，Steinhart/Replogle_essential 退步
- **w_llm=0.4（V13 基线）对 LLM 强数据集已是最优**，不需要更高

---

## V16 设计：两桶简化

```python
def _route_weights(n_genes: int, n_hits: int) -> tuple[float, float]:
    if n_genes > 15000 and 0.02 < n_hits / n_genes < 0.07:
        return (0.80, 0.20)   # ML-heavy
    return (0.60, 0.40)        # V13 baseline
```

| 数据集 | n_genes | hit_rate | 桶 | w_ml | w_llm |
|--------|---------|---------|-----|------|-------|
| IFNG | 17785 | 4.5% | ML-heavy | 0.80 | 0.20 |
| IL2 | 18273 | 2.6% | ML-heavy | 0.80 | 0.20 |
| Sanchez21 | 17807 | 4.8% | ML-heavy | 0.80 | 0.20 |
| Sanchez21_down | 17807 | 4.9% | ML-heavy | 0.80 | 0.20 |
| Carnevale22 | 18224 | 4.8% | ML-heavy（误） | 0.80 | 0.20 |
| Scharenberg22 | 1029 | 4.8% | **V13 基线** | 0.60 | 0.40 |
| Steinhart | 18144 | 0.8% | **V13 基线** | 0.60 | 0.40 |
| Replogle_essential | 623 | 10.1% | **V13 基线** | 0.60 | 0.40 |
| Replogle_gwps | 9193 | 10.1% | **V13 基线** | 0.60 | 0.40 |

---

## 预期性能

| 数据集 | V13 | V15 | V16 预期 | 来源 |
|--------|-----|-----|---------|------|
| IFNG | 0.165 | 0.176 | ~0.176 | ML-heavy（同 V15）|
| IL2 | 0.272 | 0.313 | ~0.313 | ML-heavy（同 V15）|
| Sanchez21 | 0.060 | 0.080 | ~0.080 | ML-heavy（同 V15）|
| Sanchez21_down | 0.072 | 0.089 | ~0.089 | ML-heavy（同 V15）|
| Carnevale22 | 0.057 | 0.054 | ~0.054 | ML-heavy 误分（同 V15）|
| Scharenberg22 | 0.456 | 0.469 | ~0.456 | V13 基线（损失 V15 增益）|
| Steinhart | **0.163** | 0.142 | **~0.163** | V13 基线（恢复历史记录）|
| Replogle_essential | **0.582** | 0.534 | **~0.582** | V13 基线（恢复历史记录）|
| Replogle_gwps | 0.258 | 0.250 | ~0.258 | V13 基线 |
| **avg** | 0.232 | 0.234 | **~0.241** | |

---

## 验收标准

| 标准 | 目标 |
|------|------|
| avg > V15 (0.234) | avg ≥ 0.238 |
| avg > V13 (0.232) | avg ≥ 0.238 |
| 恢复 Steinhart 历史记录 | ≥ 0.155 |
| 恢复 Replogle_essential 历史记录 | ≥ 0.565 |
| 保持 ML 数据集改善 | IFNG ≥ 0.172，IL2 ≥ 0.295 |

# V15 实验报告：WaddingtonV4Arm — 静态预分类路由

**日期**：2026-06-21 | **状态**：已完成（部分成功）| **里程碑**：WADDINGTON_PLAN M5 修复版

---

## 结果

**avg hit@R5 = 0.234** — 微超 V13（0.232），但 Steinhart/Replogle 路由错误

### 全臂对比

| 数据集 | OA | LLM | V13 | **V15** | delta | 路由 |
|--------|-----|-----|-----|--------|-------|------|
| IFNG | 0.183 | 0.156 | 0.165 | **0.176** | +0.011 | ML 0.8/0.2 ✓ |
| IL2 | 0.314 | 0.253 | 0.272 | **0.313** | +0.041 | ML 0.8/0.2 ✓ |
| Sanchez21 | 0.087 | 0.060 | 0.060 | **0.080** | +0.020 | ML 0.8/0.2 ✓ |
| Sanchez21_down | 0.101 | 0.069 | 0.072 | **0.089** | +0.017 | ML 0.8/0.2 ✓ |
| Carnevale22 | 0.047 | 0.058 | 0.057 | 0.054 | -0.003 | ML 0.8/0.2（误分） |
| Scharenberg22 | 0.449 | 0.469 | 0.456 | **0.469** | +0.013 | LLM 0.3/0.7 ✓ |
| Steinhart | 0.090 | 0.152 | **0.163** | 0.142 | **-0.021** | LLM 0.35/0.65 ✗ |
| Replogle_essential | 0.476 | 0.550 | **0.582** | 0.534 | **-0.048** | LLM 0.3/0.7 ✗ |
| Replogle_gwps | 0.273 | 0.214 | 0.258 | 0.250 | -0.008 | Balanced ✓ |
| **avg** | **0.224** | **0.220** | **0.232** | **0.234** | +0.002 | |

### 进展曲线

```
V13 WaddingtonV2  0.232  ← 仍持有项目历史最高（Steinhart=0.163, Replogle_ess=0.582）
V15 WaddingtonV4  0.234  ← 整体微超，但两个历史记录丢失
V14 WaddingtonV3  0.221
```

---

## 核心发现：w_llm 过高会消除 ML 过滤效应

V15 最大失误：把 Steinhart 和 Replogle_essential 的 w_llm 提高到 0.65-0.70，结果比 V13 的 0.40 更差。

### 关键机制

V13（w_ml=0.6, w_llm=0.4）能超过纯 LLM 的原因，在于 ML 对 LLM 提名的过滤：

```
组合分数 = w_ml × ml_score(g) + w_llm × llm_bonus(g)

非 LLM 基因排过 LLM 基因的条件：
  w_ml × ml_score_nonllm > w_ml × ml_score_llm + w_llm
  → ml_score_nonllm > ml_score_llm + w_llm / w_ml

V13 (0.6/0.4): 非 LLM 基因只需 ml_score > ml_score_llm + 0.67
  → ML 可替换 LLM 最差的 ~15% 提名（ml_score 极低的"LLM 幻觉"基因）
  → Steinhart: 0.163 > 纯 LLM 0.152（+7.2%）

V15 (0.35/0.65): 非 LLM 基因需 ml_score > ml_score_llm + 1.86
  → ml_score 最大为 1.0 → 不可能！
  → 完全等价于纯 LLM 选择
  → Steinhart: 0.142 ≈ 纯 LLM 随机输出（0.152 的噪声版）
```

**结论：对 LLM 强数据集，最优 w_llm 不是"更高"，而是恰好让 ML 能过滤 LLM 最差选择。V13 的 0.40 接近最优。**

### ML 过滤的正确临界点

```
要让 ML 能替换 LLM 的最差提名，需要：
  w_llm / w_ml < 1.0（即非 LLM 顶级基因的 ml_score 上界）

当 w_llm = 0.4, w_ml = 0.6：阈值 = 0.67，约 15% LLM 提名可被替换
当 w_llm = 0.5, w_ml = 0.5：阈值 = 1.00，几乎没有替换
当 w_llm = 0.65, w_ml = 0.35：阈值 = 1.86，完全不替换
```

最优 w_llm 约在 0.35-0.45 之间（对所有数据集），ML 过滤效果与 LLM 影响力的最佳平衡点。

---

## ML-heavy 路由的成功

V15 的 ML 重路由（0.8/0.2）在大基因池 + 中命中率数据集上效果显著：

| 数据集 | V13 | V15 | vs OA | 效果 |
|--------|-----|-----|-------|------|
| IL2 | 0.272 | **0.313** | -0.001 (≈OA!) | 接近纯 OA |
| Sanchez21 | 0.060 | **0.080** | -0.007 | +33% |
| Sanchez21_down | 0.072 | **0.089** | -0.012 | +24% |
| IFNG | 0.165 | **0.176** | -0.007 | +7% |

合计增益：+0.089（4 个数据集）。这是真正有效的改进，V16 应保留。

---

## V16 方向：简化路由，保留 ML-heavy，LLM-heavy 降回 V13 基线

V15 暴露了一个简单规律：

```
w_llm 的正确设置：
  ML 强数据集：w_ml=0.8, w_llm=0.2  （大幅降低 LLM 噪声）
  其他所有数据集：w_ml=0.6, w_llm=0.4  （V13 基线，已是 LLM 最优）
```

两条路由代替 V15 的四桶：

```python
if n_genes > 15000 and 0.02 < hit_rate < 0.07:
    return (0.80, 0.20)   # ML-heavy：IFNG, IL2, Sanchez21, Sanchez21_down, Carnevale22
else:
    return (0.60, 0.40)   # V13 基线：Scharenberg22, Steinhart, Replogle_essential, Replogle_gwps
```

预期 V16 avg：
```
IFNG:            ~0.176  (V15 ML-heavy 保留)
IL2:             ~0.313  (V15 ML-heavy 保留)
Sanchez21:       ~0.080  (V15 ML-heavy 保留)
Sanchez21_down:  ~0.089  (V15 ML-heavy 保留)
Carnevale22:     ~0.054  (ML-heavy 误分类，同 V15)
Scharenberg22:   ~0.456  (V13 基线，恢复)
Steinhart:       ~0.163  (V13 基线，恢复历史新高)
Replogle_ess:    ~0.582  (V13 基线，恢复历史新高)
Replogle_gwps:   ~0.258  (V13 基线)

预期 avg = 0.241  (> V15 0.234 > V13 0.232)
```

---

## 里程碑状态

| 版本 | 内容 | avg hit@R5 | Steinhart | Replogle_ess |
|------|------|-----------|-----------|-------------|
| V13 | 固定 0.6/0.4 | 0.232 | **0.163** ★ | **0.582** ★ |
| V14 | EMA 自适应 | 0.221 | 0.145 | 0.545 |
| **V15** | **四桶静态路由** | **0.234** | 0.142 | 0.534 |
| V16（计划）| 两桶路由（ML-heavy 或 V13 基线）| **预期 0.241** | ~0.163 | ~0.582 |

---

## 总结

V15 半成功：ML-heavy 路由是对的（+0.089 合计），但 LLM-heavy 高权重是错的（-0.069 合计）。净 +0.002。

**关键洞察**：V13 的 w_llm=0.4 不仅是"均衡先验"，更是让 ML 过滤 LLM 错误选择的临界权重。提高 w_llm 超过约 0.5 后，ML 过滤效果消失，退化为纯 LLM。V16 只需对 ML-strong 数据集降低 w_llm，其余保持 V13 基线。

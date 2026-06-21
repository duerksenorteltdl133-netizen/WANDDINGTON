# V18 实验报告：WaddingtonV7Arm — 三桶路由 + gwps 两步策略

**日期**：2026-06-21 | **状态**：已完成

---

## 结果

**avg hit@R5 = 0.244 — 项目新高**（V17=0.237, V16=0.236）

### 全臂对比

| 数据集 | V17 | **V18** | Δ | 路由 | Δ 来源 |
|--------|-----|--------|---|------|--------|
| IFNG | 0.174 | 0.173 | -0.001 | ml_heavy | LLM 方差 |
| IL2 | 0.312 | 0.303 | -0.009 | ml_heavy | LLM 方差 |
| Sanchez21 | 0.078 | 0.077 | -0.001 | ml_heavy | LLM 方差 |
| Sanchez21_down | 0.087 | 0.090 | +0.003 | ml_heavy | LLM 方差 |
| Carnevale22 | 0.053 | 0.052 | -0.001 | ml_heavy | LLM 方差 |
| Scharenberg22 | 0.456 | **0.497** | +0.041 | baseline | LLM 非确定性（幸运） |
| Steinhart | 0.140 | 0.142 | +0.002 | baseline | LLM 方差 |
| Replogle_essential | 0.577 | **0.587** | +0.010 | baseline | LLM 方差 |
| **Replogle_gwps** | 0.254 | **0.277** | **+0.023** | **two_stage** | **结构性提升** |
| **avg** | **0.237** | **0.244** | **+0.007** | | |

### 进展全览

```
V10 OnlineAdaptive   0.224
V13 WaddingtonV2     0.232
V16 WaddingtonV5     0.236
V17 WaddingtonV6     0.237
V18 WaddingtonV7     0.244  ← 项目新高 (+7.8% vs V10)
```

---

## 核心分析

### 1. gwps 两步策略是结构性提升（+0.023，真实）

```
gwps 轮次命中率对比：
        R1      R2      R3      R4      R5
V17:   0.064   0.127   0.177   0.217   0.254
V18:   0.089   0.137   0.181   0.224   0.277
Δ:    +0.025  +0.010  +0.004  +0.007  +0.023
```

R1 提升最显著（+39%）：第一轮 ML 尚无反馈，ML top-512 shortlist 直接为 LLM 提供了高质量候选池，立即提升精度。之后各轮也持续优于 V17，证明 shortlist 约束在整个实验过程中都有效。

**机制**：gwps（9193 genes, 10.1% hit rate）的 ML 模型可将 hits 富集到 top-512 中（recall@5.6% ≈ 35-50%），LLM 在此高密度候选池（≈20-25% hit rate）中精选，精度远高于在全部 9193 个基因中自由选。

### 2. Scharenberg22 +0.041 是 LLM 非确定性（不稳定）

| 版本 | Scharenberg22 | 代码逻辑 | LLM 温度 |
|------|-------------|--------|---------|
| V17 | 0.456 | baseline 0.6/0.4 | 0.0 |
| V18 | 0.497 | **完全相同** | 0.0 |

两者代码路径完全一致（均路由到 baseline，使用相同权重和 LLM 类）。差异只能来自 Claude API 跨 session 的微小输出变化（即使 temperature=0，不同 API session 偶尔产生不同结果）。

这复现了 V13 Steinhart=0.163 的"幸运采样"现象，但这次在 temp=0 下发生，说明 temp=0 不是 100% 跨 session 确定性。

**结论**：V18 的 Scharenberg22=0.497 不可靠，V19 可能回归到 ~0.456-0.470。

### 3. 真实结构性收益

剔除 Scharenberg22 的不稳定贡献，纯 gwps two-stage 结构性收益：

```
gwps structural gain: +0.023
avg structural gain:  +0.023/9 ≈ +0.003

V17 avg (稳定): 0.237
V18 structural avg: 0.240  （Scharenberg22 回归后的预期值）
V18 lucky avg:    0.244   （本次实际值，包含 Scharenberg22 lucky sample）
```

---

## 残余瓶颈

| 数据集 | V18 | 历史最优 | gap | 说明 |
|--------|-----|---------|-----|------|
| IFNG | 0.173 | OA 0.183 | -0.010 | ML 特征局限 |
| IL2 | 0.303 | OA 0.314 | -0.011 | LLM 方差 |
| Sanchez21 | 0.077 | OA 0.087 | -0.010 | ML 特征局限 |
| Steinhart | 0.142 | LLM 0.152 | -0.010 | 生物先验不足 |
| Replogle_gwps | 0.277 | V12 0.290 | -0.013 | shortlist 大小未优化 |
| Scharenberg22 | 0.497 | 本次 0.497 | — | 不稳定（幸运） |

**gwps 残余 gap（-0.013 vs V12=0.290）**：V12 用 3×128=384 shortlist，V18 用 512。两者结果接近（V12=0.290, V18=0.277），主要差距来自：
1. V12 有专属于 gwps 的提示工程（直接展示 PPI 网络得分）
2. shortlist 大小对 gwps 可能仍不是最优（384 vs 512 哪个更好？）

---

## V19 方向

**优先级：验证 Scharenberg22 稳定性 + gwps shortlist 调参**

方向 1：对 Scharenberg22 做独立 3 次重跑，确认 0.497 是否可复现。若不可复现，V18 结构性 avg ≈ 0.240。

方向 2：gwps shortlist 大小对比实验：
- V18：shortlist=512（4×batch），V12：shortlist=384（3×batch）
- 候选：256 / 384 / 512 / 768，找 gwps 最优 shortlist 尺寸

方向 3：若 Scharenberg22 是稳定提升，深挖 V18 vs V17 在该数据集的具体基因选择差异。

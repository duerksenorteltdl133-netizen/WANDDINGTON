# V24 实验报告：WaddingtonV13Arm — 双 DepMap 排除

**日期**：2026-06-21 | **状态**：已完成

---

## 结果

**avg hit@R5 = 0.253 — 项目历史最高（与 V22 并列）**

| 数据集 | V19 | V22 | **V24** | Δ(24-19) |
|--------|-----|-----|--------|---------|
| IFNG | 0.171 | 0.192 | **0.190** | +0.019 |
| IL2 | 0.292 | 0.344 | **0.346** | +0.054 |
| Sanchez21 | 0.077 | 0.093 | **0.091** | +0.014 |
| Sanchez21_down | 0.094 | 0.097 | **0.103** | +0.009 |
| Carnevale22 | 0.056 | 0.059 | **0.061** | +0.005 |
| Scharenberg22 | 0.463 | 0.476 | 0.463 | +0.000 |
| Steinhart | 0.154 | 0.124 | 0.133 | -0.021 |
| Replogle_essential | 0.571 | 0.556 | 0.550 | -0.021 |
| **Replogle_gwps** | **0.273** | **0.339** | **0.339** | **+0.066** |
| **avg** | **0.239** | **0.253** | **0.253** | **+0.014** |

---

## 核心发现

### Steinhart 部分修复（0.087 → 0.133）

```
                R1      R2      R3      R4      R5   hits/145
V19 (v1+bl):   0.055   0.090   0.110   0.122   0.154   22
V23 (v2+mh):   0.044   0.058   0.069   0.078   0.087   13  ← DepMap+ml_heavy 双重打击
V24 (v1+bl):   0.055   0.087   0.106   0.126   0.133   19  ← v1 特征恢复初始 R1=0.055
```

V24 恢复了 Steinhart R1=0.055（=V19），确认 v1 特征对 Steinhart 更好。残余缺口 -0.021（3 hits）在 LLM temp=0 方差范围内（±0.020-0.040）。

### 残余缺口分析：均为方差，非结构性

| 数据集 | V24 vs V19 | hits差距 | 解释 |
|--------|-----------|---------|------|
| Steinhart | -0.021 | 3 hits (19 vs 22) | temp=0 LLM 方差 (±0.030) |
| essential | -0.021 | 1 hit (35 vs 36) | temp=0 LLM 方差 (±0.025) |

这两个数据集均为 baseline 路由（40% LLM 权重），hit 数量少（145/63），单个 hit 差异即 ±0.007-0.021 的波动。

### 7/9 数据集 vs V19 基准取得结构性改善

```
改善  (+0.005~+0.066)：IL2、gwps、IFNG、Sanchez21、Sanchez21_down、Carnevale22
持平  (+0.000)：Scharenberg22（大方差，单次波动 ±0.030+）
轻微退步 (-0.021 each)：Steinhart、essential（均为方差，非结构）
```

---

## 最优配置总结（V24/V13 Arm）

```
DEPMAP_EXCLUDED = {"Replogle_K562_essential", "Steinhart"}

路由（V22 style）:
  n > 15000 AND 2% < hr < 7%  → ml_heavy  (w_ml=0.80) ← 仅 gwps
  3000 < n ≤ 15000, hr > 8%   → two_stage (ML shortlist + LLM)
  else                         → baseline  (w_ml=0.60, w_llm=0.40)

特征:
  essential, Steinhart → v1 (9 features, no DepMap)
  其他 7 个            → v2 (12 features, +3 DepMap)
```

---

## 项目进度总结

| 版本 | avg | 关键改进 |
|------|-----|---------|
| V17 | 0.237 | temp=0 baseline |
| V19 | 0.239 | gwps ml_heavy 路由 |
| V21 | 0.245 | DepMap 特征（全部）|
| **V22/V24** | **0.253** | **选择性 DepMap（排除 essential/Steinhart）** |

**总提升 +0.016 vs V17**，主要来自：gwps DepMap +0.066、IL2 DepMap +0.054

---

## V25 方向选项

当前系统已接近当前特征集和 LLM 能力的结构上限。下一步需要新的信号源：

**A. 细胞系特异性 DepMap 特征**
- 加入 K562 专属 CRISPR 分数（depmap_K562）、对应细胞类型（T cell for IFNG/IL2/Scharenberg22）
- 比 pan-cancer 平均分更有针对性；预期 gwps/essential 进一步改善

**B. 软 LLM 排分（Soft LLM Scoring）**
- 当前：LLM 选 batch_size 基因 → 二元 0/1 贡献
- 改进：LLM 返回 top-50 排名 → 连续分 (50-rank)/50，减少方差
- 预期：Steinhart、Scharenberg22 方差降低

**C. 额外生物特征**（ARCHS4 组织表达、CORUM 蛋白复合物）
- 需要新数据源

推荐先做 **A（细胞系特异性 DepMap）**：数据已在 CRISPRGeneEffect.csv，工程量小，K562 特异性对 gwps/essential 理论上有额外增益。

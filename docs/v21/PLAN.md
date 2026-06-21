# V21 计划：WaddingtonV10Arm — DepMap 特征增强

**日期**：2026-06-21 | **状态**：计划中

---

## 背景

当前 LOO LightGBM 使用 9 个纯 PPI/通路特征，无细胞系特异性数据。
DepMap 24Q4 CRISPRGeneEffect.csv（1178 cell lines × 17916 genes）
包含现成的 CRISPR 必需性信号：

| 特征 | gwps AUC | Scharenberg22 AUC | IL2 AUC |
|------|---------|-----------------|---------|
| depmap_frac_ess（新） | **0.841** | **0.851** | 0.755 |
| depmap_mean（新）     | 0.829   | 0.789   | 0.740 |
| 当前最强 (pli_score+string_degree_norm) | ~0.65-0.70 | ~0.70 | ~0.65 |

---

## 新特征（3个）

| 特征名 | 定义 | 主要受益数据集 |
|--------|------|--------------|
| `depmap_frac_ess` | 1178 个 cell line 中 Chronos ≤ -0.5 的比例 | gwps, Scharenberg22, IL2 |
| `depmap_mean_score` | 均值 Chronos 得分（越负越必需） | 全部 |
| `depmap_min_score` | 最小 Chronos 得分（任一 cell line 中最必需） | 强必需基因 |

---

## 实现步骤

1. **生成富化训练数据** `lgbm_training_data_v2.csv`
   - 从 DepMap 计算 3 个基因级特征（17916 genes）
   - 与现有训练数据（118885 行）左合并
   - 缺失基因的 DepMap 特征填 0

2. **更新特征列表**（在 `llm_reasoning_arm.py` 和 `online_adaptive_arm.py` 中）
   - FEATURE_COLS 增加 3 个新特征

3. **创建 WaddingtonV10Arm**（指向 v2 训练数据，其余与 V9/V8 相同）
   - 路由逻辑、权重、LLM 温度、shortlist 均不变
   - 唯一变化：ML 模型训练特征更丰富

---

## 预期性能

| 数据集 | V19 | V21 预期 | Δ | 机制 |
|--------|-----|---------|---|------|
| Replogle_gwps | 0.273 | ~0.290 | +0.017 | ML shortlist 质量 ↑ |
| Scharenberg22 | 0.463 | ~0.490 | +0.027 | ML AUC 0.789→0.851 |
| IL2 | 0.292 | ~0.310 | +0.018 | ML 召回率 ↑ |
| IFNG | 0.171 | ~0.185 | +0.014 | ML AUC 0.617→0.645 |
| Sanchez21/down | ~0.085 | ~0.095 | +0.010 | ML 改善 |
| Replogle_essential | 0.571 | ~0.590 | +0.019 | ML AUC 0.658→0.677 |
| Carnevale22 | 0.052 | ~0.055 | +0.003 | 改善有限（AUC 0.533）|
| Steinhart | 0.154 | ~0.150 | ≈0 | DepMap 不相关（AUC 0.486）|
| **avg** | **0.239** | **~0.252** | **+0.013** | |

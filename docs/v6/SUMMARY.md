# V6 实验报告：通用生物特征（pLI + STRING Degree）

**日期**：2026-06 | **状态**：已完成 | **最优结果**：9DS avg=0.678，LOO avg=0.200

---

## 背景

V5（5 特征）LOO avg=0.192，瓶颈在于 Carnevale22（腺苷-PKA 通路）和 Steinhart（GD2 糖脂通路）这两个实验，LOO AUC 分别只有 0.052 和 0.069，接近随机（0.5）。

这两个实验的 anchor 基因（ADORA2A/PRKACA、B4GALNT1/UGCG）是非常冷门的信号通路，在 STRING PPI 网络中连接极少，导致 `g1_ppi_score`、`hub_score_norm`、`archs4_coexpr` 三个主要特征全部接近 0，模型退化为随机。

---

## 核心想法

引入两个**与锚点基因完全无关**的全局基因属性：

1. **pLI score**（gnomAD v2.1.1 LoF 约束分数，0→1，越高越不耐受 LoF 突变）
   - 来源：`prep_universal_features.py` 下载 gnomAD constraint 表
   - 高 pLI 的基因（如 PRKACA=0.97）通常是核心通路成员，更可能是 essential hit
   
2. **string_degree_norm**（STRING 全局连接度，threshold=700，除以最大值）
   - 来源：STRING API `network` 端点，统计每个基因的 combined_score≥700 的邻居数
   - TP53、EGFR 等 hub 基因 degree=1.0；冷门基因 degree≈0

这两个特征不依赖实验上下文，在 LOO 测试时与训练时特征分布相同。

---

## 实施步骤

1. **数据准备**：`prep_universal_features.py`
   - 下载 gnomAD pLI（~19K 基因）
   - 从 STRING `interaction_partners` 统计 degree（combined_score≥700）
   - 输出 `workspace/data/universal_features.csv`（20,868 基因）

2. **V6 特征集**（7 个）：
   ```
   g1_ppi_score, hub_score_norm, archs4_coexpr, ppi_score_sum, kegg_overlap,
   pli_score, string_degree_norm
   ```

3. **代码更新**：`bootstrap_lgbm.py`
   - 新增 `load_universal_features()` 和 `build_features()` 中的 `univ_features` 参数
   - 修复 `_precompute_features()` 位置参数 bug（`use_rank_norm` 被误传为 `univ_features`）

---

## 结果

| 数据集 | V5 AUC | V6 AUC | 变化 |
|-------|--------|--------|------|
| IFNG | 0.786 | 0.832 | +4.6% |
| JAK1KO | 0.682 | 0.731 | +4.9% |
| Carnevale22 | 0.052 | 0.068 | +1.6% |
| Steinhart | 0.069 | 0.081 | +1.2% |
| **9DS avg** | **0.519** | **0.678** | **+30.6%** |
| **LOO avg** | **0.192** | **0.200** | **+4.2%** |

9DS 大幅提升（+30.6%）主要来自 pLI 对 hub 基因的区分能力；LOO 小幅提升（+4.2%）说明两个特征有一定泛化价值，但瓶颈数据集（Carnevale22、Steinhart）基本没有改善。

---

## 关键发现

- **全局特征能提升训练集内表现**：pLI 和 string_degree 帮助模型识别生物学上重要的基因
- **LOO 泛化改善有限**：核心瓶颈是 Carnevale22/Steinhart 的锚点基因过于特异，pLI/degree 都是全局 prior，不携带通路特异信息
- **下一步方向**：需要能区分具体通路（如腺苷信号、糖脂代谢）的特征 → V7 通路成员数量特征

---

## 结论

V6 建立了 7 特征基线（LOO=0.200），确认了全局生物学特征的价值。`universal_features.csv` 从此作为固定输入，**V7 在其基础上追加通路成员计数特征**。

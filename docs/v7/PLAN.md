# V7 计划：通路成员数量特征（Pathway Membership Count）

**日期**：2026-06 | **状态**：进行中 | **目标**：LOO avg > 0.210

---

## 问题诊断

V6 LOO avg=0.200，瓶颈：

| 数据集 | 生物背景 | V6 LOO AUC |
|-------|---------|------------|
| Carnevale22 | 腺苷受体-PKA 信号（ADORA2A/PRKACA） | ~0.068 |
| Steinhart | GD2 糖脂生物合成（B4GALNT1/UGCG） | ~0.081 |

这两个数据集的命中基因集中在特定代谢/信号通路，而 pLI 和 STRING degree 是全局 prior，无法区分通路内基因和通路外基因。

---

## 假设

一个基因参与的**通路数量**（KEGG、Reactome）在生物学意义上区分"通路枢纽基因"（参与多条通路，更可能是功能冗余或跨通路协调）和"通路孤立基因"（参与很少通路，更可能是特异性执行者）。

对于 Carnevale22 这类实验，hit 基因（如 PRKACA=68 KEGG 通路，极高）在通路数量上与非 hit 基因有系统性差异，pLI 无法捕捉这一差异。

---

## 新增特征

### 1. `kegg_pathway_count_norm`
- **定义**：该基因属于多少个 KEGG 通路 / max 通路数
- **来源**：`_kegg_cache/{GENE}.json`（已缓存 19,943 个基因，免费获取）
- **示例**：MAPK1=112（max，=1.0），PRKACA=68（=0.607），TP53=49（=0.438），B4GALNT1=1（=0.009）

### 2. `reactome_pathway_count_norm`
- **定义**：该基因属于多少个 Reactome 通路 / max 通路数
- **来源**：MyGene.info 批量 API（`pathway.reactome` 字段），结果缓存到 `_reactome_cache/`
- **示例**：Reactome 通路更细粒度（>2,500 条），预期 PRKACA 等 hub 基因在 Reactome 中也有高覆盖

---

## 特征集（9 个，V7）

```
g1_ppi_score          # 候选基因与锚点基因的最大 STRING PPI 分数
hub_score_norm         # 基因在 315 个 PPI cache 文件中的出现比例
archs4_coexpr          # 与锚点基因的最大 ARCHS4 共表达相关系数
ppi_score_sum          # 在所有 PPI cache 中的 STRING 分数之和（归一化）
kegg_overlap           # 与锚点基因共享的 KEGG 通路比例
pli_score              # gnomAD pLI（LoF 约束）
string_degree_norm     # STRING 全局连接度（threshold=700）
kegg_pathway_count_norm      # 新增 V7：KEGG 通路成员数
reactome_pathway_count_norm  # 新增 V7：Reactome 通路成员数
```

前 5 个为锚点相关特征（anchor-specific），后 4 个为全局特征（anchor-independent）。

---

## 实施计划

### 步骤 1：数据准备（`prep_pathway_features.py`）
- 从 `_kegg_cache/` 统计每个基因的 KEGG 通路数 → `kegg_pathway_count_norm`
- 调用 MyGene.info API 批量获取 Reactome 通路数，缓存到 `_reactome_cache/`
- 归一化：除以各自最大值
- 输出：`workspace/data/pathway_features.csv`

### 步骤 2：模型更新（`bootstrap_lgbm.py`）
- 新增 `PATHWAY_FEAT_CSV`、`load_pathway_features()`
- `FEATURE_COLS` 扩展到 9 个
- `build_features()`、`_precompute_features()`、`cross_dataset_eval()`、`run()` 传递 `pathway_features`

### 步骤 3：推理更新（`gene_ranker.py`）
- 新增 `_load_pathway_features()`、`_get_pathway_features()` 懒加载
- `_lgbm_scores()` 和 `_lgbm_scores_with_rank_norm()` 中：n_feat≥9 走 V7 分支，n_feat==7 走 V6 分支（向后兼容）

### 步骤 4：运行 V7
```bash
cd workspace/evaluation
python3 prep_pathway_features.py      # ~20K 基因 Reactome 批量查询
python3 bootstrap_lgbm.py             # 训练 + 评估
```

---

## 预期结果

| 场景 | LOO avg |
|------|---------|
| 乐观：Carnevale22 能被通路数量区分 | 0.215~0.230 |
| 中性：通路数量与 pLI 信息高度重叠 | 0.200~0.210 |
| 悲观：通路数量对瓶颈数据集无效 | ~0.200 |

---

## 失败后的备选方向

若 V7 LOO 无提升：

- **方向 B**：直接在 `kegg_overlap` 特征加权（对冷门通路锚点用 Reactome overlap 替代）
- **方向 C**：二阶段架构 — 第一阶段用 PPI 扩展锚点候选集，第二阶段用 ML 精排
- **方向 D**：文献挖掘 — 自动从 PubMed 摘要提取新锚点基因（替代人工标注）

---

## 风险

1. **Reactome 批量查询速度**：20K 基因 × 500/batch = 40 批次，预计 5~10 分钟
2. **特征冗余**：`kegg_pathway_count_norm` 与 `string_degree_norm` 可能高度相关（hub 基因在两者中都高），LightGBM 的 `num_leaves=31` 可能无法有效利用细粒度信号
3. **样本不平衡**：9-特征模型参数与 V6 相同（scale_pos_weight 自动调整），但更多特征可能导致 300 棵树不够收敛

---

## 附：V3→V7 进展表

| 版本 | 特征数 | 9DS avg | LOO avg | 关键改进 |
|-----|--------|---------|---------|---------|
| V3 | 3 | 0.476 | — | 基线（PPI + hub + essential） |
| V4 | 5 | 0.484 | 0.192 | +ARCHS4 coexpr + KEGG overlap |
| V5 | 5 | 0.519 | 0.192 | PPI cache 315 个（+DepMap oncogenes） |
| V6 | 7 | 0.678 | 0.200 | +pLI + STRING degree |
| **V7** | **9** | **TBD** | **TBD** | **+KEGG count + Reactome count** |

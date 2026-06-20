# V7 实验报告：通路成员数量特征（Pathway Membership Count）

**日期**：2026-06-20 | **状态**：已完成 | **最优结果**：9DS avg=0.716，LOO avg=0.217

---

## 背景

V6（7 特征，pLI + STRING degree）LOO avg=0.200，核心瓶颈是两个冷门通路数据集（Carnevale22=0.052，Steinhart=0.069），其锚点基因（ADORA2A/PRKACA、B4GALNT1/UGCG）在 STRING PPI 网络中连接稀疏，导致所有锚点相关特征接近 0。

V7 假设：一个基因参与的通路数量（KEGG、Reactome）是与锚点完全无关的全局属性，PRKACA（参与 68 条 KEGG 通路）vs B4GALNT1（参与 1 条 KEGG 通路）的差异应能被模型利用。

---

## 新增特征

### `kegg_pathway_count_norm`
- **定义**：基因属于多少条 KEGG 通路 / max(112)
- **来源**：`_kegg_cache/{GENE}.json`（19,943 个基因，免费读取）
- **示例**：MAPK1/MAPK3=1.0，PRKACA=0.607，TP53=0.438，B4GALNT1=0.009，UGCG=0.009

### `reactome_pathway_count_norm`
- **定义**：基因属于多少条 Reactome 通路 / max(514)
- **来源**：MyGene.info 批量 API，`_reactome_cache/` 缓存（19,943 个基因，~7 分钟下载）
- **示例**：RPS27A=1.0（泛素标签），UBB/UBC=0.934，GRB2=0.463，MAPK1=0.432

---

## 特征集（9 个，V7）

```
g1_ppi_score               锚点特异
hub_score_norm             锚点特异（全局 PPI cache）
archs4_coexpr              锚点特异
ppi_score_sum              锚点特异（全局 PPI cache）
kegg_overlap               锚点特异
pli_score                  全局（V6 新增）
string_degree_norm         全局（V6 新增）
kegg_pathway_count_norm    全局（V7 新增）
reactome_pathway_count_norm 全局（V7 新增）
```

---

## 结果

### 9DS 训练集表现（train-on-all）

| 数据集 | AUC-ROC | hit_ratio@R5 |
|-------|---------|-------------|
| IFNG | 0.949 | 0.576 |
| IL2 | 0.982 | 0.821 |
| Sanchez21 | 0.945 | 0.541 |
| Sanchez21_down | 0.931 | 0.517 |
| Carnevale22 | 0.931 | 0.487 |
| Scharenberg22 | 1.000 | 1.000 |
| Steinhart | 0.992 | 0.903 |
| Replogle_K562_essential | 1.000 | 1.000 |
| Replogle_K562_gwps | 0.965 | 0.603 |
| **平均** | **0.966** | **0.716** |

### LOO 泛化评估（leave-one-dataset-out）

| 数据集 | AUC-ROC | hit_ratio@R5 |
|-------|---------|-------------|
| IFNG | 0.629 | 0.168 |
| IL2 | 0.733 | 0.306 |
| Sanchez21 | 0.564 | 0.077 |
| Sanchez21_down | 0.572 | 0.091 |
| Carnevale22 | 0.505 | 0.048 |
| Scharenberg22 | 0.712 | 0.449 |
| Steinhart | 0.542 | 0.076 |
| Replogle_K562_essential | 0.658 | 0.492 |
| Replogle_K562_gwps | 0.652 | 0.247 |
| **平均** | **0.619** | **0.217** |

### 特征重要性（cross-dataset 模型，split gain）

| 排名 | 特征 | 重要性 |
|-----|------|--------|
| 1 | string_degree_norm | 1579 |
| 2 | pli_score | 1442 |
| 3 | ppi_score_sum | 1405 |
| **4** | **reactome_pathway_count_norm** | **1260** |
| 5 | archs4_coexpr | 733 |
| **6** | **kegg_pathway_count_norm** | **734** |
| 7 | g1_ppi_score | 690 |
| 8 | kegg_overlap | 680 |
| 9 | hub_score_norm | 477 |

---

## V3→V7 进展对比

| 版本 | 特征数 | 9DS avg | LOO avg | vs BDA |
|-----|--------|---------|---------|--------|
| V3 | 3 | 0.450 | — | — |
| V4 | 5 | 0.473 | 0.161 | +26% |
| V5 | 5 | 0.519 | 0.192 | +50% |
| V6 | 7 | 0.678 | 0.200 | +56% |
| **V7** | **9** | **0.716** | **0.217** | **+69%** |
| BDA baseline | — | ~0.128 | — | — |

---

## 分析

### reactome 比 kegg 重要性高的原因
Reactome 有 2500+ 条细粒度通路（远多于 KEGG 的 ~300 条），区分能力更强。KEGG 通路数量与 STRING degree 相关性高（hub 基因同时参与更多 KEGG 通路），信息冗余较多；Reactome 因更细粒度，与 string_degree_norm 的重叠较少，新增信息量更大。

### Carnevale22/Steinhart 依然是瓶颈
- Carnevale22 LOO hit_ratio 0.048（V6:0.052，下降）
- Steinhart LOO hit_ratio 0.076（V6:0.069，略升）

通路成员数量是全局 prior，不能区分"腺苷通路基因"和"糖脂通路基因"，因为 PRKACA 参与多条通路（=0.607）但 hit 基因中也有 UGCG（=0.009）。特征提供的是"通路丰富度"信号，不是"通路特异性"信号。

### LOO 提升来源
+0.017 的提升（0.200→0.217）主要来自 Scharenberg22（0.449）、Replogle K562 系列（0.492/0.247）等数据集，这些数据集中的 hit 基因（自噬、剪接、转录复合体相关）在 Reactome 中有较高的通路覆盖度。

---

## 关键发现

1. **reactome_pathway_count_norm 是有价值的全局特征**（第4重要），在 V6 全局特征的基础上进一步提升 LOO +8.5%
2. **KEGG count 与 STRING degree 高度冗余**（均反映基因的"枢纽程度"），增量贡献有限
3. **瓶颈数据集不受通路数量特征影响**：Carnevale22/Steinhart 的 hit 基因在通路数量上与非 hit 基因没有系统性差异

---

## 结论与下一步

V7 正式将 LOO avg 从 0.200 提升到 **0.217**（+8.5%），通路成员数量特征（尤其是 Reactome）确实携带了额外的全局生物学信号。

但 Carnevale22/Steinhart 仍然是主要瓶颈（LOO hit_ratio < 0.08）。继续在全局 prior 方向上添加特征的边际收益会越来越小，因为这两个实验需要的是"通路特异性"信息，而不是更多的全局信号。

**下一步备选：**
- **方向 B（数据扩充）**：寻找类似生物学背景的公开 CRISPR 数据集（PRISM、DepMap pooled screens）
- **方向 C（两阶段）**：第一阶段用通路数据库推断候选通路，第二阶段针对性排名
- **方向 D（文献挖掘）**：从 PubMed 自动推断新锚点基因，替代当前人工标注

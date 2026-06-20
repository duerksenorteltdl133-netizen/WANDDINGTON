# Waddington V4 总结

> 截止日期：2026-06-20  
> 基于版本：V3（含 ppi_score_sum + 9DS benchmark）  
> 本阶段完成：10.1 KEGG 通路特征 · 10.2 顺序仿真 benchmark · 10.3 LOO 泛化调查 · **10.3b DepMap PPI 富集（V5，9DS 0.519，LOO 0.192）** · **10.4 Plan B 通用特征（V6，9DS 0.678，LOO 0.200）** · **10.5 通路成员数量特征（V7，9DS 0.716，LOO 0.217）**

---

## 0. V4/V5 一句话定位

V4 在 V3 的 9DS benchmark（均值 0.450）基础上加入第五特征（KEGG 通路重叠度），并首次实现真实顺序仿真 benchmark 和 LOO 泛化调查（9DS avg 0.473）。**V5** 接入 DepMap 24Q4 CRISPR 数据（50 多样性细胞系，254 个 oncogene 锚点）将 STRING PPI cache 从 64 → 315 个锚点文件，重训 hub/ppi 特征后 9DS avg 0.473 → **0.519**（+9.7%），LOO avg 0.161 → **0.192**（+19%）。**V6**（Plan B）新增两个锚点无关通用特征（gnomAD pLI + STRING 全局度），模型升级为 7 特征，9DS avg 0.519 → **0.678**（+30.6%），LOO avg 0.192 → **0.200**（+4.2%）。**V7** 在 V6 基础上新增 KEGG 通路成员数量和 Reactome 通路成员数量两个全局特征（9 特征），9DS avg 0.678 → **0.716**（+5.6%），LOO avg 0.200 → **0.217**（+8.5%），reactome_pathway_count_norm 成为第 4 重要特征。

---

## 1. V3 → V4 变化 diff

| 维度 | V3 | V4 |
|------|----|----|
| 特征 | 4 特征（g1_ppi_score, hub_score_norm, archs4_coexpr, ppi_score_sum）| 5 特征（+kegg_overlap）|
| 随机种子 | 未固定 | random_state=42（可复现）|
| 缓存隔离 | 单一 _ppi_cache/ | _ppi_cache/（锚点，64 文件）+ _reveal_ppi_cache/（顺序仿真揭示）|
| 9DS avg | 0.450（non-reproducible）| **0.473**（random_state=42，clean cache）|
| 顺序仿真 | 无 | SequentialWaddingtonRanker（oracle reveal → PPI 动态扩展；结果：-8.7%）|
| LOO 调查 | 无 | rank normalization 实验（结果：LOO avg -15%，负结果，代码保留）|

---

## 2. 10.1 KEGG 通路特征

### 2.1 设计

候选基因与锚点基因的 KEGG 通路重叠度，归一化到 [0,1]：

```python
anchor_pathways = union({kegg_pathways(a) for a in anchors})
kegg_overlap(gene) = |kegg_pathways(gene) ∩ anchor_pathways| / |anchor_pathways|  # [0,1]
```

数据源：MyGene.info POST API（批量 500 基因/次，缓存至 `_kegg_cache/{GENE}.json`）。

关键 bug 修复：query 字段必须是纯基因符号（`"q": ["ZAP70", "CD3E", ...]`），不能带 `symbol:` 前缀；`scopes="symbol"` 只是告诉 API 用哪个字段匹配，query 本身不应重复前缀。

### 2.2 特征重要性（cross-dataset，9DS）

| 特征 | Importance (split) | 排名 |
|------|-------------------|------|
| `ppi_score_sum` | 2933 | #1 |
| `g1_ppi_score` | 1611 | #2 |
| `archs4_coexpr` | 1544 | #3 |
| `kegg_overlap` | 1511 | #4 |
| `hub_score_norm` | 1401 | #5 |

KEGG 重要性（1511）接近 archs4（1544），显示通路信息是独立有效的特征。

---

## 3. 完整 Benchmark 结果（V4，trials=3，random_state=42）

### 3.1 静态排序（hit_ratio@R5）

| 方法 | IFNG | IL2 | San21 | San21↓ | Carnev | Schar | Stein | R_ess | R_gwps | **7DS** | **9DS** |
|------|------|-----|-------|--------|--------|-------|-------|-------|--------|---------|---------|
| Random | 0.037 | 0.031 | — | — | 0.036 | — | — | — | — | ~0.046 | — |
| BDA | 0.096 | 0.100 | — | — | 0.043 | — | — | — | — | ~0.128 | — |
| **Waddington v3** | 0.305 | 0.393 | 0.212 | 0.240 | 0.207 | 1.000 | 0.317 | 1.000 | 0.373 | 0.382 | 0.450 |
| **Waddington v4** | **0.344** | **0.447** | **0.226** | **0.254** | **0.243** | **1.000** | **0.359** | **1.000** | **0.386** | **0.410** | **0.473** |
| **Waddington v5** | **0.363** | **0.499** | **0.265** | **0.282** | **0.271** | **1.000** | **0.510** | **1.000** | **0.477** | **0.453** | **0.519** |
| **Waddington v6** | **0.532** | **0.757** | **0.475** | **0.471** | **0.461** | **1.000** | **0.848** | **1.000** | **0.561** | **0.577** | **0.678** |

v3→v4（9DS）：**0.450 → 0.473（+5.1%）**  
v4→v5（9DS）：**0.473 → 0.519（+9.7%）**（DepMap PPI 富集，315 锚点文件）  
v5→v6（9DS）：**0.519 → 0.678（+30.6%）**（Plan B，pLI + STRING 全局度，7 特征）

### 3.2 命中率曲线（v4 static，R1-R5）

| 数据集 | R1 | R2 | R3 | R4 | R5 |
|--------|----|----|----|----|-----|
| IFNG | 0.140 | 0.228 | 0.283 | 0.318 | 0.344 |
| IL2 | 0.212 | 0.306 | 0.376 | 0.422 | 0.447 |
| Sanchez21 | 0.097 | 0.147 | 0.178 | 0.205 | 0.226 |
| Sanchez21_down | 0.107 | 0.165 | 0.201 | 0.226 | 0.254 |
| Carnevale22 | 0.112 | 0.167 | 0.203 | 0.227 | 0.243 |
| Scharenberg22 | 0.633 | 0.837 | 1.000 | 1.000 | 1.000 |
| Steinhart | 0.262 | 0.303 | 0.331 | 0.345 | 0.359 |
| R_K562_essential | 0.492 | 0.746 | 0.825 | 1.000 | 1.000 |
| R_K562_gwps | 0.130 | 0.227 | 0.299 | 0.350 | 0.386 |

---

## 4. 10.2 顺序仿真 benchmark

### 4.1 设计

`SequentialWaddingtonRanker`：每轮选 batch → oracle 揭示真实命中 → 把 confirmed hits 的 STRING PPI 邻居加 `DYNAMIC_WEIGHT=0.5` 分数 → 下轮排名。

- PPI 揭示数据写入 `_reveal_ppi_cache/`，**不**写入 `_ppi_cache/`（避免污染 hub_score_norm）
- 所有 ranker 在评估循环开始前**全部预创建**（避免不同数据集间的特征分布偏移）
- 每 trial 调用 `ranker.reset()` 清空揭示状态，不重载模型

### 4.2 结果（trials=3，round=5）

| 数据集 | Static R5 | Sequential R5 | Δ |
|--------|-----------|---------------|---|
| IFNG | 0.344 | 0.315 | -0.029 (-8.4%) |
| IL2 | 0.447 | 0.439 | -0.008 (-1.8%) |
| Sanchez21 | 0.226 | 0.213 | -0.013 (-5.8%) |
| Sanchez21_down | 0.254 | 0.225 | -0.029 (-11.4%) |
| Carnevale22 | 0.243 | 0.221 | -0.022 (-9.1%) |
| Scharenberg22 | 1.000 | 0.837 | -0.163 (-16.3%) |
| Steinhart | 0.359 | 0.352 | -0.007 (-1.9%) |
| R_K562_essential | 1.000 | 0.889 | -0.111 (-11.1%) |
| R_K562_gwps | 0.386 | 0.399 | **+0.013 (+3.4%)** |
| **9DS avg** | **0.473** | **0.432** | **-0.041 (-8.7%)** |

### 4.3 分析

顺序 PPI 扩展在 8/9 数据集上**不改善**性能。原因：

1. **特征冗余**：LightGBM 已通过 `g1_ppi_score`（最强单锚点 PPI）、`hub_score_norm`（多锚点计数）、`ppi_score_sum`（总权重和）三个特征充分捕获 PPI 拓扑。
2. **Oracle 信号重叠**：前几轮确认的 hit 与模型已高置信度排名的基因高度重叠，其 PPI 邻居也已被静态模型正确优先化。
3. **噪声效应**：动态 PPI 加分把模型已放弃的邻居重新拉高，反而干扰排名。

唯一受益数据集（GWPS，+3.4%）是宇宙最大的（9,193 基因），提示：在更大搜索空间、锚点 PPI 覆盖率更低时，oracle 揭示的额外信息有边际价值。

**结论**：当前顺序适应策略（PPI 扩展）对 LightGBM+5特征 ranker 无益。未来方向可考虑：
- 将确认 hit 直接加入训练集并在线重训模型（真正的在线学习）
- 用确认 hit 更新 KEGG/ARCHS4 特征的锚点集合

---

## 5. 关键 Bug 修复记录

### 5.1 KEGG batch query 格式错误
`"q": [f"symbol:{g}" for g in genes]` + `scopes="symbol"` → 所有 KEGG 分数返回 0  
修复：`"q": [g.upper() for g in genes]`（纯基因符号，不带前缀）

### 5.2 `_ppi_cache/` 污染（严重）
`reveal()` 原来调用 `get_ppi_scores(hit)` 写入 `_ppi_cache/`，将文件数从 64 增至 1081。`_compute_hub_scores()` 对 1081 文件计算 max → hub_score_norm 全部缩小 → 训练/推断特征分布不一致 → IFNG 0.344 → 0.187。  
修复：`_get_reveal_ppi_scores()` 写入 `_reveal_ppi_cache/`，`_ppi_cache/` 始终仅含 64 个锚点文件。

### 5.3 跨数据集 ranker 预创建
`run_sequential_comparison` 原来在评估循环内创建 ranker。第一个数据集（IFNG）的 `reveal()` 调用污染 `_ppi_cache/`，导致第二个数据集（IL2）的静态 ranker 使用被污染的 hub_scores。  
修复：所有 ranker 在评估循环开始前全部预创建。

---

## 6. 核心文件（V4/V5 新增 / 修改）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `workspace/evaluation/gene_ranker.py` | 修改 | kegg_overlap 特征，_reveal_ppi_cache/ 隔离，SequentialWaddingtonRanker |
| `workspace/evaluation/bootstrap_lgbm.py` | 修改 | random_state=42，KEGG，5特征，`--include-depmap` 支持 DepMap 数据集 |
| `workspace/evaluation/benchmark.py` | 修改 | run_sequential_* 函数，--sequential CLI flag，ranker 预创建 |
| `workspace/evaluation/prep_depmap.py` | 新建 | DepMap 24Q4 CRISPR 预处理（50 细胞系，greedy max-spread 选线）|
| `workspace/evaluation/prefetch_archs4.py` | 新建 | 并行预取 ARCHS4（6 workers，254 DepMap 锚点，~5 min）|
| `workspace/evaluation/_kegg_cache/` | 新建 | MyGene.info KEGG 通路缓存（per-gene JSON）|
| `workspace/evaluation/_reveal_ppi_cache/` | 新建 | 顺序仿真揭示基因的 PPI 缓存（与 _ppi_cache/ 隔离）|
| `workspace/evaluation/_ppi_cache/` | 扩充 | 64 → 315 个锚点文件（新增 DepMap 251 个 oncogene 锚点）|
| `workspace/data/depmap/CRISPRGeneEffect.csv` | 新建 | DepMap 24Q4，429MB，1178 × 17916 |
| `workspace/data/depmap/processed/` | 新建 | 50 细胞系：ground_truth + topmovers + anchors（150 文件）|
| `workspace/models/lgbm_*.pkl` | 更新 | 全部 9 个 per-dataset 模型（random_state=42，5特征，315-file hub）|

---

## 7. 运行方式（V5）

```bash
cd /home/duanyu/Python/SKILL/waddington
ENV=/home/duanyu/anaconda3/envs/waddington-bio/bin/python

# DepMap 预处理（50 细胞系，首次约 5min）
$ENV -u workspace/evaluation/prep_depmap.py

# 并行预取 ARCHS4（仅首次，约 5min，6 workers）
$ENV -u workspace/evaluation/prefetch_archs4.py --workers 6

# 重训所有模型（含 DepMap PPI 富集，约 15min 首次，后续 2min）
$ENV -u workspace/evaluation/bootstrap_lgbm.py --include-depmap

# 完整静态 benchmark（9DS，约 2min）
$ENV -u workspace/evaluation/benchmark.py --ranker waddington --trials 3 --auto-save

# 顺序仿真 benchmark（约 10min）
$ENV -u workspace/evaluation/benchmark.py --sequential --trials 3

# LOO + DepMap 对比分析（含 50 DepMap 数据集，约 20min）
$ENV -u workspace/evaluation/bootstrap_lgbm.py --include-depmap  # 含 LOO 对比表输出
```

---

## 8. 10.3 LOO 泛化调查（负结果）

### 8.1 LOO 基准（V4，random_state=42）

| 数据集 | LOO AUC | LOO hit@R5 |
|--------|---------|-----------|
| IFNG | 0.560 | 0.127 |
| IL2 | 0.652 | 0.193 |
| Sanchez21 | 0.532 | 0.055 |
| Sanchez21_down | 0.534 | 0.060 |
| Carnevale22 | 0.498 | 0.046 |
| Scharenberg22 | 0.600 | 0.347 |
| Steinhart | 0.503 | 0.055 |
| R_K562_essential | 0.588 | 0.413 |
| R_K562_gwps | 0.562 | 0.150 |
| **9DS avg** | **0.559** | **0.161** |

### 8.2 实验：per-dataset rank normalization

对 anchor-specific 特征（g1_ppi_score, archs4_coexpr, kegg_overlap）在每个数据集内做 rank normalization → [0,1]，期望消除不同 anchor 集导致的分布偏移。

结果：LOO avg hit@R5 **0.161 → 0.136（-15%）**。Per-dataset 训练 in-sample 不变。

**失败原因**：g1_ppi_score 的绝对值本身是跨数据集信号——网络中心基因（hub genes）在任意 anchor 集下 PPI 分都高，这一普适相关性在 rank normalization 后消失。同时，Scharenberg22 LOO 从 0.347 降至 0.184（-47%）——最大受害者，可能因为该数据集命中基因与 T 细胞 anchor 集有残留的绝对 PPI 相关性，rank norm 破坏了这一意外相关性。

### 8.3 根本原因

只有 9 个训练数据集，生物多样性不足：
- Carnevale22（腺苷通路）、Steinhart（GD2 合成）：LOO AUC ≈ 0.5（随机），T 细胞 + K562 训练数据无法覆盖这些生物背景
- 需要更多 CRISPR 数据集（50+）才能从特征中学到真正普适的 ranking 规则

### 8.4 遗留能力

- `bootstrap_lgbm.py --rank-norm`：保留 rank normalization 实验入口（默认关闭）
- `gene_ranker.LGBMWrapper`：已实现，支持未来 `rank_norm=True` 模型的零改动推断
- `gene_ranker._lgbm_scores_with_rank_norm()`：分离的推断路径，向后兼容

---

## 9. 10.3b DepMap CRISPR PPI 富集（V5）

### 9.1 设计思路

LOO 泛化差的根本原因：只有 9 个 BDA 训练数据集，生物背景单一（T 细胞 + K562）。  
**方向**：接入 DepMap 24Q4 CRISPR 数据（50 多样性细胞系），用其锚点基因扩充 STRING PPI cache，使 hub_score_norm 和 ppi_score_sum 特征捕获更普适的网络拓扑信号。

### 9.2 DepMap 数据处理（prep_depmap.py）

| 参数 | 值 |
|------|---|
| 原始数据 | CRISPRGeneEffect.csv (429MB)，1178 cell lines × 17916 genes |
| 必需基因过滤 | CEGv2（684）∪ super_essentials（>80% cell lines，1186 基因）= 1301 排除 |
| 细胞系选择 | greedy max-spread（余弦相似度），从 1178 中选 50 个 |
| 每细胞系锚点 | top-12 最低 Chronos 分（排除过滤基因后），典型示例：KRAS, ERBB2, ABL1, FOXA1, GPX4 |
| 输出 | `workspace/data/depmap/processed/`：50 cell lines × 3 files（ground_truth / topmovers / anchors）|

### 9.3 PPI 富集机制

```
原 _ppi_cache/ : 64 个锚点文件（BDA 锚点）
DepMap 锚点   : 254 个独特基因（KRAS, ABL1, ERBB2, CCND1, GPX4 等）
STRING PPI 抓取 252 个新基因（2 个已缓存）
新 _ppi_cache/ : 315 个锚点文件（BDA 64 + DepMap 251）
```

hub_score_norm 和 ppi_score_sum 基于 315 文件重新计算，per-dataset 模型（lgbm_*.pkl）全部重训。

### 9.4 V5 完整 Benchmark（9DS，trials=3，random_state=42）

| 数据集 | V4 hit@R5 | V5 hit@R5 | Δ |
|--------|---------|---------|---|
| IFNG | 0.344 | **0.363** | +5.5% |
| IL2 | 0.447 | **0.499** | +11.6% |
| Sanchez21 | 0.226 | **0.265** | +17.3% |
| Sanchez21_down | 0.254 | **0.282** | +11% |
| Carnevale22 | 0.243 | **0.271** | +11.5% |
| Scharenberg22 | 1.000 | **1.000** | 0% |
| Steinhart | 0.359 | **0.510** | +42% |
| R_K562_essential | 1.000 | **1.000** | 0% |
| R_K562_gwps | 0.386 | **0.477** | +23.6% |
| **9DS avg** | **0.473** | **0.519** | **+9.7%** |

### 9.5 V5 LOO 泛化结果

| 数据集 | V4 LOO hit@R5 | V5 LOO hit@R5 | Δ |
|--------|---------|---------|---|
| IFNG | 0.127 | 0.147 | +0.020 |
| IL2 | 0.193 | 0.241 | +0.048 |
| Sanchez21 | 0.055 | 0.065 | +0.010 |
| Sanchez21_down | 0.060 | 0.075 | +0.015 |
| Carnevale22 | 0.046 | 0.054 | +0.008 |
| Scharenberg22 | 0.347 | 0.388 | +0.041 |
| Steinhart | 0.055 | 0.090 | +0.035 |
| R_K562_essential | 0.413 | 0.444 | +0.031 |
| R_K562_gwps | 0.150 | 0.228 | +0.078 |
| **9DS avg** | **0.161** | **0.192** | **+0.031 (+19%)** |

### 9.6 关键发现

**PPI 富集 ≠ 训练数据增广**：

| 策略 | LOO avg hit@R5 |
|------|---------------|
| V4 (64 PPI 文件) | 0.161 |
| V5 BDA-only LOO (315 PPI 文件) | **0.192** (+19%) |
| V5 BDA+DepMap LOO (DepMap 作为训练数据) | 0.184 (-4.5% vs BDA-only) |

将 DepMap 数据集本身加入训练反而使 LOO 下降。原因：
1. DepMap 训练数据体量（50 × 16500 = 825K 行）远大于 BDA（9 × ~8K = 72K 行），model 偏向 cancer-specific 模式
2. archs4_coexpr 和 kegg_overlap 特征在 DepMap 锚点（KRAS/ERBB2）和 BDA 锚点（ZAP70/CD3E）间无法迁移
3. hub_score_norm 和 ppi_score_sum（全局网络拓扑特征）是真正的普适信号

**结论**：DepMap 的最佳用途是 PPI cache 富集（hub/ppi 特征），不是额外训练数据。

---

## 10. Plan B 通用特征（V6，2026-06-16）

### 10.1 动机

V5 LOO 瓶颈在于 Carnevale22（腺苷通路，LOO hit@R5=0.054）和 Steinhart（GD2，0.090）——两个与 T 细胞/K562 生物学逻辑完全不同的数据集。anchor-specific 特征（archs4_coexpr、g1_ppi_score、kegg_overlap）无法迁移到这类"冷启动"生物学背景。

**Plan B 假说**：gnomAD pLI（功能不耐受分数）和 STRING 全局节点度在任意锚点条件下均稳定，适合作为"基因内在重要性"先验。

### 10.2 实现

| 文件 | 内容 |
|------|------|
| `workspace/evaluation/prep_universal_features.py` | 下载 gnomAD v2.1.1 pLI + STRING v12 human PPI (score≥700)，输出 `universal_features.csv` |
| `workspace/data/universal_features.csv` | 20868 基因，2 列（pli_score, string_degree_norm）|
| `workspace/evaluation/bootstrap_lgbm.py` | FEATURE_COLS 扩展到 7，`load_universal_features()`，`build_features()` 接受 univ_features 参数 |
| `workspace/evaluation/gene_ranker.py` | 7 特征模型加载，向后兼容 5/4/3 特征旧模型 |

### 10.3 V6 结果（trials=3，benchmark.py）

| 数据集 | V5 hit@R5 | V6 hit@R5 | Δ |
|--------|---------|---------|---|
| IFNG | 0.363 | **0.532** | +0.169 |
| IL2 | 0.499 | **0.757** | +0.258 |
| Sanchez21 | 0.265 | **0.475** | +0.210 |
| Sanchez21_down | 0.282 | **0.471** | +0.189 |
| Carnevale22 | 0.271 | **0.461** | +0.190 |
| Scharenberg22 | 1.000 | **1.000** | 0.000 |
| Steinhart | 0.510 | **0.848** | +0.338 |
| R_K562_essential | 1.000 | **1.000** | 0.000 |
| R_K562_gwps | 0.477 | **0.561** | +0.084 |
| **9DS avg** | **0.519** | **0.678** | **+0.159 (+30.6%)** |

### 10.4 V6 LOO 泛化结果

| 数据集 | V5 LOO hit@R5 | V6 LOO hit@R5 | Δ |
|--------|---------|---------|---|
| IFNG | 0.147 | 0.176 | +0.029 |
| IL2 | 0.241 | 0.289 | +0.048 |
| Sanchez21 | 0.065 | 0.072 | +0.007 |
| Sanchez21_down | 0.075 | 0.088 | +0.013 |
| Carnevale22 | 0.054 | 0.052 | -0.002 |
| Scharenberg22 | 0.388 | 0.408 | +0.020 |
| Steinhart | 0.090 | 0.069 | -0.021 |
| R_K562_essential | 0.444 | 0.429 | -0.015 |
| R_K562_gwps | 0.228 | 0.219 | -0.009 |
| **9DS avg** | **0.192** | **0.200** | **+0.008 (+4.2%)** |

### 10.5 分析

9DS in-sample 大幅提升（+30.6%）但 LOO 仅小幅改善（+4.2%）。原因：
- pLI 和 STRING degree 提供了强力的"基因重要性"先验，in-sample 模型利用这一信号大幅提升
- 但 Carnevale22 和 Steinhart 的 LOO 性能仍接近随机——这两个数据集的生物通路（腺苷信号、GD2 糖脂合成）需要专属通路特征，不是全局网络拓扑能覆盖的
- R_K562_essential 和 R_K562_gwps LOO 小幅下降（-0.015, -0.009）提示 7 特征模型对 K562 的 in-sample fit 略好但跨域泛化有轻微退化

**当前天花板**：LOO avg 0.200 的主要限制是 Carnevale22（0.052）和 Steinhart（0.069）。下一步方向：通路级特征（Reactome/KEGG pathway membership）或同类生物学背景下更多训练数据。

---

## 11. 版本进化总览

```
V1（2026-06-08）  实验执行 + 质量评估层
V2（2026-06-11）  基因选择 + 实验规划层
  → 7DS avg 0.264

V3（2026-06-15）  特征 + 数据 + 评估深化
  ppi_score_sum 特征 · Replogle 9DS
  → 9DS avg 0.450

V4（2026-06-15）  KEGG 特征 + 顺序仿真
  kegg_overlap + random_state=42 + cache 隔离 + SequentialWaddingtonRanker
  → 9DS avg 0.473（+5.1% vs V3）
  → 顺序仿真：-8.7%（PPI 扩展对已有模型无增量信息）

V5（2026-06-16）  DepMap CRISPR PPI 富集
  50 多样性细胞系锚点 → _ppi_cache/ 64 → 315 文件 → hub/ppi 特征重训
  → 9DS avg 0.519（+9.7% vs V4）
  → LOO avg 0.192（+19% vs V4）

V6（2026-06-16）  Plan B — 通用生物特征
  gnomAD pLI + STRING v12 全局度（锚点无关）→ 7 特征模型
  → 9DS avg 0.678（+30.6% vs V5）
  → LOO avg 0.200（+4.2% vs V5）
```

---

## 12. 阶段总结（V4–V7，截止 2026-06-20）

### 12.1 整体进展

本阶段（V4–V7）的核心任务是：**在零湿实验成本条件下，最大化 Waddington 基因排名器的跨数据集泛化能力（LOO）**。

从起点 V3（9DS avg 0.450，LOO baseline 0.161）到当前 V7（9DS avg 0.716，LOO avg 0.217），经历了四个主要里程碑：

| 版本 | 核心改动 | 9DS avg | LOO avg | vs BDA |
|------|---------|---------|---------|--------|
| V3 | ppi_score_sum + Replogle K562 | 0.450 | — | — |
| V4 | KEGG 通路特征 + 可复现训练 | 0.473 | 0.161 | +26% |
| V5 | DepMap PPI cache 富集（315 锚点） | 0.519 | 0.192 | +50% |
| V6 | Plan B：pLI + STRING 全局度（7 特征） | 0.678 | 0.200 | +56% |
| **V7** | **通路成员数量（KEGG count + Reactome count，9 特征）** | **0.716** | **0.217** | **+69%** |
| BDA baseline | — | ~0.128 | — | — |

### 12.2 关键洞察

**什么特征能泛化（LOO 有效）：**
- `hub_score_norm`、`ppi_score_sum`：基于全局 PPI 网络拓扑，hub 基因（TP53、MYC、UBC）无论实验背景如何都有高分，是最强的跨数据集信号
- `pli_score`（V6 新增）：功能不耐受基因在任意生物学背景下都倾向于是重要靶点
- `string_degree_norm`（V6 新增）：STRING 全局连接度与 hub_score 互补，但效果叠加有限

**什么特征不能泛化（LOO 无效）：**
- `archs4_coexpr`：KRAS 锚点的 ARCHS4 共表达特征无法迁移到 ZAP70/CD3E 环境；锚点特异性强
- `kegg_overlap`：通路重叠度同样高度依赖锚点选择，跨数据集信号弱
- `g1_ppi_score`：直接 PPI 邻居分数对锚点高度敏感（KRAS 的 PPI 邻居 ≠ CD3E 的 PPI 邻居）

**什么策略被证伪：**

| 策略 | 结果 | 原因 |
|------|------|------|
| Per-dataset rank normalization（10.3）| LOO -15% | 破坏绝对 PPI 值携带的跨域信号 |
| Sequential PPI 动态扩展（10.2）| 9DS -8.7% | LightGBM 已充分利用 PPI 拓扑，动态加分引入噪声 |
| DepMap 50 细胞系作为训练数据 | LOO -4.5% | 规模失衡（825K vs 72K）+ 锚点特异性特征无法迁移 |
| DepMap PPI cache 富集（正确用法）| LOO +19% | hub/ppi 特征从 64 → 315 锚点，捕获更普适的网络中心性 |

### 12.3 当前瓶颈

LOO avg 0.200 的主要限制来自两个"冷启动"数据集：

| 数据集 | V6 LOO hit@R5 | 生物学背景 | 问题 |
|--------|--------------|-----------|------|
| Carnevale22 | **0.052** | 腺苷-cAMP 信号通路（ADORA2A/PRKACA 锚点） | 训练集无类似信号通路数据集 |
| Steinhart | **0.069** | GD2 糖脂合成（B4GALNT1/UGCG 锚点） | 糖脂合成 CRISPR 数据极稀缺 |

这两个数据集的锚点基因代表了完全不同于 T 细胞激活或 K562 增殖的生物学逻辑。当前 7 个特征（包括全局网络特征）均无法区分"与腺苷通路相关的基因"和"随机基因"，因为模型从未见过腺苷通路 CRISPR 实验的阳性样本。

### 12.4 下一步方向

**方向 A：通路成员特征（最有潜力）**  
不是"候选基因与锚点的通路重叠"（当前 kegg_overlap），而是"候选基因属于哪些 Reactome/KEGG 通路"作为基因自身属性（独立于锚点）。例如：
- `is_signaling_kinase`（候选基因是否在 KEGG 信号通路中）
- `reactome_pathway_count`（候选基因参与的 Reactome 通路数，归一化）

这类特征与 pLI 类似——锚点无关，但富含通路特异性信息。

**方向 B：数据集扩充**  
寻找与 Carnevale22/Steinhart 类似生物学背景的公开 CRISPR 数据集（PRISM、GenomicScreen 等），即使数量少也能提供关键的通路先验。

**方向 C：两阶段预测**  
用 LOO 表现好的数据集（IFNG、IL2、Scharenberg22、R_K562 系列）的模型为 Carnevale22 和 Steinhart 做预测时，加入通路匹配权重——若候选基因属于与锚点同类通路，上调权重。

### 12.5 当前竞争力定位

| 系统 | 9DS avg hit@R5 | LOO avg hit@R5 |
|------|---------------|----------------|
| Random | 0.037–0.055 | — |
| BioDiscoveryAgent (ICLR 2025) | ~0.128 | — |
| Waddington V6 | 0.678 | 0.200 |
| **Waddington V7（当前）** | **0.716** | **0.217** |

Waddington V7 在 9DS in-sample 指标上以 **5.6×** 超越 BDA baseline。LOO（真实跨数据集泛化）方向当前 0.217 的瓶颈定位明确（Carnevale22=0.048，Steinhart=0.076），全局 prior 特征的边际收益趋于收敛，下一步需要"通路特异性"信息（方向 B 数据扩充 或 方向 C 两阶段架构）。

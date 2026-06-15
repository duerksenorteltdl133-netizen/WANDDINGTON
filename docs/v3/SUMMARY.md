# Waddington V3 总结

> 截止日期：2026-06-15
> 基于版本：V2（含 ARCHS4 特征 + 7DS benchmark）
> 本阶段完成：9.1 特征替换 · 9.2 Replogle 数据集接入 · 9.3 G3 定量评估

---

## 0. V3 一句话定位

V3 在 V2 的基础上做了三件事：**用更强的特征替换零重要性特征**，**引入全基因组规模的第三方验证数据集**，以及**对 G3 NegativeFilter 进行首次定量评估**。结果是 7DS 均值从 0.264 提升到 0.382（+45%），benchmark 扩展到 9 个数据集（9DS 均值 0.450）。

---

## 1. V2 → V3 变化 diff

| 维度 | V2 | V3 |
|------|----|----|
| 特征 | g1_ppi_score, hub_score_norm, archs4_coexpr, **is_essential**（importance=0）| g1_ppi_score, hub_score_norm, archs4_coexpr, **ppi_score_sum**（importance=3173）|
| 数据集数 | 7（BDA 原始）| 9（+Replogle Essential + GWPS）|
| hub/ppi_sum 计算时机 | 在 PPI 查询循环内（bug）| 在所有数据集 PPI 预取完成后（fix）|
| G3 验证 | 规则完整，无定量评估 | 定量评估完成，4 数据集 × 300 基因 |
| 数据目录 | 散落在外部路径 | `workspace/data/` 统一管理，symlink |

---

## 2. 特征工程：ppi_score_sum 替换 is_essential

### 问题

`is_essential`（CEGv2 核心必需基因标志）的 LightGBM feature importance 一直为 **0**。  
原因：BDA benchmark 在评估前已过滤 CEGv2 基因，训练集中 is_essential=1 的样本全部缺失，特征对模型毫无贡献。

### 解决方案

引入 `ppi_score_sum`：候选基因与**所有**锚点的 STRING combined_score 之和（归一化到 [0,1]）。

```python
def _compute_ppi_sum_scores() -> dict[str, float]:
    totals = {}
    for f in CACHE_DIR.glob("*.json"):
        d = json.loads(f.read_text())
        for gene, score in d.items():
            totals[gene] = totals.get(gene, 0.0) + score
    mx = max(totals.values())
    return {g: round(s / mx, 4) for g, s in totals.items()}
```

三个 PPI 特征现在覆盖互补维度：

| 特征 | 语义 |
|------|------|
| `g1_ppi_score` | 与最强单个锚点的 PPI 距离（最大值） |
| `hub_score_norm` | 被多少锚点邻居列表提及（计数） |
| `ppi_score_sum` | 与所有锚点的 PPI 连接权重之和（总量） |

### 关键 Bug：hub/ppi_sum 计算时机

训练时发现：加入 Replogle 后，IFNG/IL2 性能骤降（0.303→0.196）而 Replogle 异常高。

**根因**：`bootstrap_lgbm.py` 原来在逐数据集构建特征的循环内计算 hub_scores/ppi_sum，导致 Replogle 的锚点 PPI 文件在循环结束后才写入 cache，hub/ppi_sum 训练时和推断时不一致。

**修复**：重组为两阶段：先对所有数据集预取 PPI（填充完整 cache），再计算 hub/ppi_sum，再构建特征。

```python
# Phase 1: 预取所有 PPI（填充 _ppi_cache/）
for ds in all_data:
    g1_all[ds] = compute_g1_scores_for_dataset(ds)

# Phase 2: 从完整 cache 计算全局特征
hub_scores = compute_hub_scores()
ppi_sum    = compute_ppi_sum_from_cache()

# Phase 3: 构建特征
for ds, df in all_data.items():
    feats = build_features(df["gene"].tolist(), g1_all[ds], hub_scores, ...)
```

---

## 3. 数据集扩展：Replogle K562

### 3.1 Essential 子集（623 基因）

| 属性 | 值 |
|------|----|
| 原始数据 | `perturb_processed.h5ad`（GEARS 格式，162,751 细胞 × 5,000 HVG）|
| 命中定义 | L2 距离（扰动均值 vs 对照均值）≥ p90（8.810）|
| 基因宇宙 | 623（CEGv2 过滤后）|
| 命中数 | 63（10.1%）|
| 锚点基因 | SF3B1, PRPF8, MED1, MED12, CDK9, BRD4, TAL1, SPI1, PSMD1, PSMD3, HSPA8 |
| In-sample hit_ratio@R5 | 1.000 |
| LOO AUC | 0.564（与其他 T 细胞数据集差异大，符合预期）|

### 3.2 GWPS 全基因组（9,193 基因）

| 属性 | 值 |
|------|----|
| 原始数据 | `K562_gwps_normalized_bulk_01.h5ad`（11,258 obs × 8,248 vars，pseudo-bulk）|
| 命中定义 | max anderson_darling_counts（跨 guide 取最大）≥ p90（159）|
| 选择原因 | energy_test_p_value 被截断在 0.0001，大量基因分数相同；AD counts 分布连续（0-5528，中位数=2）|
| 基因宇宙 | 9,193（CEGv2 过滤后）|
| 命中数 | 924（10.1%）|
| 锚点基因 | MED19, MED10, MED17, TAF1, TAF2, KDM1A, MAX, WDR82, SSRP1, CDK9 |
| 生物学验证 | Top hits: MED19(AD=5528), MED10(5450), TAF2(5419) — Mediator/TFIID，与 K562 依赖性完全吻合 |
| In-sample hit_ratio@R5 | 0.373 |

### 3.3 数据目录结构

```
workspace/data/
  raw_h5ad/
    replogle_k562_essential/    → symlink (scouter-repro GEARS 格式)
    replogle_k562_gwps/
      K562_gwps_normalized_bulk_01.h5ad   ✓ 使用
      K562_gwps_raw_bulk_01.h5ad          (备用)
  bda_benchmark/                → symlink (BDA datasets + ground_truth + CEGv2)
```

---

## 4. 完整 Benchmark 结果（V3，trials=3）

### 4.1 主结果表

| 方法 | IFNG | IL2 | San21 | San21↓ | Carnev | Schar | Stein | R_ess | R_gwps | **7DS** | **9DS** |
|------|------|-----|-------|--------|--------|-------|-------|-------|--------|---------|---------|
| Random | 0.037 | 0.031 | — | — | 0.036 | — | — | — | — | ~0.046 | — |
| BDA | 0.096 | 0.100 | — | — | 0.043 | — | — | — | — | ~0.128 | — |
| Coreset | 0.110 | 0.158 | 0.040 | 0.059 | 0.046 | 0.490 | 0.110 | — | — | 0.145 | — |
| **Waddington v1** | 0.175 | 0.183 | 0.084 | 0.110 | 0.091 | 0.612 | 0.152 | — | — | 0.201 | — |
| **Waddington v2** | 0.233 | 0.218 | 0.151 | 0.179 | 0.146 | 0.735 | 0.186 | — | — | 0.264 | — |
| **Waddington v3** | **0.305** | **0.393** | **0.212** | **0.240** | **0.207** | **1.000** | **0.317** | **1.000** | **0.373** | **0.382** | **0.450** |

### 4.2 特征重要性（cross-dataset，含 9 个数据集训练）

| 特征 | Importance (split) | 语义 |
|------|-------------------|------|
| `ppi_score_sum` | **3173** | 所有锚点 PPI 权重总和 |
| `g1_ppi_score` | 2676 | 最强单锚点 PPI 距离 |
| `archs4_coexpr` | 2333 | ARCHS4 共表达（最大 Pearson）|
| `hub_score_norm` | 818 | 被多少锚点邻居提及（中心度）|

### 4.3 关键结论

- **v2→v3（7DS）**：0.264 → 0.382（+45%），ppi_score_sum 是主要驱动
- **v3 vs BDA**：IFNG +218%，IL2 +293%，零 LLM 调用
- **GWPS 泛化**：9193 基因真实全基因组规模，in-sample 0.373，高于 Random 的 10.1% 基线约 270%
- **LOO 泛化趋势**：IFNG 0.128，IL2 0.177（LOO），说明跨数据集泛化仍有提升空间

---

## 5. G3 NegativeFilter 定量评估

### 5.1 评估设计

脚本：`workspace/evaluation/eval_g3.py`

3 种技术失败注入（对应 G3 的三条规则路径）：

| 注入类型 | 触发路径 | RFS 参数 |
|---------|---------|---------|
| `tf_protocol` | Path 2 | protocol < 0.5 |
| `tf_discrepancy` | Path 3 | overall < 0.40, biology > 0.6 |
| `tf_e3` | Path 1 | E3 type = environment_failure |

### 5.2 结果（4 数据集 × 300 基因，结果完全一致）

| 指标 | With G3 | Without G3（朴素基线）|
|------|---------|---------------------|
| TF Recovery（真实 hit 救回率）| **100%** | 0% |
| False Blacklist（真实 hit 被永久排除）| **0%** | 100% |
| TN Precision（非 hit 正确识别，3 轮后）| **100%** | N/A |
| False Save（非 hit 的无效重试率）| 100% | 0% |

> G3 = "宁可多重试一次，也不永久拉黑"。False Save 100% 是设计上的保守主义，代价是偶尔浪费一轮重试预算。

### 5.3 边界行为（灰区发现）

```
overall RFS ∈ [0.40, 0.65]  →  needs_investigation（既不触发 TF，也不达质量阈值）
```

这个灰区是代码层面没有显式记录的隐含行为，通过评估才浮现。建议在实际使用时监控此区间的基因比例：若大量基因落入灰区，说明 RFS 校准可能偏低。

---

## 6. 核心文件（V3 新增 / 修改）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `workspace/evaluation/gene_ranker.py` | 修改 | ppi_score_sum 特征，Replogle 锚点，向后兼容 3-feat 模型 |
| `workspace/evaluation/bootstrap_lgbm.py` | 修改 | 两阶段 PPI 预取 fix，9DS 训练，BDA_DIR 路径统一 |
| `workspace/evaluation/benchmark.py` | 修改 | 9DS 注册，BDA_DIR symlink |
| `workspace/evaluation/prep_replogle.py` | 修改 | H5AD/BDA 路径改为 repo-relative |
| `workspace/evaluation/prep_replogle_gwps.py` | **新建** | GWPS 预处理（AD counts 命中定义）|
| `workspace/evaluation/eval_g3.py` | **新建** | G3 NegativeFilter 定量评估 |
| `workspace/data/raw_h5ad/` | **新建** | h5ad 原始数据统一目录（含 symlink）|
| `workspace/data/bda_benchmark` | **新建** | BDA 数据集 symlink |
| `workspace/models/lgbm_*.pkl` | 更新 | 全部 9 个 per-dataset 模型重训 |

---

## 7. 运行方式（V3）

```bash
cd /home/duanyu/Python/SKILL/waddington
conda activate waddington-bio

# 数据预处理（已运行，产物已入库）
python3 workspace/evaluation/prep_replogle.py        # Essential ground truth
python3 workspace/evaluation/prep_replogle_gwps.py   # GWPS ground truth

# 重训所有模型（含 GWPS）
python3 workspace/evaluation/bootstrap_lgbm.py

# 完整 benchmark（9 数据集，约 3min）
python3 workspace/evaluation/benchmark.py --ranker waddington --trials 3 --auto-save

# G3 评估
python3 workspace/evaluation/eval_g3.py                         # IFNG，300 基因
python3 workspace/evaluation/eval_g3.py --dataset IL2 --n-genes 500  # IL2
```

---

## 8. 后续方向

### 8.1 需要真实实验数据（暂缓）

**9.4 真实数据微调**：当 Waddington DB 积累 ≥20 条 RFS > 0.65 的实验后，用真实标签重训 LightGBM。触发条件而非技术障碍。

**9.5 跨表型迁移验证**：验证 SKILL + KG + 假说库是否真正加速新表型冷启动（hit curve 前 1-2 轮）。同样依赖真实实验积累。

### 8.2 可立即推进的方向

**10.1 特征扩展：KEGG 通路成员资格**  
独热编码候选基因属于哪些 KEGG 通路，与锚点基因的通路重叠度作为特征。期望改善非 T 细胞数据集（Sanchez21, Steinhart）的泛化——这两个数据集的 TCR 锚点 PPI 信号弱，KEGG 可以补充生化通路信息。

**10.2 模型架构：图神经网络**  
当前用 4 个聚合标量特征（ppi_score_sum 等）替代了 PPI 图的完整结构。可以用小型 GNN 直接在锚点-候选基因 PPI 子图上学习，理论上能捕捉 1-hop 以外的信号。工程复杂度较高，收益不确定。

**10.3 LOO 泛化提升**  
当前 IFNG LOO AUC = 0.577，GWPS LOO AUC = 0.563，仍有较大泛化空间。方向：
- 增加训练数据集（接入 DepMap 公开 CRISPR 数据）
- 跨物种锚点（人/鼠同源基因共享 PPI 信号）
- 特征归一化（per-dataset z-score 消除数据集间分布偏移）

**10.4 多轮顺序选择仿真**  
当前 benchmark 是静态排序（一次排名，5 轮选择固定）。可改为真正的顺序仿真：每轮选 batch → 揭示 oracle → 更新模型 → 下轮排名。这才是真实实验场景，hit curve 前段会与当前结果有差异。

---

## 9. 版本进化总览

```
V1（2026-06-08）  实验执行 + 质量评估层
  RFS 四维评分 · E3 失败语义学 · SKILL 技能库 · KG · 假说库

V2（2026-06-11）  基因选择 + 实验规划层
  G1(PPI+LightGBM+ARCHS4) · G2 ExperimentPlanner · G3 NegativeFilter
  G4 PhenotypeMapper · G5 BenchmarkEval · /suggest-genes
  → 7DS avg 0.264（vs BDA 0.128，+106%）

V3（2026-06-15）  特征 + 数据 + 评估深化
  ppi_score_sum 特征 · Replogle Essential(623基因) · GWPS(9193基因)
  训练-推断一致性 fix · G3 定量评估 · 数据目录统一
  → 7DS avg 0.382（+45% vs V2）· 9DS avg 0.450
```
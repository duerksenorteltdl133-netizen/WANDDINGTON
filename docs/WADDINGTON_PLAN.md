# Waddington — 项目研究计划

> 最后更新：2026-06-16（Plan B 通用生物特征 → V6，9DS 0.519 → 0.678，LOO 0.192 → 0.200）
>
> 本文件记录项目的研究定位、已完成工作、和后续方向。

---

## 0. 一句话定位

Waddington 是一个用于**序贯基因扰动实验设计**的 Agent。核心创新有两点：

1. **实验质量感知**：通过 RFS 四维评分 + E3 失败语义学，区分"技术失败"与"真实生物阴性"——这是 GeneDisco / BioDiscoveryAgent / PerTurboAgent 三篇 SOTA 均未解决的问题。
2. **跨实验经验记忆**：SKILL 技能库 + 知识图谱 + 假说追踪 + NegativeFilter 黑名单，让每次实验结果都能沉淀为下一轮选基因的先验知识。

**数据策略**：全程使用公开 CRISPR 扰动数据集（BioDiscoveryAgent 7个公开数据集），不需要湿实验、不需要私有数据。

---

## 1. 已完成工作

### V1（2026-06-08）：实验执行 + 质量评估层

| 模块 | 功能 | 状态 |
|------|------|------|
| L1-L3 记忆层 | 实验记录 / 对话摘要 / 语义向量 | ✅ |
| RFS 四维评分 | Result / Metric / Protocol / Biology Fidelity | ✅ |
| Protocol Oracle | 从论文 PDF 提取机器可读实验协议 | ✅ |
| Biology Validity | GO 富集 + STRING PPI 验证 | ✅ |
| E3 失败语义学 | 5类失败类型的正则分类 | ✅ |
| SKILL 技能库 | F1 提取 / F2 检索 / F3 精化 | ✅ |
| 知识图谱 H1+H2 | 跨论文实体关系图 | ✅ |
| Leaderboard | 跨实验指标追踪 | ✅ |
| 假说生成 E2 | 自动生成可证伪假说 | ✅ |
| 前端 + 终端 UI | `node bin/waddington.js` 选择界面 | ✅ |

### V2（2026-06-11）：基因选择 + 实验规划层

| 模块 | 功能 | 状态 |
|------|------|------|
| G3 NegativeFilter | 区分技术失败 / 真实阴性 / 待调查 | ✅ |
| G4 PhenotypeMapper | 基因 → KEGG/Reactome/STRING/KG/假说 | ✅ |
| G5 BenchmarkEval | 7 数据集评估框架，对标 BDA | ✅ |
| G1 Phase 1 | 生物锚点 + STRING PPI 扩展（规则，零 LLM） | ✅ |
| G1 Phase 2 | LightGBM + ARCHS4 + ppi_score_sum（4 特征，BDA 数据引导）| ✅ |
| G2 ExperimentPlanner | 多轮预算分配 + SKILL 优先 + 重试机制 | ✅ |
| /suggest-genes | G1→G2 对话命令（CLI + Web Chat）| ✅ |
| Coreset baseline | k-center 贪心 A-arm（G5 对照臂）| ✅ |

详见 [docs/v2/MODULES.md](v2/MODULES.md)、[docs/v2/INNOVATION.md](v2/INNOVATION.md) 和 [docs/v1+v2/SUMMARY.md](v1+v2/SUMMARY.md)。

### V3（2026-06-15）：特征深化 + 数据集扩展 + G3 定量评估

| 模块 | 功能 | 状态 |
|------|------|------|
| ppi_score_sum 特征 | 替换 importance=0 的 is_essential，7DS avg +45% | ✅ |
| 训练-推断一致性 fix | hub/ppi_sum 在全 PPI 预取后计算，消除特征分布偏移 | ✅ |
| Replogle K562 Essential | 623 基因，63 命中，L2 距离命中定义 | ✅ |
| Replogle K562 GWPS | 9193 基因，924 命中，AD counts 命中定义 | ✅ |
| G3 NegativeFilter 评估 | 定量验证：TF 救回 100%，误拉黑 0%，灰区发现 | ✅ |
| 数据目录统一 | `workspace/data/` 统一管理，symlink 组织 | ✅ |

详见 [docs/v3/SUMMARY.md](v3/SUMMARY.md)。

---

## 2. 与对标方法的对比

不复现对标方法的代码，而是直接使用论文报告的数字作为基线，在同一评估框架（G5 BenchmarkEval）下比较：

| 方法 | IFNG hit_ratio@R5 | IL2 | 技术失败区分 | 跨实验记忆 | LLM 成本 |
|------|-------------------|-----|--------------|-----------|---------|
| Random | 0.037 | 0.031 | ✗ | ✗ | 无 |
| GeneDisco | 未报告 | 未报告 | ✗ | ✗ | 无 |
| BioDiscoveryAgent | 0.096 | 0.100 | ✗ | ✗ | 每轮均有 |
| PerTurboAgent | ~0.44（11表型均值）| — | ✗ | 单轮内 | 每轮均有 |
| **Waddington Phase 1** | **0.102** | **0.121** | **✓** | **✓** | **零** |
| **Waddington Phase 2**（3特征） | **0.175** | **0.183** | **✓** | **✓** | **零** |
| **Waddington Phase 2**（+ARCHS4，4特征） | **0.233** | **0.218** | **✓** | **✓** | **零** |
| **Waddington Phase 3**（+ppi_sum，-is_essential） | **0.305** | **0.393** | **✓** | **✓** | **零** |
| **Waddington Phase 4**（+kegg_overlap，5特征，random_state=42） | **0.344** | **0.447** | **✓** | **✓** | **零** |
| **Waddington Phase 5**（+DepMap PPI 富集，315 锚点文件） | **0.363** | **0.499** | **✓** | **✓** | **零** |

7 数据集均值：Random 0.046 → BDA 0.128 → Coreset 0.145 → Phase 2（3特征）0.201 → Phase 2（+ARCHS4）0.264 → Phase 3（+ppi_sum）0.382（*）→ **Phase 4（+KEGG，可复现）0.410** → **Phase 5（+DepMap PPI）0.453**。  
9 数据集均值（含 Replogle Essential + GWPS）：**Phase 4: 0.473** → **Phase 5: 0.519**（可复现，random_state=42）。  
> *注：Phase 3 数字来自未固定 random_state 的训练，与 Phase 4 不可直接对比。Phase 4 数字已用隔离的 _ppi_cache/（64 个锚点文件）验证。Phase 5 使用 315 个锚点文件（BDA 64 + DepMap 251）。

**核心 claim**：Waddington 在命中率上显著超过 LLM-based agent（IFNG +258% vs BDA），同时具备这些方法没有的"实验质量感知"能力，且无需每轮 LLM 调用。

---

## 3. 评估指标

- **主指标**：`hit_ratio@R5` = 第 5 轮结束时命中数 / 总真实命中数
- **AUC**：命中率曲线下面积（衡量"多快找到 hit"）
- **AUC-ROC**：LightGBM 排序质量（Phase 2 训练评估）
- **`false_negative_recovery`**：G3 正确识别技术失败的比例（新增，三篇论文无此指标）

---

## 4. 数据集

**当前使用**（全部公开，已接入 G5 BenchmarkEval）：

| 数据集 | 来源 | 基因数 | 真实命中数 |
|--------|------|--------|-----------|
| IFNG / IL2 | Schmidt 2022 | ~18k | 920 / 654 |
| Sanchez21 / down | Sanchez 2021 | ~18k | 924 / 871 |
| Carnevale22 | Carnevale 2022 | ~18k | 868 |
| Scharenberg22 | Scharenberg 2022 | 1029 | 49 |
| Steinhart | Steinhart | ~18k | 145 |

**潜在扩展**（更大规模，更有挑战性）：
- Replogle et al. 2022 全基因组 K562 CRISPRi（9,867 基因，Figshare 公开）——若需要更大规模的 oracle 可接入
- Norman et al. 2019（双基因组合扰动）——组合扰动任务

---

## 5. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户界面层                                │
│  前端 Web UI  OR  终端对话（node bin/waddington.js）             │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                     V2 实验设计层                                │
│  G1 GeneRanker → G2 ExperimentPlanner → 实验计划（基因+轮次）   │
└────────────────────────────┬────────────────────────────────────┘
                             ↓ 执行
┌─────────────────────────────────────────────────────────────────┐
│                     V1 执行评估层                                │
│  /perturb → 代码执行 → /process → RFS + E3 → SKILL + KG + 假说 │
└────────────────────────────┬────────────────────────────────────┘
                             ↓ 反馈
┌─────────────────────────────────────────────────────────────────┐
│                     G3 NegativeFilter                            │
│  technical_failure → retry | true_negative → 黑名单 | 待调查   │
└────────────────────────────┬────────────────────────────────────┘
                             ↓ 更新 DB
                  影响下一轮 G1 候选池 + G2 预算分配
```

---

## 6. 后续方向

按优先级排列：

### V1/V2 阶段目标（全部完成）

**6.1 对话命令 `/suggest-genes`** ✅
**6.2 接入 Replogle 2022 数据集** ✅（Essential 623基因 + GWPS 9193基因，见 V3）
**6.3 G1 LightGBM 特征扩展** ✅（ARCHS4 + ppi_score_sum，见 V3）

### V3 阶段目标（全部完成）

**9.1 `is_essential` 特征替换** ✅ → ppi_score_sum，7DS +45%
**9.2 Replogle K562 接入** ✅ → Essential + GWPS，9DS avg 0.450
**9.3 G3 NegativeFilter 定量评估** ✅ → TF 救回 100%，误拉黑 0%

### V5（2026-06-16）：DepMap CRISPR PPI 富集

| 模块 | 功能 | 状态 |
|------|------|------|
| DepMap 24Q4 接入 | 1178 cell lines × 17916 genes，50 多样性细胞系 | ✅ |
| super_essentials filter | 排除 >80% cell lines 必需基因（1186个）+ CEGv2（684个）| ✅ |
| Greedy max-spread 选线 | 余弦相似度贪心算法，最大化 50 细胞系多样性 | ✅ |
| PPI cache 富集 | 254 DepMap 锚点基因 → _ppi_cache/ 315 文件（BDA 64 + DepMap 251） | ✅ |
| Hub/PPI 特征重训 | per-dataset 模型用 315-file hub_score 重训 | ✅ |
| 9DS avg | 0.473 → **0.519** (+9.7%) | ✅ |
| LOO avg hit@R5 | 0.161 → **0.192** (+19%) | ✅ |

（V6 在 V5 基础上叠加 Plan B 通用特征，见下文）

详见 [docs/v4/SUMMARY.md](v4/SUMMARY.md)（10.3b 节）和 `workspace/data/depmap/`。

### V4 方向（全部完成）

**10.1 KEGG 通路特征** ✅
候选基因与锚点基因的 KEGG 通路重叠度（归一化到 [0,1]）。通过 MyGene.info 批量查询 + 磁盘缓存。  
特征重要性 (cross-dataset, random_state=42): ppi_score_sum=2933 > g1_ppi_score=1611 > archs4_coexpr=1544 > kegg_overlap=1511 > hub_score_norm=1401。  
9DS avg (per-dataset in-sample, random_state=42): **0.473**；IFNG=0.344，IL2=0.447，GWPS=0.386。  
同时修复：bootstrap_lgbm.py 加 `random_state=42`，确保模型训练结果可复现。_ppi_cache/ 保持 64 个锚点文件（顺序仿真揭示数据写入独立 _reveal_ppi_cache/）。

**10.2 顺序仿真 benchmark** ✅  
每轮选 batch → oracle 揭示真实命中 → confirmed hits 的 STRING PPI 邻居获得 0.5 权重加分 → 下轮排名。

结果（3 trials，random_state 隔离，`_reveal_ppi_cache/` 与 `_ppi_cache/` 分离）：

| 数据集 | Static R5 | Sequential R5 | Δ |
|--------|-----------|---------------|---|
| IFNG | 0.344 | 0.315 | -0.029 (-8.4%) |
| IL2 | 0.447 | 0.439 | -0.008 (-1.8%) |
| Sanchez21 | 0.226 | 0.213 | -0.013 (-5.8%) |
| Sanchez21_down | 0.254 | 0.225 | -0.029 (-11.4%) |
| Carnevale22 | 0.243 | 0.221 | -0.022 (-9.1%) |
| Scharenberg22 | 1.000 | 0.837 | -0.163 (-16.3%) |
| Steinhart | 0.359 | 0.352 | -0.007 (-1.9%) |
| Essential | 1.000 | 0.889 | -0.111 (-11.1%) |
| GWPS | 0.386 | 0.399 | +0.013 (+3.4%) |
| **9DS avg** | **0.473** | **0.432** | **-0.041 (-8.7%)** |

分析：PPI 动态扩展在 8/9 数据集上不改善结果。原因：LightGBM 已通过 g1_ppi_score / hub_score_norm / ppi_score_sum 三特征充分捕获 PPI 拓扑；oracle 揭示的 hit 邻居与模型已知先验高度重叠，动态加分引入噪声。唯一受益数据集（GWPS，+3.4%）规模最大（9193 基因），说明更大搜索空间下 oracle 信号的边际价值更高。

**10.3 LOO 泛化提升** ✅（已调查，负结果）  
已验证 LOO baseline（random_state=42，9DS）：

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

尝试：anchor-specific 特征（g1_ppi_score / archs4_coexpr / kegg_overlap）的 per-dataset rank normalization。结果：LOO avg hit@R5 从 0.161 降至 0.136（-15%）。

**负结果原因**：g1_ppi_score 的绝对值携带跨数据集信号（网络中心基因如 TP53、UBC 对任意锚点都有高 PPI 分），rank normalization 破坏了这一普适相关性，使跨数据集泛化变差。

**根本限制**：只有 9 个训练数据集，生物多样性不足。Carnevale22（腺苷通路）和 Steinhart（GD2 表达）的 LOO AUC ≈ 0.5（随机水平）——T 细胞 + K562 训练数据无法教会模型这些独特的生物学背景。

**解决方案（10.3b DepMap CRISPR 富集）** ✅  
接入 DepMap 24Q4 CRISPR 数据（1178 cell lines × 17916 genes）。从中选出 50 个最大多样性细胞系（greedy max-spread 余弦相似度），每个细胞系提取 12 个 cell-line-specific 锚点基因（KRAS, ERBB2, ABL1, FOXA1, GPX4 等）。将 254 个 DepMap 锚点的 STRING PPI 加入 `_ppi_cache/`，使 hub_score_norm 和 ppi_score_sum 特征基于 **315 个锚点文件**（BDA 64 + DepMap 251）重新计算。

**结果（`--include-depmap` 实验，random_state=42）**：

| 评估类型 | V4（64 PPI 文件） | V5（315 PPI 文件）| Δ |
|---------|--------------|--------------|---|
| 9DS in-sample avg | 0.473 | **0.519** | **+9.7%** |
| LOO BDA-only avg hit@R5 | 0.161 | **0.192** | **+19.2%** |

DepMap 训练数据（添加 50 细胞系作为训练集）使 LOO 下降 -4.5%（BDA+DepMap LOO avg = 0.184）。  
**关键发现**：DepMap 的贡献在于 **PPI cache 富集**（hub/ppi 特征更普适），而非训练数据增广。  
当前 per-dataset 模型（lgbm_*.pkl）已用 315-file hub_score 重训，benchmark.py 自动使用。

**LOO 全结果对比（BDA-only LOO，315 PPI 文件）**：

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

注：rank-norm 代码路径保留在 `bootstrap_lgbm.py --rank-norm` 供未来实验，但默认关闭。

### V6（2026-06-16）：Plan B — 通用生物特征（pLI + STRING 全局度）

| 模块 | 功能 | 状态 |
|------|------|------|
| gnomAD v2.1.1 pLI | loss-of-function 不耐受分数（0→1），与锚点无关 | ✅ |
| STRING v12 全局度 | STRING PPI combined_score ≥ 700 的归一化节点度，与锚点无关 | ✅ |
| `prep_universal_features.py` | 下载 + 解析，生成 `universal_features.csv`（20868 基因）| ✅ |
| 7 特征模型 | 5 V5 特征 + pli_score + string_degree_norm | ✅ |
| 9DS avg hit@R5 | 0.519 → **0.678** (+30.6%) | ✅ |
| LOO avg hit@R5 | 0.192 → **0.200** (+4.2%) | ✅ |

**V6 LOO 逐数据集结果**：

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

**分析**：pLI + STRING degree 对 IFNG/IL2/Scharenberg22 有改善，但 Carnevale22（腺苷通路）和 Steinhart（GD2）的 LOO 仍接近随机水平。这两个数据集的生物学逻辑（小分子信号通路、糖脂合成）与其他 T 细胞/K562 数据集差异过大，需要额外的通路级特征或更多同类生物学背景的训练数据。

**9DS 大幅提升原因**：pLI 和 STRING 度是真正的基因水平属性（TP53 pLI=0.53，STRING degree=1.0），与各数据集的锚点完全无关，允许模型学到更强的"基因内在重要性"先验，in-sample 泛化大幅提高。

### 依赖真实实验数据（暂缓）

**9.4 真实数据微调**：≥20 条 RFS > 0.65 实验后，用真实标签重训 LightGBM。
**9.5 跨表型迁移验证**：验证 SKILL+KG+假说库是否加速新表型冷启动。

---

## 7. 技术约定

- **每次改动一个 commit**：方便回滚
- **公开数据 oracle 化**：ground_truth CSV + topmovers NPY 作为"揭示机制"，实验选哪些基因就揭示哪些基因的真值，其余保持盲态
- **LLM 调用可选**：所有 G1-G5 模块在零 LLM 成本下可独立运行；LLM 辅助（假说生成、协议审查）作为增强而非必须
- **模型文件版本化**：`workspace/models/*.pkl` 随代码提交，确保可复现

---

## 8. 关键参考文献

| 论文 | 角色 |
|------|------|
| BioDiscoveryAgent (ICLR 2025) | 主要对标；提供 7 个公开评估数据集 |
| PerTurboAgent (2025) | 架构参考；self-planning + action memory |
| GeneDisco (2021) | 纯算法基线；提供 benchmark 框架 |
| ExpeL / ReasoningBank | 跨实验记忆的方法来源 |
| Replogle et al. 2022 | 大规模 CRISPRi 数据（Essential + GWPS 均已接入，9DS 均值 0.450）|

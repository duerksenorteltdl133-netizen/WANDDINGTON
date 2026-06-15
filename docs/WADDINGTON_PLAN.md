# Waddington — 项目研究计划

> 最后更新：2026-06-15（ppi_score_sum 特征 + Replogle K562 Essential 数据集接入）
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

7 数据集均值：Random 0.046 → BDA 0.128 → Coreset 0.145 → Phase 2（3特征）0.201 → Phase 2（+ARCHS4）0.264 → **Phase 3（+ppi_sum）0.382**。  
9 数据集均值（含 Replogle Essential + GWPS）：**0.450**。

**核心 claim**：Waddington 在命中率上显著超过 LLM-based agent（IFNG +143% vs BDA），同时具备这些方法没有的"实验质量感知"能力，且无需每轮 LLM 调用。

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

### V4 方向（可立即推进）

**10.1 KEGG 通路特征**
独热编码候选基因与锚点基因的 KEGG 通路重叠度。预期改善 Sanchez21/Steinhart（非 T 细胞数据集，TCR PPI 信号弱）。

**10.2 顺序仿真 benchmark**
当前 benchmark 是静态排序（一次排名，5 轮固定选择）。改为真实顺序仿真：每轮选 batch → oracle 揭示 → 更新模型 → 下轮排名。测量 hit curve 早期轮次的动态提升。

**10.3 LOO 泛化提升**
当前 IFNG LOO AUC=0.577，GWPS LOO AUC=0.563，仍有较大空间。方向：接入 DepMap CRISPR 数据扩充训练集，或 per-dataset 特征归一化消除分布偏移。

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

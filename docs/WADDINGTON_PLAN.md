# Waddington — 项目研究计划

> 最后更新：2026-06-14（G1 ARCHS4 特征扩展 + /suggest-genes 命令完成）
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
| G1 Phase 2 | LightGBM + ARCHS4 共表达（4 特征，BDA 数据引导）| ✅ |
| G2 ExperimentPlanner | 多轮预算分配 + SKILL 优先 + 重试机制 | ✅ |
| /suggest-genes | G1→G2 对话命令（CLI + Web Chat）| ✅ |
| Coreset baseline | k-center 贪心 A-arm（G5 对照臂）| ✅ |

详见 [docs/v2/MODULES.md](v2/MODULES.md)、[docs/v2/INNOVATION.md](v2/INNOVATION.md) 和 [docs/v1+v2/SUMMARY.md](v1+v2/SUMMARY.md)。

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

7 数据集均值：Random 0.046 → BDA 0.128 → Coreset 0.145 → Phase 2（3特征）0.201 → **Phase 2（4特征）0.264**。

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

### 近期（可实现，不依赖更多数据）

**6.1 对话命令 `/suggest-genes`** ✅ 已完成
把 G1→G2 串入对话流：`node bin/waddington.js suggest-genes IFNG --budget 200 --rounds 4`，Web Chat 中也可直接输入 `/suggest-genes IFNG --budget 200`。

**6.2 接入 Replogle 2022 大规模数据集**
作为更严格的 benchmark，且基因数（9,867）更接近真实 CRISPR 全基因组筛选规模。

**6.3 G1 LightGBM 特征扩展** ✅ 已完成（ARCHS4）
ARCHS4 共表达已作为第 4 特征加入，feature importance=3608（接近 ppi_score 的 3941），均值命中率 +31%。
待考虑的后续扩展：
- `is_essential` 替换（importance=0，可换 STRING 度中心性）
- 通路成员资格独热编码（KEGG）

### 中期（需要积累真实实验数据）

**6.4 真实实验数据微调 Phase 2 模型**
当 Waddington DB 积累 ≥20 条 `RFS > 0.65` 的高质量实验后，运行 `bootstrap_lgbm.py` 用真实标签重训，模型收敛到当前研究场景。

**6.5 三臂消融实验**
| 臂 | 配置 | 目的 |
|----|------|------|
| A | 纯 Random / 纯规则（G1 Phase 1 无 LightGBM） | 基线 |
| B | G1+G2，但无 G3 质量过滤 | 验证 G3 价值 |
| C | 完整 Waddington V2 | 主张 |

可在 G5 BenchmarkEval 框架内直接实现，已有所需基础设施。

### 长期

**6.6 跨表型迁移学习**
当积累多个表型的实验数据后，测试 Waddington 的"跨实验经验记忆"是否确实加速新表型的冷启动（hit curve 的前 1-2 轮是否明显优于无记忆版本）。

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
| Replogle et al. 2022 | 大规模 CRISPRi 数据（待接入） |

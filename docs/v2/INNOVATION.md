# Waddington V2 创新点分析

> **V2 核心转变**：从"代码复现助手"升级为"基因扰动实验设计 Agent"。
> 代码执行从主要任务降级为中间步骤；基因选择、实验规划、结果解释成为核心能力。
>
> **关键洞察**：GeneDisco / BioDiscoveryAgent / PerTurboAgent 三篇 SOTA 都无法区分
> "技术失败"和"真实生物阴性"——Waddington 的 RFS + E3 架构天然解决了这个问题。

---

## 零、V2 实现状态总览

| 模块 | 类别 | 状态 | 核心文件 |
|------|------|------|---------|
| **V1 全部模块** | 记忆 / 评分 / 技能 / KG | ✅ 已完成（见 v1/INNOVATION.md） | 见 v1 |
| **G3 NegativeFilter** | 技术失败 vs 生物阴性区分 | ✅ 已完成 | `src/web/negative-filter.ts` |
| **G5 BenchmarkEval** | 对 BioDiscoveryAgent 数据集的评估 | ✅ 已完成 | `workspace/evaluation/benchmark.py` |
| **G4 PhenotypeMapper** | 基因 → 表型反向查询 | ✅ 已完成 | `src/web/phenotype-mapper.ts` `workspace/evaluation/phenotype_mapper.py` |
| **G1 GeneRanker** | 基因候选生成与排序 (Phase 1) | ✅ 已完成 | `src/web/gene-ranker.ts` `workspace/evaluation/gene_ranker.py` |
| **G2 ExperimentPlanner** | 多轮实验规划 | ✅ 已完成 | `src/web/experiment-planner.ts` |

---

## 一、V1 回顾与 V2 起点

### V1 建立了什么

V1 的核心贡献是让 Waddington 具备**科学记忆与质量评估**的能力：

```
用户上传论文 PDF
    ↓ /paper-audit
  ProtocolSpec（机器可读实验协议）
    ↓ /perturb
  代码执行（注入 SKILL + 假说 + 历史）
    ↓ /process
  RFS 四维评分（fire-and-forget）
    ├── Result Fidelity（数值对比）
    ├── Metric Fidelity（LLM 指标定义审查）
    ├── Protocol Fidelity（LLM 代码合规审查）
    └── Biology Validity（GO + STRING PPI）
  → Leaderboard 更新 → SKILL 精化 → 假说生成 → KG 更新
```

**V1 的局限**：Waddington 被动等待用户提供"要复现哪篇论文、要扰动哪个基因"。它是执行者，不是提议者。

---

### V2 解决的问题

科学家的真实工作流不是"我有一篇论文，帮我复现"，而是：

> "我想研究粒细胞分化。哪些基因值得扰动？哪些已有可信数据？我下一轮实验预算有限，应该先测什么？"

这正是 GeneDisco / BioDiscoveryAgent / PerTurboAgent 在解决的问题。V2 把这个能力引入 Waddington，并在两个维度上超越它们：

1. **闭合执行环路**：三篇论文提出候选基因后交给人类做实验，Waddington 直接执行并用 RFS 评估结果质量
2. **区分失败类型**：三篇论文把所有"低命中率"视为等价信号，Waddington 能区分技术失败（重试）和真实阴性（移除候选）

---

## 二、V2 技术背景

### 三篇参考论文对比

| | GeneDisco (2021) | BioDiscoveryAgent (ICLR 2025) | PerTurboAgent (2025) |
|-|-----------------|-------------------------------|----------------------|
| **方法** | 批量主动学习（7 种 acquisition function） | LLM + 工具（PubMed/KEGG/ARCHS4/Critic） | LLM + 动作记忆 + LightGBM + GSEA |
| **命中率** | 0.24（基线） | 0.128（平均，5 轮） | 0.44（平均，11 表型） |
| **代码执行** | ✗ | ✗ | ✗ |
| **区分技术失败** | ✗ | ✗ | ✗ |
| **假说追踪** | ✗ | 部分（文献引用） | 部分（GSEA 通路） |
| **跨论文知识** | ✗ | ✗ | ✗ |

### 关键发现：噪声标签问题

三篇论文训练模型时使用二元命中/未命中标签，但"未命中"有两种本质不同的原因：

```
实验结果 = 低命中率
     ├── 技术失败（conda 错误 / n_hvg 不对 / 归一化错误）
     │   → 该基因应当重试，不是真正的阴性
     └── 真实生物阴性
         → 该基因对目标表型确实无影响
```

Waddington V1 的 `RFS.protocol_fidelity < 0.5` 或 `E3.type == "environment_failure"` 直接标识出第一类，这是三篇论文都没有的信号。

---

## 三、V2 新增模块详解

### G3：NegativeFilter（优先级最高，实现成本最低）

**原理**：V1 模块的直接组合，无需新的 LLM 调用。

```typescript
interface FilterVerdict {
  verdict: "true_negative" | "technical_failure" | "needs_investigation";
  confidence: "high" | "medium" | "low";
  reason: string;
  action: "remove_from_candidates" | "retry_with_fix" | "manual_review";
  suggested_fix?: string;  // 来自 E3 FailureRecord
}
```

**判断逻辑**：

```
输入：gene, metrics, RFSResult, FailureRecord?
                                     ↓
              ┌──────────────────────────────────────┐
              │  任一条件为真 → technical_failure     │
              │  · FailureRecord.type ∈              │
              │    {environment_failure,             │
              │     data_access_failure,             │
              │     protocol_ambiguity}              │
              │  · RFS.protocol < 0.5                │
              │  · RFS.overall < 0.4 且              │
              │    RFS.biology > 0.6                 │
              │    （生物分好但结果差 = 技术问题）     │
              └──────────────────────────────────────┘
                                     ↓
              ┌──────────────────────────────────────┐
              │  以下条件 → true_negative             │
              │  · RFS.overall > 0.65                │
              │  · RFS.protocol > 0.7                │
              │  · metrics 持续低（≥2 次）            │
              └──────────────────────────────────────┘
                                     ↓
                          needs_investigation（其余）
```

**为什么这是独特贡献**：
任何只有 `metrics` 没有 `RFS` 的系统都无法做出这个区分。
Waddington 的 Protocol Fidelity 分数是这个过滤器的核心依据。

---

### G4：PhenotypeMapper（实现成本低，查询现有数据）

**功能**：给定一个基因，返回它可能影响的表型/通路，利用 Waddington 已积累的数据。

**数据来源**（无需新 API）：
1. KG 中 `Gene → perturbed_in → Dataset` + `Paper → claims → Metric`（结构化实验证据）
2. 假说库中涉及该基因的所有条目（`hypotheses` 表）
3. STRING `interaction_partners`（PPI 邻居，已有 D2 基础设施）
4. MyGene.info KEGG + Reactome 通路注释（测试验证可用）

**输出示例**：
```json
{
  "gene": "CEBPE",
  "phenotypes": [
    {
      "name": "granulopoiesis",
      "evidence_type": "kg_claim",
      "source": "paper:gears-2024",
      "metric_value": 0.82,
      "confidence": "high"
    },
    {
      "name": "Transcriptional regulation of granulopoiesis",
      "evidence_type": "reactome_pathway",
      "confidence": "medium"
    }
  ],
  "ppi_neighbors": ["CEBPA", "SPI1", "GFI1", "RARA"],
  "hypotheses": [
    { "text": "CEBPE regulates GFI1 suppression...", "confidence": "supported" }
  ]
}
```

---

### G1：GeneRanker（核心模块，分两阶段）

**阶段一（纯检索，无 ML）**：整合多源信号，输出带分数的候选基因列表。

**输入**：目标表型描述（自然语言）+ 可选：细胞系、数据集、预算轮次

**信号来源与权重**：

| 信号 | 来源 | 权重说明 |
|------|------|----------|
| KG 实验证据 | `kg_edges`: Paper→claims→Metric，Gene→perturbed_in | 最高优先，已验证数据 |
| SKILL 成功率 | `workspace/skills/*.skill.json` | `success_rate ≥ 0.7` → 技术可靠 |
| 假说状态 | `hypotheses` 表 `confidence=speculative` | 待验证假说优先推荐 |
| STRING PPI 邻居 | 已有 D2 API | 与已知命中基因相邻 |
| MyGene.info 通路 | KEGG + Reactome | 目标表型相关通路中的基因 |
| NegativeFilter 历史 | `experiments` 表 | 排除已确认的 true_negative |
| CEGv2 黑名单 | BioDiscoveryAgent 685 个核心必需基因 | 直接降权，避免假阳性 |

**输出**：
```typescript
interface GeneCandidate {
  gene: string;
  rank_score: number;           // 综合分数 0-1
  reasons: string[];            // 可解释理由列表
  historical_rfs?: number;      // 历史 RFS 均值
  skill_match?: SkillRecord;    // 对应 SKILL
  filter_status: "candidate" | "true_negative" | "technical_retry";
  related_hypotheses: HypothesisRecord[];
  pathway_evidence: string[];   // KEGG/Reactome 通路名
  ppi_neighbors_hits: string[]; // 已知命中基因中的 PPI 邻居
}
```

**阶段二（ML 推断，PerTurboAgent 风格，延迟激活）**：
积累 ≥ 20 条有效实验记录（RFS > 0.65）后，用 LightGBM 在 SKILL 库 + 指标历史上训练一个轻量分类器，输出概率分数叠加到阶段一的检索分数上。

---

### G2：ExperimentPlanner（多轮规划）

**功能**：给定 N 个候选基因和每轮预算 K，输出每轮的实验安排。

**核心策略**：

1. **优先高置信 SKILL 基因**：已有 SKILL 的基因技术准备好了，可以直接跑，节省调试时间
2. **穿插探索**：每轮预留 20% 预算给 NegativeFilter 标记为 `needs_investigation` 的基因（重试）
3. **技术分散**：同轮次不要全选同一模型 / 同一细胞系，降低系统性偏差
4. **假说驱动优先**：有具体假说（`confidence=speculative`）的基因优先安排，因为实验结果直接更新假说置信度

**输出**：
```typescript
interface ExperimentPlan {
  round: number;
  genes: string[];
  rationale: string;           // 本轮选择理由
  expected_rfs_floor: number;  // 基于 SKILL 历史的预期 RFS 下界
  fallback_genes: string[];    // 若某基因环境失败，替换候选
}
```

---

### G5：BenchmarkEval（评估框架）

**目的**：在 BioDiscoveryAgent 的公开评估数据集上测试 GeneRanker，与三篇论文直接比较。

**数据集**（已克隆到 `keypaper/code/BioDiscoveryAgent/datasets/`）：
- `ground_truth_IFNG.csv`：T 细胞 IFN-γ 产生相关基因
- `ground_truth_IL2.csv`：IL-2 产生相关基因
- `ground_truth_Sanchez21.csv`：神经元胆碱循环
- `ground_truth_Carnevale22.csv`：CAR-T 细胞腺苷信号
- `ground_truth_Horlbeck.csv`：K562 两基因组合扰动（100K 对）

**评估指标**：
- `hit_ratio`：发现的真实命中数 / 总真实命中数（累积，按轮次）
- `AUC`：命中率曲线下面积
- `false_negative_recovery`：NegativeFilter 正确识别技术失败的比例（新增，三篇论文无此指标）

---

## 四、新的完整系统架构

```
┌────────────────────────────────────────────────────────────────┐
│                    用户输入层                                   │
│  "研究粒细胞分化，预算 3 轮，每轮测 20 个基因"                  │
└────────────────────────┬───────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                 G1 GeneRanker                                  │
│  KG 证据 + SKILL 历史 + 假说库 + STRING PPI + KEGG/Reactome    │
│  → 带可解释理由的排序候选列表                                   │
└────────────────────────┬───────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                 G2 ExperimentPlanner                           │
│  分轮安排 + SKILL 优先 + 探索/利用平衡                          │
└────────────────────────┬───────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────────┐
│            V1 执行层（代码执行 + 评估）                         │
│  /perturb → 代码执行 → /process → RFS + E3 + Leaderboard       │
│  → SKILL 精化（F3）→ 假说更新 → KG 更新                        │
└────────────────────────┬───────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                 G3 NegativeFilter                              │
│  RFS + E3 → technical_failure / true_negative / investigation  │
│  技术失败 → 修复后重试；真实阴性 → 移出候选池                  │
└────────────────────────┬───────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                 G4 PhenotypeMapper                             │
│  对确认命中基因 → 反向推断影响的表型/通路                       │
│  → 更新 KG → 生成新假说 → 指导下一轮 GeneRanker                │
└────────────────────────────────────────────────────────────────┘
```

---

## 五、与三篇论文的差异化定位

| 能力维度 | GeneDisco | BioDiscoveryAgent | PerTurboAgent | **Waddington V2** |
|---------|-----------|-------------------|----------------|-------------------|
| 基因候选生成 | ML acquisition | LLM + 工具 | LLM + 记忆 + ML | LLM + KG + SKILL + 假说 |
| 代码执行闭环 | ✗ | ✗ | ✗ | **✓** |
| 复现质量评估（RFS） | ✗ | ✗ | ✗ | **✓** |
| 技术失败 vs 生物阴性 | ✗ | ✗ | ✗ | **✓（G3 NegativeFilter）** |
| 假说追踪与更新 | ✗ | 部分 | 部分 | **✓（E2 + G4）** |
| 跨论文知识图谱 | ✗ | ✗ | ✗ | **✓（H1+H2）** |
| SKILL 复用（减少技术失败） | ✗ | ✗ | ✗ | **✓（F1+F2+F3）** |
| 两基因组合 | ✗ | 部分 | ✗ | 可扩展（Horlbeck 数据集） |
| 新表型自主发现 | ✗ | ✗ | ✗ | 待探索 |

---

## 六、论文核心 Claim（V2 版本）

> **"现有基因扰动实验设计 Agent 将所有低命中率实验视为等价的生物信号。
> 我们指出这混淆了技术失败与真实阴性，并提出 RFS-guided NegativeFilter，
> 首次将实验质量评估融入候选基因选择循环。
> 结合自进化 SKILL 库（减少技术失败率）和可证伪假说追踪，
> Waddington V2 实现了从"代码执行工具"到"科学实验设计 Agent"的完整跨越。"**

可实证的主张（对应 G5 BenchmarkEval）：
1. NegativeFilter 正确区分技术失败与真实阴性的准确率 > 随机（A/B 测试）
2. **G1 Phase 1 实测（7 数据集，3 trials，filter_essential=True）**：
   | 数据集 | Random | Waddington G1 | BDA (paper) |
   |--------|--------|--------------|-------------|
   | IFNG | 0.030 | **0.102** | 0.096 |
   | IL2 | 0.039 | **0.121** | 0.100 |
   | Carnevale22 | 0.028 | **0.044** | 0.043 |
   | Scharenberg22 | 0.109 | **0.265** | — |
   | 7数据集均值 | 0.046 | **0.107** | 0.128* |
   \* BDA 平均仅基于其报告的 4 个数据集且无 essential 过滤
3. 引入 SKILL 库后，技术失败率在 N 轮后下降（可用 Leaderboard 数据验证）

---

## 七、V2 实施优先级

| 顺序 | 模块 | 依赖 | 状态 |
|------|------|------|------|
| 1 | **G3 NegativeFilter** | V1 RFS + E3（全部已有） | ✅ 完成（commit 823a2c9） |
| 2 | **G4 PhenotypeMapper** | KG + 假说库 + STRING + MyGene.info | ✅ 完成（commit 9759d2e） |
| 3 | **G5 BenchmarkEval** | BioDiscoveryAgent 数据集（已克隆） | ✅ 完成（commit 0915823） |
| 4 | **G1 GeneRanker Phase 1** | G3 + G4 + KG + SKILL + STRING PPI | ✅ 完成（commit 18fbdc4），IFNG 0.102 > BDA 0.096 |
| 5 | `/api/gene-select` 端点 | G1 | ✅ 完成（同 G1 提交） |
| 6 | **G2 ExperimentPlanner** | G1 | ✅ 完成（commit 3c09315） |
| 7 | **G1 Phase 2（LightGBM）** | ≥ 20 条 RFS > 0.65 实验 | 🔲 待数据积累 |

---

## 八、所需外部资源（V2 新增）

| 资源 | 类型 | 用途 | 获取方式 |
|------|------|------|---------|
| BioDiscoveryAgent 数据集 | CSV/NPY，< 10MB | G5 评估基准 | 已克隆 |
| CEGv2.txt（685 核心必需基因） | TXT，< 50KB | G1 黑名单过滤 | 已克隆 |
| MyGene.info API | REST，免注册 | KEGG + Reactome 通路注释 | 在线，测试可用 |
| STRING interaction_partners | REST，已有账号 | 基因相似度（PPI 邻居） | 已有 D2 基础设施 |
| `gget` Python 包 | pip，已安装 | ARCHS4 共表达查询 | waddington-bio 环境 |
| `lightgbm` Python 包 | pip，已安装 | G1 阶段二 ML 推断 | waddington-bio 环境 |
| `mygene` Python 包 | pip，已安装 | MyGene.info 封装 | waddington-bio 环境 |

---

## 九、参考文献（V2 新增）

| 论文 | 本地路径 |
|------|---------|
| GeneDisco: A Benchmark for Experimental Design in Drug Discovery (2021) | `/home/duanyu/Python/keypaper/Mehrjou 等 - 2021 - GeneDisco...pdf` |
| BioDiscoveryAgent: An AI Agent for Designing Genetic Perturbation Experiments (ICLR 2025) | `/home/duanyu/Python/keypaper/Roohani 等 - 2025 - BioDiscoveryAgent...pdf` |
| PerTurboAgent: A Self-Planning Agent for Boosting Sequential Perturb-seq Experiments (2025) | `/home/duanyu/Python/keypaper/Hao 等 - PerTurboAgent...pdf` |

# Waddington 基因选择策略：从复现工具到实验设计 Agent

> 基于三篇核心论文的分析：GeneDisco (2021)、BioDiscoveryAgent (ICLR 2025)、PerTurboAgent (2025)
> 
> **核心论点**：这三篇论文各自解决了"选哪些基因做扰动"的问题，但都缺少一个关键的闭环——
> 它们提出候选基因后，**不执行实验、不验证复现质量、不区分技术失败和生物阴性**。
> Waddington 已有的基础设施恰好填补这个缺口，使其成为第一个"提议→执行→评估→精化"的完整闭环。

---

## 一、三篇论文的核心方法与局限

### GeneDisco（2021）— 批量主动学习基线

**方法**：7 种 acquisition function（BADGE、Coreset、AdvBIM 等）在基因嵌入空间（Achilles/STRING/CCLE）中选择下一批实验基因，目标是最大化"命中基因"发现率。

**关键数字**：最佳 normalized AUC ≈ 0.255，作为领域基线标准。

**核心局限**：
- 纯 ML 方法，无法整合文献中的机理知识
- 不区分"实验技术失败"和"真正的生物阴性"
- 没有代码执行层，无法知道结果是否可重现
- 不处理两基因/高阶扰动

---

### BioDiscoveryAgent（ICLR 2025）— LLM + 工具推理

**方法**：LLM agent 调用 PubMed / KEGG / Reactome / ARCHS4 / AI Critic 工具，闭环迭代（每轮 128 个基因，5 轮），命中率 **平均 0.128**（比随机高 ≈ 2.3×）。

**工具架构**：
- Literature Search（PubMed）：检索特定基因/通路文献
- Gene Search（ARCHS4 共表达、KEGG 通路富集）：查找候选基因
- AI Critic：另一个 LLM 审查预测，提升多样性

**核心局限**：
- 没有自己的实验执行能力——提交候选基因列表后等待人类实验
- 无法知道某个"阴性"结果是技术失败还是真实阴性
- 无历史实验质量记录，每次从零开始
- 对两基因组合仅有初步支持（17.5 vs 6.1 随机，但可扩展性差）
- 单次试验成本 $0.19–0.60，没有缓存机制

---

### PerTurboAgent（2025）— 自规划 Agent + 行动记忆

**方法**：LLM agent 内置三类动作（推理/ML推断/富集分析），配合 action memory 跨轮次积累知识；ML 推断用 LightGBM + GenePT 嵌入；GSEA 分析正/负命中通路。命中率 **平均 0.44**（最佳在翻译相关表型），是目前 SOTA。

**关键设计**：
- 延迟 ML 激活：前几轮数据不足时不训练模型，避免误导
- 自我反思动作：回顾历史轮次，修正预测
- GSEA 富集：正命中 vs 阴性命中的通路差异

**核心局限**：
- 依赖预定义的表型 + 关联描述基因（ADG），**无法自主发现新表型**
- 仍然只解决"给定表型找基因"，不解决"给定基因描述哪些表型会受影响"
- 使用固定的 K562 Perturb-seq 数据库，不支持新的实验数据即时整合
- 没有实验执行层，无法区分技术失败和生物阴性
- 扩展到其他细胞系/数据集需要重新设置

---

## 二、三篇论文共同的未解决问题

这是 Waddington 可以直接切入的空白：

### 问题 1：技术失败与生物阴性的混淆（最重要）

三篇论文都用"命中/未命中"二元标签训练模型，**但"未命中"有两种完全不同的原因**：
- A. 技术失败：conda 环境错误、n_hvg 设置错误、归一化方式不对 → 不代表该基因真的不是命中
- B. 真实生物阴性：该基因确实对目标表型无影响

BioDiscoveryAgent 和 PerTurboAgent 都把 A 和 B 混为一谈，导致模型学习了噪声标签。

**Waddington 的 RFS + E3 失败分类已经能区分这两类**。

---

### 问题 2：没有跨实验的复现质量追踪

三篇论文假设所有实验结果都是"真实可信的"，没有机制评估某个实验结果是否可重现。

如果 CEBPE 在 Norman2019 上的 pearson_de = 0.85，但 RFS = 0.31（Protocol Fidelity 低），那么这个 0.85 可能是错误的，不应该作为训练数据。

**Waddington 的 RFS 四维评分解决了这个问题**。

---

### 问题 3：跨论文、跨数据集的知识不流通

三篇论文都在独立的数据集上评估，没有积累跨论文的知识：
- Norman2019 上 CEBPE 是 granulopoiesis 相关
- Replogle2022 上同样的基因可能被独立重复发现
- 但没有系统连接这两个发现

**Waddington 的知识图谱（H1+H2）构建了这种跨论文的结构**。

---

### 问题 4：单向数据流（只用历史结果，不验证结果质量）

三篇论文的反馈循环：`选基因 → 做实验 → 得结果 → 更新模型`

但这个循环缺少一步：**评估结果本身的质量**。如果某轮实验结果质量低（RFS < 0.5），它不应该被纳入模型更新，否则会传播错误。

---

### 问题 5：没有"可执行假说"的生成

三篇论文都在回答"哪些基因会命中"，但没有回答"为什么命中"、"下一步如何验证"。PerTurboAgent 的 GSEA 分析部分触及了这个问题，但没有产出可追踪、可证伪的假说。

---

## 三、Waddington 的重新定位

### 当前定位（代码复现助手）

```
用户 → /perturb → 代码执行 → 指标输出
                    ↑ 注入 SKILL/历史
```

### 新定位（实验设计 + 执行的闭环 Agent）

```
[目标表型/研究问题]
        ↓
[基因候选生成]  ← 文献 + KG + SKILL库 + 假说库
        ↓
[实验优先级排序]  ← RFS历史 + 成功率 + 失败分类
        ↓
[代码执行]  ← 现有的 /perturb + Protocol Oracle
        ↓
[质量评估]  ← RFS 四维 + Biology Validity
        ↓
[失败区分]  ← E3 分类（技术 vs 生物阴性）
        ↓
[知识更新]  ← SKILL精化 + KG更新 + 假说更新 + Leaderboard
        ↓
[下一轮基因推荐]  ← 上一轮所有信息的综合
```

**关键转变**：代码执行变成中间一步，而不是全部。这个循环是三篇论文都没有实现的。

---

## 四、具体可实现的新模块

### 模块 G1：GeneRanker — 基因候选生成与排序

**解决的问题**：GeneDisco 的 acquisition function + BioDiscoveryAgent 的工具调用 + PerTurboAgent 的知识整合，全部放在 Waddington 的历史数据上下文中。

**输入**：目标表型描述（自然语言）
**输出**：按优先级排序的基因列表，每个基因附带推荐理由

**数据源**（按优先级）：
1. **Waddington KG**：已有的 `Gene → perturbed_in → Dataset`、`Paper → claims → Metric` 关系
2. **SKILL 库**：`success_rate >= 0.7` 的基因优先（已知可以成功复现）
3. **假说库**：status=`speculative` 的假说中提到的基因（待验证）
4. **外部数据库**：STRING PPI（已有 D2 的调用能力）、KEGG、ARCHS4

**核心区别于 BioDiscoveryAgent**：Waddington 在推荐基因时会同时输出：
- 该基因的历史 RFS 均值（技术可靠性）
- E3 失败分类历史（是否曾经技术失败过）
- 相关假说（知道预期结果是什么）

```typescript
// 伪接口
interface GeneCandidate {
  gene: string;
  score: number;              // 综合优先级分数
  reasons: string[];          // 可解释理由
  historical_rfs?: number;    // 历史 RFS 均值（技术可信度）
  skill_match?: SkillRecord;  // 是否有对应 SKILL
  related_hypotheses: HypothesisRecord[];
  kg_evidence: KgNode[];      // KG 中支持该基因的证据
  failure_history?: FailureType[]; // 历史失败类型
}
```

---

### 模块 G2：ExperimentPlanner — 多轮实验规划

**解决的问题**：PerTurboAgent 的"self-planning"在 Waddington 上的实现，但利用已有的 SKILL/RFS 数据。

**核心逻辑**：
1. 给定 N 个候选基因和 K 的实验容量
2. 优先选择：有 SKILL 记录（节省调试时间）、RFS 历史良好、假说支持
3. 对 RFS 低但 Biology 分高的基因：标记为"技术失败候选"，下一轮重试时改进协议
4. 对 RFS 高但 Biology 低的基因：真实阴性，不再优先

**关键 insight**：这是 GeneDisco / BioDiscoveryAgent / PerTurboAgent 都没有的——**用实验质量（RFS）而非实验结果（hit/miss）来指导下一轮选择**。

---

### 模块 G3：NegativeFilter — 技术失败 vs 生物阴性的区分器

这是对领域最重要的贡献。

**当前问题**：一个基因扰动后 pearson_de = 0.12（低），可能是：
- A. 真的对目标表型没影响（生物阴性）→ 从候选列表中移除
- B. 协议错误（n_hvg 设置错误、conda 环境问题）→ 下一轮修复后重试

**Waddington 的判断逻辑**：
```
if RFS.protocol < 0.5 or RFS.biology < 0.3:
    → 技术失败，标记为 "needs_retry"，注入 SKILL 修复建议
else if metrics 低:
    → 真实生物阴性，标记为 "true_negative"，从候选列表移除
```

这个过滤器让 GeneRanker 的训练信号更干净——只有高质量实验（RFS > 0.7）的结果才纳入基因评分更新。

---

### 模块 G4：PhenotypeMapper — 反向查询（基因 → 表型）

**解决的问题**：三篇论文都是"表型 → 基因"方向，但科学家有时想知道"这个基因影响哪些表型"。

**利用现有模块**：
- KG 中的 `Gene → perturbed_in → Dataset` + `Paper → claims → Metric`
- 假说库中涉及该基因的所有假说（正向/反向）
- SKILL 库中该基因的历史最佳指标分布

**输出**：给定基因，返回它可能影响的通路/表型及置信度，利用 Waddington 积累的实验历史。

---

## 五、新的 API 设计

```
POST /api/gene-select
  body: { phenotype: string, cell_line?: string, budget: number, round?: number }
  → { candidates: GeneCandidate[], reasoning: string, next_action: string }

POST /api/experiment-plan  
  body: { candidates: GeneCandidate[], model: string, dataset: string, budget: number }
  → { planned: ExperimentPlan[], priority_order: string[], estimated_rounds: number }

GET /api/gene-history/:gene
  → { rfs_history: number[], failure_types: FailureType[], hypotheses: HypothesisRecord[], skill?: SkillRecord }

POST /api/negative-filter
  body: { gene: string, metrics: Record<string,number>, rfs: RFSResult }
  → { verdict: "true_negative" | "needs_retry" | "technical_failure", reason: string }
```

---

## 六、与三篇论文的差异化定位

| 能力 | GeneDisco | BioDiscovery Agent | PerTurboAgent | **Waddington（扩展后）** |
|------|-----------|-------------------|----------------|--------------------------|
| 基因候选生成 | ML + embedding | LLM + 工具 | LLM + 动作记忆 | **LLM + KG + SKILL历史** |
| 实验执行 | ✗ | ✗ | ✗ | **✓（代码执行闭环）** |
| 复现质量评估 | ✗ | ✗ | ✗ | **✓（RFS 四维）** |
| 技术失败区分 | ✗ | ✗ | ✗ | **✓（E3 + RFS）** |
| 假说追踪 | ✗ | 部分（文献引用） | 部分（GSEA） | **✓（可证伪假说库）** |
| 跨论文知识 | ✗ | ✗ | ✗ | **✓（KG 结构化）** |
| SKILL 复用 | ✗ | ✗ | ✗ | **✓（技能库）** |
| 两基因组合 | ✗ | 部分 | ✗ | 可扩展 |
| 可解释性 | 低 | 高（推理链） | 中 | **高（每步可追溯）** |

---

## 七、论文叙事建议

如果要写论文，核心 claim 可以这样叙述：

> **"现有基因扰动实验设计 Agent 假设实验结果是可信的，但忽略了一个关键问题：一个'未命中'基因可能是技术失败而非真实阴性。Waddington 引入 RFS（复现保真度评分）和 E3 失败分类，首次将实验质量评估融入基因选择循环，使 Agent 能够区分技术失败和真实阴性，从而避免将噪声标签纳入学习信号。"**

这个贡献是三篇论文都没有做到的，且在生物学上有直接意义。

---

## 八、实施优先级

按实现成本从低到高、价值从高到低排序：

| 优先级 | 模块 | 成本估计 | 核心价值 |
|--------|------|----------|----------|
| P1 | G3 NegativeFilter | 低（现有 RFS + E3 组合） | 直接区分技术失败/生物阴性 |
| P2 | G4 PhenotypeMapper | 低（查询 KG + 假说库） | 反向查询，补充 BioDiscoveryAgent |
| P3 | G1 GeneRanker（基础版） | 中（整合 KG/SKILL/假说） | 基因候选生成主干 |
| P4 | 新 endpoint /api/gene-select | 中（调用 G1+G3+G4） | 完整 API 接口 |
| P5 | G2 ExperimentPlanner | 高（多轮规划逻辑） | 端到端实验设计闭环 |

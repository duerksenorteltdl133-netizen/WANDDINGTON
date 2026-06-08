# Waddington 创新点分析

> 核心问题：Waddington 能做什么是 Claude Code / GitHub Copilot 做不到的？

---

## 一、为什么"PDF→代码复现"不够

Claude Code 和 Codex 已经能做到：读 PDF、搜索 arXiv、安装依赖、运行 Python 脚本、执行基准测试。
这些是"工具能力"，而非"研究能力"。

**根本差距**在于：一个通用编码助手每次启动都是白纸，没有跨会话的科学记忆，不知道"上次在 Norman2019 上 GEARS 比 scGPT 高 12%"，也不知道"CEBPE 属于粒细胞生成调控因子"。Waddington 的机会在于**从一个工具进化成一个有机构记忆的研究伙伴**。

---

## 二、已完成的基础（Phase 1–5）

| 层 | 实现 | 位置 |
|----|------|------|
| L1 结构化记忆 | 实验记录（gene/model/metrics），/perturb 时自动注入历史 | `src/web/db.ts` `experiments` 表 |
| L2 摘要记忆 | 对话摘要 + FTS5 BM25 检索，自动命名会话 | `src/web/summarize.ts` |
| L3 向量记忆 | MiniLM 384维嵌入 + 余弦相似度 + RRF 融合 | `src/web/embed.ts` |

这是三级检索的骨架，下面是在此基础上可以做的七个创新方向。

---

## 三、创新方向

### 创新 1：自进化扰动技能库（最高优先级）
**对应论文**：MSTAR (ICLR 2026, 2604.11811)、Memento-Skills (2603.18743)、EvolveR (ICLR 2026)  
**课程模块**：技能.md Lv.2 自进化技能系统

**Claude Code 的局限**：每次 `/perturb` 都重新推理如何安装环境、写脚本、选参数。  
**Waddington 的机会**：当一次 `/perturb` 成功后，将整个工作单元（conda env 名、脚本路径、关键参数、数据预处理步骤、该基因所属 pathway 类型）结晶为一个可复用的 SKILL，下次同类基因直接调用，无需重新推理。

**具体实现**：
- 新增 `workspace/skills/` 目录，每个成功实验自动生成一个 `{gene}_{model}_{dataset}.skill.json`
- SKILL 包含：`{conda_env, script_template, params, gene_class, pathway, last_pearson_de, success_rate}`
- `/model install` 后自动注册 SKILL 模板
- `/perturb` 前先查技能库——若有该基因类别的成功先例，以 `--from-skill` 模式启动（跳过环境推理步骤）
- 定期淘汰：30天内成功率 < 50% 的技能降级为 `deprecated`

**差异化理由**：CellAgent (ICLR 2026) 做的是多智能体单细胞分析，但没有技能持久化。Waddington 的技能库在多次实验后越跑越快。

---

### 创新 2：假说—实验—反思循环
**对应论文**：Agent Laboratory (2501.04227)、Experiential Reflective Learning (2603.24639)、Advancing the Scientific Method (2505.16477)  
**课程模块**：记忆.md Lv.3 自进化记忆库

**Claude Code 的局限**：运行完脚本，输出指标，会话结束——没有生物学解释。  
**Waddington 的机会**：在 `agent_end` 之后，自动对结果做一步假说生成：

```
CEBPE KO pearson_de=0.71 (GEARS)，与上次 CEBPA KO=0.74 相似度高（cosine 0.89）
→ 假说：CEBPE 和 CEBPA 可能共享部分靶基因，建议运行 /perturb CEBPA+CEBPE 组合扰动
→ DE 基因中 GFI1、MPO 上调符合粒细胞生成先验
```

这些假说存入 `hypotheses` 表，并在同类实验时作为上下文注入 Pi。

**实现要点**：
- `src/web/hypothesize.ts`：在 experiments 结果上运行一个轻量 LLM 调用（可以是 Pi 的一个隐性 prompt），生成 1-2 条假说
- 假说带置信度分类：`speculative` / `supported` / `refuted`（后续实验后更新）
- `/perturb GENE2` 时若有与 GENE2 相关的 `supported` 假说，自动作为 context 前缀

---

### 创新 3：跨论文知识图谱
**对应论文**：HiGraAgent (EACL 2026, 2026.findings-eacl.62)、LinearRAG (2510.10114)、Graph RAG (2404.16130)  
**课程模块**：记忆.md Lv.2 知识库多跳推理

**Claude Code 的局限**：每次 `/discuss` 读论文都从头开始，无法回答"有哪些论文在 Norman2019 上测了 GEARS 且 pearson_de > 0.7？"  
**Waddington 的机会**：构建一个异质知识图谱：

```
节点类型：Paper, Model, Gene, Dataset, Metric, CellType
边：Paper --benchmarks_on--> Dataset
    Paper --claims--> Metric (value: 0.71)
    Model --evaluated_by--> Paper
    Gene --perturbed_in--> Dataset
```

存储在 SQLite（已有基础），用 NetworkX 序列化。

**支持的多跳查询**：
- "哪个模型在 TF 敲除上普遍最好？"（Model→Gene class→Metric）
- "GEARS 被哪些 2024 年后的论文引用并复现？"（Paper→Paper→Model）
- "/design 新实验"时，自动检索已有的 gene-dataset-model 组合避免重复

**实现要点**：
- `/discuss` 完成后增加一步 "knowledge extraction" prompt，结构化提取实体关系
- 新增 `GET /api/graph?node=CEBPE&depth=2` API
- Web UI 中 Experiments 面板下方增加 "Related papers" 条目

---

### 创新 4：多智能体并行复现流水线
**对应论文**：CellAgent (ICLR 2026)、Multi-Agent Collaboration via Evolving Orchestration (ICLR 2025)  
**课程模块**：编排.md Lv.2/3 进阶静态/动态编排

**Claude Code 的局限**：`/replicate` 是串行的——读论文、下数据、装环境、跑代码一步一步来，中间任何一步卡住整个流程停滞。  
**Waddington 的机会**：`/replicate` 时启动三个并行子任务：

```
Agent A (Paper Reader)  → 提取 methods、代码链接、超参数表
Agent B (Data Fetcher)  → 并行下载 GEO/Zenodo 数据集
Agent C (Env Builder)   → 并行创建 conda 环境、安装依赖
     ↓ 三个完成后汇合
Agent D (Executor)      → 运行复现脚本
Agent E (Comparator)    → 与论文报告指标对比，生成差异分析
```

**实现要点**：
- 在 `web-server.ts` 中实现 `orchestrate(subtasks[])` 函数，并发调用多个 Pi 实例（或工具调用）
- 用 `orchestration_log` 表追踪每个子任务状态
- Web UI 中 `/replicate` 时显示并行进度面板

---

### 创新 5：资源感知实验计划
**对应论文**：On Time, Within Budget (2605.06110)、DecisionBench (2605.19099)  
**课程模块**：编排.md Lv.3 进阶动态编排

**Claude Code 的局限**：用户说"跑一下 scGPT"，Claude Code 不知道显卡内存够不够、时间预算多少。  
**Waddington 的机会**：在 `/perturb` 和 `/benchmark` 前自动检测资源约束，给出适配方案：

```
检测到：GPU 8GB VRAM，可用时间 2h
scGPT 全量需要 24GB，建议：
  - 方案A: GEARS（4GB，~30min）[推荐]
  - 方案B: scGPT + LoRA 量化（8GB，~90min）
  - 方案C: 仅前200个DE基因子集
```

**实现要点**：
- 新增 `workspace/resource_profiles/` 目录，每个模型记录实测显存占用、运行时间
- `/benchmark` 前自动调用 `nvidia-smi` 检测当前资源
- 用历史 experiments 表估算当前任务资源需求（基于 gene 数量、dataset 大小）

---

### 创新 6：基准演进追踪器
**对应论文**：PaperArena (2510.10909)、SciAgentGym (2602.12984)

**Claude Code 的局限**：不知道 GEARS 在 Norman2019 上的 SOTA 是 2023 年 0.71，后来被 scGPT 超越到 0.74。  
**Waddington 的机会**：维护一个活的 benchmark leaderboard：

- `workspace/benchmarks/leaderboard.json`：按 dataset×gene_class 维度追踪各模型指标
- 每次新实验结果自动更新 leaderboard
- `/discuss` 处理新论文时，如果论文声明 SOTA，自动设计一个验证实验并提示用户
- Web UI 中增加 "Leaderboard" 标签页，可视化各模型在不同数据集上的指标演进

---

### 创新 7：生物学先验约束验证（最具差异化）
**背景**：这是任何通用编码助手无法复制的核心护城河。

**Claude Code 的局限**：跑完 GEARS，输出 pearson_de=0.71，会话结束。它不知道 CEBPE 应该调控哪些下游基因，也无法判断结果在生物学上是否合理。  
**Waddington 的机会**：在 `agent_end` 后，对 top DE 基因做先验验证：

- **KEGG/GO 富集**：top 上调/下调基因是否富集在已知相关 pathway？
  - `CEBPE KO → granulopoiesis pathway enrichment p<0.001 ✓（符合预期）`
- **STRING 网络**：预测的 DE 基因与已知 CEBPE 调控靶点的 overlap？
- **反常预测标记**：若某个模型预测的 top DE 基因与 GO 先验完全无关，自动标记 `suspicious`

**实现要点**：
- 接入 NCBI Entrez API（免费）做 GO 富集
- 接入 STRING API 查询基因调控网络（已有 MCP/skill 框架）
- 验证结果存入 `experiments.bio_validation_json` 字段
- 这是 Claude Code / Codex 在结构上无法做到的：它们没有领域先验，而 Waddington 可以集成

---

## 四、与现有工作的差异化对比

| | Claude Code | CellAgent (ICLR 2026) | Waddington（目标） |
|--|--|--|--|
| 跨会话记忆 | ✗ | ✗（每次分析独立） | ✓ L1-L3 三级 |
| 技能自进化 | ✗ | ✗ | ✓（创新1）|
| 生物假说生成 | ✗ | 部分（分析结果解释） | ✓（创新2）|
| 跨论文知识图谱 | ✗ | ✗ | ✓（创新3）|
| 并行复现流水线 | ✗ | 多智能体分析 | ✓（创新4）|
| 资源感知规划 | ✗ | ✗ | ✓（创新5）|
| 生物先验验证 | ✗ | ✗ | ✓（创新7）|

CellAgent 是最接近的竞品，但它专注于**分析**（scRNA-seq 处理流程），而 Waddington 专注于**研究**（假说→实验→知识积累→技能复用）。

---

## 五、实施优先级建议

```
立即可做（已有基础，扩展即可）：
  创新6 - Leaderboard 追踪器（experiments 表已有数据）
  创新2 - 假说生成（在 /process 后加一步 LLM 调用）

中期（需新增模块）：
  创新1 - 自进化技能库（最高 ROI，核心差异化）
  创新7 - 生物先验验证（接入 NCBI/STRING API）

长期（架构变动）：
  创新3 - 知识图谱（需设计图数据库 schema）
  创新4 - 并行多智能体（需重构 web-server.ts 进程管理）
  创新5 - 资源感知规划（需积累资源画像数据）
```

---

## 参考文献

| 论文 | 本地路径 |
|------|---------|
| MSTAR: Every Task Deserves Its Own Memory Harness (ICLR 2026) | `/home/duanyu/文档/Paper/2604.11811v2.pdf` |
| HiGraAgent: Dual-Agent Adaptive Reasoning over Hierarchical KG (EACL 2026) | `/home/duanyu/文档/Paper/2026.findings-eacl.62.pdf` |
| LinearRAG (2025) | `/home/duanyu/文档/Paper/2510.10114v4.pdf` |
| Graph RAG: From Local to Global (2024) | `/home/duanyu/文档/Paper/2404.16130v2.pdf` |
| Agentic RAG Survey (2025) | `/home/duanyu/文档/Paper/2501.09136v4.pdf` |
| RAG-Anything: All-in-One RAG (2025) | `/home/duanyu/文档/Paper/2510.12323v1.pdf` |
| AAFLOW: Scalable Patterns for Agentic AI Workflows (ICLR 2026) | `/home/duanyu/文档/Paper/2605.02162v1.pdf` |
| From Intent to Execution: Composing Agentic Workflows (2026) | `/home/duanyu/文档/Paper/2605.03986v1.pdf` |
| On Time, Within Budget: Constraint-Driven Resource Allocation (2026) | `/home/duanyu/文档/Paper/2605.06110v2.pdf` |
| DecisionBench (2026) | `/home/duanyu/文档/Paper/2605.19099v1.pdf` |
| Rethinking Memory Mechanisms of Foundation Agents (2026) | `/home/duanyu/文档/Paper/2602.06052v3.pdf` |
| CellAgent: LLM-Driven Multi-Agent for Single-Cell Analysis (ICLR 2026) | arXiv 2407.09811 |
| Agent Laboratory (2025) | arXiv 2501.04227 |
| Experiential Reflective Learning for Self-Improving LLM Agents (2026) | arXiv 2603.24639 |
| Memento-Skills: Let Agents Design Agents (2026) | arXiv 2603.18743 |
| SciAgentGym (2026) | arXiv 2602.12984 |
| PaperArena (2025) | arXiv 2510.10909 |

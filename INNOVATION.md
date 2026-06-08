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

---

## 六、本次新增：基于 2026 年最新论文的深化方向

> 以下是结合课程论文（/home/duanyu/Python/Myproject/ai-agent-assignment/ch/可选模块）和本地 PDF 深度阅读后的新增建议，优先级独立标注。

---

### 新增 A：复现保真度分数（RFS）——**最直接的论文贡献**

**灵感**：DecisionBench（2605.19099）的核心发现：*"quality-only evaluation would miss the orchestration signal"*，过程级指标揭示了比结果指标多 15–31pp 的隐藏性能空间。

**问题**：目前 Waddington 和 Claude Code 都只报告"跑完了，pearson_de=0.71"——没有区分**代码跑通**和**科学被复现**。

**设计**：一个四维 Replication Fidelity Score（RFS），类比 DecisionBench 的 quality / cost / delegation-fidelity 多轴框架：

| 维度 | 定义 | 如何检测 |
|------|------|---------|
| **Protocol Fidelity** | 是否遵循论文中的预处理顺序、train/test split 策略、HVG 数量等 | 对比 `paper-to-experiment` skill 提取的协议 vs 生成的 run.py |
| **Metric Fidelity** | 指标定义是否与论文一致（top-k 值、delta 计算方式） | 提取论文 metrics 描述，与 `simple_eval.py` 对比 |
| **Result Fidelity** | 数值是否在论文报告值的统计允差内 | `|our_value - paper_value| / paper_value` |
| **Biological Validity** | 结果是否符合领域先验（无 artifact，DE 基因方向正确） | 生物学 oracle 规则（创新7 的扩展）|

**示例输出**：
```
RFS = 0.62 | Protocol: 0.90 | Metric: 0.50 | Result: 0.80 | Biology: 0.30
WARNING [Metric]: paper uses top-50 DEGs, we used top-20 — rerun with k=50
WARNING [Biology]: Scouter pearson=0.165 falls below expected range [0.5, 0.8]
```

**为什么比通用 agent 更强**：Claude Code 能说"代码运行成功"，RFS 能说"科学复现了 62%，卡点在 Metric 定义"。这是**可测量、可比较的差距**，正是论文需要的核心 claim。

**对应课程模块**：编排.md Lv.3（执行轨迹记录）、记忆.md Lv.2（知识库多跳推理，验证逻辑）

**四维实现难度**：

| 维度 | 计算方式 | 难度 | 前置依赖 |
|------|---------|------|---------|
| Result Fidelity | `1 - \|our - paper\| / paper`，纯数学 | 简单 | 无 |
| Metric Fidelity | LLM 提取 paper 指标定义 + 对比 eval 代码 | 中等 | PDF 提取能读懂方法段 |
| Protocol Fidelity | LLM-as-judge（ProtocolSpec vs run.py） | 中等 | Protocol Oracle 先做好 |
| Biology Validity | GO 富集 p-value + STRING 网络 overlap | 偏硬 | NCBI/STRING API 接入 |

**接口设计**：
```typescript
// src/web/rfs.ts
export interface RFSResult {
  overall: number;
  protocol: number;   // LLM judge 0-1，依赖 ProtocolSpec
  metric: number;     // LLM judge 0-1
  result: number;     // 数学计算
  biology: number;    // GO 富集，可选
  warnings: string[];
}

export async function computeRFS(
  protocolSpec: ProtocolSpec | null,
  runScript: string,
  ourMetrics: Record<string, number>,
  paperMetrics: Record<string, number>,
  deGenes?: string[]
): Promise<RFSResult>
```

**最小可行路径**（先做前两维，够用于 demo）：

1. 定义 ProtocolSpec JSON Schema（半天）
2. 手工标注 GEARS / scGPT / CPA 三篇论文的 ProtocolSpec（一天）
3. 实现 Result Fidelity + Metric Fidelity（一天，最简单的两维）
4. 制造一个 metric mismatch 演示：故意用 top-20 复现 top-50 的论文，展示 Waddington 检测并阻止错误比较
5. Protocol Fidelity 和 Biology Validity 后补，不影响前期 demo 的说服力

---

### 新增 B：MSTAR 风格的记忆程序进化

**灵感**：MSTAR（2604.11811）把记忆表示为可执行 Python 模块（Schema/Logic/Instruction），通过 reflective code evolution 自动搜索最优记忆结构。关键发现：**每个任务有自己最优的记忆结构，通用记忆会显著降低性能**。

**当前 Waddington 问题**：三级记忆（L1 实验表/L2 摘要/L3 向量）结构固定，对"论文阅读"和"实验调试"使用同一套记忆结构，而这两个子任务的最优记忆形式完全不同：
- 论文阅读 → 最优：实体关系图（模型-数据集-指标三元组）
- 实验调试 → 最优：错误模式字典（`{错误签名: 修复步骤}`）

**设计**：参照 MSTAR 的 Schema/Logic/Instruction 三组件，为 Waddington 的不同任务设计**可演化的记忆模块**：

```python
# 示例：调试专用记忆程序
class DebugMemory:
    Schema = {"error_sig": str, "model": str, "fix": str, "success_rate": float}
    Logic = "vector_search over (error_sig, model) → top-3 fixes"
    Instruction = "Before attempting a fix, always query debug memory with the error message."
```

每次调试会话后，reflector agent 对失败案例生成 patch，更新记忆程序。

**对应课程模块**：记忆.md Lv.3 自进化记忆库（MSTAR 就是该模块的参考文献）

---

### 新增 C：概率性成功最大化规划（MCPP for Bioinformatics）

**灵感**：On Time Within Budget（2605.06110）把 agentic workflow 执行形式化为：给定 budget B 和 deadline D，最大化 P(workflow completes | B, D)，用 Monte Carlo Portfolio Planning 在线分配资源。

**当前 Waddington 问题**：`/benchmark` 是"能跑就跑"，没有形式化的成功概率估计。

**设计**：利用 `workspace/benchmarks/` 中已有的历史运行数据，为每个 (model, dataset, mode) 组合维护一个**经验成功率 p̂**，然后在新任务启动时做 MCPP 式的分配：

```
输入：3个模型, GPU 8h budget
历史数据：
  GEARS  + norman2019 + full: p̂=0.85, 耗时 3.5h
  scGPT  + norman2019 + full: p̂=0.60, 耗时 4.0h (经常 OOM)
  CPA    + norman2019 + smoke: p̂=0.90, 耗时 0.5h

MCPP 规划：先跑 GEARS(full) + CPA(smoke)，若失败再尝试 scGPT(smoke)
P(至少1个full成功) = 1 - (1-0.85) = 0.85 → 在8h内有0.92概率有成果
```

**对应课程模块**：编排.md Lv.3 进阶动态编排（约束驱动、错误恢复、执行轨迹）

---

### 新增 D：PerturbBench — 计算生物学论文复现基准（最大影响力）

**灵感**：DecisionBench 通过建立标准 benchmark，让所有 agent 方法在同一尺度上被评测，成为该方向的基础设施论文。

**空白（修正版）**：现在已经有 PaperBench、ScienceAgentBench、BixBench、LMR-BENCH 等评测 AI agent 做科学任务或论文复现的基准；真正空白不是"有没有基准"，而是**没有一个专门评测单细胞扰动论文复现保真度的基准**。BixBench 更偏开放式生物信息分析问答，PaperBench 更偏通用 AI/ML 论文复现；Waddington 可以把缺口收窄到 perturbation prediction 的 protocol、metric、dataset split 和 biological validity。

**设计**：收录 20 篇基因扰动预测论文，每篇提供：
- 输入：PDF + GitHub URL + GEO accession
- 标准答案：正确 conda 环境、预处理脚本、metric 定义、论文报告值
- 难度分级：easy（有完整 README）/ medium / hard（无文档，需逆向工程）
- 评测维度：RFS 的四个维度 + 环境安装成功率

**论文价值**：PerturbBench 本身可作为 NeurIPS / ICLR **Datasets & Benchmarks track** 独立投稿，同时也是 Waddington 论文的评测基础。

---

## 七、本次进一步补充：把创新点收束成可投稿的主线

> 读完课程的「编排 / 记忆 / 技能」模块，再对照 ICLR 2025/2026 的 agent 论文后，我建议不要把 Waddington 包装成"更会写代码的 Claude Code"，而要包装成一个**可审计、可学习、可验证的领域科学工作流系统**。

### 补充 1：Protocol Oracle，而不是单纯 Code Agent

**核心想法**：通用 agent 的强项是写代码，弱项是判断"这段代码是否忠实执行了论文协议"。Waddington 应该把论文中的 protocol 抽取成机器可检查的 `ProtocolSpec`，再用它约束复现脚本。

```yaml
paper: GEARS
dataset: Norman2019
perturbation_type: CRISPRa
split:
  type: combination_holdout
  unseen_single: true
preprocess:
  normalization: log1p
  hvg: paper_reported_or_detected
metric:
  pearson_de:
    top_k: 20
    de_reference: observed_vs_control
```

**为什么有创新性**：Claude Code/Codex 可以写出能跑的 `run.py`，但通常不会把"论文协议"作为一等对象持久化、验证和复用。Waddington 的 claim 可以变成：**从 paper-to-code 提升到 paper-to-protocol-to-code**。

**落地位置**：
- `outputs/<slug>.provenance.md` 增加 `ProtocolSpec` 和 `ImplementationSpec` 对照表
- `workspace/evaluation/evaluation_engine.py` 增加 protocol check hooks
- `/paper-audit` 先生成 `ProtocolSpec`，`/replicate` 必须引用它

**前置条件（当前瓶颈）**：Waddington 目前的 PDF 提取用 `unpdf`（pdfjs-dist 封装），把每页所有 text span 平铺成一个字符串——表格的列结构完全丢失，图片被忽略。ProtocolSpec 里的 `hvg: 2000`、`split: combination_holdout`、`top_k: 20` 等关键信息大多在论文的表格和方法段结构中，平铺文字无法可靠提取。

**PDF 提取改进选项**（三选一，按成本排序）：

| 方案 | 工具 | 优点 | 成本 |
|------|------|------|------|
| 换 `marker-pdf` | Python，本地跑 | 保留表格为 Markdown，标注图片位置 | 半天 |
| 用 `pymupdf` text blocks | Python，带坐标 | 可重建列结构，提取嵌入图片 | 一天 |
| 维持现状，依赖 LLM 推理 | 不换 | 零改动 | Protocol Fidelity 准确率低 |

推荐先用 `marker-pdf` 替换 `unpdf`，这是 Protocol Oracle 能否自动化的关键前提。

### 补充 2：Bio-Critic 闭环，把"跑出来"变成"科学上可信"

**核心想法**：把 reviewer / data-analyst / verifier 三个 subagent 组织成一个固定的批判循环：

```
bioinfo-runner 产生 metrics
    ↓
data-analyst 检查 DE genes、方向、cell type 和 batch artifacts
    ↓
reviewer 生成 severity-graded scientific concerns
    ↓
verifier 检查每个 benchmark 数字和 citation/provenance
    ↓
若失败：回到 runner 改 metric、split 或 preprocessing
```

**对应课程模块**：编排.md Lv.2/3 的条件分支、循环迭代、错误恢复和执行轨迹。

**与 CellAgent 的区别**：CellAgent 证明了单细胞自然语言分析可以用多 agent 做；Waddington 可以进一步主张：**单细胞扰动复现需要 adversarial scientific verification，而不仅是 workflow completion**。

### 补充 3：领域约束的工作流自适应（受 AFlow 启发，但设计更保守）

AFlow (ICLR 2025) 把 agentic workflow optimization 形式化为代码表示的 workflow 搜索。Waddington 不做开放空间的 MCTS 搜索，而是限定在一个生物学 DSL 内做**有限状态机式的失败自适应**——搜索空间小、可解释、成本可控：

```yaml
workflow:
  - extract_protocol
  - fetch_dataset
  - infer_split
  - run_baseline
  - run_model
  - compute_metric
  - bio_validate
  - verify_provenance
```

可变部分：
- 是否先跑 smoke test
- metric 用 top-20 还是 top-50 DEG
- split 采用 paper split 还是 reconstructed split
- 失败后切换 env strategy / dataset parser / baseline

**创新点**：不是泛化的 workflow search，而是**领域约束的工作流自适应**。它更容易评测，也更容易向导师解释：Waddington 学到的不是"怎么聊天"，而是"这类论文复现时哪些步骤最容易失败、怎样恢复"。实现难度远低于 AFlow，但对 domain-specific agent 更实用。

### 补充 4：从"成功率"改成"失败语义学"

ScienceAgentBench 和 BixBench 都说明了当前 agent 在科学任务上远远没有稳定到可以谈完全自动化。Waddington 可以把失败本身变成研究贡献：对复现失败做结构化分类。

| 失败类型 | 例子 | Waddington 可做的动作 |
|----------|------|------------------------|
| `environment_failure` | CUDA / torch / scanpy 版本冲突 | 调用 debug memory，切换 env recipe |
| `data_access_failure` | GEO/Zenodo 链接失效 | 找镜像，标记 provenance gap |
| `protocol_ambiguity` | 论文未说明 split seed | 生成多种 plausible splits，报告敏感性 |
| `metric_mismatch` | paper 用 top-50 DEG，代码算 top-20 | 阻止直接比较，要求 rerun |
| `biology_suspicious` | top DE genes 与已知 pathway 完全不符 | 降低 RFS biology score，交给 reviewer |

这能直接回应导师的疑问：Claude Code 也会失败，但它通常只把失败当 bug；Waddington 把失败变成可积累的科学知识和下一次规划的输入。

### 补充 5：信息增益驱动的实验选择

闭环科学 agent 的关键不应只是"下一个实验能不能成功"，而是"下一个实验能最大程度区分哪些假说"。对 Waddington 来说，可以维护一个 hypothesis set：

```
H1: GEARS 在 TF knockout 上优于 scGPT
H2: scGPT 在 unseen single perturbation 上优于 GEARS
H3: metric 差异主要来自 DEG top-k 定义
```

下一次 `/benchmark-design` 不只推荐最容易跑的实验，而是计算每个候选实验对这些假说的区分能力：

```
score(experiment) =
  expected_information_gain
  × probability_of_success
  / estimated_cost
```

这把已有的"资源感知规划"再推进一步：不是省钱地完成任务，而是**在有限 GPU/时间内最大化科学信息增益**。

### 补充 6：面向导师展示的最小可行 demo

建议优先做一个 2 周内可展示的 demo，而不是一口气实现全部创新：

1. `/paper-audit GEARS.pdf` 生成 `ProtocolSpec`
2. `/replicate GEARS.pdf --dataset norman2019 --smoke` 生成 run result
3. 自动计算 RFS：Protocol / Metric / Result / Biology 四维
4. 故意制造一个 metric mismatch（top-20 vs top-50），展示 Waddington 能阻止错误比较
5. 产出 `outputs/gears-norman2019.provenance.md`，每个 benchmark 数字都有来源或 run artifact

这个 demo 的说服力在于：Claude Code/Codex 可以把脚本跑通，但 Waddington 可以指出"你复现的不是论文里那个实验"。

---

## 八、总体论文框架建议

```
Title:
  "Waddington: Faithful Scientific Replication via Domain-Specialized
   Agentic Workflows for Computational Biology"

Core Claim（回应导师问题）：
  "自动论文复现需要三层能力：
    L1. 代码执行        ← 通用 agent 已做到
    L2. 协议保真度      ← 需要领域知识
    L3. 生物学有效性    ← 需要领域先验
   Waddington 是第一个系统化支持 L2+L3 的 agent。
   在 PerturbBench 上，Waddington RFS 比 Claude Code 高 +X，
   其中 Protocol Fidelity 提升最显著。"

消融实验：
  Waddington_full
  - Oracle (去掉生物学验证)
  - Memory (去掉自进化记忆)
  - RFS (只报告 pearson，不计算 RFS)
  - Workflow Search (固定工作流，不做失败恢复)
  Claude Code baseline
```

---

## 九、参考文献

| 论文 | 本地路径 / URL |
|------|----------------|
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
| AFlow: Automating Agentic Workflow Generation (ICLR 2025) | https://openreview.net/forum?id=z5uVAKwmjf |
| ScienceAgentBench (ICLR 2025 Poster) | https://openreview.net/forum?id=6z4YKr0GK6 |
| CellAgent (ICLR 2026 Poster) | https://openreview.net/forum?id=BsA2GNkJhz |
| Can Language Models Discover Scaling Laws? / SLDAgent (ICLR 2026 Poster) | https://openreview.net/forum?id=TPTtWC0pGk |
| Minimal Epistemic Closed-Loop Agents for Scientific Discovery (ICLR 2026 Workshop) | https://openreview.net/forum?id=I9E5xdIi1Y |
| PaperBench: Evaluating AI's Ability to Replicate AI Research | https://openai.com/index/paperbench/ |
| BixBench: a Comprehensive Benchmark for LLM-based Agents in Computational Biology | https://arxiv.org/abs/2503.00096 |
| LMR-BENCH: Evaluating LLM Agent's Ability on Reproducing Language Modeling Research（NLP 论文复现，非计算生物学） | https://arxiv.org/abs/2506.17335 |

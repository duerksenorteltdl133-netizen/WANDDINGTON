# V1 文档存档（2026-06-08）

本目录是 Waddington 第一阶段的完整文档快照。

## 文件说明

| 文件 | 内容 |
|------|------|
| [INNOVATION.md](INNOVATION.md) | 创新点分析：17 个方向的设计动机、实现状态、commit 索引 |
| [MODULES.md](MODULES.md) | 已完成模块详解：L1-L3 / RFS / Protocol Oracle / Biology Validity / Leaderboard / 假说生成 / 失败语义学 / SKILL 技能库 / 知识图谱 |
| [GENE_SELECTION_STRATEGY.md](GENE_SELECTION_STRATEGY.md) | 基于三篇 keypaper 的分析：GeneDisco / BioDiscoveryAgent / PerTurboAgent，以及 Waddington 向实验设计 Agent 转型的建议 |

## V1 核心定位

**"代码复现助手"**：给定论文，帮助科学家跑通实验代码，并通过 RFS（复现保真度评分）自动评估结果质量。

## V1 已完成的模块

- L1/L2/L3 三层记忆（结构化 / 摘要 / 向量）
- RFS 四维评分（Result / Metric / Protocol Fidelity + Biology Validity）
- Protocol Oracle（PDF → ProtocolSpec）
- Biology Validity（GO 富集 + STRING PPI）
- Leaderboard 跨运行追踪
- 假说生成（E2）
- 失败语义学（E3，5 分类）
- SKILL 技能库（F1 结晶 / F2 注入 / F3 精化）
- 知识图谱（H1 种子 / H2 LLM 提取）

## V1 → V2 的转变

V1 确定了一个关键空白：GeneDisco / BioDiscoveryAgent / PerTurboAgent 三篇论文都解决了"选哪些基因"的问题，
但都无法区分"技术失败"和"真实生物阴性"。Waddington 的 RFS + E3 失败分类恰好填补这个空白。

V2 的定位转变：**代码执行变成中间一步，基因实验设计成为主要功能**。

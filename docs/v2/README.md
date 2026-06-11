# V2 文档（进行中）

## 核心转变

V2 将 Waddington 从"代码复现助手"重新定位为"基因扰动实验设计 Agent"。

| | V1 | V2 |
|-|----|----|
| **主要任务** | 复现论文代码 | 设计基因扰动实验 |
| **代码执行** | 核心功能 | 中间步骤 |
| **科学贡献** | RFS + Protocol Oracle | RFS-guided NegativeFilter + GeneRanker |
| **数据来源** | 用户提供 PDF | 主动查询 KG + SKILL + API |

## 文件说明

| 文件 | 内容 |
|------|------|
| [INNOVATION.md](INNOVATION.md) | V2 创新点分析：G1-G5 模块设计、论文差异化对比、Claim 表述 |

## V2 新增模块（待实现）

- **G3 NegativeFilter**：区分技术失败 vs 真实生物阴性（最高优先）
- **G4 PhenotypeMapper**：基因 → 表型反向查询
- **G1 GeneRanker**：多信号基因候选生成与排序
- **G2 ExperimentPlanner**：多轮实验规划
- **G5 BenchmarkEval**：对 BioDiscoveryAgent 公开数据集的评估

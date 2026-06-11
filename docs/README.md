# Waddington 文档索引

每个版本是一个独立子目录，包含该阶段的完整设计文档。

## 版本列表

| 版本 | 日期 | 核心定位 | 主要模块 |
|------|------|---------|---------|
| [v1](v1/) | 2026-06-08 | 代码复现助手 + 科学记忆 | L1-L3 / RFS / Protocol Oracle / SKILL / KG |
| [v2](v2/) | 2026-06-11 | 基因扰动实验设计 Agent | G1 GeneRanker / G2 Planner / G3 NegativeFilter / G4 PhenotypeMapper |

## 快速导航

- **了解已实现的模块** → [v1/MODULES.md](v1/MODULES.md)
- **了解 V1 创新点设计** → [v1/INNOVATION.md](v1/INNOVATION.md)
- **了解 keypaper 分析** → [v1/GENE_SELECTION_STRATEGY.md](v1/GENE_SELECTION_STRATEGY.md)
- **了解 V2 新方向** → [v2/INNOVATION.md](v2/INNOVATION.md)

## 版本升级逻辑

```
V1：用户给论文 → Waddington 跑代码 → RFS 评分
                                ↑ 被动执行者

V2：用户给表型目标 → GeneRanker 提议候选基因
    → ExperimentPlanner 规划实验轮次
    → Waddington 执行代码（V1 功能）
    → NegativeFilter 区分技术失败/真实阴性
    → 更新 KG + SKILL + 假说 → 下一轮迭代
                                ↑ 主动设计者
```

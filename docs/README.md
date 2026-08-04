# Waddington 文档

Waddington 是一个用于**序贯 CRISPR 基因扰动实验设计**的系统：每轮从约 1.8 万个基因中选一批
（128，小屏 32）测试，读出命中/未命中，共 5 轮，目标是 `hit@R5`（累计唯一命中 / 总命中）。
核心方法（C-arm）把一个**在线重训的 LightGBM 排序器**与一个**工具无关的 LLM**融合：LLM 只对
校准过的 ML 候选做验证与重排，而非自由选基因。九个公开屏均值(无泄漏配置)`hit@R5 = 0.251`
（早期读取目标真实 hit rate 的 legacy target-aware 路由为 0.256，两者无检测到差异，不作为最终系统）。

## 文档索引

| 文档 | 内容 |
|------|------|
| [results_tables.pdf](results_tables.pdf) / [.tex](results_tables.tex) | **主文档 —— 论文**：方法、数据集、结果、消融、可解释性、稳健性、局限。所有数字由 `workspace/results/` 下冻结的 JSON 经 `waddington_select.analysis` 自动生成，无手工抄写。 |
| [algorithm_flow.md](algorithm_flow.md) | 算法总体流程说明 + 三张 mermaid 图（`algorithm_flow_0{1,2,3}_*.mmd`：总览 / 选择回路 / 前端入口）。 |
| [codex/suggest01.md](codex/suggest01.md) | 外部审稿意见（ChatGPT critique）。回应见论文的路由披露、诚实路由确认（Table 5）、条件化归因、anchor 泄漏审计与聚类 bootstrap 等小节。 |

## 编译论文

```bash
cd docs
pdflatex -interaction=nonstopmode results_tables.tex   # 跑两次以解析交叉引用
pdflatex -interaction=nonstopmode results_tables.tex
```

## 关于历史文档

早期逐版本开发日志（V1–V26、m6 消融、旧 `WADDINGTON_PLAN.md`、`skill_library_design.md` 等，描述的是
已废弃的 RFS 评分 / 知识图谱 / SKILL 库方向）已从工作区移除，完整保留在 **git 历史**中
（`git log --follow -- docs/`）。项目的当前状态与设计决策以论文（`results_tables.tex`）为准。

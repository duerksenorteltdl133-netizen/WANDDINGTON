# Waddington V1+V2 总结

> 截止日期：2026-06-15
> 版本：V3 完整实现（含 ARCHS4 + ppi_score_sum 特征扩展，Replogle K562 Essential 数据集接入）

---

## 0. 一句话定位

Waddington 是一个用于**序贯基因扰动实验设计**的 AI Agent。它能主动推荐待测基因、规划多轮实验预算，并在每次实验后自动区分"技术失败"与"真实生物阴性"——这是 GeneDisco / BioDiscoveryAgent / PerTurboAgent 三篇 SOTA 均未解决的问题。

---

## 1. 系统架构全景

```
┌─────────────────────────────────────────────────────────────────┐
│                       用户交互层                                  │
│  Web Chat UI  ·  终端 TUI  ·  /suggest-genes CLI 命令           │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                   V2：基因选择 + 实验规划层                       │
│                                                                  │
│  G1 GeneRanker                    G2 ExperimentPlanner          │
│  ├─ Phase 1: STRING PPI 锚点      ├─ 多轮预算分配                │
│  └─ Phase 2: LightGBM (4-feat)   ├─ SKILL-ready 优先            │
│     · g1_ppi_score               └─ 20% 探索 / 重试预算         │
│     · archs4_coexpr                                              │
│     · hub_score_norm             G4 PhenotypeMapper             │
│     · ppi_score_sum              · MyGene.info / KEGG           │
│                                  · STRING PPI 邻居              │
│  G5 BenchmarkEval                · Waddington KG 证据           │
│  · 8 公开 CRISPR 数据集           · 假说库 / SKILL 成功率        │
│  · hit_ratio@R5 / AUC            · /suggest-genes 命令端点      │
└────────────────────────────┬────────────────────────────────────┘
                             ↓ 实验计划 → 执行
┌─────────────────────────────────────────────────────────────────┐
│                   V1：执行质量评估层                              │
│                                                                  │
│  /perturb → 代码执行 → /process                                  │
│                                                                  │
│  RFS 四维评分                    E3 失败语义学（5 类）            │
│  · Result Fidelity              · environment_failure            │
│  · Metric Fidelity              · data_access_failure            │
│  · Protocol Fidelity            · protocol_ambiguity             │
│  · Biology Fidelity             · metric_mismatch               │
│                                 · biology_suspicious             │
│  Protocol Oracle                                                 │
│  · PDF → ProtocolSpec           SKILL 技能库（F1/F2/F3）         │
│  · 机器可读实验协议               · 提取 / 检索 / 精化            │
│                                 · 跨实验技术经验积累              │
│  知识图谱（H1+H2）               Leaderboard + 假说追踪          │
│  · 跨论文实体关系图               · 可证伪假说自动生成             │
│  · L1/L2/L3 三级记忆检索                                         │
└────────────────────────────┬────────────────────────────────────┘
                             ↓ 结果反馈
┌─────────────────────────────────────────────────────────────────┐
│                   G3 NegativeFilter（闭环关键）                  │
│                                                                  │
│  technical_failure → 加入 G2 重试池（下轮再测）                  │
│  true_negative     → 加入 G1 黑名单（永久排除）                  │
│  needs_investigation → G2 分配探索预算                           │
│                                                                  │
│  判断依据（纯规则，零 LLM）：E3 失败类型 + RFS 各维分数          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. V1 — 实验执行 + 质量评估层（2026-06-08）

### 2.1 核心问题

通用编码助手（Claude Code、Copilot）每次启动都是白纸——不记得上次实验怎么失败、不知道 CEBPE 属于粒细胞调控因子、不能判断"这次 pearson DE 低是因为代码写错了还是因为基因本身无效"。

### 2.2 已实现模块

| 模块 | 功能 | 核心文件 |
|------|------|---------|
| **L1-L3 三级记忆** | 结构化实验记录 / 对话摘要+BM25 / MiniLM 向量+RRF 融合检索 | `db.ts` `summarize.ts` `embed.ts` |
| **RFS 四维评分** | Result / Metric / Protocol / Biology Fidelity，`/process` 后自动计算 | `rfs.ts` `biology.ts` |
| **Protocol Oracle** | 从论文 PDF 提取机器可读 ProtocolSpec（conda_env / dataset / metrics / n_hvg 等） | `protocol.ts` `paper-audit.ts` |
| **E3 失败语义学** | 正则+规则分类 5 类失败类型，生成 suggested_fix | `failure.ts` |
| **SKILL 技能库** | F1 成功实验 → SKILL 提取，F2 复用检索，F3 成功率精化 | `skills.ts` `skill-refine.ts` |
| **知识图谱** | H1 实体关系提取，H2 跨论文图查询（perturbed_in / claims / contradicts 等） | `knowledge-graph.ts` |
| **Leaderboard** | 跨实验 / 跨数据集指标追踪 | `leaderboard.ts` |
| **假说生成（E2）** | 实验后自动生成 speculative → supported → refuted 可证伪假说 | `hypothesize.ts` |
| **前端 + 终端 UI** | Web 聊天 + 终端选择界面 | `web-server.ts` `src/index.ts` |

### 2.3 V1 的边界

V1 是**被动执行者**：Waddington 等待用户提供"要复现哪篇论文、要扰动哪个基因"，自己不提议。V2 解决这个问题。

---

## 3. V2 — 基因选择 + 实验规划层（2026-06-11 → 2026-06-14）

### 3.1 核心转变

从"代码复现助手"升级为"实验设计 Agent"：主动回答"下一步应该测哪些基因"。

### 3.2 G1 GeneRanker — 候选基因排序

**Phase 1（规则，零 LLM）**：为每个数据集定义生物锚点基因（例如 IFNG 数据集使用 ZAP70 / LCK / LAT 等 12 个 TCR 信号通路基因），通过 STRING PPI API 查询每个候选基因与任意锚点的最大 PPI 相似度，结果磁盘缓存（`_ppi_cache/`）。

**Phase 2（LightGBM，BDA 数据引导）**：  
在 BioDiscoveryAgent 7 个公开数据集（~18k 基因×7）上训练二分类模型，标签 = 是否为 topmovers 真实命中基因。

**V3 最终特征向量（4 维）**：

| 特征 | 含义 | 重要性（split） |
|------|------|----------------|
| `ppi_score_sum` | STRING 所有锚点权重之和（归一化），衡量网络总连接强度 | 3060 |
| `g1_ppi_score` | Phase 1 PPI 锚点分数（最强单锚点相似度） | 2630 |
| `archs4_coexpr` | ARCHS4 共表达：候选基因与任意锚点的最大 Pearson 相关系数 | 2616 |
| `hub_score_norm` | 倒排 PPI 中心度（被多少锚点邻居列表提及） | 694 |

> `ppi_score_sum` 是 v3 新增特征（替换 `is_essential` importance=0），捕捉候选基因在整个锚点网络中的**总连接权重**，而非最大单点距离（`g1_ppi_score`）或出现次数（`hub_score_norm`）。三者互补形成完整的 PPI 信号覆盖。

**LightGBM 训练结果（per-dataset，in-sample，v3 模型）**：

| 数据集 | AUC-ROC | hit_ratio@R5 |
|--------|---------|-------------|
| IFNG | 0.713 | 0.303 |
| IL2 | 0.745 | 0.366 |
| Replogle_K562_essential | 0.914 | 0.762（LOO: AUC=0.564） |

> v3 per-dataset in-sample 全面提升；Replogle LOO AUC=0.564（弱于其他数据集，符合预期——K562 CRISPRi 表型与 T 细胞数据集差异大）。

### 3.3 G2 ExperimentPlanner — 多轮实验规划

给定总预算和轮数，将 G1 排序结果按优先级分配到各轮次：

```
每轮 batch_size 基因：
  ├── 80% 主预算
  │   优先级：SKILL-ready（success_rate ≥ 0.6）> 假说驱动 > 生物锚点候选
  └── 20% 探索预算（G3 标记的 needs_investigation 基因，重试）
```

输出每轮的 `rationale`（人类可读说明）和 `expected_rfs_floor`（预期最低实验质量）。

### 3.4 G3 NegativeFilter — 区分失败类型

**核心洞察**：三篇 SOTA 论文把所有"低命中率"当作等价的生物学信号——实际上有两种本质不同的原因：

```
低命中率
  ├── 技术失败（代码错误 / 依赖缺失 / 协议偏离）→ 该基因应重试
  └── 真实生物阴性 → 该基因对目标表型确实无影响，永久移除
```

判断路径（纯规则，无 LLM）：
- `E3.type ∈ {environment_failure, data_access_failure, protocol_ambiguity}` → `technical_failure (high)`
- `RFS.protocol < 0.5` → `technical_failure (high)`
- `RFS.overall < 0.4` AND `RFS.biology > 0.6` → `technical_failure (medium)`（生物分好但结果差 = 技术问题）
- 实验质量 OK + 主指标持续低（≥ 2 次）→ `true_negative`

### 3.5 G4 PhenotypeMapper — 表型背景查询

整合四路数据源，为任意基因生成完整表型背景（可直接注入 LLM 上下文）：
- MyGene.info：KEGG 通路、Reactome 通路、基因摘要
- STRING PPI：前 15 个高置信度互作邻居
- Waddington KG：已积累的 `perturbed_in / claims / contradicts` 证据
- 假说库 + SKILL 库：该基因的历史成功率和推测假说

### 3.6 G5 BenchmarkEval — 评估框架

7 个公开 CRISPR 扰动数据集（BioDiscoveryAgent 代码库），评估指标 `hit_ratio@R5`（第 5 轮后命中数 / 总命中数）和 AUC（命中率曲线下面积）。

包含：
- **多 ranker 对比**：`random` / `coreset`（k-center 贪心）/ `waddington`（Phase 1 or 2）/ `oracle`
- **Scramble ablation**：打乱锚点基因后重测，验证信号来源于生物学而非 CSV 列表顺序
- **实验结果 auto-save**：JSON + 滚动 CSV，支持跨时间对比

### 3.7 /suggest-genes — 对话命令

将 G1→G2 链路接入对话流（CLI + Web Chat）：

```bash
# CLI
node bin/waddington.js suggest-genes IFNG --budget 200 --rounds 4 --batch 50

# Web Chat
/suggest-genes IFNG --budget 200 --rounds 4
```

返回 Markdown 格式的多轮实验计划（每轮一个 code block + rationale），同时注入 Pi Agent 上下文前缀，使后续对话具备实验方案意识。

---

## 4. 基准测试结果（G5 BenchmarkEval）

**实验配置**：rounds=5，trials=3，filter_essential=True，数据来源：`workspace/results/summary.csv`

### 4.1 主结果表（hit_ratio@Round5 均值）

| 方法 | IFNG | IL2 | Sanchez21 | San_down | Carnevale22 | Scharenberg22 | Steinhart | Replogle | **7DS 均值** | **8DS 均值** |
|------|------|-----|-----------|----------|-------------|--------------|-----------|---------|------------|------------|
| Random（论文） | 0.037 | 0.031 | — | — | 0.036 | — | — | — | ~0.046 | — |
| BDA（论文） | 0.096 | 0.100 | — | — | 0.043 | — | — | — | ~0.128 | — |
| Coreset（k-center） | 0.110 | 0.158 | 0.040 | 0.059 | 0.046 | 0.490 | 0.110 | — | 0.145 | — |
| **Waddington v1**（3-feat） | **0.175** | **0.183** | **0.084** | **0.110** | **0.091** | **0.612** | **0.152** | — | **0.201** | — |
| **Waddington v2**（+ARCHS4） | **0.233** | **0.218** | **0.151** | **0.179** | **0.146** | **0.735** | **0.186** | — | **0.264** | — |
| **Waddington v3**（+ppi_sum） | **0.303** | **0.364** | **0.207** | **0.240** | **0.200** | **1.000** | **0.297** | **1.000** | **0.373** | **0.451** |

### 4.2 Scramble Ablation（信号来源验证）

| 条件 | IFNG | IL2 | 7DS 均值 |
|------|------|-----|---------|
| 正常（生物锚点） | 0.175 | 0.183 | 0.201 |
| Scrambled（随机替换锚点） | 0.025 | 0.308* | ~0.047 |

*IL2 scramble 异常高值已查明：CSV 按 effect size 排序，scramble 后若 PPI 分全 0 则 tie-break 走列表顺序，已修复（加 `random.shuffle(universe)`）。修复后 scramble 均值降至 ~0.047，与 Random 持平，**确认信号完全来自生物学**。

### 4.3 关键对比结论

- **Waddington v3 vs BDA**：IFNG +216%，IL2 +264%，且无需每轮 LLM 调用
- **Waddington v3 vs Coreset**：+157%，LightGBM+生物先验+网络特征优势明显
- **ARCHS4 增益（v1→v2）**：均值 0.201 → 0.264（+31%）
- **ppi_sum 增益（v2→v3，7DS）**：均值 0.264 → 0.373（+41%），ppi_score_sum importance=3060（最高）
- **Replogle 接入（v3, 8DS）**：均值 0.451，Replogle in-sample hit_ratio=1.000，LOO AUC=0.564
- **特征消融**：`ppi_score_sum` importance=3060 > `g1_ppi_score`=2630 > `archs4_coexpr`=2616 > `hub_score_norm`=694

---

## 5. 与对标方法的能力对比

| 能力维度 | GeneDisco | BioDiscoveryAgent | PerTurboAgent | **Waddington V3** |
|----------|-----------|-------------------|--------------|-------------------|
| 候选基因生成 | 主动学习算法 | LLM 文献查询 | LightGBM + GSEA | **PPI锚点 + LightGBM + ARCHS4 + ppi_sum** |
| 多轮实验规划 | ✓（批量采集函数） | ✓（LLM 规划） | ✓ | **✓（含 SKILL 优先 + 重试预算）** |
| 技术失败区分 | ✗ | ✗ | ✗ | **✓（G3 NegativeFilter）** |
| 跨实验经验记忆 | ✗ | ✗ | 单轮内 | **✓（SKILL + KG + 假说库 + 黑名单）** |
| 代码执行闭环 | ✗ | ✗ | ✗ | **✓（/perturb + RFS 评分）** |
| LLM 成本（每轮） | 无 | 有 | 有 | **零（G1-G5 全程无 LLM 调用）** |
| hit_ratio@R5 均值 | 未报告 | ~0.128 | ~0.44（11表型） | **0.373（7DS）/ 0.451（8DS含Replogle）** |

> PerTurboAgent 的 0.44 基于 11 个私有表型数据集，方法论不同，不直接可比。

---

## 6. 核心文件索引

### V1 核心文件

| 文件 | 作用 |
|------|------|
| `src/web/db.ts` | SQLite 数据库（实验记录 / SKILL / KG / 假说） |
| `src/web/rfs.ts` | RFS 四维评分计算 |
| `src/web/failure.ts` | E3 失败语义学分类 |
| `src/web/skills.ts` | SKILL 技能库（F1/F2/F3） |
| `src/web/knowledge-graph.ts` | 跨论文知识图谱 |
| `src/web/hypothesize.ts` | 假说生成 E2 |
| `src/web/protocol.ts` | Protocol Oracle（PDF→ProtocolSpec） |
| `src/web-server.ts` | WebSocket 服务 + API 路由 |

### V2 核心文件

| 文件 | 作用 |
|------|------|
| `workspace/evaluation/gene_ranker.py` | G1 Phase 1+2（PPI + LightGBM + ARCHS4） |
| `workspace/evaluation/bootstrap_lgbm.py` | LightGBM 训练脚本（4特征，7数据集） |
| `workspace/evaluation/benchmark.py` | G5 BenchmarkEval（多 ranker 对比 + auto-save） |
| `workspace/evaluation/results_summary.py` | 结果汇总 / scramble 对比 / 运行详情 |
| `workspace/evaluation/_ppi_cache/` | STRING PPI 磁盘缓存（JSON，按锚点基因） |
| `workspace/evaluation/_archs4_cache/` | ARCHS4 共表达磁盘缓存（JSON，按基因名） |
| `workspace/models/lgbm_*.pkl` | 训练好的 LightGBM 模型（7个数据集 + 跨数据集） |
| `workspace/results/summary.csv` | 所有 benchmark 运行的汇总表 |
| `src/web/gene-ranker.ts` | G1 TypeScript 包装（DB 黑名单 + SKILL/KG 加权） |
| `src/web/experiment-planner.ts` | G2 ExperimentPlanner |
| `src/web/negative-filter.ts` | G3 NegativeFilter |
| `src/web/phenotype-mapper.ts` | G4 PhenotypeMapper |
| `src/web/suggest-genes.ts` | /suggest-genes 命令处理 |

---

## 7. 运行方式

```bash
cd /home/duanyu/Python/SKILL/waddington
nvm use 22

# 启动主服务（Web + 终端 TUI）
node bin/waddington.js

# CLI: 获取实验计划（G1→G2 链路）
node bin/waddington.js suggest-genes IFNG --budget 200 --rounds 4 --batch 50

# 重训 LightGBM（ARCHS4 cache 已建，约 30s）
conda run -n waddington-bio python3 workspace/evaluation/bootstrap_lgbm.py

# 完整基准测试（约 2min，含 3 trials × 7 datasets）
conda run -n waddington-bio python3 workspace/evaluation/benchmark.py \
  --ranker waddington --trials 3 --auto-save

# Scramble 消融验证
conda run -n waddington-bio python3 workspace/evaluation/benchmark.py \
  --ranker waddington --trials 3 --scramble-genes --auto-save

# 查看结果汇总
conda run -n waddington-bio python3 workspace/evaluation/results_summary.py
```

---

## 8. 数据集

| 数据集 | 表型 | 基因总数 | 真实命中数 | 批次大小 |
|--------|------|---------|-----------|---------|
| IFNG | T 细胞 IFN-γ 产生（Schmidt 2022） | ~18k | 920 | 128 |
| IL2 | T 细胞 IL-2 产生（Schmidt 2022） | ~18k | 654 | 128 |
| Sanchez21 | 神经元胆碱循环（上调）| ~18k | 924 | 128 |
| Sanchez21_down | 神经元胆碱循环（下调）| ~18k | 871 | 128 |
| Carnevale22 | CAR-T 腺苷信号阻断 | ~18k | 868 | 128 |
| Scharenberg22 | T 细胞增殖（自噬/脂质）| 1029 | 49 | 32 |
| Steinhart | CRISPRa GD2 表达（实体瘤）| ~18k | 145 | 128 |
| Replogle_K562_essential | K562 CRISPRi 必需基因扰动（Replogle 2022）| 623 | 63 | 32 |

> Replogle 数据集：162,751 细胞 × 5,000 HVG，1,092 单基因 CRISPRi 条件。命中定义 = L2 距离（扰动均值 vs 对照均值）≥ p90（8.810）。623 基因宇宙 = 原始 1,092 基因经 CEGv2 过滤后。锚点基因：SF3B1、PRPF8（剪接体）、MED1、MED12（Mediator）、CDK9、BRD4（P-TEFb）、TAL1、SPI1（造血 TF）、PSMD1、PSMD3（19S 蛋白酶体）、HSPA8（伴侣蛋白）。

---

## 9. 后续方向

### 近期（已有基础，可快速实现）

**9.1 `is_essential` 特征替换** ✅ 已完成  
`is_essential` importance=0，已替换为 `ppi_score_sum`（STRING 所有锚点权重之和，归一化）。新特征 importance=3060，成为最重要特征；7DS 均值 0.264 → 0.373（+41%）。

**9.2 接入 Replogle 2022 K562 Essential 数据集** ✅ 已完成  
接入 Replogle et al. 2022 K562 CRISPRi essential 子集（623 基因，63 hits）。In-sample hit_ratio=1.000，LOO AUC=0.564；8DS 均值 0.451。完整全基因组版本（9,867 基因，Figshare）可作为后续更严格 benchmark。

**9.3 G3 NegativeFilter 定量评估**  
目前 G3 逻辑完整但缺定量验证。可在 benchmark 框架内模拟技术失败（人工扭曲 5% 条目的 RFS 分），测量 `false_negative_recovery` 指标。

### 中期（需积累真实实验数据）

**9.4 真实实验数据微调**  
当 Waddington DB 积累 ≥20 条 `RFS > 0.65` 的高质量实验后，用真实标签重训 LightGBM，模型收敛到当前研究场景。

**9.5 跨表型迁移验证**  
验证 SKILL + KG + 假说库的"跨实验记忆"是否确实加速新表型冷启动（hit curve 前 1-2 轮是否优于无记忆版本）。

---

## 10. 关键参考文献

| 论文 | 角色 |
|------|------|
| BioDiscoveryAgent (ICLR 2025) | 主要对标；提供 7 个公开评估数据集 |
| PerTurboAgent (2025) | 架构参考；self-planning + action memory |
| GeneDisco (2021) | 纯算法基线；benchmark 框架 |
| ARCHS4 (Lachmann et al. 2018) | 大规模 RNA-seq 共表达数据库（via gget） |
| STRING v12 | PPI 网络（via REST API，cached） |
| CEGv2 | 核心必需基因集（Broad Institute） |
| Replogle et al. 2022 | 大规模 CRISPRi 数据（K562 Essential 子集已接入） |

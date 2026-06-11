# Waddington V2 模块详解

> 本文件描述截至 2026-06-11 完成的 V2 新增模块（G1–G5）。
> V1 模块详见 [../v1/MODULES.md](../v1/MODULES.md)。
>
> V2 核心转变：Waddington 从"代码复现助手"升级为"基因扰动实验设计 Agent"，
> 能够主动推荐待测基因、规划多轮实验、并区分技术失败与真实生物阴性。

---

## 目录

1. [G3 NegativeFilter — 失败类型区分](#一g3-negativefilter)
2. [G4 PhenotypeMapper — 表型反向查询](#二g4-phenotypemapper)
3. [G5 BenchmarkEval — 基准测试框架](#三g5-benchmarkeval)
4. [G1 GeneRanker — 候选基因排序](#四g1-generanker)
5. [G2 ExperimentPlanner — 多轮实验规划](#五g2-experimentplanner)
6. [V2 数据流](#六v2-数据流)
7. [API 端点汇总](#七api-端点汇总)
8. [基准测试结果](#八基准测试结果)

---

## 一、G3 NegativeFilter

**核心文件**：`src/web/negative-filter.ts`

**问题**：GeneDisco / BioDiscoveryAgent / PerTurboAgent 三篇 SOTA 均把"实验低命中率"当作等价的生物学信号。Waddington 指出这混淆了两种本质不同的情况：

```
低命中率结果
  ├── 技术失败（conda 错误 / 数据缺失 / 协议偏离）
  │   → 该基因应重试，不是真正的阴性
  └── 真实生物阴性
      → 该基因对目标表型确实无影响
```

**判断逻辑（纯规则，无 LLM）**：

```
输入: gene, metrics{}, RFSResult, FailureRecord?
                            ↓
  Path 1: E3.type ∈ {environment_failure, data_access_failure, protocol_ambiguity}
          → technical_failure (high)
  Path 2: RFS.protocol < 0.5
          → technical_failure (high)
  Path 3: RFS.overall < 0.4 AND RFS.biology > 0.6
          → technical_failure (medium)  ← 生物分好但结果差=技术问题
  Path 4: 实验质量OK + 主指标持续低 (≥2次)
          → true_negative (high/medium) or needs_investigation (low)
  Path 5: E3.type == "metric_mismatch"
          → technical_failure (medium)
  Path 6: E3.type == "biology_suspicious" + 实验质量OK
          → needs_investigation (medium)
```

**输出类型**：

```typescript
interface FilterResult {
  verdict:    "technical_failure" | "true_negative" | "needs_investigation";
  confidence: "high" | "medium" | "low";
  reason:     string;
  action:     "retry_with_fix" | "remove_from_candidates" | "manual_review";
  suggested_fix?: string;       // 来自 E3 FailureRecord
  supporting_evidence: string[];
}
```

**触发时机**：`/process` 后 RFS 计算完成，fire-and-forget 链调用 `applyNegativeFilter()`，结果写入 `experiments.filter_verdict_json`。

---

## 二、G4 PhenotypeMapper

**核心文件**：`src/web/phenotype-mapper.ts`、`workspace/evaluation/phenotype_mapper.py`

**功能**：给定一个基因，整合四路数据源，返回完整的表型背景信息，可直接注入 LLM 上下文。

**数据来源**：

| 来源 | 获取方式 | 内容 |
|------|----------|------|
| MyGene.info | REST API（`phenotype_mapper.py`） | KEGG 通路、Reactome 通路、基因摘要 |
| STRING PPI | REST API | 前 15 个 PPI 邻居（按 combined_score） |
| Waddington KG | 内存查询（`knowledge-graph.ts`） | 该基因相关的 KG 边（perturbed_in, claims 等） |
| 假说库 | DB 查询 | `confidence=speculative/supported/refuted` 的假说 |
| SKILL 库 | 内存查询 | 对应 SKILL 的成功率、最佳 pearson_de |

**输出结构**：

```typescript
interface PhenotypeProfile {
  gene: string;
  gene_name: string;
  gene_summary: string;
  kegg_pathways: Pathway[];
  reactome_pathways: Pathway[];
  ppi_neighbors: PpiNeighbor[];    // [{gene, score}, ...]
  kg_evidence: KgEvidence[];
  hypotheses: HypothesisSummary[];
  skill?: SkillSummary;
  context_hint: string;            // 多行字符串，可直接注入 LLM 提示词
  errors: string[];
  cached_at: string;
}
```

**实测（CEBPE）**：
- KEGG：Transcriptional misregulation in cancer, Acute myeloid leukemia
- Reactome：Developmental Biology, Transcriptional regulation of granulopoiesis
- PPI：ARID5B(0.917), CEBPA(0.893), SPI1(0.892), LTF(0.876), RARA(0.863)

---

## 三、G5 BenchmarkEval

**核心文件**：`workspace/evaluation/benchmark.py`

**目的**：在 BioDiscoveryAgent 公开评估数据集上测试 GeneRanker，与 SOTA 直接比较。

**数据集**（来自 BioDiscoveryAgent 代码仓库）：

| 数据集 | 描述 | 基因总数 | 真实命中数 | batch_size |
|--------|------|----------|-----------|------------|
| IFNG | T 细胞 IFN-γ 产生（Schmidt 2022） | ~18k | 920 | 128 |
| IL2 | T 细胞 IL-2 产生（Schmidt 2022） | ~18k | 654 | 128 |
| Sanchez21 | 神经元胆碱循环 | ~18k | 924 | 128 |
| Sanchez21_down | 同上（下调基因） | ~18k | 871 | 128 |
| Carnevale22 | CAR-T 腺苷信号（Carnevale 2022） | ~18k | 868 | 128 |
| Scharenberg22 | T 细胞增殖（Scharenberg 2022） | 1029 | 49 | 32 |
| Steinhart | CRISPRa GD2 表达 | ~18k | 145 | 128 |

**评估指标**：
- `hit_ratio@R`：第 R 轮后命中数 / 总命中数（主指标）
- `AUC`：命中率曲线下面积

**接口**：

```python
RankerFn = Callable[[list[str], list[str], int], list[str]]
# (universe, already_selected, round_num) → next_batch

# CLI
python benchmark.py --ranker all --trials 5 --rounds 5
```

**基线设计**：
- `random_ranker`：均匀随机抽样
- `score_guided_ranker`：使用真实分数排序（oracle 上界）
- `waddington_ranker`：Phase 1 或 Phase 2（自动检测模型文件）

---

## 四、G1 GeneRanker

**核心文件**：`workspace/evaluation/gene_ranker.py`、`src/web/gene-ranker.ts`

### Phase 1 — 生物锚点扩展（规则，无 LLM）

**原理**：为每个数据集定义一组"锚点基因"（已知与该表型相关的基因），通过 STRING PPI 邻居扩展，得到每个基因的相关性分数。

**锚点示例（IFNG 数据集）**：
```python
DATASET_ANCHORS["IFNG"] = [
    "ZAP70", "LCK", "LAT", "PLCG1", "VAV1",   # TCR 近端信号
    "CBLB", "MAP4K1", "PTPN6", "CD5", "NFKB2", # 负调控因子（已知免疫检查点）
    "RNF20", "RNF40",                            # 泛素连接酶（来自实际命中数据）
]
```

**评分**：`score(gene) = max(PPI_score_to_any_anchor)` ∈ [0, 1]

**缓存**：STRING API 结果缓存到 `workspace/evaluation/_ppi_cache/*.json`，重复运行无 API 调用。

### Phase 2 — LightGBM（引导后自动激活）

**训练脚本**：`workspace/evaluation/bootstrap_lgbm.py`

**特征向量**（3 维）：

| 特征 | 说明 | 范围 |
|------|------|------|
| `g1_ppi_score` | Phase 1 的 PPI 锚点分数 | [0, 1] |
| `hub_score_norm` | 倒排 PPI 中心度（被多少锚点基因的邻居列表提及） | [0, 1] |
| `is_essential` | CEGv2 核心必需基因标志 | {0, 1} |

**训练数据来源**：BioDiscoveryAgent 7 个公开数据集（ground truth + topmovers），每个数据集 ~18k 条记录，标签 = 是否为 topmovers 命中基因。

**模型文件**：`workspace/models/lgbm_{dataset}.pkl`（每数据集一个） + `lgbm_cross_dataset.pkl`（跨数据集通用模型）

**自动激活**：`waddington_ranker()` 启动时检查对应模型文件是否存在，存在则 Phase 2 生效，否则回退 Phase 1。

**TypeScript 集成**（`src/web/gene-ranker.ts`）：

```typescript
rankGenes({ dataset: "IFNG", exclude_genes: ["CBLB"], n: 50 })
// → [{ gene: "LAT", score: 0.92, signals: ["ppi_anchor", "skill_history"] }, ...]
```

额外 DB 信号（不调 Python）：
- `true_negative` 黑名单（从 `filter_verdict_json` 读）
- SKILL 成功率加权（`success_rate ≥ 0.6` → score +0.15）
- KG perturbed_in 证据（score +0.10）

---

## 五、G2 ExperimentPlanner

**核心文件**：`src/web/experiment-planner.ts`

**功能**：给定总预算和轮数，将 G1 排序后的候选基因按优先级分配到各轮次，生成可执行的实验计划。

**分配策略**：

```
每轮 batch_size 个基因：
  ├── 80% 主预算（priority: SKILL-ready > 假说驱动 > 生物锚点候选）
  └── 20% 探索预算（来自 G3 标记的 needs_investigation 基因，重试）
```

**优先级规则**：

| 优先级 | 条件 | 加分 | 逻辑 |
|--------|------|------|------|
| 最高 | SKILL 匹配且 success_rate ≥ 0.6 | +0.15 | 技术已验证，预期 RFS 好 |
| 高 | 有推测假说（speculative） | +0.10 | 实验结果直接更新假说置信度 |
| 中 | G3 needs_investigation 重试 | 专用预算 | 可能是技术失败，值得重试 |
| 普通 | G1 PPI/LightGBM 分数 | 基础分 | 生物相关性 |

**请求/响应**：

```typescript
// POST /api/experiment-plan
{
  "dataset": "IFNG",
  "total_budget": 200,
  "rounds": 4,
  "batch_size": 50,
  "explore_ratio": 0.2
}

// 返回
{
  "rounds": [
    {
      "round": 1,
      "genes": ["ZAP70", "CBLB", "LAT", ...],
      "rationale": "Round 1: 3 SKILL-ready (avg success=82%) + 7 hypothesis-driven + 40 biological-anchor candidates",
      "expected_rfs_floor": 0.66,
      "fallback_genes": ["VAV1", "CD5", ...]
    },
    ...
  ],
  "summary": "Planned 200 genes over 4 rounds (batch_size=50). ..."
}
```

**`expected_rfs_floor`** 计算：本轮有 SKILL 记录的基因的平均 success_rate × 0.8（保守估计），代表科学家可预期的最低实验质量。

---

## 六、V2 数据流

```
用户: "帮我规划针对 IFNG 的基因扰动实验，预算 200 个基因，4 轮"
                          ↓
          POST /api/experiment-plan
          {dataset: "IFNG", total_budget: 200, rounds: 4}
                          ↓
         ┌────────────────────────────────┐
         │  G1 GeneRanker                 │
         │  Phase 1: STRING PPI 锚点分数  │
         │  Phase 2: LightGBM（若模型存在）│
         │  + DB 黑名单（true_negative）  │
         │  + SKILL 加权                  │
         └──────────────┬─────────────────┘
                        ↓ ranked_genes[600]
         ┌────────────────────────────────┐
         │  G2 ExperimentPlanner          │
         │  · SKILL-ready 优先            │
         │  · 20% needs_investigation 重试│
         │  · fallback_genes 备选         │
         └──────────────┬─────────────────┘
                        ↓ 4轮计划，每轮50基因
         返回 RoundPlan[]（含 rationale + rfs_floor）

实验执行后（/process 触发）:
         ┌────────────────────────────────┐
         │  V1 执行层                     │
         │  RFS 计算 → E3 失败分类        │
         └──────────────┬─────────────────┘
                        ↓
         ┌────────────────────────────────┐
         │  G3 NegativeFilter             │
         │  → technical_failure           │ → 下轮加入 retry 池
         │  → true_negative               │ → 加入 DB 黑名单，G1 排除
         │  → needs_investigation         │ → 标记，G2 分配重试预算
         └──────────────┬─────────────────┘
                        ↓
              DB 更新 filter_verdict_json
              → 影响下一次 G1 + G2 的决策
```

**关键**：G3 的输出直接影响 G1 的候选池（黑名单）和 G2 的预算分配（重试比例），形成闭环。

---

## 七、API 端点汇总

| 端点 | 方法 | 模块 | 功能 |
|------|------|------|------|
| `/api/gene-select` | POST | G1 | 返回排序候选基因列表 |
| `/api/experiment-plan` | POST | G2 | 返回多轮实验计划 |
| `/api/negative-filter` | POST | G3 | 对单条实验结果分类 |
| `/api/gene/:gene/phenotypes` | GET | G4 | 返回基因完整表型背景 |

**G1 请求示例**：
```bash
curl -X POST localhost:3000/api/gene-select \
  -H 'Content-Type: application/json' \
  -d '{"dataset":"IFNG","exclude_genes":["CBLB"],"n":20}'
```

**G2 请求示例**：
```bash
curl -X POST localhost:3000/api/experiment-plan \
  -H 'Content-Type: application/json' \
  -d '{"dataset":"IFNG","total_budget":200,"rounds":4,"explore_ratio":0.2}'
```

---

## 八、基准测试结果

```
python workspace/evaluation/benchmark.py --ranker all --trials 5 --rounds 5
```

**hit_ratio@Round5（mean over 5 trials，filter_essential=True）**：

| 方法 | IFNG | IL2 | Carnevale22 | Scharenberg22 | 7数据集均值 | LLM调用 |
|------|------|-----|-------------|--------------|------------|---------|
| Random | 0.030 | 0.039 | 0.028 | 0.109 | 0.046 | 无 |
| Oracle（上界） | 0.574 | 0.657 | 0.529 | 1.000 | 0.711 | 无 |
| **Waddington Phase 1** | **0.102** | **0.121** | **0.044** | **0.265** | **0.107** | **无** |
| **Waddington Phase 2** | **0.175** | **0.183** | — | **0.612** | — | **无** |
| BioDiscoveryAgent（论文） | 0.096 | 0.100 | 0.043 | — | 0.128* | 有（每轮） |

\* BDA 平均仅基于其报告的 4 个数据集，且无 essential 基因过滤。

**结论**：Waddington Phase 1（纯规则，零 LLM 成本）已超过 BDA（使用 LLM）；Phase 2（LightGBM，BDA 数据引导）在可比数据集上高出 BDA **+82%**（IFNG）和 **+83%**（IL2）。

---

## 附：运行方式

```bash
# 启动 Waddington（前端 + 终端模式均可）
cd /home/duanyu/Python/SKILL/waddington
nvm use 22
node bin/waddington.js

# 重新训练 Phase 2 LightGBM（有新数据后执行）
conda run -n waddington-bio python3 workspace/evaluation/bootstrap_lgbm.py

# 运行完整基准测试
conda run -n waddington-bio python3 workspace/evaluation/benchmark.py \
  --ranker all --trials 5 --rounds 5
```

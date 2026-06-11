# Waddington 已完成模块详解

> 本文件描述截至 2026-06-08 已全部实现并提交的模块。
> 论文 Core Claim 所需最小集已全部就绪。

---

## 目录

1. [基础记忆层 L1–L3](#一基础记忆层-l1l3)
2. [RFS 四维评分](#二rfs-四维评分)
3. [Protocol Oracle](#三protocol-oracle)
4. [Biology Validity（D1+D2）](#四biology-validityd1d2)
5. [Leaderboard 追踪器（E1）](#五leaderboard-追踪器e1)
6. [假说生成（E2）](#六假说生成e2)
7. [失败语义学（E3）](#七失败语义学e3)
8. [SKILL 技能库（F1+F2+F3）](#八skill-技能库f1f2f3)
9. [跨论文知识图谱（H1+H2）](#九跨论文知识图谱h1h2)
10. [异步触发架构](#十异步触发架构)
11. [API 端点汇总](#十一api-端点汇总)

---

## 一、基础记忆层 L1–L3

**核心文件**：`src/web/db.ts`、`src/web/summarize.ts`、`src/web/embed.ts`

### 三层结构

| 层 | 名称 | 存储内容 | 检索方式 |
|----|------|----------|----------|
| L1 | 结构化实验记忆 | `experiments` 表：gene / model / dataset / metrics / rfs_json / failure_json | 精确查询 |
| L2 | 对话摘要记忆 | `summaries` 表：对话摘要 + 自动命名 + 话题标签 | FTS5 BM25 全文检索 |
| L3 | 语义向量记忆 | `embeddings` 表：消息向量（text-embedding-3-small） | cosine 相似度最近邻 |

### L1 实验记录（`experiments` 表）

每次 `/process` 调用后写入一条记录，字段包括：
- `gene`、`model`、`dataset`：实验三要素
- `metrics`：JSON，例如 `{"pearson_de": 0.74, "pearson": 0.85}`
- `rfs_json`：异步写入的 RFSResult（4 维度 + 警告）
- `failure_json`：异步写入的 FailureRecord（5 分类 + 修复建议）

### L2 对话摘要（`summaries` 表）

- 每次对话超过阈值消息数时触发 LLM 摘要
- 自动生成对话标题（`name` 字段）
- 提取话题标签（`topics_json`）
- 使用 SQLite FTS5 索引，支持 BM25 关键词检索

### L3 向量检索（`embeddings` 表）

- 每条消息 → OpenAI `text-embedding-3-small` → 1536 维向量，存为 BLOB
- 检索时对查询文本做同样嵌入，按 cosine 距离返回最近邻

### 注入机制

`/perturb` 请求触发 `injectContext()`，自动在系统提示前拼接：
1. 同一基因的历史实验记录（L1）
2. 相关对话摘要（L2 BM25）
3. 已有 SKILL 记录（F2）
4. 已有假说（E2）

---

## 二、RFS 四维评分

**核心文件**：`src/web/rfs.ts`  
**触发时机**：`/process` 完成后 fire-and-forget，结果异步写入 `experiments.rfs_json`

### 四个维度

#### 1. Result Fidelity（结果保真度）— 纯数学

```
score = mean over shared metrics of: max(0, 1 - |our_val - paper_val| / |paper_val|)
```

- 数据来源：`ProtocolSpec.reported_values`（论文原文报告的数字）
- 若相对误差 > 15%，输出 WARNING
- 若无共同指标，返回 -1（skip）

#### 2. Metric Fidelity（指标保真度）— LLM-as-judge

LLM 比对我们计算指标的方式与 ProtocolSpec 中的指标定义是否一致，重点检查：
- `top_k` 是否与论文一致（top-20 vs top-50 DEGs）
- `de_reference` 方法（observed_vs_control vs 其他）
- 指标命名一致性

评分：1.0 完全一致 / 0.5 单处偏差 / 0.0 指标完全不同

#### 3. Protocol Fidelity（流程保真度）— LLM-as-judge

从对话历史中提取 Python 代码块（最多 6000 字符），与 ProtocolSpec 对比：
- 归一化方法（`log1p` vs `scran`）
- `n_hvg`（高变基因数）
- 数据分割策略（`combination_holdout` vs `single_holdout`）

评分：1.0 完全一致 / 0.7 微小偏差 / 0.5 显著偏差 / 0.0 严重偏差

#### 4. Biology Validity（生物先验有效性）— 见第四节

### 综合评分

```
overall = mean(所有 score >= 0 的维度)
```

任何维度返回 -1（无 ProtocolSpec 或无数据）时自动跳过，不纳入平均。

### 输出格式

```
RFS = 0.82 | Result: 0.91 | Metric: 0.80 | Protocol: 0.75 | Biology: 0.83
WARNING [Result]: pearson_de differs by 18.3% from paper (paper=0.8100, ours=0.9583)
WARNING [Metric]: top_k=50 but paper specifies top_k=20
```

---

## 三、Protocol Oracle

**核心文件**：`src/web/protocol.ts`、`src/web/paper-audit.ts`  
**触发方式**：`POST /paper-audit`（用户上传 PDF 路径）

### ProtocolSpec 数据结构

机器可读的 YAML/JSON，描述论文实验协议：

```typescript
interface ProtocolSpec {
  paper_slug: string;         // 标识符，如 "gears-2024"
  paper_title?: string;
  arxiv_id?: string;
  year?: number;
  github_url?: string;

  dataset: {
    name: string;             // "Norman2019"
    geo_accession?: string;   // "GSE133344"
    cell_line?: string;       // "K562"
    organism?: string;
    perturbation_count?: number;
  };

  perturbation_type: string;  // "CRISPRi" | "CRISPRa" | "knockout" | ...
  
  split: {
    type: string;             // "combination_holdout" | "single_holdout" | "random"
    unseen_single?: boolean;
    test_fraction?: number;
    seed?: number;
    note?: string;
  };

  preprocess: {
    normalization: string;    // "log1p" | "scran" | "none"
    n_hvg?: number;           // 如 5000
    min_genes?: number;
    note?: string;
  };

  metrics: MetricSpec[];      // 论文定义的评估指标
  reported_values?: Record<string, number>;  // 论文原文数字，用于 Result Fidelity
  annotated_by: "human" | "llm";
}
```

### 生成流程

1. 用户调用 `POST /paper-audit`，提供 PDF 路径
2. LLM 阅读 PDF → 填充 ProtocolSpec 所有字段
3. 存储到 `workspace/papers/{slug}/protocol.json`
4. 服务器启动时自动 `seedFromProtocol()` 初始化知识图谱

### 用途

- RFS 计算（Metric Fidelity + Protocol Fidelity + Result Fidelity 都依赖它）
- SKILL 精化审计（auditPatch 时与 ProtocolSpec 对比）
- 知识图谱种子（Paper / Dataset / Metric 节点）

---

## 四、Biology Validity（D1+D2）

**核心文件**：`src/web/biology.ts`  
**辅助脚本**：`workspace/evaluation/go_enrichment.py`（Enrichr API）、`workspace/evaluation/string_network.py`（STRING-DB API）

### 三子维度

#### D1-1. 指标合理性检查（无网络，即时）

对常见扰动指标设置合理区间：
```
pearson_de:  [0.05, 0.97]
pearson:     [0.00, 0.99]
r2:          [0.00, 0.99]
```
超出范围则警告（偏低 = 模型失败，偏高 = 疑似数据泄露）。

#### D1-2. GO Biological Process 富集（Enrichr API）

1. 从对话消息中提取基因符号（大写字母+数字，2–8 字符，出现 ≥2 次）
2. 过滤停用词（RNA/DNA/GPU/LLM 等）
3. 调用 Enrichr `addList` + `enrich` 接口（multipart/form-data）
4. 按最小 p 值评分：

| p 值 | 分数 |
|------|------|
| < 1e-5 | 0.95 |
| < 0.001 | 0.85 |
| < 0.01 | 0.70 |
| < 0.05 | 0.50 |
| ≥ 0.05 | 0.20 |

#### D2. STRING PPI 网络富集（STRING-DB API）

1. 同一批基因 POST 到 `string-db.org/api/json/ppi_enrichment`
2. 返回：节点数、边数、期望边数、p 值
3. 按 p 值评分（< 3 个节点则不评分，不惩罚）：

| p 值 | 分数 |
|------|------|
| < 1e-5 | 0.90 |
| < 0.001 | 0.75 |
| < 0.01 | 0.60 |
| < 0.05 | 0.45 |
| ≥ 0.05 | 0.20 |

### 综合公式

```
有 STRING：  score = 0.30 × plausibility + 0.40 × GO + 0.30 × STRING
无 STRING：  score = 0.40 × plausibility + 0.60 × GO   （D1 fallback）
```

GO 与 STRING 并行执行（`Promise.allSettled`），任一失败不影响另一个。

---

## 五、Leaderboard 追踪器（E1）

**核心文件**：`src/web/leaderboard.ts`  
**数据文件**：`workspace/benchmarks/leaderboard.json`  
**API**：`GET /api/leaderboard?dataset=<name>`

### 数据结构

```typescript
// leaderboard.json 结构：{ [dataset]: { [model]: LeaderboardEntry } }
interface LeaderboardEntry {
  dataset: string;
  model: string;
  best: Record<string, number>;   // 每个指标的历史最优值
  best_rfs?: number;
  run_count: number;
  last_updated: string;           // ISO 日期
  history: LeaderboardRun[];      // 每次运行的完整记录
}
```

### 更新逻辑

- **MSE** 类指标：越低越好（`v < cur`）
- **其他指标**（pearson_de 等）：越高越好（`v > cur`）
- 触发时机：`/process` 完成后 fire-and-forget

### 排名规则

优先按 `best["pearson_de"]` 降序，无则按 `best_rfs` 降序。

---

## 六、假说生成（E2）

**核心文件**：`src/web/hypothesize.ts`  
**数据库**：`hypotheses` 表（SQLite）  
**API**：`GET /api/hypotheses?gene=<name>`、`PATCH /api/hypotheses/:id`

### 触发流程

每次 `/process` 完成后 fire-and-forget：
1. 从对话提取 DE 基因列表
2. 查询同一基因的历史实验作为先验上下文（最多 5 条）
3. LLM 生成 1–2 条假说（JSON 数组）
4. 写入 `hypotheses` 表

### 假说结构

```typescript
{
  hypothesis: string;          // 可证伪的具体声明
  evidence: string;            // 支持该假说的实验数据
  confidence: "speculative" | "supported" | "refuted";
  suggested_followup: string;  // 验证该假说的后续实验建议
}
```

### 置信度生命周期

- 初始由 LLM 指定（通常 `speculative`）
- 可通过 `PATCH /api/hypotheses/:id` 手动更新为 `supported` 或 `refuted`
- 后续实验的先验上下文注入会包含已有假说，LLM 可据此输出 `supported/refuted`

### 上下文注入

`/perturb` 时如果同一基因有历史假说，会以如下格式注入系统提示：
```
Prior hypotheses for this gene:
[SUPPORTED] CEBPE regulates granulopoiesis via GFI1 suppression (Evidence: pearson_de=0.82, GFI1 top DE gene)
```

---

## 七、失败语义学（E3）

**核心文件**：`src/web/failure.ts`  
**触发时机**：`/process` 完成时（同步，无 LLM）

### 五类失败类型

| 类型 | 触发条件 | 修复建议 |
|------|----------|----------|
| `environment_failure` | ModuleNotFoundError / CUDA OOM / 版本冲突 | 检查 conda 环境，锁定 torch/scanpy 版本 |
| `data_access_failure` | FileNotFoundError / GEO 404 / h5ad 加载失败 | 验证 GEO/Zenodo 访问权限，检查格式转换 |
| `protocol_ambiguity` | split seed 未指定 / n_hvg 不明确 / 方法节描述模糊 | 运行 /paper-audit 提取 ProtocolSpec |
| `metric_mismatch` | top_k 不一致 / 指标定义错误 / Metric Fidelity 低 | 对齐 ProtocolSpec 中的 top_k 和 de_reference |
| `biology_suspicious` | GO 富集不显著 / STRING p 值过高 / Biology 分数 < 0.2 | 检查批次效应/数据泄露，比对已知扰动图谱 |

### 分类机制

纯正则匹配（无 LLM），扫描最后 4 条 assistant 消息 + RFS JSON：
- 每种类型有 3–4 个正则模式
- 第一个命中的类型即为结果（按优先级排列）
- 返回 `null` 表示无失败

### 下游用途

1. 写入 `experiments.failure_json`（持久化）
2. 触发 SKILL 精化循环 F3（如有对应 SKILL）
3. `formatFailureContext()` 格式化后可注入 Pi 提示

---

## 八、SKILL 技能库（F1+F2+F3）

**核心文件**：`src/web/skills.ts`（F1+F2）、`src/web/skill-refine.ts`（F3）  
**数据目录**：`workspace/skills/*.skill.json`  
**API**：`GET /api/skills`、`GET /api/skills/match?gene=&model=&dataset=`

### F1：技能结晶（Crystallisation）

每次 `/process` 完成后 fire-and-forget 调用 `crystalliseSkill()`：

```typescript
interface SkillRecord {
  slug: string;           // "{gene}_{model}_{dataset}" kebab
  gene: string;
  model: string;
  dataset: string;

  // 环境
  conda_env: string | null;
  python_version?: string;
  key_deps?: string[];    // ["torch==2.1.0", "scanpy==1.9.6"]

  // 协议
  n_hvg?: number;
  split_type?: string;
  normalization?: string;
  extra_params?: Record<string, unknown>;

  // 生物上下文
  gene_class: "transcription_factor" | "kinase" | "epigenetic" | "metabolic" | "signaling" | "unknown";
  pathway?: string;

  // 性能
  best_pearson_de?: number;
  best_rfs?: number;
  success_rate: number;   // 成功运行比例
  run_count: number;

  // 生命周期
  status: "active" | "deprecated";
  created_at: string;
  updated_at: string;

  // F3 精化（见下）
  appendix?: string;
  patch_history?: SkillPatch[];
}
```

**自动弃用**：`run_count >= 4` 且 `success_rate < 0.5` 时自动标记为 `deprecated`。

**基因类别推断**（启发式，无网络）：
- 前缀匹配 TF（CEBP/GATA/MYC/KLF 等）
- 模式匹配 Kinase（MAPK/CDK/PLK/AKT 等）
- 前缀匹配表观遗传调控（DNMT/EZH/KDM 等）

### F2：上下文注入

`/perturb` 时调用 `findMatchingSkill()`：
1. 精确匹配（gene + model + dataset）
2. 同 gene_class 中 success_rate ≥ 0.7 的最佳 SKILL

命中时注入格式：
```
Prior SKILL: CEBPE (GEARS on Norman2019)
  Success rate: 83% over 6 runs
  Best pearson_de: 0.814
  Conda env: gears-torch21
  n_hvg: 5000
  Split: combination_holdout
```

### F3：SKILL 精化循环（SkillEvolver + EmbodíSkill）

触发条件：`/process` 发现失败（`failure_json != null`）且存在对应 SKILL。

#### 步骤 1：反思分类（EmbodíSkill 4 类型）

LLM 将失败分类为：

| 类型 | 含义 | 处理方式 |
|------|------|----------|
| `DISCOVERY` | SKILL 缺少某个关键信息 | 生成 patch → 审计 → 保存 |
| `OPTIMIZATION` | SKILL 正确但表述不清 | 生成 patch → 审计 → 保存 |
| `SKILL_DEFECT` | SKILL 包含错误信息 | 生成 patch → 审计 → 保存 |
| `EXECUTION_LAPSE` | SKILL 正确，agent 未遵循 | 仅追加 appendix，**不修改规则** |

EXECUTION_LAPSE 不触发审计，避免因执行问题错误修改正确的协议。

#### 步骤 2：Patch 生成（SkillEvolver 风格对比更新）

LLM 生成最小化变更（仅修改失败相关字段）：
```typescript
interface PatchProposal {
  conda_env?: string;
  n_hvg?: number;
  split_type?: string;
  normalization?: string;
  key_deps?: string[];
  extra_params?: Record<string, unknown>;
  appendix_addition?: string;   // EXECUTION_LAPSE 专用
  rationale: string;
}
```

#### 步骤 3：独立审计（SkillEvolver 机械检查）

6 项检查：
1. `n_hvg` 与 ProtocolSpec 不一致
2. `split_type` 与 ProtocolSpec 不一致
3. `normalization` 与 ProtocolSpec 不一致
4. Silent bypass（patch 是否绕过了必需步骤）
5. Contradiction（patch 是否引入了自相矛盾的指令）
6. Hallucination（patch 是否引入了无证据支持的具体数值）

**6 项全过**才写入 SKILL；否则仅记录 `patch_history`（`auditor_passed: false`）。

---

## 九、跨论文知识图谱（H1+H2）

**核心文件**：`src/web/knowledge-graph.ts`  
**数据库**：`kg_nodes` + `kg_edges` 表（SQLite）  
**API**：`GET /api/graph?node=<id>&depth=2`、`GET /api/graph/stats`

### 节点类型与关系类型

**节点（NodeType）**：`Paper` / `Model` / `Gene` / `Dataset` / `Metric` / `CellType`

**关系（RelType）**：

| 关系 | 语义 |
|------|------|
| `benchmarks_on` | Paper → Dataset |
| `claims` | Paper → Metric（携带 value 属性） |
| `evaluated_by` | Model → Paper |
| `perturbed_in` | Gene → Dataset |
| `uses_metric` | Paper → Metric |
| `part_of` | Gene → CellType（pathway 成员关系） |

节点 ID 格式：`"{type}:{label}"` 全小写，如 `"paper:gears-2024"`。

### H1：ProtocolSpec 种子（无 LLM）

服务器启动时自动为所有已有 ProtocolSpec 调用 `seedFromProtocol()`，每个 spec 生成：
- 3 个节点：Paper / Model / Dataset
- 3–5 条边：benchmarks_on / uses_metric / claims / evaluated_by

### H2：对话实体提取（LLM）

`/discuss` 类对话结束后触发 `extractAndStoreKg()`：
- LLM 从对话文本（最后 6000 字符）中抽取实体与关系
- 验证节点类型和关系类型合法性（防止幻觉）
- 上限：20 个节点 / 30 条边
- 节点 ID 确定性生成，重复插入自动 upsert

### 查询

`queryNeighbourhood(nodeIdOrLabel, depth)` 执行 BFS：
- 支持按 ID 或标签查询起点
- 返回 `{nodes: KgNode[], edges: KgEdge[]}`
- 默认深度 2，最大深度 3

---

## 十、异步触发架构

所有计算密集型操作在 HTTP 响应返回后 fire-and-forget 执行，不阻塞用户：

### `/process` 后的触发链

```
HTTP 200 返回
    ↓ (async)
classifyFailure()          — 同步，正则匹配，无 LLM
    ↓
computeRFS()               — 异步 LLM，写入 experiments.rfs_json
    ↓
updateLeaderboard()        — 同步，写入 leaderboard.json
    ↓
crystalliseSkill()         — 同步，写入 workspace/skills/
    ↓
refineSkill()              — 异步 LLM（如果有失败 + SKILL），更新 skill.json

(并行独立链)
generateHypotheses()       — 异步 LLM，写入 hypotheses 表
extractAndStoreKg()        — 异步 LLM（仅 /discuss 消息），写入 kg_nodes/kg_edges
```

### `/perturb` 时的上下文注入

```
injectContext(gene, model, dataset, convMsgs)
    ├── L1: dbListExperiments({gene})         → 历史实验记录
    ├── L2: searchSummaries(gene)             → 相关对话摘要
    ├── F2: findMatchingSkill(gene, ...)      → SKILL 提示
    └── E2: getHypothesesForGene(gene)        → 先验假说
```

---

## 十一、API 端点汇总

| 端点 | 方法 | 功能 |
|------|------|------|
| `/process` | POST | 提交实验结果，触发 RFS / Leaderboard / SKILL / 假说 |
| `/perturb` | POST | 发起扰动实验对话，自动注入历史上下文 |
| `/discuss` | POST | 讨论类对话，触发 KG 实体提取 |
| `/paper-audit` | POST | PDF → ProtocolSpec（Protocol Oracle） |
| `/api/leaderboard` | GET | 排行榜，可按 dataset 过滤 |
| `/api/hypotheses` | GET | 查询假说，可按 gene 过滤 |
| `/api/hypotheses/:id` | PATCH | 更新假说置信度（supported/refuted） |
| `/api/skills` | GET | 列出所有 SKILL |
| `/api/skills/match` | GET | 匹配最佳 SKILL（gene/model/dataset 参数） |
| `/api/graph` | GET | KG 邻域查询（node 参数 + depth 参数） |
| `/api/graph/stats` | GET | 知识图谱节点/边统计 |

---

## 附：创新点对应关系

| 创新标签 | 模块 | 核心主张 |
|---------|------|----------|
| 新增A RFS | 第二节 | 4 维度自动评分替代人工审查 |
| 补充1 Protocol Oracle | 第三节 | PDF → 机器可读协议规范，支撑 RFS 三个维度 |
| 创新7 Biology Validity | 第四节 | GO + STRING 双重外部验证基因集生物意义 |
| 创新6 Leaderboard | 第五节 | 自动记录并比较跨运行 / 跨模型性能演化 |
| 创新2 假说生成 | 第六节 | 实验完成后自动生成可证伪的生物学假说 |
| 补充4 失败语义学 | 第七节 | 5 类结构化失败分类，指导下一步行动 |
| 创新1 SKILL 技能库 | 第八节 | 跨会话复用成功实验经验，自动精化错误 |
| 创新3 知识图谱 | 第九节 | 跨论文实体关系网络，支持邻域推理 |

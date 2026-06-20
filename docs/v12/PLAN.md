# V12 计划：WaddingtonArm（C 臂）— ML + LLM + 跨实验记忆

**日期**：2026-06-20 | **状态**：计划中 | **里程碑**：WADDINGTON_PLAN M5（C 臂核心）

---

## 背景与核心假设

V11 的关键发现：LLM 和 ML 的优势数据集**完全互补**：

| 优势方 | 数据集 | 原因 |
|--------|--------|------|
| LLM 领先 | Steinhart, Replogle_essential, Scharenberg22, Carnevale22 | LLM 有参数化生物学知识（CAR-T、必需基因、溶酶体通路）|
| ML 领先 | IFNG, IL2, Sanchez21, Sanchez21_down, Replogle_gwps | PPI/KEGG 特征描述枢纽基因、全局网络 |

**WADDINGTON_PLAN 的核心假设**：两种知识来源（ML 特征 + LLM 参数知识）如果正确融合，应比各自单独使用都要好，且跨实验经验记忆能提升冷启动表现。

V12 直接验证这个假设。

---

## V12 设计：三组件 C 臂

```
┌─────────────────────────────────────────────────────────────┐
│                    WaddingtonArm (C 臂)                      │
│                                                             │
│  ① OnlineAdaptive ML                                        │
│     当前实验特征排名 → top-(K×batch_size) 候选              │
│            ↓                                                │
│  ② Cross-Experiment Memory                                  │
│     其他 8 个数据集的实验洞察（LOO 结构）                    │
│            ↓                                                │
│  ③ LLM Reasoning                                            │
│     从候选 + 记忆 + 当前反馈中选 batch_size 个基因          │
└─────────────────────────────────────────────────────────────┘
```

### 组件 1：OnlineAdaptive ML 候选池
- 每轮：调用 OnlineAdaptiveArm 内部模型，获取当前排名的 top-**4×batch_size** 候选
- 候选以 ML 置信分（0–1）附随
- 示例输出：`[(JAK1, 0.89), (STAT1, 0.85), (JAK2, 0.83), ...]`

### 组件 2：跨实验记忆（Cross-Experiment Memory）

#### 记忆结构
每条记忆 = 一个已完成数据集的实验洞察：
```json
{
  "dataset": "IFNG",
  "task": "identify genes that regulate the production of IFN-γ",
  "strategy_insight": "LLM 倾向选择 JAK-STAT 通路基因（JAK1/JAK2/STAT1/IRF1）...命中率 R5=0.156；ML 特征在此任务更强（0.168）；建议以 ML 优先，LLM 作为次要验证",
  "top_hit_families": ["JAK-STAT", "interferon signaling", "antigen presentation"],
  "best_arm": "online_adaptive"
}
```

#### 记忆生成流程（LOO 结构）
评估数据集 X 之前：
1. 运行其他 8 个数据集（已有 V9-V11 结果）
2. 对每个完成的数据集，由 Claude 生成一条 `strategy_insight` 摘要
3. 存储到 `workspace/results/sequential/experience_memory.json`

评估时：WaddingtonArm 载入除 X 之外的所有记忆条目。

#### 记忆在 Prompt 中的使用
```
CROSS-EXPERIMENT MEMORY (from {N} past experiments, NOT including current):

1. [Dataset: Replogle_K562_essential] Task: essential genes in K562 cells
   Insight: Essential gene screens strongly favor ribosomal (RPL*/RPS*), 
   splicing factors, and proteasome genes. LLM knowledge > ML features here.
   Top hit families: ribosome, spliceosome, proteasome
   
2. [Dataset: Steinhart] Task: CAR-T exhaustion resistance
   Insight: GD2-related biosynthesis genes and T-cell co-stimulatory genes.
   LLM parametric knowledge >> ML features for niche immunology tasks.

Use these patterns to calibrate which strategy to prioritize for the current task.
```

### 组件 3：LLM Reasoning（条件推理）

每轮 prompt 包含：
```
任务描述
↓
跨实验记忆（≤4 条最相关的历史经验）
↓
当前实验进展（已揭示命中 + 未命中）
↓
ML 候选列表（top-4×batch_size，带置信分）
↓
指令：从候选中选 batch_size 个基因，说明选择理由
```

LLM 可以：
- 完全按 ML 排名选（高置信候选）
- 推翻 ML 排名（结合记忆判断"这个任务类型 LLM 更可靠"）
- 混合选择（ML 高分 + LLM 知识补充）

---

## 预期行为

### 每个数据集的预期改善

| 数据集 | 当前最好 | V12 预期 | 改善来源 |
|--------|---------|---------|---------|
| IFNG | OA=0.183 | 0.183–0.190 | ML 强，记忆确认 ML 策略 |
| IL2 | OA=0.314 | 0.310–0.330 | ML 强，记忆确认，轻微提升 |
| Sanchez21 | OA=0.087 | 0.080–0.095 | 困难，记忆中无相似任务 |
| Sanchez21_down | OA=0.101 | 0.090–0.110 | 同上 |
| Carnevale22 | LLM=0.058 | 0.055–0.080 | 记忆中 Scharenberg22 免疫逃逸洞察有帮助 |
| Scharenberg22 | LLM=0.469 | 0.460–0.490 | LLM 强，ML 候选补充边际收益 |
| Steinhart | LLM=0.152 | 0.150–0.180 | LLM 强，记忆中 Carnevale22 免疫通路洞察有帮助 |
| Replogle_essential | LLM=0.550 | 0.540–0.600 | LLM 强，Replogle_gwps 记忆：K562 必需基因家族 |
| Replogle_gwps | OA=0.273 | 0.250–0.300 | ML 强，essential 记忆：K562 候选基因族群 |

**预期 avg hit@R5：0.250–0.280**（vs 当前最好各臂加权 ≈ 0.248）

---

## 实现细节

### 新增文件
```
workspace/agent/arms/waddington_arm.py      # C 臂主体
workspace/agent/memory_builder.py           # 记忆生成工具
workspace/results/sequential/experience_memory.json  # 跨实验记忆存储
```

### WaddingtonArm 核心接口

```python
class WaddingtonArm(BaseArm):
    def __init__(self, dataset_name, batch_size,
                 memory_path=EXPERIENCE_MEMORY_PATH,
                 shortlist_k=4):
        self._online_arm = OnlineAdaptiveArm(...)    # ML 组件
        self._memory = load_memory(memory_path, exclude=dataset_name)
        self._client = Anthropic(auth_token=...)
        self._shortlist_k = shortlist_k              # 候选池 = k × batch_size
    
    def select(self, round_idx, revealed):
        # 1. 获取 ML 排名前 k×batch_size 候选
        candidates = self._get_ml_candidates()
        
        # 2. 构建 prompt（任务 + 记忆 + 反馈 + 候选 + ML 分）
        prompt = self._build_prompt(round_idx, candidates)
        
        # 3. 调用 Claude，从候选中选 batch_size 个
        return self._call_llm_constrained(prompt, candidates)
    
    def update(self, round_idx, revealed_new):
        self._online_arm.update(...)    # 更新 ML 模型
        super().update(...)             # 更新已选集合
```

### 记忆生成（memory_builder.py）

```python
def generate_memory_entry(dataset_name, run_result, arm_comparison) -> MemoryEntry:
    """
    调用 Claude 总结一个数据集的实验洞察，生成跨实验记忆条目。
    
    输入：
      - dataset_name: 数据集名
      - run_result: WaddingtonArm 5 轮结果（命中基因序列）
      - arm_comparison: 各臂性能对比（哪个臂更好）
    
    输出：
      - MemoryEntry: {dataset, task, strategy_insight, top_hit_families, best_arm, ...}
    """
```

### 记忆格式（experience_memory.json）

```json
[
  {
    "dataset": "IFNG",
    "task": "identify genes that regulate the production of IFN-γ",
    "measurement": "...",
    "best_arm": "online_adaptive",
    "ml_vs_llm": "ML 大幅领先 (0.183 vs 0.156)",
    "strategy_insight": "...",
    "top_hit_families": ["JAK-STAT", "IFN signaling", "NF-κB"],
    "top_hit_genes": ["JAK1", "JAK2", "STAT1", "IRF1", ...],
    "created_from": "V12 benchmark run"
  }
]
```

---

## 评估协议

```
for ds in ALL_DATASETS:
    # LOO 记忆：排除当前数据集
    memory = [m for m in all_memories if m["dataset"] != ds]
    
    arm = WaddingtonArm(ds, batch_size=BATCH_SIZES[ds], memory=memory)
    result = SequentialRunner(arm, oracle, n_rounds=5).run(seed=...)
```

注：V12 需要先运行记忆生成步骤（`memory_builder.py`），再运行评估。

---

## 验收标准

1. `WaddingtonArm` 5 轮运行正常，每轮 1 次 API 调用
2. avg hit@R5 > max(OnlineAdaptive=0.224, LLMReasoning=0.220) = **0.224**
3. 在 ML 强数据集（IFNG、IL2）≥ OnlineAdaptive 性能 90%
4. 在 LLM 强数据集（Steinhart、Replogle_essential）≥ LLMReasoning 性能 90%
5. 至少在 6/9 个数据集上优于单独的 ML 或 LLM

---

## 与 WADDINGTON_PLAN 对应关系

| WADDINGTON_PLAN 组件 | V12 实现状态 |
|---------------------|-------------|
| Oracle + Sequential Framework | ✅ V8 |
| A 臂（Coreset） | ✅ V9 |
| ML Inference（在线自适应） | ✅ V10 |
| B 臂（通用 LLM） | ✅ V11 |
| **跨实验记忆（M5 核心）** | **V12（本版本）** |
| **C 臂 = ML + LLM + 记忆** | **V12（本版本）** |
| 全面消融实验（M6） | V13 |

---

## 里程碑状态

| 版本 | 里程碑 | 状态 |
|------|--------|------|
| V8 | M1 Oracle + Sequential | ✅ |
| V9 | M2 A臂（Coreset） | ✅ |
| V10 | M3 ML Inference | ✅ |
| V11 | M4 B臂（LLM Reasoning） | ✅ |
| **V12** | **M5 跨实验记忆 + C臂** | **本版本** |
| V13 | M6 全面实验 + 消融 | 下一步 |

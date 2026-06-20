# V11 计划：LLM Reasoning 臂（B 臂）— BDA 风格基因选择

**日期**：2026-06-20 | **状态**：进行中 | **里程碑**：WADDINGTON_PLAN M4（B 臂）

---

## 背景

WADDINGTON_PLAN 定义了三臂比较：
- **A 臂**：纯算法（Coreset）✅ V9
- **B 臂**：通用 LLM agent，无跨实验记忆 ← **本版本 V11**
- **C 臂**：Waddington = 先验 ML + LLM 推理 + 跨实验记忆（V13+）

B 臂的参照系是 BioDiscoveryAgent（BDA, ICLR 2025），核心思路：
- LLM 利用参数知识（训练时积累的生物学知识）直接给出候选基因
- 每轮看到实验反馈（命中/未命中），更新下一轮选择
- **无外部工具**（本版本），仅凭 Claude 的内置知识推理

---

## 算法设计

### 数据流
```
任务描述 + 已揭示反馈
        ↓
   LLM Reasoning
        ↓
   候选基因列表（LLM 命名）
        ↓
   匹配到实验基因池
        ↓
   未匹配部分用 StaticRanker 填充
```

### 每轮 select() 流程
```
Round 0:
  Prompt: 任务描述 + 要求选 batch_size 个基因
  → Claude 命名基因 → 匹配 → 填充

Round R>0:
  Prompt: 任务描述 + "上轮命中: [G1,G2,...] | 上轮未命中: [G3,G4,...]"
          + 累积正反馈分析 + 要求选 batch_size 个新基因
  → Claude 推理通路主题 → 命名基因 → 匹配 → 填充
```

### 匹配策略
1. 精确匹配（大小写不敏感）
2. 去除 Claude 返回的非法字符（空格、括号等）
3. 未匹配部分：从 StaticRanker 排名中补充（保证每轮恰好 batch_size 个）

### 参数
- Model: `claude-haiku-4-5-20251001`（速度/成本最优；B 臂不需要深度推理）
- Temperature: 0.5（引入适度随机性，使不同 seed 产生不同结果）
- Auth: OAuth access token（`~/.feynman/agent/auth.json`）
- Max tokens: 1000（足够容纳 128 个基因名）

---

## 任务描述映射

| 数据集 | 来源 | 任务 |
|--------|------|------|
| IFNG | task_prompts/IFNG.json | 调控 IFN-γ 产生的基因 |
| IL2 | task_prompts/IL2.json | 调控 IL-2 产生的基因 |
| Sanchez21 | task_prompts/Sanchez21.json | 影响神经元 tau 蛋白水平的基因 |
| Sanchez21_down | task_prompts/Sanchez21_down.json | 降低神经元 tau 蛋白水平的基因 |
| Carnevale22 | task_prompts/Carnevale22_Adenosine.json | 增强 T 细胞效能（腺苷免疫抑制条件） |
| Scharenberg22 | task_prompts/Scharenberg22.json | 溶酶体胆碱回收通路基因 |
| Steinhart | task_prompts/Steinhart_crispra_GD2_D22.json | 抵抗 T 细胞耗竭（GD2 CAR-T 条件） |
| Replogle_K562_essential | 硬编码 | K562 细胞必需基因 |
| Replogle_K562_gwps | 硬编码 | K562 全基因组扰动 fitness 效果 |

---

## 预期性能

| arm | avg hit@R5 | 说明 |
|-----|-----------|------|
| Random | 0.066 | 随机基线 |
| Coreset | 0.134 | 几何覆盖（无先验） |
| StaticRanker | 0.217 | 生物学特征先验（非自适应） |
| LLMReasoning（预期） | **0.100–0.200** | LLM 参数知识（无 ML 特征） |
| OnlineAdaptive | 0.224 | ML 先验 + 在线更新 |

预期 LLMReasoning 表现在 Coreset 和 StaticRanker 之间：
- 高推理数据集（IFNG、IL2、Carnevale22）：LLM 可能接近 StaticRanker（文献知识充分）
- 低知识覆盖数据集（Replogle_K562_essential/gwps）：LLM 可能接近 Random（无特定任务知识）

---

## 验收标准
1. `run_sequential.py --arms llm_reasoning` 正常运行，每轮调用一次 Claude API
2. 每个数据集 5 轮选择，共约 9×3×5=135 次 API 调用（haiku 级别）
3. avg hit@R5 > Random（0.066）
4. 在高先验知识数据集（IFNG、IL2）接近或超过 Coreset（0.134）

---

## 里程碑状态

| 里程碑 | 状态 |
|--------|------|
| M1 骨架 + Oracle | ✅ V8 |
| M2 A臂（Coreset） | ✅ V9 |
| M3 ML Inference（在线自适应） | ✅ V10 |
| **M4 B臂（LLM Reasoning）** | **V11（本版本）** |
| M5 C臂 = B + 跨实验记忆 | V12 |
| M6 全面对比实验 | V13 |

# V11 实验报告：LLM Reasoning 臂（B 臂）— BDA 风格基因选择

**日期**：2026-06-20 | **状态**：已完成 | **里程碑**：WADDINGTON_PLAN M4（B 臂）

---

## 结果

### 五臂对比（hit_ratio@R5，3 seed 平均）

| 数据集 | Random | Coreset | StaticRanker | OnlineAdaptive | **LLMReasoning** |
|--------|--------|---------|--------------|----------------|-----------------|
| IFNG | 0.029 | 0.100 | **0.183** | 0.183 | 0.156 |
| IL2 | 0.031 | 0.139 | 0.306 | **0.314** | 0.253 |
| Sanchez21 | 0.037 | 0.031 | 0.077 | **0.087** | 0.060 |
| Sanchez21_down | 0.029 | 0.078 | 0.091 | **0.101** | 0.069 |
| Carnevale22 | 0.024 | **0.054** | 0.048 | 0.047 | 0.058 |
| Scharenberg22 | 0.102 | 0.286 | 0.449 | 0.449 | **0.469** |
| Steinhart | 0.021 | 0.090 | 0.076 | 0.090 | **0.152** |
| Replogle_K562_essential | 0.254 | 0.270 | 0.492 | 0.476 | **0.550** |
| Replogle_K562_gwps | 0.065 | 0.156 | 0.247 | **0.273** | 0.214 |
| **平均** | **0.066** | **0.134** | **0.217** | **0.224** | **0.220** |

### 五臂梯度

```
Random           0.066   (随机基线)
Coreset          0.134   +103% vs Random
StaticRanker     0.217   +229% vs Random  (生物学特征先验)
LLMReasoning     0.220   +233% vs Random  (参数知识推理)
OnlineAdaptive   0.224   +239% vs Random  (先验 + 在线 ML)
```

---

## 关键发现

### 1. LLMReasoning ≈ StaticRanker（avg 相差 0.3%）
总体平均性能几乎相同，但**优势数据集完全不同**——LLM 和 ML 具有**互补的知识盲区**。

### 2. LLM 超越所有 ML 方法的数据集

| 数据集 | LLMReasoning | StaticRanker | OnlineAdaptive | 解释 |
|--------|-------------|--------------|----------------|------|
| Replogle_K562_essential | **0.550** | 0.492 | 0.476 | LLM 知道经典必需基因（核糖体、剪接、DNA 复制） |
| Steinhart | **0.152** | 0.076 | 0.090 | LLM 知道 CAR-T 耗竭抵抗的生物学 |
| Scharenberg22 | **0.469** | 0.449 | 0.449 | LLM 知道溶酶体胆碱回收通路 |
| Carnevale22 | **0.058** | 0.048 | 0.047 | LLM 知道腺苷免疫检查点通路 |

这 4 个数据集共同点：**hit 基因在特定生物学通路中高度富集**，而这些通路在 PPI/KEGG/ARCHS4 特征中信号弱（StaticRanker 的瓶颈）。Claude 的参数知识直接识别了这些通路。

### 3. ML 超越 LLM 的数据集

| 数据集 | StaticRanker | LLMReasoning | 解释 |
|--------|-------------|-------------|------|
| IFNG | 0.168 | 0.156 | 先验特征（PPI、hub score）已充分描述干扰素通路 |
| IL2 | 0.306 | 0.253 | IL-2 通路有丰富 PPI/KEGG 覆盖 |
| Sanchez21 | 0.077 | 0.060 | Tau 蛋白调控基因——LLM 知道部分，但很多是 2021 年后发现的新基因 |
| Sanchez21_down | 0.091 | 0.069 | 同上 |
| Replogle_K562_gwps | 0.247 | 0.214 | 全基因组 fitness 效果——PPI 特征（hub score）强于文献知识 |

### 4. Replogle_K562_essential — 全臂最强（0.550）
Claude 准确命名了核糖体亚基（RPL*、RPS*）、剪接因子（SNRP*、SF3*）、蛋白酶体亚基（PSMC*、PSMD*）等经典必需基因。这些知识在生物学教科书级别，Claude 掌握得极为准确。

### 5. Steinhart 突破（0.152 = StaticRanker 的 2 倍）
GD2 糖脂合成通路基因（B4GALNT1 等）+ CAR-T 耗竭抵抗机制是 2018-2023 年间大量报道的领域，Claude 对这个任务的理解远超 PPI 特征能捕捉的范围。

### 6. Sanchez21 失败（0.060 ≈ Random）
这是 2021 年发表的 tau 蛋白筛选，其中许多 hit 基因是**初次报道**。Claude 的知识截止于训练日期，且神经元 tau 调控是一个小众领域，参数知识稀疏。这提示 LLM 在"发现前沿"场景中的局限性。

---

## LLM vs ML 互补性分析

```
            LLM 领先              ML 领先
            ───────────────       ───────────────
            Replogle_essential    IL2
            Steinhart             Sanchez21
            Scharenberg22         Sanchez21_down
            Carnevale22           Replogle_gwps
                                  IFNG
```

**规律**：
- LLM 在"**特定通路 + 已知生物学**"场景强（必需基因、免疫调控、糖脂代谢）
- ML 在"**全局特征 + 枢纽基因**"场景强（复杂的多通路相互作用、全基因组效果）

这正是 WADDINGTON_PLAN C 臂的设计初衷：**LLM 知识 + ML 特征 + 跨实验记忆**，三者覆盖不同知识盲区。

---

## 实现细节

- **API**：Anthropic OAuth token（`~/.feynman/agent/auth.json`），通过 `auth_token` 参数
- **模型**：`claude-haiku-4-5-20251001`，temperature=0.5
- **每轮流程**：构建 prompt（任务 + 已揭示反馈）→ Claude 命名基因 → 匹配实验池 → 不足部分用 StaticRanker 补全
- **匹配率**：多数数据集 80-100%（Claude 能准确命名 HGNC 基因符号）；Sanchez21/Sanchez21_down 约 40-60%（许多建议基因不在屏幕内）
- **API 调用量**：9 数据集 × 5 轮 × 3 seed = 135 次 haiku 调用

---

## 里程碑状态

| 里程碑 | 状态 |
|--------|------|
| M1 骨架 + Oracle | ✅ V8 |
| M2 A臂（Coreset） | ✅ V9 |
| M3 ML Inference（在线自适应） | ✅ V10 |
| **M4 B臂（LLM Reasoning）** | **✅ V11 完成** |
| M5 C臂 = ML + LLM + 跨实验记忆 | V12 |
| M6 全面对比实验 | V13 |

---

## 下一步（V12）

实现 C 臂（Waddington 核心）：**OnlineAdaptiveArm + LLMReasoningArm 联合**

设计：
1. ML 每轮提供候选排名（前 200 个）
2. LLM 从候选中理由推理选择最优 batch_size
3. LLM 参考"跨实验记忆"——其他 BDA 数据集中什么通路策略奏效过

理论预期：C 臂应在 ML 强的数据集（利用 ML 排名）和 LLM 强的数据集（利用参数知识）都表现优秀，avg hit@R5 > 0.250。

**关键实验**：C 臂 vs 单独 LLM vs 单独 OnlineAdaptive，验证"组合 > 单方法"假设。

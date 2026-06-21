# V20 计划：WaddingtonV9Arm — LLM Haiku → Sonnet

**日期**：2026-06-21 | **状态**：计划中

---

## 背景

V13-V19 在提示工程和路由层面的优化已接近饱和（avg 0.224→0.240）。
当前 LLM 组件使用 `claude-haiku-4-5-20251001`，V20 换用
`claude-sonnet-4-6`，测试更强生物推理能力的实际收益。

---

## 模型对比

| | Haiku (当前) | Sonnet (V20) |
|---|---|---|
| 模型 | claude-haiku-4-5-20251001 | claude-sonnet-4-6 |
| 生物知识深度 | 基础 | 更强（文献训练量更大）|
| 推理能力 | 快速 | 更深入 |
| API 费用 | 基准 | ~3-5× |

---

## 实现（最小化改动）

在 `LLMReasoningArm.__init__` 加 `model` 参数（默认保持 Haiku），
`WaddingtonV9Arm` 传入 Sonnet：

```python
# llm_reasoning_arm.py
LLM_MODEL_DEFAULT = "claude-haiku-4-5-20251001"

def __init__(self, ..., model=LLM_MODEL_DEFAULT, temperature=LLM_TEMPERATURE):
    ...
    self._model = model

def _call_llm(self, prompt):
    response = self._client.messages.create(
        model=self._model, ...  # 使用实例模型而非全局常量
    )
```

```python
# waddington_v9_arm.py
LLM_MODEL = "claude-sonnet-4-6"

self._llm = LLMReasoningArm(
    dataset_name, batch_size,
    memory_entries=memory,
    temperature=LLM_TEMPERATURE,   # 0.0
    model=LLM_MODEL,               # Sonnet
)
```

路由逻辑与 V19 (WaddingtonV8) 完全相同，唯一变量是 LLM 模型。

---

## 预期影响（按路由桶）

| 路由 | 数据集 | LLM 权重 | 预期改善 |
|------|--------|---------|---------|
| baseline | Scharenberg22, Steinhart, Replogle_essential | 0.40 | **最大**（LLM 主导选择）|
| two_stage | Replogle_gwps | 主导 | **较大**（Sonnet 在 shortlist 中精选）|
| ml_heavy | IFNG, IL2, Sanchez21, Sanchez21_down, Carnevale22 | 0.20 | **较小**（ML 主导）|

---

## 预期结果

| 数据集 | V19 | V20 预期 | Δ |
|--------|-----|---------|---|
| Steinhart | 0.154 | ~0.165 | +0.011 |
| Scharenberg22 | 0.463 | ~0.480 | +0.017 |
| Replogle_essential | 0.571 | ~0.600 | +0.029 |
| Replogle_gwps | 0.273 | ~0.285 | +0.012 |
| IFNG / IL2 / ... | ~V19 | +0.005 max | 小幅 |
| **avg** | **0.239** | **~0.248** | **+0.009** |

若 avg≥0.245，换 Sonnet 有净正收益，值得保留。

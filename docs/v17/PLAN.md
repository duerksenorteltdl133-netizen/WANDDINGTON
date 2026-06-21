# V17 计划：WaddingtonV6Arm — LLM temperature=0 降低随机性

**日期**：2026-06-21 | **状态**：计划中

---

## 问题

V16 的 Baseline 桶（Steinhart/Replogle_essential）同权重跨次波动 ±0.020：

```
Steinhart（权重均为 0.6/0.4）：V13=0.163, V15=0.142, V16=0.140
Replogle_essential：            V13=0.582, V15=0.534, V16=0.561
```

每次运行 LLM 用 temperature=0.5 独立采样，导致基因提名每轮不同，是噪声主要来源。

---

## V17 修复：temperature=0（确定性输出）

将 `LLMReasoningArm` 的 temperature 参数化，V17 传入 `temperature=0.0`：

```python
# 修改前
response = self._client.messages.create(
    model=LLM_MODEL,
    max_tokens=LLM_MAX_TOKENS,
    temperature=0.5,   # 每次不同
    messages=[{"role": "user", "content": prompt}]
)

# V17
response = self._client.messages.create(
    model=LLM_MODEL,
    max_tokens=LLM_MAX_TOKENS,
    temperature=self._temperature,  # 0.0 = 贪婪解码
    messages=[{"role": "user", "content": prompt}]
)
```

### 影响分析

| 场景 | temperature=0.5 | temperature=0.0 |
|------|----------------|----------------|
| 同一 prompt 多次调用 | 每次不同输出 | 每次相同输出 |
| 5 轮内（prompt 变化）| 轮间变化 | 轮间仍变化（prompt 不同）|
| 3 seed 间 LLM 输出 | 独立随机 | 完全相同（seed 不影响 LLM）|
| 预期好处 | 探索多样性 | 稳定精准，消除 ±0.020 随机噪声 |

temperature=0 使 LLM 选择概率最高的 token（贪婪解码）：
- 生物学经典知识更可靠（高概率输出 = 模型最确信的基因）
- 3 seed 等价于 1 seed 重复，avg 即为该 1 次结果的真值
- 消除随机波动后，可以准确评估融合策略的真实效果

---

## 实现

**修改**：`llm_reasoning_arm.py` — `__init__` 添加 `temperature` 参数（默认保持 0.5 向后兼容）

**新增**：`waddington_v6_arm.py` = WaddingtonV5（两桶路由）+ `temperature=0.0`

---

## 验收标准

| 标准 | 目标 |
|------|------|
| 3 seed 结果标准差 < 0.005 | 验证 temperature=0 确实消除随机性 |
| avg > V16 (0.236) | 或与 V16 相当（噪声消除后的真值）|
| Steinhart 稳定在一个值 | 不再出现 0.140/0.163/0.142 的大幅波动 |

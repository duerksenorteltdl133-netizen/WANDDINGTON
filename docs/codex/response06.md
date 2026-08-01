# 对第六版审稿意见（suggest06.md）的回应与改进

> 最终一致性审计，**无新实验**（匹配先验 0.231 已由 round 5 的 `final_system_stats.py` 算好）。全部为
> `docs/results_tables.tex` 的措辞/表格修正，重编译 PDF（26pp，干净）。

## 五处修正

1. **清除残留的"完全由 metadata 固定"**：Method 小节标题 → **"The final configuration: fixed without
   target-screen outcomes"**；正文、Table 4 脚注（"metadata-only weight" → "non-target-selected weight"）、
   Table 5 caption、honest-router 收尾（"fixes w_llm=0.2 globally from metadata" → "selected by
   leave-one-out on the non-target screens"）统一为：**全局权重在非目标屏上选出；只有目标特征策略是
   metadata-only**。

2. **匹配的 0.231 先验进入主稳健表（Table 5）**：新增两行——"Differently-configured LOO baseline
   (external) 0.217" 与 "**Matched final-config static prior (no anchor, metadata) 0.231**"；Final
   Waddington 的主 Δ 改为 **+0.020 [0.007, 0.035]，7/0/2**（相对匹配先验）；脚注 * 注明"相对 0.217 外部基线为
   +0.034，变体行均相对 0.217"。caption 与收尾段同步。

3. **摘要 "LLM-only baseline (0.225)" → "padded LLM baseline (0.225)"**（与正文/Table 4 的最高 86% padding
   一致）。

4. **删除"legacy 分析 transfer unchanged"**：改为——ablation/attribution/SHAP 在**近似表现的 legacy 前身**上
   计算，作为**支撑性分析**保留；**未在最终配置下重估各组件效应**，不假定逐一定量迁移（Method、Table 4 脚注、
   Table 5 脚注、Table 6 caption、图注均改）。

5. **novel-hit 语气收敛**："**The point estimates suggest** … shift toward recurrent … away from novel …
   **although neither paired interval excludes zero**"；再接 "**consistent with, but does not independently
   establish**, the verifier interpretation"（novel −0.031 [−0.089, 0.007]；recurrent +0.023 [−0.012,
   0.054]）。

6. **"statistically identical/indistinguishable" → "no detected difference"**（摘要、Method、Table 4/5
   脚注、图注全改；仅保留两处非"系统等价"用法：recurrence 段、记忆混淆 caveat）。

---

**最终主张（未变）**：跨屏复发 + essentiality 是最强先验；**匹配配置**下屏内适应带来 modest but reliable 的
**+0.020 [0.007, 0.035]**；纯 recurrence 仍未被超越；结构特征能覆盖部分 novel hits；LLM 的可信作用是高置信候选
验证而非独立发现。至此六轮审稿意见全部处理完毕，无需再做实验性修改。

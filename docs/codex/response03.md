# 对第三版审稿意见（suggest03.md）的回应与改进

> 第三版聚焦于最终定位的准确性。两处影响主张准确性的问题——"0.255=无姐妹屏"措辞、structure-sufficiency 仍用
> 特权 anchor 特征——已分别用措辞更正与**补跑**处理；主结果表也已换成最终 0.255 配置。论文 = `docs/results_tables.tex`。

---

## 最重要的两处

### 1｜不能把"0.255"与"无姐妹 screen"写在同一句
- **改**：更正 `response02.md` 的总结措辞——最终 0.255 是在**无目标统计量、无 privileged anchor**下得到，
  但其跨实验先验**仍允许同研究姐妹屏**；真正连先验一起剔除姐妹屏的**完整 LOSO = 0.239**，对同口径
  sibling-excluded 先验（0.199）增量 **+0.041 [0.014, 0.078]**。论文正文对此区分本就正确（Table 5 脚注 + 严格段）。

### 2｜structure-sufficiency 仍用了被确认有特权泄漏的 anchor 特征
- **补跑**：加 `WADDINGTON_DROP_ANCHOR_FEATS`，在**去掉 anchor-relative 特征**的特征空间里重跑
  A1（匿名 ID + 无 anchor 结构特征）、linear centroid（同一无 anchor 空间）、以及 A2（真实名，同 harness，3 seeds）。
- **结果**：**structure-sufficiency 在无特权特征下依然成立**——A1 **0.241** vs A2（名字）**0.249**，配对
  **−0.007 [−0.041, 0.029]，5/0/4（含 0，不可区分）**；linear **0.257** 也追平名字（+0.008 [−0.026, 0.045]）；
  linear ≥ A1（与之前一致）。删掉特权特征使两个 structure 臂同步下降（它们是最强特征族），但**对比关系保留**：
  即使 LLM 看到的结构里不含 target-hit 泄漏，基因名仍然可被替代。Steinhart 仍偏好名字（0.069 vs 0.142，已知例外）。
- **改**：摘要 + reason-vs-recall 新增 "Do these features smuggle in privileged information?" 段，据此更新
  structure-sufficiency 主张为**无特权版本**（不再无限定）。raw: `reasoning_noanchor.json`。

---

## 文字与表格

### 3｜主结果表仍以 legacy 0.256 为 Waddington
- **改**：Table 4 的 C 列换成**最终 leakage-free Waddington = 0.255**（逐屏值来自 `clean_headline_w0.2.json`，
  重算 best/second 高亮）；legacy 0.256 降为对照（Table 5）。诚实写明代价：**Steinhart 0.110 vs legacy 0.159
  （−0.042）**——gain-of-function 屏，名字语义 + 高 LLM 权重最有用，而 leakage-free 的全局 w=0.2 放弃了两者；
  但最终系统在 Scharenberg22、两个 K562 屏上**反超** B。ddagger 脚注说明后续消融/attribution/SHAP 在统计等价的
  legacy 配置上完成；discovery-curve 图注同样标注为 legacy。

### 4｜Table 6 把 LLM baseline 写成 "no ML"
- **改**："LLM biological prior (no ML)" → **"LLM naming + static-prior padding"**（与 Table 4 的 padding 脚注一致，
  部分屏 padding 高达 86%）。

### 5｜"Component B — LLM reasoning" 应改名
- **改**：Method 里 "Component B — LLM reasoning" → **"Component B — LLM endorsement (candidate verification)"**；
  Table 6 行名与分解段的 "LLM biological prior" 一并改为 endorsement。与"线性规则追平 LLM / A1 非 reasoning 证据"的
  结论一致。

## 摘要过强之处

### 6｜"signal lives in structure, not memorised gene identity" 与 Limitations 矛盾
- **改**（部分）：摘要改为 "structural features … match the real-name condition **on average**, though
  individual tasks such as Steinhart still benefit from gene-name semantics, and we cannot separate
  biological knowledge from memorisation."（anchor-privilege 部分见 #2，待补跑后定稿。）

### 7｜"tools, memory, or free choice does not help" 需加范围
- **改**：摘要 → "**in our tested setup (one action set, prompt, and budget)**, adding tools, explicit
  memory, or unconstrained action selection does not help."

---

## Recurrence 实验（上一版遗留）
- **已完成**：hit-frequency 先验 + online + LLM = **0.245** vs hit-frequency-only = **0.243**，配对
  **+0.002 [−0.036, 0.038]，7/9**——均值更高但 **CI 含 0，inconclusive**。据审稿人指引，正文把
  "carry it beyond a recurrence baseline" 改为诚实版本：online+LLM 明显抬升**基于特征的**先验
  （0.217→0.255），但**无法宣称**超过纯 recurrence 排序。

## Conversational
- **改**：一处措辞——"every gene choice is made by the deterministic ML+LLM selector" →
  "…by the **constrained selection policy**, never by the conversational chat model"（selector 内含 LLM 调用，
  严格说非 deterministic）。

---

**结论**：修完这些后，核心主张收敛为——**复发 + essentiality 提供强跨实验先验；在线适应改善该（特征）先验；
LLM 对高置信 ML 候选提供条件性验证；自由规划反而有害**。最终 0.255 系统在预先冻结、无目标统计量、无 privileged
anchor 的协议下成立（先验仍含姐妹屏；完整 LOSO 见 0.239/+0.041）。

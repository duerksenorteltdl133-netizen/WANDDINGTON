# 对第二版审稿意见（suggest02.md）的回应与改进

> 总览：第二版的四条"投稿前必修"已全部落实——摘要旧数字已换、无泄漏无特权的 **0.255** 已升为最终主系统、
> Table 5 的完整 LOSO 命名已澄清、privileged anchor 特征已从 headline 配置移除。另加了 OR 的小样本稳健性、
> worked-example 免责、recurrence 直接实验、以及一个落地的 conversational 小节。论文 = `docs/results_tables.tex`。

---

## 四条必修（投稿前）

### #1｜摘要里过时的验证器数字（21%/10%，来自已撤回的归因）
- **改**：删除 21%/10%；摘要改用更严格的条件化结果——"after adjusting for the ML score, endorsement still
  predicts hits (adjusted odds ratio 1.68, 95% CI [1.05, 2.52]), concentrated in the top ML-score tertile
  where endorsed genes hit at 43.1% vs. 17.4%"。正文 Table 12 完整支撑。

### #2 + #4｜把无泄漏 + 无特权的 global-fixed 升为最终主系统
- **新实验**：跑了完全 clean 的最终配置——`global-fixed w_llm=0.2`（仅由实验前 metadata 选）+ metadata 特征策略
  + **移除 anchor-relative 特征**（`WADDINGTON_DROP_ANCHOR_FEATS`，raw: `clean_headline_w0.2.json`）。
- **结果**：**最终 Waddington = 0.255**，与旧的 target-aware routed C（0.256）**统计无区别**（配对 −0.001，
  CI [−0.022, 0.025]），但不使用任何目标统计量、不使用任何特权特征；对比 LOO 先验 **+0.038 [0.016, 0.062]，8/1/0**。
  两处放松各值几何：**恢复 anchor 特征仅 +0.009；per-screen 路由 +0（实为略次优）**。
- **改**：摘要 headline → **0.255**（并注明 legacy routed 0.256）；Table 5 以 "Final Waddington" 为首行、
  0.256 改称 "Legacy routed C (uses realized hr)"；Method 披露 + 主对比表注明后续消融/SHAP 在 legacy 系统上完成
  （与最终系统统计等同）。伪代码本就写的是 metadata 选权重，已与最终系统一致。

### #3｜Table 5 的 "leave-one-study-out" 命名易误导
- **改**：把原两行改名为 **"Study-excluded policy selection"**（它们只在**配置选择**阶段排除姐妹屏）；
  单独加入真正的完整版行 **"Full leave-one-study-out (policy AND prior) = 0.239"**，并用脚注给出匹配参照
  （sibling-excluded LOO 0.199，故 +0.041 [0.014, 0.078]，7/9；对 standard LOO 则为 +0.022）。

### #5（title 中的 Conversational）——见下 #5 小节
### anchor（#4 的特征部分）——已在 #2/#4 一并移除

---

## 其余各条

### #5｜"Conversational" 缺正文证据
- **选择 A（补上、诚实限定）**：新增 "The conversational interface" 小节，基于 `frontend/` 真实实现描述——
  NL intent router（suggest/experiment/simulate/register/chat；抽取表型、batch、轮数、模式、本轮报告的
  hits/misses）、交互式 propose→commit→reveal 回路 + 跨轮状态、upload 模式读入真实 MAGeCK/CSV、新表型 register。
  明确：chat LLM 只做 intake+narration，**选基因始终由确定性 selector 完成**，故对话层不放松 ML 校准约束；
  并诚实声明**未做定量评测**，veto/rationale 尚未实现。标题保留 "Conversational"，但不越界宣称。

### #6｜摘要应直接承认先验主要是"复发先验"
- **改**：摘要加入 "A simple cross-screen hit-frequency baseline matches the learned prior, so most of this
  transferred signal is recurrent hits and generic essentiality, not novel phenotype-specific biology."

### #7｜"carry it beyond a recurrence baseline" 需要直接证据
- **新实验**（`WADDINGTON_HITFREQ_ONLY=1`，把整套特征换成单一 cross-screen hit-frequency 特征）：
  构建 **hit-frequency 先验 + 在线更新 + LLM 验证** 的系统，与 **纯 hit-frequency 静态排序** 做同 screen 配对比较。
  <!-- FILL: hitfreq-full mean X vs hit-freq-only 0.243, paired +D [lo,hi] W/T/L -->
  结果：__（运行中，待填）__。

### #8｜八簇上的 OR 需要小样本稳健性
- **改**：条件化归因加入 **leave-one-screen-out jackknife**——逐一删屏后 adjusted OR 仍在
  **[1.39, 1.87]，全部 > 1**；删掉 Steinhart（最强屏、最该担心的混杂来源）后仍为 **1.65**，说明效应不由单屏驱动。
  写入正文（`analysis/conditional_attribution.py`）。

### #9｜一轮 worked example 数字过强（88% vs 均值 46.5%）
- **改**：caption/正文加免责——"This single round is a mechanistic illustration, not a representative rate:
  its 88% agreement hit rate runs above the 46.5% pooled rate; the pattern, not the level, is the point."

---

## 新增/改动的可复现产物

| 模块 / 数据 | 作用 |
|---|---|
| `WADDINGTON_DROP_ANCHOR_FEATS` + `clean_headline_w0.2.json` | 无特权最终配置（0.255） |
| `WADDINGTON_HITFREQ_ONLY` + `hitfreq_prior_full.json` | recurrence 先验 + online + LLM（#7） |
| `analysis/conditional_attribution.py`（+ jackknife） | OR 1.68 + 逐屏删除范围 [1.39,1.87]（#8） |
| Table 5 重构 | Final Waddington 0.255 为首行；legacy 0.256；完整 LOSO 0.239（#2/#3/#4） |

**结论**：最终主系统 **0.255** 是在**预先冻结、无目标统计量、无 privileged anchor** 的协议下得到（注意：它的
跨实验先验**仍允许使用同研究姐妹屏**）。进一步在**完整 leave-one-study-out**（策略选择与先验训练都剔除姐妹屏）下，
绝对性能降至 **0.239**，但相对同口径 sibling-excluded 先验（0.199）的增量仍为 **+0.041 [0.014, 0.078]**。
不要把"0.255"与"无姐妹 screen"写在同一句。论文主张收敛为：跨实验复发 + essentiality 是强先验；在线适应稳定增益；
LLM 只在高置信 ML 候选上做稀疏验证；自由规划反而有害。

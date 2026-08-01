# 对第八版审稿意见（suggest08.md）的回应与改进

> 无新实验。审稿人指出"回应信说已改、PDF 里仍有"——**这是我的失误，已定位根因并修正**。
> 根因：部分短语**跨行折断**（`statistically` 与 `identical` 分在两行，行级 grep 抓不到），以及
> **同一表述有多处副本**（我只改了一处）。**新的验证标准：对渲染后的 `pdftotext` 文本做审计，而非只 grep 源码。**

## 一、残留措辞（已按渲染 PDF 逐条清零，audit = 0）
1. "statistically identical"（折行）→ "computed on this near-performing predecessor and are retained as
   supporting analyses"。
2. 方法页 "the single most valuable component"（第二处副本）→ "In the legacy predecessor's paired ablation,
   removing this online retraining produced the largest average loss"。
3. memory 强解释（"parametric knowledge … redundant … correctness was never the bottleneck"）→ "provided no
   measurable gain … may reflect redundancy … but ineffective retrieval, presentation, or use cannot be
   excluded"。
4. 附录 "the LLM's T-cell biology is what fills the gap" → "a gene-name-conditioned parametric signal
   appears to fill part of the gap, although its origin cannot be distinguished from memorized associations"；
   另一处 "parametric biology is what the ML prior lacks" → "the ML prior's knockout-derived features have
   least to say"。
5. tool-agent 表说明 "online ML with LLM reasoning" → "online ML with **constrained LLM endorsement**"。

## 二、摘要（现在突出最核心结果）
- 加入并加粗：**"Against its matched static prior, Waddington improves hit@R5 from 0.231 to 0.251
  (+0.020, 95% CI [0.007, 0.035]); but replacing that prior with the pure hit-frequency ranking yields no
  advantage over recurrence alone (0.239 vs. 0.243)."**
- "LLM-only baseline" → "**padded LLM baseline**"；压缩 tools/memory/structure-sufficiency 篇幅。

## 三、Table 5 列名
- "$\Delta$ vs. LOO" → "**$\Delta$ vs. stated ref.**"；每行 reference 在脚注中明确（Final→matched 0.231；
  legacy/router variants→external 0.217；full-LOSO→sibling-excluded 0.199）。同时收紧列宽修掉一处 overfull。

## 四、legacy Tables 6–7 移入附录
- 把 legacy stepwise decomposition（tab:progression）与逐组件 ablation（tab:ablation）及相应段落移入
  "Appendix: supporting and legacy analyses" 的首个子节 "Legacy component decomposition and ablation"；
  主文替换为一段简洁桥接（online 最大损失 / LLM 分支被 padding 混杂 / gene-name shuffle −0.010、Steinhart
  −0.084 → 引出 reason-vs-recall）。**保留** reason-vs-recall（tab:reasoning，摘要正式结论）与 conditional
  endorsement（tab:attrib, tab:cond_attrib，支撑 verifier 主张）于主文。

## 五、reason-vs-recall 两句过强
- "the gene name remains dispensable" → "consistent with gene-name dispensability on average under the
  tested feature representation"。
- "impossible on the one screen where biology is doing real work" → "Steinhart is the clearest exception,
  where the available structural features do not recover the benefit associated with gene-name semantics"。

## 六、标题脚注
- tool-agent 不再是 "central finding"；改为 "**Supporting experiments further show that … a freely planning
  tool-using variant underperforms the constrained policy (Appendix)**"。

---

**验证（按审稿人要求）**：clean build（删 aux/log/pdf 重编两遍）+ 对 `pdftotext` 渲染文本审计——10 个目标短语
全部 = 0；正向检查通过（摘要 0.231→0.251 与 0.239 vs 0.243、Table 5 "stated ref."、附录 "Legacy component
decomposition"、标题脚注 "Supporting experiments"）；无 undefined refs；节序为 主文 → Limitations → Appendix。

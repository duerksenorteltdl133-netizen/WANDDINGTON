这一版已经明显接近可投稿状态，**0.255 的 clean headline、完整 LOSO、条件化验证器分析和 conversational 小节都处理得很好**。不过，我检查新版 PDF 后，仍有几个必须修正的地方，其中两处会直接影响主张的准确性。

# 最重要的两处

## 1. 不能说“0.255 是无姐妹屏协议下的结果”

你在回应总结最后写道：

> 核心结论现在是在预先冻结、无目标统计量、**无姐妹 screen**、无 privileged anchor 的协议下成立（0.255）

这不准确。

论文中的 **0.255 final Waddington**：

* 不使用目标 hit rate；
* 不使用 anchor-relative features；
* 但它的跨实验先验**仍允许使用同研究姐妹屏**。

真正同时从策略选择和先验训练中剔除姐妹屏的 full leave-one-study-out 是：

[
0.239
]

对应的 matched sibling-excluded prior 是：

[
0.199
]

增量为：

[
+0.041\ [0.014,0.078]
]

论文正文对此区分是正确的。

因此总结必须改成：

> 0.255 的主系统是在预先冻结、无目标统计量、无 privileged anchor 的协议下得到；进一步在完整 leave-one-study-out 设置下，绝对性能降至0.239，但相对于同口径 sibling-excluded prior 的增量仍为+0.041。

不要把“0.255”和“无姐妹screen”写在同一句里。

---

## 2. Structure-sufficiency 实验仍使用了被确认有特权泄漏的 anchor features

这是当前最值得警惕的问题。

你已经将anchor-relative features从**最终headline系统**中删除，这是正确的。但A1、线性质心规则和“structure replaces gene name”分析似乎仍使用旧的完整结构特征，包括：

* anchor-relative PPI；
* anchor-relative co-expression；
* pathway overlap；
* 以及其他结构与essentiality特征。

正文还明确说A1的特征包括anchor-relative结构。

但前文已经确认：

* 51%的anchor本身就是目标screen的hit；
* 这是“genuine privileged information”。

因此目前不能毫无限定地在摘要中说：

> replacing every gene name with structural features leaves accuracy unchanged, so the signal lives in structure

因为这个“structure”中包含了一部分目标任务特权信息。即使anchor只贡献0.015，它仍然会污染这个特定的机制主张。

### 最佳处理

重新跑以下两项，删除anchor-relative features：

* A1：匿名ID＋无anchor结构特征；
* linear centroid：同一无anchor结构空间。

然后与真实名称A2比较。

### 若暂时不重跑

摘要和正文必须限定为：

> In the legacy feature space, structural features can substitute for gene names on average; because that analysis includes anchor-relative features later identified as privileged, the result should not be interpreted as a fully leakage-free demonstration of structure sufficiency.

但这样会明显削弱摘要，所以更推荐补跑。

---

# 还需要修复的文字和表格问题

## 3. Table 4仍把legacy 0.256称为Waddington主方法

摘要、Method和Table 5已经将final Waddington定义为0.255，但主结果Table 4和Figures仍然展示：

> C: Waddington = 0.256

随后才在正文括号中解释它是legacy系统。

这会让读者困惑：

* 到底哪个是正式方法？
* 图中的Waddington为什么不是摘要中的Waddington？
* paired results究竟对应哪个系统？

最好直接重做Table 4和主要Figure，使 **Final Waddington 0.255**成为正式行；把Legacy routed C 0.256放入Table 5作为对照。

如果旧消融无法全部重跑，可以保留Table 7，但标题必须写成：

> Ablations of the statistically equivalent legacy routed configuration

主结果表不应再以legacy系统作为“Waddington”。

---

## 4. Table 6把LLM baseline写成“no ML”，与事实冲突

Table 6目前写：

> LLM Reasoning (B): LLM biological prior (no ML)

但Table 4已经诚实说明，B存在大量来自静态LOO-LightGBM的padding，某些screen甚至达到86%，所以它**不是no ML**。

应改成：

> LLM branch, padded by the static prior

或：

> LLM naming + static-prior padding

并避免称它为纯粹的“LLM biological prior”。

---

## 5. “Component B — LLM reasoning”应改名

既然线性质心规则已经追平LLM，而且论文明确承认A1不是LLM reasoning的证据，那么方法部分继续写：

> Component B — LLM reasoning

会与论文自己的结论不一致。

建议改成：

> **Component B — LLM endorsement**

或：

> **LLM-based candidate verification**

同样，Table 6中的“LLM Reasoning”也应统一改名。

---

# 摘要仍有两处略微过强

## 6. “signal lives in structure, not memorised gene identity”与Limitations矛盾

摘要目前说：

> the signal lives in the structure, not in memorised gene identity

但Limitations又正确承认：

> 无法区分LLM的生物知识与记忆；
> 所有九个screen都不能作为训练截止时间后的干净控制。

而且Steinhart上基因名仍有明显正贡献。

建议改成：

> On average across these screens, structural features suffice to match the real-name condition, although individual tasks such as Steinhart still benefit from gene-name semantics and we cannot separate biological knowledge from memorisation.

这与数据更一致。

## 7. “tools, memory, or free choice does not help”仍需加范围

摘要目前容易被理解为一般性结论。正文已经很好地限定为“一个action set、prompt、stopping rule和budget”。

摘要也应写成：

> In our tested setup, adding tools, explicit memory, or unconstrained action selection does not improve performance.

---

# Recurrence实验是当前最后一个真正未完成项

你列出的：

> hit-frequency prior + online update + LLM verification
> vs. hit-frequency-only

仍然处于“运行中，待填”状态。

在这个结果出来之前，正文第9页这句话：

> online-ML and LLM-verification components are what carry it beyond a recurrence baseline

仍然没有直接证据。

建议等实验完成后按结果处理：

* 若配对CI排除0：保留并量化该结论；
* 若均值更高但CI包含0：写“higher mean, but inconclusive”；
* 若没有提升：明确说明系统主要重新包装了recurrence signal。

在结果未完成前，不要提交最终稿。

---

# Conversational部分基本合格

这次新增的小节已经能够支撑标题：

* NL intent router；
* propose–commit–reveal；
* 跨轮状态；
* MAGeCK/CSV上传；
* 新表型注册；
* 明确未做定量界面评估；
* 明确chat模型不直接决定基因。

只有一句建议调整：

> every gene choice is made by the deterministic ML + LLM selector

因为selector中仍包含LLM调用，严格说不一定是deterministic。可改为：

> every gene choice is made by the constrained selection policy rather than by the conversational chat model.

# 当前状态判断

这版已经解决了此前最严重的headline泄漏问题，最终0.255的定位也很干净。摘要已经明确说明它来自实验前metadata、无目标统计量且无privileged features。

投稿前优先完成：

1. **完成recurrence paired experiment。**
2. **重跑无anchor的A1和linear-centroid分析。**
3. **将0.255真正替换进主结果表和主图。**
4. **修正“0.255无姐妹screen”的回应措辞。**
5. **将LLM reasoning统一改成endorsement/verification。**
6. **修正Table 6的“no ML”错误。**

完成这些后，论文的核心主张会非常清楚：

[
\boxed{
\text{复发与essentiality提供强跨实验先验}
+
\text{在线适应改善该先验}
+
\text{LLM对高置信候选提供条件性验证}
}
]

而不是更容易被攻击的“LLM能够独立推理并发现新生物学”。

# 对审稿意见（suggest01.md）的回应与改进

> 一句话总览：审稿人指出的三类核心风险——**按目标屏调参的路由、近邻屏泄漏、若干数字/文字不一致**——
> 已全部用**新实验或诚实披露**处理。**headline 结论未被削弱**：跨实验先验 > 单实验方法这一主张，在
> 冻结协议、去泄漏路由、留一研究（leave-one-study-out）之后仍然成立。所有数字由冻结 JSON 经
> `waddington_select.analysis` 自动生成，无手工抄写。

论文 = `docs/results_tables.tex`（22 页，编译干净）。下表按审稿人自己的 P0/P1/P2 优先级组织。

---

## P0 —— 不解决就影响结果有效性

### P0-1｜路由使用了目标屏的真实 hit rate（最严重）
- **意见**：fusion routing 依据真实 hit rate 选权重、feature set 又是"试到最好留着"，构成测试集调参。
- **改进**：做了**去泄漏路由确认实验**，协议在看结果前**冻结并提交**（`waddington_select/router_protocol.py`）。
  新增两个只用非目标屏 + 实验前元数据（池大小、扰动模态、细胞系）的开关：`WADDINGTON_FORCE_WLLM`
  （全局单一权重，不看 hit rate）与 `WADDINGTON_FEATURE_POLICY=metadata`（纯元数据特征规则）。
- **结果**：诚实 **global-fixed（w=0.2）= 0.264 ≥ 现行有路由的 C 0.256**；对比 LOO 先验
  **+0.047 [0.025, 0.071]，9/0/0**；nested 元数据路由 0.260。即**真实 hit-rate 路由没有制造结果**，反而在小屏上
  略次优（Scharenberg22 在 w=0.2 下 0.55 vs 有路由 0.45）。
- **位置**：Method"What the router may and may not know"披露 + Results"Robustness to a leakage-free router"
  （Table 5）。复现：`python -m waddington_select.analysis.router_analysis`。

### P0-2｜留一屏不足以阻止近邻（同研究）泄漏
- **意见**：IFN-γ/IL-2、Sanchez21/-down、K562-Essential/-GWPS 三对同源屏，留一屏时姐妹屏仍在训练集。
- **改进**：（a）先验探针里报告**排除姐妹屏**的 LOO；（b）新增 `WADDINGTON_EXCLUDE_STUDY`，把同研究姐妹屏
  从跨实验先验的训练集中剔除，跑**最严格的留一研究**（姐妹屏既不参与配置选择、也不进先验）。
- **结果**：姐妹屏进先验时 C=0.264 → 剔除后 **0.239**（K562-Essential 0.587→0.444、IL-2 0.358→0.308）。
  但**同样的处理也把裸 LOO 先验从 0.243 拉到 0.199**；同口径对比（双方都被剥夺姐妹屏）**C 仍胜先验
  +0.041 [0.014, 0.078]，7/9 屏获胜**。结论：姐妹结构抬高的是**绝对命中率**，不是 C-over-prior 的增量。
- **位置**："What the cross-experiment prior actually learns"子节 + Table 5 后的严格留一研究段。
  复现：`python -m waddington_select.analysis.prior_probes`（含 sibling 排除）。

### P0-3｜三处会被立刻抓到的矛盾
- **A（是否真跑了 BioDiscoveryAgent）**：删除 Limitations 里残留的"never ran their agent"，全篇统一为
  "受控改编运行（我们的后端 + 评测框架）"。
- **B（混用 6 屏与 9 屏均值）**：把层级改为**同一六屏**上的 `BDA 0.105 < LOO 0.187 < C 0.217`，0.256 单独标注为九屏。
- **C（GeneDisco 5 条还是 8 条规则）**：表格单元格显式区分"oracle over **their 8**（转写）"与
  "oracle over **our 5**（受控）"，并核实受控 best-per-screen 确为 5 条规则。

---

## P1 —— 决定论文贡献是否站得住

### P1-3｜"LLM 是验证器"需要控制 ML 分数的条件化实验
- **意见**：agreement 组 46.5% 可能只是"ML 分最高的那批"，需在固定 ML 分后看 endorsement 是否仍有增益。
- **改进**：在八个加权屏上按**屏内 ML 分十分位**分层，比较"LLM 点名 vs 未点名"；再做带屏固定效应的
  logistic 回归（`analysis/conditional_attribution.py`）。（顺带查清 JSON 里 `overall` 的 llm_only=27.7% 是把退化的
  two_stage 屏 K562-GWPS 混入所致；论文用的 8.1% 才对。）
- **结果**：endorsement 的价值**只集中在 ML 高分区**——顶部三分位 **43.1% vs 17.4%（2.48×）**，中低分位≈0；
  logistic **OR = 1.68，95% CI [1.05, 2.52]**（屏聚类 bootstrap，排除 1）。即"验证器"效应在控制 ML 分后**依然成立**，
  且精确化为"只在 ML 已自信处验证"。
- **位置**：Explainability"Does endorsement add signal beyond the ML score?"+ Table 12。

### P1-4｜reasoning vs recall 缺一个简单线性基线
- **意见**：A1 用结构特征达 0.265，但没证明是 LLM 在推理——一个线性质心规则可能就够。
- **改进**：新增 `waddington_c_linear`（`_LinearCentroidLLMArm`），在**同样的匿名特征空间**里用
  (命中质心 − 非命中质心) 方向给候选打分，**不用 LLM**。
- **结果**：**线性规则 0.268 ≈ A1 的 LLM 0.265**（线性还略高）。据此把结论从"LLM 会推理"**诚实改写**为
  **"结构足以替代基因名；LLM 只是实现该映射的一种（此处可被线性规则替代的）方式"**——摘要也相应改为
  "structure-sufficiency rather than LLM reasoning per se"。
- **位置**：摘要 + Reasoning-vs-recall 的"Is this the LLM reasoning, or would any rule do?"段。

### P1-5｜跨实验先验的"反平凡化"基线
- **意见**：先验主要收益也许来自通用 essentiality / hub / "容易成为任何屏命中"，而非表型特异迁移。
- **改进 + 结果**（均在 `analysis/prior_probes.py`）：
  - **跨屏命中频率基线**（无模型、无特征）= **0.243 = LOO**——LightGBM 并未超过"数命中复发"。
  - **特征族消融**：DepMap-only 0.230、intrinsic-only 0.218、去 DepMap 0.228、全特征 0.243——先验重度依赖
    knockout essentiality，非屏特异。
  - **新命中率**：收益集中在命中复发的屏（K562-Essential 仅 6% 新命中），在新命中主导屏（Carnevale22 80%）近随机。
  - **anchor 泄漏审计**：**51%（42/82）的 anchor 本身就是本屏命中**（gene_ranker.DATASET_ANCHORS），
    但**去掉全部 anchor-relative 特征仅损失 0.015**（0.243→0.228）——泄漏真实但不承重。
- **诚实结论**（写入子节）：先验靠的是**复发 + essentiality**，不是发现新的表型特异生物学；但即便剔除姐妹屏
  (0.182)、去 DepMap (0.219)、去 anchor (0.228)，仍远高于单实验方法（~0.11）。

---

## P2 —— 表达与定位

- **§6 标题里的 "Agent"**：保留但加限定，改为
  **"Waddington: A Constrained Conversational ML–LLM Agent for Sequential CRISPR Gene Selection"**，
  并用脚注说明——有状态序贯回路、逐轮观测反馈、跨轮更新、自然语言对话前端 ⇒ 是 agent；"constrained
  conversational" ⇒ 不是自由规划的工具型 agent，策略刻意把 LLM 限制为对校准 ML 候选的验证/重排。
- **§7 "工具无用"缩小范围**：小节标题由"Does giving the LLM tools help? (No.)"改为
  **"A freely planning tool-using agent underperforms the constrained pipeline"**，并加一句 scope 说明
  （单一 action set / prompt / 预算，不等于"工具通常无用"）。
- **§8 统计增强**：新增 `analysis/clustered_ci.py`——**以屏为簇的 bootstrap**。绝对均值 CI 因九屏异质而重叠
  （不再宣称均值显著），但**配对增量**排除 0（C vs LOO +0.039 [0.019, 0.062]，9/0/0），并给出 win/tie/loss。
- **§9 记忆污染**：P1-4 的线性基线已把"LLM 生物推理"的口径整体收敛为"结构足够"；验证器主张也已由条件化
  实验（OR 1.68）实证支撑，而非诉诸记忆。
- **伪代码 + 一轮实例**：Method 里加了 C-arm 一次 campaign 的方框伪代码 + IFN-γ 第 1 轮真实走查
  （both 桶 14/16=88% vs ml-only 38% / llm-only 40%）。

---

## 新增的可复现产物（都不需重跑 LLM，除路由确认外）

| 模块 / 数据 | 作用 |
|---|---|
| `waddington_select/router_protocol.py` + `workspace/results/router/protocol.json` | 冻结的去泄漏路由协议（结果前提交） |
| `analysis/router_analysis.py` + `workspace/results/router/*.json` | 去泄漏路由两变体 + 留一研究 + 配对 bootstrap |
| `analysis/conditional_attribution.py` | 控制 ML 分后的 endorsement 增益（OR 1.68） |
| `analysis/prior_probes.py` | 姐妹排除 / 命中频率 / 特征族 / 新命中 / anchor 审计 |
| `analysis/clustered_ci.py` | 屏聚类 bootstrap + win/tie/loss |
| `arms/waddington_c_feature_reasoning_arm.py::WaddingtonCLinearArm` | A1 的线性质心对照（无 LLM） |
| 受控 `workspace/results/bda_controlled/` + `sequential/genedisco_ported.json` | BDA / GeneDisco 在我们 benchmark 上的受控运行 |

**总结**：审稿人最担心的"性能提升可能同时受 per-screen 配置、近邻迁移、通用 essentiality 影响"——三点都被
量化：配置（路由）不承重、近邻迁移抬绝对值但不抬增量、通用 essentiality 是先验的主要来源（已诚实写明）。
锁定路由、留一研究、条件化归因之后，结论更稳而非更弱。

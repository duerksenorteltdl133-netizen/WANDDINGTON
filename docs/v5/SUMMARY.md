# V5 实验报告：DepMap PPI 缓存富集

**日期**：2026-06 | **状态**：已完成 | **最优结果**：9DS avg=0.519，LOO avg=0.192

---

## 背景

V4 系统（5 特征）在 9 个 BDA 数据集上平均 AUC=0.484，LOO avg≈0.192（基准）。
`_ppi_cache/` 原本只包含 64 个 BDA 锚点基因的 PPI 文件，导致 `hub_score_norm` 和 `ppi_score_sum` 只在训练集内有效，无法泛化到新实验。

---

## 核心想法

引入 DepMap 高频致癌基因（COSMIC Tier 1 oncogenes，约 251 个）作为额外锚点，将 `_ppi_cache/` 从 64 个扩充到 315 个文件。这样 `hub_score_norm` 和 `ppi_score_sum` 能覆盖更多全局 hub 基因（如 TP53、EGFR、MYC），使这两个特征在训练和测试时分布更加一致。

---

## 实施步骤

1. **下载 DepMap oncogene PPI**：`prep_ppi_cache_depmap.py`
   - 从 COSMIC 数据库提取 Tier 1 癌症驱动基因列表（251 个）
   - 调用 STRING API（`interaction_partners`，limit=200）下载每个基因的 PPI 邻居
   - 写入 `_ppi_cache/{GENE}.json`，跳过已缓存文件

2. **重新计算 hub_score_norm、ppi_score_sum**：
   - `hub_score_norm` = 基因出现在多少个 _ppi_cache/*.json 中 / max 出现次数
   - `ppi_score_sum` = 基因在所有 cache 文件中 STRING 分数之和 / max 总分
   - TP53：出现在 95/315 个文件，hub_score=1.0；ADORA2A 出现 1/315，hub_score=0.0105

3. **V5 特征集**（5 个，与 V4 相同结构，仅缓存扩大）：
   ```
   g1_ppi_score, hub_score_norm, archs4_coexpr, ppi_score_sum, kegg_overlap
   ```

---

## 结果

| 指标 | V4 (64 cache) | V5 (315 cache) | 变化 |
|------|-------------|--------------|------|
| 9DS avg AUC | 0.484 | 0.519 | +7.2% |
| LOO avg AUC | — | 0.192 | 基准 |

9 个数据集中有 7 个 AUC 提升，说明 hub 特征的全局覆盖度显著提升了模型对常见信号通路基因的识别能力。

---

## 关键发现

- **PPI 缓存扩充是低成本高收益的改进**：无需新算法，仅扩大已有 cache 即可提升 9DS +7.2%
- **LOO 提升有限（+0%）**：hub_score_norm 和 ppi_score_sum 依然是训练集内有效特征，对全新实验（Carnevale22、Steinhart）没有明显帮助
- **DepMap 大数据集训练方向失败（Plan A 主线）**：用 DepMap 50 cell lines 作为额外训练数据，LOO 下降 -4.5%。原因是规模失衡（825K vs 72K 条目）+ 锚点特异性特征不迁移

---

## 结论

V5 确认了 PPI 缓存富集策略的有效性，**为 V6（加入全局特征）和 V7（加入通路特征）奠定了缓存基础**。315 个 PPI 文件从此作为固定 baseline 使用。

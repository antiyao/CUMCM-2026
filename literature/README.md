# CUMCM Historical Modeling Knowledge Base

这是为 CUMCM 2026 准备的历史论文知识库。核心是 32 篇已批准论文的深度蒸馏，而不是 PDF 收藏或可直接复制的解题模板。

每篇报告保留模型选择、数学结构、参数与假设、验证边界、敏感性、复现审计、数值复核和 claim-level traceability。历史方法只是参考；真正比赛中必须根据当前数据、假设、目标和约束重新判断。

## Scope

- Batch 1：5 篇 calibration reports。
- Batch 2：10 篇 schema v1.1 reports。
- Batch 3：17 篇 schema v1.1 reports。
- 合计：32/32 篇，全部通过对应结构校验，无 active blocker。

Batch 1 保留冻结的 `1.0-calibration` 例外；不应将它们改写成 v1.1 或补造后来才定义的复现等级。

## Provenance boundaries

| Tier | 含义 |
|---|---|
| `V` | 全国一等奖已与官方名单独立交叉核验。 |
| `E` | 官方页面明确标识为优秀论文，但精确奖级未知。 |
| `O` | 论文身份与官方展示匹配，奖级未核验。 |
| `O*` | 主文与官方展示一致，但存在额外伴随代码附录或版本边界。 |
| `L` | 仅有本地收集副本；文件名、目录或声称不构成奖项证据。 |

官方展示不等于全国一等奖。详细来源、核验 URL、SHA 和版本边界见 [`metadata/provenance.csv`](metadata/provenance.csv)。

## How to use

1. 比赛早期先读 [`synthesis/QUICK_REFERENCE.md`](synthesis/QUICK_REFERENCE.md)，建立常见决策规则和失败模式清单。
2. 按题型、目标、技术或验证需求查 [`synthesis/INDEX.md`](synthesis/INDEX.md)，选出约 3–6 篇最相关论文。
3. 用 [`metadata/core_papers.csv`](metadata/core_papers.csv) 过滤年份、题号、原型、方法、验证和 exemplar。
4. 需要数学细节、证据边界或可复用技术时，进入 [`per_paper/`](per_paper/)。
5. 引用历史结论前回到逐篇报告的 Traceability，不从 INDEX 或 QUICK_REFERENCE 直接当作原始证据。

## Shareable structure

```text
literature/
├── README.md
├── metadata/
│   ├── core_papers.csv
│   ├── provenance.csv
│   ├── completion.csv
│   └── model_matrix.csv
├── per_paper/
│   └── <32 validated distillations>
└── synthesis/
    ├── INDEX.md
    └── QUICK_REFERENCE.md
```

`model_matrix.csv` 保留比 `core_papers.csv` 更细的预处理、模型、优化、验证、敏感性和鲁棒性字段，因此不属于冗余进度表。

## Local-only material

`raw_papers/`、`extracted/`、`acquisition/` 和 `tmp/` 包含 PDF 原件、OCR、官方页面快照、采集过程记录、临时渲染和旧工作流审计。它们故意保留在本机并由 `.gitignore` 排除，不属于正常知识检索的依赖。

不要为了减小 Git 仓库删除原始 PDF。需要复核公式、图表、OCR 或 provenance 时，再使用本地原件和过程归档。

# CUMCM 2026 正式论文

主文件为`main.tex`，通过`sections/`组织章节；使用XeLaTeX，当前线上TeX Live版本为2025。

已完成：1.1问题背景、1.2四问要求、1.3图示流程与6条模型假设。摘要、符号、四问模型和模型评价等仍待编写，不能把本工程视为完整定稿。当前计算结果以仓库`results/final_recommendation/`为准。

当前SJTU项目：https://latex.sjtu.edu.cn/project/6aa27f6bbd92933f73a5ac15 。正文与线上协作时，先检查双方当前内容再按章节同步，避免覆盖队员编辑。

本地编译：

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build main.tex
```

最新预览为`build/main.pdf`；本地根目录旧`main.pdf`因失效已删除。`figures/总体流程图_图示版.pdf`是实际Canva矢量导出；可编辑SVG在同目录，详细来源见仓库`figures/overview/canva/`。

类文件与样式来自保留的原模板。编译通过不等于已完成当届格式、匿名、AI披露或最终提交审查。

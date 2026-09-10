# 论文工作区

- `template-original/`：2026 LaTeX 原模板，完整保留。
- `overleaf/`：正式论文源码，对应 SJTU Overleaf 项目根目录。
- `releases/`：按日期保存源码 ZIP、编译 PDF 和交付材料。

## 协作约定

1. 代码、原始数据、计算结果以仓库为准；正文以 Overleaf 为准。
2. 按章节分工，一人维护主文件、样式和图表同步。
3. 图表由本地程序生成，选定后导入 `overleaf/figures/` 和 `overleaf/tables/`。
4. 下载线上源码后先比较差异，再更新本地；本地与线上不同时独立修改同一章节。
5. 每轮整合完成后保存源码和 PDF。Git 提交与推送由用户明确授权。
6. 定稿前核验当届格式、匿名要求、AI 使用声明和支撑材料；占位稿不得直接提交。

## 平台

- 平台：SJTU LaTeX 文档助手（https://latex.sjtu.edu.cn）。
- 当前项目：[用户指定的论文工程](https://latex.sjtu.edu.cn/project/6aa27f6bbd92933f73a5ac15)。2026-09-10已原样上传23个本地工程文件，保留分章目录，在线XeLaTeX / TeX Live 2025编译4页通过。
- 上传前线上备份：[上传前备份_2026-09-10_6aa27f6b](https://latex.sjtu.edu.cn/project/6aa2f413bd92933f73a7e404)。上传包和核验清单见`releases/2026-09-10-overleaf-sync/`。
- 赛前历史项目：[CUMCM-2026](https://latex.sjtu.edu.cn/project/6a9ecf15bd92933f73952eba)。
- 主文件：`main.tex`；编译器：XeLaTeX。
- 2026-09-07：本地 TeX Live 2025 编译成功，输出 2 页 A4 PDF，已逐页检查。
- 2026-09-07：线上项目已创建，设置为 XeLaTeX、TeX Live 2025、`main.tex`，成功生成 2 页 PDF，已检查线上预览。
- 原模板 12 个文件移动前后 SHA-256 一致；正式骨架中的 `.cls` 和 `.sty` 保持原样。
- 本地日志有 STHeiti 粗体字形替代警告，未发现文字溢出或缺字。本地和线上中文字体可能因系统环境而不同，以线上最终 PDF 为排版基准。
- 初始源码 ZIP 和本地预览：`releases/2026-09-07-initial/`。
- 当前菜单未显示 Git/GitHub 集成入口；先使用手动上传和源码 ZIP 回存流程。
- 尚未添加队友，尚未完成多人编辑及线上源码回存的完整演练。

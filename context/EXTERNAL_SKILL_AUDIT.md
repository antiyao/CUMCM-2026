# 外部 Skill 与官方 AI 规则审计

核查日期：2026-09-10。范围仅为总指令第 2、12 节的两个核心绘图候选、Codex 官方技能发现机制，以及本地论文格式文件指向的官方 AI 使用规定。未检索或阅读本届其他参赛者解答，未重新启动往年论文蒸馏。

## 结论与接入范围

两个候选均有与本项目直接相关的用途，已先隔离下载、阅读和静态审查，再分别接入 `.agents/skills/scientific-visualization/` 与 `.agents/skills/matplotlib/`。每个目录保留 `LICENSE.md`、`PROVENANCE.json`，没有嵌套安装整个上游仓库，没有修改既有论文技能或知识库，也没有安装 Python 包、浏览器、云服务或其他外部技能。

| 项目 | 当前核实结果 |
|---|---|
| 上游仓库 | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) |
| 固定 commit | `9cf7d9aea7d84754db4c167ab04b299d33c444bc`，commit 时间 `2026-09-07T09:35:26Z` |
| 入口版本 | 两项 `metadata.version` 均为 `1.2` |
| 许可证 | 上游仓库 `LICENSE.md` 为 MIT，Copyright 2025 K-Dense Inc.；上游 Matplotlib 入口原先的 license 链接指向绘图库许可证，已在本地入口澄清技能自身采用仓库 MIT |
| 隔离副本 | `results/audit/external_skills/9cf7d9aea7d84754db4c167ab04b299d33c444bc/` |
| 下载范围 | 两个技能目录及根许可证，共 26 文件、280632 字节；`DOWNLOAD_MANIFEST.json` 保存逐文件 URL、字节数与 SHA-256 |
| 静态扫描 | `STATIC_SCAN.json`，覆盖全部 10 个 Python 文件的 AST、导入和 I/O/执行调用定位 |

本机相关技能目录的有界检查未找到已存在的同名绘图技能。读取了内置 `openai-docs/SKILL.md` 与 `skill-installer/SKILL.md`；后者默认指向旧 `openai/skills` 及用户安装目录，本次没有使用其默认获取或安装流程，而是把已审查的两个目录复制到用户指定的项目目录。安装后的入口可供后续轮次发现；本轮实际通过读取文件应用其绘图原则，不声称热加载已经被 UI 验证。

## 实际阅读与审查深度

完整阅读了两个上游 `SKILL.md`、根 `LICENSE.md`，以及 scientific-visualization 的 `references/publication_guidelines.md`、`references/color_palettes.md`、`scripts/_common.py`、`scripts/palette_audit.py`。逐段检查了 `scripts/figure_export.py` 的核心导出与文件写入实现、`scripts/style_presets.py` 的本地资源动态导入、`assets/color_palettes.py` 的数据与动态导入目标、Matplotlib 两个脚本的主入口与输出实现。

其他脚本做了 AST/导入/I/O 静态扫描，未执行；这不等同于对全部脚本和依赖的安全证明。期刊规范参考文件并非本届国赛要求，因此没有为套用期刊尺寸而展开阅读或执行其 publisher-profile 工具。

## 风险、局部适配与执行边界

1. 未在扫描的 Python 文件中发现网络请求、原始数据上传、凭证读取、远程 shell、付费 API 或外部进程执行代码。`exec_module` 仅加载同目录的固定 `assets/color_palettes.py`，目标已经检查；`os.chmod(0600)` 只用于新建临时输出文件，不涉及系统安全设置。
2. Matplotlib 原入口含环境安装、uv/Python 全局升级和 GUI 后端建议，两个入口都有自动为上游论文添加引用的指令。已在安装版入口添加项目范围规则，移除自动论文引用段，替换 Matplotlib Setup，明确不跟随环境升级、原始数据上传、营销和自动添加未核实论文引用。原文完整保留在隔离目录，修改逐项记录于 provenance。
3. Matplotlib 的 `plot_template.py` 使用演示数据、默认输出 `plot.png` 并可直接覆盖；`style_configurator.py` 以 `open(..., 'w')` 覆盖样式文件。安装版入口明确禁止把这两个演示脚本直接运行到项目结果目录。不得把其硬编码的演示误差带当成本题置信区间或预测区间。
4. scientific-visualization 导出器默认拒绝覆盖，采用同目录临时文件与替换。它仍不能证明图中数据、来源归属、账本或模型正确。未运行示例生成器；后续仅在阅读所需函数后按项目新输出路径使用。
5. 上游固定包版本和 Nature 等期刊尺寸都是历史快照。继续使用项目实际环境、Matplotlib 静态后端与已有中文字体；不得据此宣称满足国赛论文格式，不能通过压制缺字警告掩盖中文缺字。
6. 本次未安装 statistical-analysis、scientific-critical-thinking、frontend-design、SciencePlots、Plotly 或 Kaleido。SciencePlots 是可选绘图库样式包，不是 Agent Skill。建模和验证优先。

## 可直接采用的本题绘图要求

- 图前写明论点、源结果路径、转换、单位、图型及图注；用脚本重现，任何平滑、聚合、归一化必须记录。
- Matplotlib `Figure/Axes` 显式 API 配合 `rc_context`；使用一个布局引擎。`layout='constrained'` 后不再调用 `tight_layout()`。要求固定物理尺寸时避免 `bbox_inches='tight'` 改变页框。
- 同一物理量跨图保持颜色/单位一致，同时使用线型、点型、标注或分图。费用柱形/面积图采用零基线，策略比较共用刻度。
- 问题 1 负载、光伏、购电绘在同一功率尺度；SOC/储能量与充放电功率分开，标注物理上下界。功率与每时段电量不混用。
- SOC 日期×日内时刻热力图与紧急购电热力图分别输出；缺失数据使用明确颜色，不能默认为零。比较热力图固定色标范围。
- 预测区间须标明是经验分位、场景范围或经过校准的预测区间，并注明信息发布时间；不自动命名为置信区间。Q1 确定性实际序列不额外添加误差条。
- 账务费用分解严格引用选定账本，避免重复计入计划购电、增购、违约、退款和紧急购电。未建模能流来源归属时不画定量 Sankey。
- 每张图独立输出 PDF/SVG 与 PNG 预览，保留源数据引用。按论文最终尺寸检查中文缺字、边缘裁切、图例重叠、灰度可读性和单位。

已实际运行网络无关的 `palette_audit.py`，结果保存为隔离目录中的 `palette_smoke.json`：`okabe_ito_on_white` 五色对白背景对比度分别为 5.185、3.867、3.421、3.061、21.000，均通过 3:1 图形阈值；十组颜色对中四组未通过 ΔL*≥10 的灰度启发式筛查。因此必须配线型/点型或分图，不能称“调色板已保证无障碍”。两个本地入口与全部 Python AST 结构检查通过。

## 当前 Codex 官方发现目录

已实际打开 [官方 Build skills](https://learn.chatgpt.com/docs/build-skills)；原 `developers.openai.com/codex/skills/` 当前重定向到该页。官方写明：项目技能扫描当前工作目录到 Git 根目录各层的 `.agents/skills`；用户级目录为 `$HOME/.agents/skills`，管理级为 `/etc/codex/skills`，并有随 Codex 捆绑的系统技能。支持符号链接。变更通常自动发现，未出现时可重启。

本会话确实提供了 `~/.codex/skills` 中的现有技能，但不能据此把该历史路径、`.codex/skills` 或 `.claude/skills` 宣称为当前官方文档列出的通用发现机制。官方 Markdown 快照保存在 `results/audit/official_rules/codex_build_skills.md`。

## 官方 AI 工具使用规定核查

官方文件：[全国大学生数学建模竞赛人工智能工具使用规定（2026年试行）](https://www.mcm.edu.cn/html_cn/node/fef94648f2836ab6cc81586f4c38512b.html)，官网发布日期 2026-08-03，2026-09-01 起试行；[官方 PDF](https://www.mcm.edu.cn/upload_cn/node/785/Glps6mBh6563c55c45300fede72ddbf6eb33d3a8.pdf)。已下载 HTML、PDF、提取文本和 provenance 至 `results/audit/official_rules/`，PDF SHA-256 为 `4cf6f30cdd37d6ef2cdb3439c5dba4d9f207c12d6aafe24419e81f3c69acf59a`。

实际条款摘要：

- 第 1—2 条：涵盖大语言模型、生成式 AI、代码辅助与 AI 智能体；允许使用 AI，要求公开透明、核心建模与分析由参赛队主导，对 AI 参与内容逐项人工审查核实。
- 第 3 条：论文参考文献前必须设置 AI 工具使用声明；本项目已实际使用 AI，不能声明未使用，也不能把实际建模求解和代码实现仅写成语言润色。
- 第 4 条：支撑材料须含 PDF 格式的 `AI工具使用详情.pdf`，记录工具名称与版本/型号、目的环节、主要提示方式与过程、AI 输出采纳/人工修改/核验情况；语言润色豁免的是最后一项说明，不是整份披露。
- 第 5—7 条：隐瞒、虚假声明或未经必要人工核实直接提交 AI 生成的核心成果会取消评奖资格；新规自 2026-09-01 起优先于此前不一致规定，由全国组委会解释。

本次官方检索没有接触本届解答，不因此中止已经授权的建模工作。后续代码与数值的自动测试不能冒充参赛队员人工审核；应持续保存实际 AI 用途与交互证据，在提交前由队员复核核心模型、公式、代码、结果及披露，具体核验人和核验状态不得虚构。

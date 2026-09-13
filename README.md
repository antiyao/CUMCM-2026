# CUMCM 2026 C题

src仅保留problem1.py、problem2.py、problem3.py、problem4.py、microgrid.py五份。运行方法见docs/REPRODUCE.md。

当前输入在data/processed，原始赛题数据在data/raw，原始结果模板在templates。冻结数值在results/c2026，当前论文PDF、五份结果Excel和唯一支撑包在results/c2026/submission。论文源码在paper/overleaf，当前核验记录在results/c2026/verification。

Excel只填写原模板已有位置，行数、标签、省略号和格式不变，完整年度明细另附CSV。AI工具使用详情PDF仍待补齐，未上传比赛平台。

补充包共23个文件，按后缀分组；年度轨迹、费用摘要和核验数据已合并，包内不含空模板。运行 `python3 docs/package_submission.py` 可同步生成支撑包和论文附录，再用XeLaTeX编译论文（表格位置需连续编译三次）。

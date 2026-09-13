# C题支撑材料

四问各有一份求解代码，公共微网模型、储能控制与结果导出集中在microgrid.py。

使用Python 3.12，从解压目录运行：

```bash
python -m pip install -r configs/requirements.txt
python src/problem1.py --input data/processed/annual_inputs.npz --out runs/q1
python src/problem2.py --out runs/q2
python src/problem3.py --out runs/q3
python src/problem4.py --part 2 --out runs/q4_2
python src/problem4.py --part 3 --out runs/q4_3
```

输出目录使用尚不存在的新目录。问题二至四加--checks可运行论文对应的预测、储能控制、网格或电价基准比较。问题一默认输出LP/MILP/网格DP及敏感性检验结果。年度求解可能需要较长时间。

检查包内冻结年度结果，并据此重建Excel：

```bash
python src/microgrid.py verify
python src/microgrid.py rebuild --out runs/workbooks
```

重建后的五份Excel在runs/workbooks/filled。程序直接沿用包内result*.xlsx的行数、表头、时间标签、省略号及格式，从运行轨迹重新计算并填写数据，因此无需另附空白模板。运行轨迹使用包内冻结结果；上面各模型命令的新结果独立写入指定目录。

年度计划/调整表覆盖334天，充放电与紧急购电表只填原有日期。完整年度轨迹合并在annual_slots.csv，逐日汇总在annual_daily.csv，case列区分q2、q3、q4_2、q4_3；各case内保持日期和时段顺序。原数值文本完整保留，各方案独有字段在其他方案的记录中留空。

summaries.json按q1、q2、q3、q4_2、q4_3保存各问摘要。analysis_results.json汇总问题一敏感性和网格检验、问题三预报精度和信息价值、Excel及代码核验结果；CSV表以columns和rows保存，数值字符串保留原精度。previous_model_checks记录合并前验证，consolidation记录本次整理验证。

结果表购电标签比模型区间晚十分钟，按原样保留。数值按144个区间的序号填写，slot=0对应00:00-00:10，slot=143对应23:50-24:00；问题一的精确时间见schedule.csv。

问题四-2在不同数值库环境下冷复跑可能相差约10元，本包保留论文对应冻结结果。原始比赛附件未重复打包，处理后的必要输入已全部包含。

AI工具使用详情.pdf尚待队员补齐；加入后需再次核对文件列表、20MB限制及最终MD5。本包未上传比赛平台。

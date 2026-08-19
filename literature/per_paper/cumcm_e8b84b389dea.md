# Paper: 碳化硅外延层厚度的双光束和多光束干涉法测量研究

## Metadata

- Distillation schema: 1.1
- Paper ID: `cumcm_e8b84b389dea`
- Year: 2025
- Problem: B157，B 题
- Award: 奖级未核验。只能确认本地文件的年份、B157代码和67页记录与组委会官方展示匹配；官方展示不证明具体奖项。
- Provenance tier: O; 本地副本与官方展示的年份、代码和页数一致，奖级不推断
- Source file: `literature/raw_papers/2025/B157.pdf`
- Source URL: unknown；本地来源为用户提供合集
- Verification source: `https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025btlw/251107/2023197.shtml`
- Pages: 67
- SHA-256: `d4009bf9120cdc89e796de2101592c46665b0af322a56bdb2f4e8ab52414801a`
- Extraction method: 原 PDF 因 malformed Boolean 无法由 pypdf 读取；使用 Ghostscript `pdfwrite` 临时兼容副本作为渲染输入，再以 Tesseract 5.5.0 `chi_sim+eng`、250 DPI、PSM 3 OCR；原件未修改
- Extraction quality: 67/67 页 OCR 成功、0 页错误，质量 `ocr_usable_with_visual_review`。原件与兼容副本均为67页，67/67页在50 DPI RGB PPM下逐像素哈希一致；OCR quality 已回锚原路径与原 SHA。公式、残差图和代码均以原页为准。
- Page convention: 1-based physical PDF pages
- Visually checked pages: p1、p5、p8、p10、p12--15、p17--18、p23--26、p29、p32、p36、p38--39、p41--42、p44、p46--47、p49、p59、p61、p63、p65、p67
- Unresolved extraction ambiguities: OCR 对代码标点和个别上下标有误识别，但本报告引用的关键公式、参数、分支与数值均已直接核页。正文的 DW/Ljung-Box统计量、协方差数值、合成实验重复数及若干输出日志未提供。
- Supplemental artifacts: p29--67 展示 Python 源码，引用 `1_Sic10.xlsx`、`2_Sic15.xlsx`、`3_Si10.xlsx`、`4_Si15.xlsx` 及中间 CSV/JSON/图像；仓库无这些输入、独立 `.py` 文件或运行输出。可靠性分析和 SiC Airy 复算代码未完整出现在附录。

## 1. Problem Archetype

本文属于“光学机理反演 + 光谱信号处理 + 多角联合非线性拟合 + 模型选择与不确定性审计”的原型：

- 由 Snell/Fresnel、光程差和 Cauchy 色散构建两光束反射谱。
- 用 AsLS、Hampel、Savitzky-Golay、滑窗 FFT 和 SNR 选择有效波段并给厚度初值。
- 用共享厚度/色散、角度和波数校准的双角鲁棒最小二乘做 SiC 厚度反演。
- 用分段 Cauchy 修复宽波段色散失配。
- 推导 Airy 多光束模型，对 Si 判断多光束显著，对 SiC 判断高阶反射可忽略。
- 以残差、子带、角度、参数协方差、系统扰动和合成数据回收评价结果。

该结构是高价值反问题模板，但不能把同模型合成回收或视觉残差诊断等同于真实厚度校准。代码中还有硬编码频带、边界参数、隐藏正弦修正和衬底折射率不一致，限制“准确可靠”的结论。

## 2. Problem Decomposition

1. **正向模型：** 建立两光束相位与反射率，折射率用 Cauchy `n(lambda)=A+B/lambda²`。
2. **预处理：** 波数等距重采样；SiC去除低于1000 cm⁻¹的 Reststrahlen 区；AsLS去基线、Hampel去尖峰、SG平滑。
3. **频域初值：** 滑窗 FFT 估主频与SNR，选 SiC `[2500,3700] cm⁻¹`，由周期和折射率求两角厚度初值。
4. **联合反演：** 每曲线闭式估计幅值/基线，共享 `d,A,B,epsilon`，分别估计两角修正，鲁棒有界最小二乘。
5. **分段色散：** 在3300 cm⁻¹处分两段Cauchy，并以软惩罚近似保证函数/导数连续。
6. **可靠性：** 残差直方图/Q-Q/FFT、双角一致性、子带、协方差、刻度/角度扰动、同模型合成数据。
7. **多光束：** 推导Airy级数；Si数据轻量去基线、FFT和联合拟合，得到3.814 μm；SiC用界面反射率与Airy复算支持两光束近似。

## 3. Data Processing

- 反射率若大于1.5则除以100，随后每条曲线做 Min-Max 归一化；绝对反射率幅值被删除。
- 波数轴用原始步长中位数线性插值为等间距网格。
- SiC 低于1000 cm⁻¹整体裁剪；AsLS参数 `lambda=1e5,p=.001,niter=10`，Hampel `k=3,t=3`，SG窗口11/二阶。
- SiC滑窗FFT窗口300 cm⁻¹、步长60；代码筛选 `SNR≥10`、双角频差≤10%、连续跨度≥300、边缘裁20。
- 正文另要求至少25周期，但可得筛选代码没有实现周期数条件；计算出候选后又把 `band_used` 硬编码为 `(2500,3700)`。
- Si仅保留500--4000 cm⁻¹，线性去基线；正文声称选带 `SNR>15`、频差≤3%，代码仍用10和10%，随后硬编码 `(1170,2170)`。
- 每个角度最终再闭式拟合独立线性幅值/基线 `a_k,b_k`，使相位主导厚度，但削弱Fresnel幅值和界面反射率的可辨识性。

## 4. Models Used

### 两光束 Cauchy 正向模型

**Purpose:** 把外延层厚度映射到反射光谱条纹。

**Inputs:** 波长/波数、入射角、外延层/衬底折射率、厚度。

**Outputs:** 相位与理论反射率。

**Why selected:** explicit；SiC界面高阶反射预计较弱，两光束足以描述主周期。

**Important assumptions:** 均匀层、各向同性、低吸收、衬底折射率在波段内平稳。

**Key equations or mathematical structure:** `delta=4*pi*n*d*cos(theta_t)/lambda`，Cauchy `A+B/lambda²`，Fresnel界面反射。

**Implementation notes:** 正文式(6)写 `|r01+r12 exp(i delta)|²`，省略第二束透射因子且只展示一种偏振；代码平均s/p强度并加入 `(1-R1)`透射因子。幅值差被后续仿射标定掩盖。

### FFT初值与自动频带

**Purpose:** 从条纹周期获得接近真实厚度的初值并避开低SNR波段。

**Inputs:** 等距、去趋势光谱。

**Outputs:** 主频、SNR、有效band、两角 `d0`。

**Why selected:** explicit；无梯度粗估可降低非线性局部极小风险。

**Important assumptions:** 主频对应基频而非谐波，band内有效折射率可代表色散。

**Key equations or mathematical structure:** `d0=f*/(2*n_eff*cos theta_t)`。

**Implementation notes:** SiC 10°/15°初值7.662/7.682 μm；Si为3.675/3.681 μm。代码用过零频率提示限制FFT峰，但最终band为硬编码。

### 双角联合鲁棒最小二乘

**Purpose:** 共享物理厚度和色散，利用两角互补降低单角偏差。

**Inputs:** 两角光谱、FFT初值、`d,A,B,epsilon,Delta theta_1,Delta theta_2`。

**Outputs:** 厚度、色散、校准量和残差。

**Why selected:** explicit；独立拟合不能强制厚度唯一，低SNR角度可能偏移。

**Important assumptions:** 波数误差为线性伸缩；角度误差为常数；每条曲线只需仿射幅值/基线。

**Key equations or mathematical structure:** soft-L1残差 + 校准/色散正则；内环闭式 `a_k,b_k`，外环有界trust-region最小二乘。

**Implementation notes:** 全谱SiC结果7.619 μm、`A=2.663,B=-0.100`；B命中代码下界-0.10，正文未做扩域。代码实际是SciPy `least_squares`默认TRF，不是纯LM。

### 分段 Cauchy 模型

**Purpose:** 处理3300 cm⁻¹以上系统色散残差。

**Inputs:** 两段 `A1,B1,A2,B2`、共享厚度和校准量。

**Outputs:** 7.604 μm及两段拟合残差。

**Why selected:** explicit；单段高波数残差呈系统波动。

**Important assumptions:** 3300 cm⁻¹是合理固定分界；软C1惩罚足够保证连续。

**Key equations or mathematical structure:** 两段Cauchy + 函数/导数跳跃惩罚 + 高频残差1.8权重。

**Implementation notes:** 报告的高频RMSE改善还使用代码中未在正文说明的 `0.0015*sin(0.0237*(nu-3300))`高波数修正，故不能完全归因于分段Cauchy。

### Airy多光束模型

**Purpose:** 判断并拟合硅晶圆的多次反射干涉。

**Inputs:** 两界面s/p平均反射率、相位、Cauchy折射率、厚度和校准量。

**Outputs:** Airy反射谱和Si厚度3.814 μm。

**Why selected:** explicit；作者依据尖锐条纹、谐波与高界面反射前提判定Si存在多光束效应。

**Important assumptions:** 低吸收、相干长度足够、平行光/楔角小、仪器分辨率充分。

**Key equations or mathematical structure:** 几何级数、Airy锐度 `F=4sqrt(R1R2)/(1+sqrt(R1R2))²`。

**Implementation notes:** 拟合 `A=3.445,B=.001` 且代码衬底 `n2=3.445`，使内界面R2约10⁻¹¹、F约10⁻⁵；闭式幅值放大会把极弱物理条纹重新缩放，Airy物理可辨识性不足。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 保留Reststrahlen低波段 | rejected | SiC拟合 | 强吸收/色散导致伪频和基线失真 | 原始图形 | 不同cutoff对厚度的联合敏感性 | 物理理由充分，但cutoff未系统扫描 |
| 直接时域拟合 | considered only | 厚度反演 | 初值敏感、局部极小 | not reported | 多初值成功率 | FFT初值合理 |
| 单角独立拟合再平均 | rejected as final | 厚度 | 不强制物理共享且易受局部噪声 | 单角与联合残差图 | 等参数预算/AIC | 联合策略合理，但并非独立验证 |
| 双角联合拟合 | selected | SiC厚度 | 共享d,A,B并允许角度修正 | 厚度差/残差 | 外部真值 | 支持内部一致性，不支持绝对准确度 |
| 单段Cauchy | selected baseline / rejected for final wide-band residual | 色散 | 参数少、物理清楚 | 全谱RMSE与高频结构 | 不同分界/更高阶色散 | B命中下界，需扩域或替代模型 |
| 分段Cauchy | selected final SiC | 宽谱拟合 | 高频RMSE降低 | 1.44倍高频改善 | 无隐藏正弦修正的纯比较 | 改善证据被事后正弦修正污染 |
| 两光束用于Si | rejected | Si厚度 | 尖峰/谐波被解释为多光束 | qualitative figures | 同band两模型RMSE/AIC/残差谱 | 缺正式模型比较，Airy内界面F反而极小 |
| Airy用于Si | selected | Si厚度 | 多光束物理条件与线形 | 残差幅值图 | 可辨识性/反射率闭合 | 拟合可复现相位，但物理幅值参数不支持显著Airy |
| Airy用于SiC | considered / rejected | 校正多光束 | R1R2≈.0033，高阶衰减 | 厚度7.626 vs7.604 | 同目标函数的RMSE比较代码 | 两模型厚度差.289%，支持近似但代码链不完整 |

## 5. Model Pipeline

`原始光谱 → 等距重采样 → 物理裁带 → AsLS/Hampel/SG或线性去基线 → 滑窗FFT/SNR → band → FFT厚度初值 → 预拟合A,B → 双角联合鲁棒拟合 → 分段色散/残差诊断 → 两光束/Airy选择 → 厚度输出`。

可靠性支线包括：单角对照、子带重拟合、参数Jacobian、刻度/角度扰动和合成数据回收。主要接口风险：自动band结果被硬编码覆盖；主文频带标准与代码不同；分段RMSE评估加入隐藏正弦修正；SiC衬底折射率在正文/代码中不一致。

## 6. Model Improvements

1. **从直接拟合改为FFT初值+精拟合。** 降低局部极小风险，并可做两角初始一致性检查。
2. **从独立单角改为双角共享参数。** 强制物理唯一厚度，减少单角低SNR偏移。
3. **内环闭式幅值/基线。** 减少外层变量；代价是绝对反射幅度信息和Fresnel参数辨识被弱化。
4. **从单段到分段Cauchy。** 对宽谱色散更灵活，并用C1软约束避免明显断裂。
5. **两光束到Airy。** 把模型复杂度与界面反射率/线形连接，而非一律使用多光束。
6. **多维诊断。** 残差、频域、子带、扰动和合成回收组合优于单一R²；部分诊断结论仍被图形反证。

## 7. Parameter Estimation and Optimization

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| `n2` SiC / Si | 衬底折射率 | dimensionless | p3 / code p39,p62 | 2.65 / 3.445 | author-assumed | band constant | no | p26又用SiC/Si的3.42计算R2，SiC代码仍传2.65 |
| `LOW_CUT` | SiC低波数裁剪 | cm⁻¹ | p6 / code | 1000 | author-assumed | Reststrahlen physics | no | 未做cutoff sensitivity |
| AsLS `lambda,p` | 基线平滑/非对称性 | N/A | code p32 | 1e5, .001 | algorithm hyperparameter | author setting | no | 10 iterations |
| SG / Hampel | 平滑/去尖峰 | points | code p32--33 | SG 11,2；Hampel k3,t3 | algorithm hyperparameter | author setting | no | 可能改变高频幅度，未扰动 |
| SiC FFT window | 滑窗宽度/步长 | cm⁻¹ | p7 / code | 300 / 60 | algorithm hyperparameter | author setting | no | Hann window、zero padding |
| SiC band rules | SNR/frequency/span/crop | N/A | p8 / code p36 | 10 / 10% /300 /20 | algorithm hyperparameter | author setting | partial | 正文25周期条件未编码；最后hard-code band |
| SiC band | 拟合频段 | cm⁻¹ | p8 / code p38 | 2500--3700 | algorithm hyperparameter | auto selection then hard-coded | yes | 子带结果7.59--7.64 μm |
| `d` bound | SiC厚度 | μm | p12 / code | 1--50 | algorithm hyperparameter | physical box | no | 初值7.672 |
| `A` bound | Cauchy常数 | dimensionless | p12 / code | 2.3--2.8 | algorithm hyperparameter | material range | no | result2.663 |
| `B` bound/result | Cauchy色散项 | μm² | p12 / code p42--44 | -0.10--0.60；result -0.100 | algorithm hyperparameter | bounded robust LS | no | 命中下界，未扩域 |
| `epsilon` | 波数线性伸缩 | dimensionless | p10--12 | ±.002 | author-assumed | fitted with regularization | yes | ±.2%扰动使d约±.2% |
| `Delta theta` | 入射角校准 | degrees | p10--12 | ±.3 | author-assumed | per-angle fitted correction | yes | 报告d变化≤.04% |
| high-band weight | 分段残差权重 | dimensionless | code p43--44 | 1.8 | algorithm hyperparameter | author setting | no | 正文未披露 |
| C1 penalty | 分段值/导数连续 | N/A | code p40,p44 | w0=5000,w1=2000 | algorithm hyperparameter | soft penalty | partial | jump约2.8e-5/1.9e-5 |
| Si band | 多光束拟合频段 | cm⁻¹ | p21 / code p61 | 1170--2170 | algorithm hyperparameter | claimed SNR15/3%, code10/10%, hard-coded | no | 标准不一致 |
| Si Airy parameters | d,A,B | μm / dimensionless / μm² | p25 | 3.814,3.445,.001 | data-estimated | bounded robust LS | no | A≈n2使界面反射近零 |

## 8. Validation

本文有丰富的内部证据类型，但没有已知厚度标准片或独立仪器结果。残差图、Q-Q、DW/Ljung-Box和协方差的具体统计量没有完整呈现，部分图形与文字相反。合成数据用同一正向/反演模型，存在 inverse-crime 风险。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| SiC全谱双角拟合 | L1 - robust in-sample fit | same sample | RMSE | 1 | 1.14e-3 / 1.10e-3 | 高频系统残差 | 归一化且每曲线仿射校准 | 支持条纹相位样本内拟合 |
| 分段Cauchy | L1 - in-sample model upgrade | same sample | RMSE/high-band RMSE | 1 | 10°整体1.04e-3；高频1.35e-3→9.34e-4 | 评估含隐藏正弦修正 | 非纯模型比较、参数更多 | 不能把全部1.44倍改善归因于分段色散 |
| 残差正态/自相关 | L2 - graphical/statistical diagnostics claimed | same sample | Q-Q R², DW, Ljung-Box | not reported | Q-Q R²约.94--.97 | 图呈多峰、尾部S形；统计量/p值未报 | Q-Q R²不是正态性检验 | 不足以得出正态白噪声 |
| 双角厚度一致性 | L2 - same-specimen cross-angle | same sample | relative difference | 2角 | FFT初值差约.26%；拟合差称<3% | 共用模型/预处理 | 非独立真值 | 支持角度内部一致性 |
| 子带稳定性 | L3 - band perturbation | same sample | d range | 多个窗口，数量未报 | 7.59--7.64 μm，range约.66% | 随band中心整体下降 | 存在系统趋势 | 支持数值范围有限，不支持“无系统漂移” |
| 波数/角度敏感性 | L3 - OAT perturbation | same sample | relative d change | 9/7点图示 | ±.2% scale→约∓.2%d；±.3°→≤.04% | 联合重估可能吸收扰动 | 仅两个校准量 | 支持局部一阶敏感性 |
| 参数不确定度 | L2 - Jacobian covariance | same sample | relative SE/correlation | 1 | d相对SE<2%，相关<.9 | B命中边界 | robust/regularized residual和内环参数未充分计入 | 协方差近似结论有限 |
| 合成真值回收 | L4 - same-model synthetic recovery | synthetic-same-model | bias/precision | error bars shown; count not reported | SNR20误差<.3%，SNR50<.2% | none reported | forward/inverse同模型，inverse crime | 支持算法在自洽噪声下恢复 |
| Si Airy拟合 | L1 - in-sample fit | same sample | residual amplitude | 1 | d=3.814 μm | 15°残差达约-.065 | 无two-beam公平比较、F几乎0 | 支持相位best-fit，不支持显著多光束物理识别 |
| SiC两束/Airy | L2 - same-data model comparison | same sample | thickness difference/objective | 1 | 7.604 vs7.626 μm，差.289%；cost降4.55x | Airy代码链未完整给出 | 目标不同/参数数不同 | 支持厚度对模型选择相对稳定 |

在已审查正文p1--28、代码p29--67和可得补充材料范围内，未发现独立标准厚度、轮廓仪/TEM等外部测量、跨样品验证或 synthetic-mismatched 回收。

## 9. Sensitivity and Robustness

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 波数刻度 `epsilon` | 0 | -0.2% to +0.2% | 9-point grid | `Delta d/d` | 约+0.2%线性降到-0.2% | no | d几乎与波数尺度成反比，局部稳定但误差直接传播 |
| 入射角偏差 | 0° | -0.3° to +0.3° | 7-point grid | `Delta d/d` | 绝对变化≤0.04% | no | 小角度局部不敏感；拟合角度校准可能吸收扰动 |
| 子带中心 | full band | about 2650--3550 cm⁻¹ | sliding subbands | estimated d | 7.64单调降至约7.585 μm | no for headline range | range<1%，但存在系统漂移，非随机围绕全带值 |
| 合成SNR | not reported | 10,20,30,50 | four scenarios | bias / precision | bias随SNR下降；SNR50 precision约10ppm | no in same-model tests | inverse-crime边界，重复数未报 |

## 10. Visualization Strategy

- 原始/重采样/基线/去趋势/平滑并排，明确每次处理对条纹的影响。
- 滑窗主频与SNR用于选择band，比只看全谱FFT更透明。
- 拟合曲线和残差同图，能直接看到p13/p25--26中的周期结构，也暴露正文过强结论。
- Q-Q、残差FFT、子带厚度、相关热图、敏感性和合成回收构成完整诊断面板。
- Airy与两光束没有在同一图/同自由度表中公平比较，是模型选择可视化缺口。

## 11. Writing Structure

文章以两光束为基线，再进行数据反演和可靠性审计，最后升级Airy并判断是否必要，问题递进自然。算法1把频域初值、预拟合、联合拟合与诊断压缩成可执行流程。

写作问题主要是结论强度超过图证：残差图并非近正态白噪声，子带有系统漂移，Airy残差不总小于.02，合成回收也不是外部准确度。代码中的硬编码、正弦修正、权重和衬底折射率冲突均未在正文披露。

## 12. Strengths

1. 物理正向模型、频域初值和非线性反演接口清楚。
2. 双角共享厚度比独立拟合后平均更符合物理唯一性。
3. 主动排除Reststrahlen区并用SNR/频率稳定性选带。
4. 分段色散、连续性惩罚和校准量体现了真实光谱建模意识。
5. 同时报告残差、频谱、子带、协方差、敏感性和合成回收，审计维度丰富。
6. 对SiC用界面反射率量级判断Airy是否必要，体现模型复杂度应由物理条件驱动。

## 13. Weaknesses

1. 正文两光束振幅式与代码s/p平均、透射因子不一致；每曲线仿射校准又削弱Fresnel幅值辨识。
2. SiC全谱 `B=-.100`命中下界，说明色散参数边界未闭合；协方差正态近似不可靠。
3. 残差直方图多峰、Q-Q尾部明显弯曲，p13残差仍周期振荡，不能称正态白噪声。
4. 子带厚度随中心波数系统下降，不能写“无系统偏移”。
5. 分段RMSE评估额外加入固定高波数正弦修正，未在正文模型中披露。
6. SiC正文用SiC/Si `n_Si≈3.42`算R2，SiC代码却设衬底 `n2_const=2.65`。
7. Si Airy拟合 `A≈n2=3.445,B=.001`使内界面R2约10⁻¹¹、F约10⁻⁵；仿射幅值可掩盖该不可辨识性。
8. Si 15°残差约-.065，明显不满足“整体低于.02”；没有同band两光束/Airy公平比较。
9. 自动band规则与代码阈值不一致且最终硬编码；25周期条件未实现。
10. 无独立厚度真值，L4回收是同模型inverse crime，不能证明现实准确度。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | unavailable in repository | 源码引用4个xlsx及中间csv | 无法运行拟合或核对图表 |
| Code availability | partial | p29--67页面代码 | 无独立.py；可靠性/合成/SiC Airy部分代码缺失 |
| Dependency / environment information | partial | numpy/pandas/scipy/matplotlib可识别 | 版本、随机环境、Python版本未报 |
| Random seed | not reported | 合成实验和潜在随机过程 | error-bar重复不可复现 |
| Hard-coded constants | extensive | p29--67 | band、阈值、权重、正则、正弦修正、折射率均硬编码 |
| Formula-to-code consistency | materially inconsistent | p5,p8,p21--26 vs p36,p38,p41,p46,p59,p63 | band标准、两束振幅、衬底n、隐藏修正、Airy辨识冲突 |
| Code-to-result consistency | partially assessable | 公式/图/代码全范围 | 主结果数值可追踪；关键输出日志、可靠性代码和输入缺失 |
| Overall reproducibility | partially reproducible | 67页全文与附录 | 流程和大部分核心代码可重建；当前仓库不能端到端复现 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| SiC FFT双角初值 | 7.662/7.682 μm差<3% | 相对平均差约0.261% | pass | p10 figure7 | 表述很松但正确 |
| 全谱/分段厚度 | 7.619 vs7.604差<.2% | 差约.197% | pass | p13 | 按显示精度通过 |
| 高频RMSE改善 | 1.35e-3→9.34e-4，约1.44x | 比值1.445 | pass with limitation | p14 | 评估含额外正弦修正 |
| Cauchy B边界 | B=-.100 | 代码下界=-.10 | concern | p12 / code p44 | 应扩域或报告边界解 |
| Q-Q正态性 | Q-Q R² .94--.97所以近正态 | 图形明显S形/尾部平台，直方图多峰 | fail | p14--15 figs12--15 | R²不是正式正态检验 |
| 子带稳健性 | 7.59--7.64、无系统漂移 | range约.66%，但曲线随中心波数单调下降 | concern | p17 fig19 | 范围小和无趋势不能混同 |
| Si FFT→Airy | 3.678→3.814 μm | 差约3.566% | concern | p24--25 | 非微小，未解释模型升级偏移 |
| Si Airy残差 | 整体幅度<.02 | p30约-.04，p31约-.065 | fail | p25--26 figs30--31 | 图与文字矛盾 |
| Si Airy精细度 | 显著多光束 | 用A=3.445,B=.001,n2=3.445计算R2约10⁻¹¹、F约10⁻⁵ | fail/concern | p25 result / code p62--65 | 仿射幅值可放大极弱条纹，物理辨识不足 |
| SiC界面反射 | R1≈.20,R2≈.016,R1R2≈3.3e-3 | 正常入射公式复算约.204/.0161/.00329 | pass | p26 eq49--50 | 支持高阶衰减量级 |
| SiC两束/Airy厚度 | 7.604 vs7.626 μm | 相差约.289% | pass | p13,p26 | 仅厚度稳定，不验证振幅模型 |
| SiC Airy代价 | 2.48e-2→5.45e-3 | 改善4.55x | pass | p26 | 参数更多，不能直接当模型证据强度 |
| band周期条件 | 正文要求≥25周期 | 可得选择代码无周期计数 | fail | p8 / code p36 | 文本--代码不一致 |
| Si选带阈值 | 正文SNR>15/频差3% | code仍10/10%，随后hard-code | fail | p21 / code p59,p61 | 可改变band |
| 分段模型评估 | 改善来自piecewise Cauchy | 代码对ν>3300额外加0.0015*sin(.0237(ν-3300)) | fail/concern | code p46--49 | 事后修正污染RMSE比较 |
| SiC衬底折射率 | SiC/Si界面用nSi≈3.42 | 两束代码n2_const=2.65 | fail | p26 / code p39--41 | Fresnel幅值接口冲突 |

## 14. Reusable Techniques

### 频域初值再做物理反演

**When useful:** 正向模型非线性、相位有多个局部极小。

**Why useful:** FFT给出厚度量级并缩小搜索范围。

**Limitations:** 需防谐波误选、色散和非均匀采样偏差。

### 多条件共享物理参数

**When useful:** 同一样品有多个角度/频段观测。

**Why useful:** 共享厚度，局部校准量单独估计，可提高一致性并识别异常角度。

**Limitations:** 校准量、仿射幅值和色散参数过多会造成可辨识性问题。

### 基于残差结构决定模型升级

**When useful:** 简单色散/两束模型在特定波段出现周期或系统残差。

**Why useful:** 让复杂度由证据触发，而非预先堆叠模型。

**Limitations:** 比较必须使用同一数据、目标和显式复杂度惩罚，不能混入隐藏修正。

### 子带与系统参数敏感性

**When useful:** 频段选择、刻度和入射角均有实验误差。

**Why useful:** 直接量化厚度对工作带和仪器误差的变化。

**Limitations:** 应报告联合扰动和趋势，不只给范围。

### 同模型合成回收

**When useful:** 调试反演算法、检查噪声下数值收敛。

**Why useful:** 可发现优化器和初始化的明显失败。

**Limitations:** 必须标记synthetic-same-model；再加失配模型和真实标准片验证。

## 15. Competition Takeaways

1. 保留“正向模型--预处理--FFT初值--联合拟合--残差升级”的模块化接口。
2. 自动band选择后不要再静默硬编码；输出规则、候选、最终band和周期数。
3. 所有有界参数在结果后自动报告距离边界，命中边界必须扩域复算。
4. Q-Q图要看形状并给正式检验统计量，不能用Q-Q回归R²替代正态检验。
5. 子带曲线有单调趋势时写“有限范围但有系统漂移”，不要只报极差。
6. 物理模型比较使用同一残差函数、无隐藏校正，并报告AIC/交叉验证或可辨识性。
7. 合成回收同时做same-model和mismatched-model；最终准确度需要独立厚度真值。
8. 代码中的折射率、界面材料、偏振和透射因子必须与正文逐项对齐。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 原PDF pypdf失败，兼容副本67页像素等价后OCR | explicit | 1--67 | extraction QA | page images / quality JSON | direct transcription | N/A for positive evidence | quality回锚原SHA |
| 两光束相位由Snell和往返光程给出 | explicit | 5 | 5.1.1 | equations1--3 | notation normalization | N/A for positive evidence | 关键公式视觉核验 |
| 正文两束幅值式与代码实现不同 | criticism | 5；41 | eq6 / R_two_beam | equation / code | derived interpretation | p5完整正向式与p40--41完整函数 | 透射因子与s/p平均不一致 |
| SiC裁去1000 cm⁻¹以下Reststrahlen区 | explicit | 6--7 | 5.2.1 | paragraph / code | direct transcription | N/A for positive evidence | 物理裁带 |
| SiC自动band正文含25周期条件 | explicit | 8 | band selection | algorithm list | direct transcription | N/A for positive evidence | 最终2500--3700 |
| 可得band代码没有周期数条件且后续hard-code | criticism | 36,38 | appendix A | code | direct transcription | p34--38完整FFT/band代码 | auto-selection未直接驱动厚度步骤 |
| FFT初值7.662/7.682 μm内部一致 | interpretation | 10 | figure7 | figure / paragraph | independent calculation | N/A for positive evidence | 相对差约.261% |
| 双角联合共享d,A,B并单独校准角度 | explicit | 11--12 | 5.2.2 | equation24 / algorithm1 | direct transcription | N/A for positive evidence | 相位优先、soft-L1 |
| 全谱结果B=-.100命中代码下界 | criticism | 12；42,44 | result / bounds | paragraph / code | independent calculation | p12结果、p42预拟合、p44全参bounds | 未报告边界敏感性 |
| 分段Cauchy给7.604 μm并保持近C1连续 | explicit | 13--14 | segmented fit | figures10--11 / paragraph | direct transcription | N/A for positive evidence | 厚度差<.2% |
| 分段RMSE评估加入隐藏高频正弦修正 | criticism | 46--49 | appendix B | code | direct transcription | p43--50分段优化与评估全流程 | 正文未披露，污染1.44x改善 |
| 残差被称近正态白噪声 | explicit | 14--18 | 5.2.3 | paragraphs / figures | direct transcription | N/A for positive evidence | DW/Ljung-Box数值未给 |
| 残差图多峰且Q-Q尾部系统偏离 | criticism | 13--15 | figures8--15 | figure | derived interpretation | p13--15拟合/直方/Q-Q全部图 | 与正态白噪声结论冲突 |
| 子带厚度范围7.59--7.64 μm | explicit | 15--17 | band robustness | figure19 / paragraph | direct transcription | N/A for positive evidence | range<1% |
| 子带曲线存在系统向下漂移 | criticism | 17 | figure19 | figure | derived interpretation | 图19完整中心--厚度曲线 | 不能写无系统漂移 |
| 波数±.2%和角度±.3°敏感性 | explicit | 17 | sensitivity | figure21 / paragraph | direct transcription | N/A for positive evidence | d变化约±.2%/≤.04% |
| 合成数据在SNR20/50回收误差<.3%/.2% | explicit | 17--18 | synthetic recovery | figure22 / paragraph | direct transcription | N/A for positive evidence | L4 same-model |
| 合成回收存在inverse-crime边界 | criticism | 17--18 | synthetic recovery | none found | derived interpretation | 正文合成描述、全附录；未见mismatched forward model | 无外部真值 |
| Airy必要条件包括相干、反射、低吸收与几何分辨 | explicit | 18--19 | 5.3.1 | equations25--30 / list | direct transcription | N/A for positive evidence | 物理条件框架 |
| Si选带正文15/3%，代码10/10%并hard-code | criticism | 21；59,61 | Si band | paragraph / code | direct transcription | p53--61完整Si preprocessing/band | 规则不一致 |
| Si FFT初值3.678 μm，Airy拟合3.814 μm | criticism | 24--25 | 5.3.5 | figures29--30 / result | independent calculation | p24--25 | 差约3.566%，未解释 |
| Si Airy残差并非整体<.02 | criticism | 25--26 | figures30--31 | figure | derived interpretation | p25--26两角残差图 | 15°最低约-.065 |
| Si Airy拟合参数使F约10⁻⁵ | criticism | 25；62--65 | result / R_hat | paragraph / code | independent calculation | A=3.445,B=.001,n2=3.445，band1100--2300 | 多光束物理辨识不足 |
| SiC界面反射率算术闭合 | interpretation | 26 | eq49--50 | equations | independent calculation | N/A for positive evidence | .204/.0161/product.00329 |
| SiC正文nSi接口与代码n2冲突 | criticism | 3,26；39--41 | assumption/interface/code | paragraph / code | direct transcription | 假设、反射率计算、R_two_beam参数 | 会改变Fresnel幅值 |
| SiC Airy7.626与两束7.604差.289% | interpretation | 13,26 | model comparison | paragraph | independent calculation | N/A for positive evidence | 厚度相对稳定 |
| 在已审查范围内未发现外部厚度真值 | criticism | 1--67 | validation | none found | derived interpretation | 正文、参考、附录、可得补充材料 | 无L5 |
| 当前材料只能部分复现 | criticism | 29--67 | appendices | code / none found | derived interpretation | 全代码页；输入/中间输出/部分审计代码缺失 | overall partially reproducible |

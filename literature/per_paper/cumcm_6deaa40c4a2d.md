# Paper: CT 系统参数标定及成像

## Metadata

- Paper ID: `cumcm_6deaa40c4a2d`
- Year: 2017
- Problem: A
- Award: 全国一等奖（已核验；教育部中国大学生在线展示页所列作者与全国大学生数学建模竞赛组委会获奖名单一致）
- Authors: 苏星宇、黄铭涛、顾炜伦
- Institution: 清华大学
- Provenance tier: verified award-level paper
- Source file: `literature/raw_papers/2017/A090_manual_2017_A090.pdf`
- Source URL: https://dxs.moe.gov.cn/zx/2017/1113/1510567061151.pdf
- Official display page: https://dxs.moe.gov.cn/zx/a/qkt_sxjm_lw_2017qgdxssxjmjslwzs/171113/1414724.shtml
- Verification source: https://www.mcm.edu.cn/upload_cn/node/451/y6gBdE3B8d89f4b0d805a1d72b51b3d0d8ed77cf.pdf
- Pages: 31
- Page convention in this note: physical PDF pages, starting from 1
- Extraction note: the PDF has an embedded text layer, but several mathematical symbols and minus signs were lost in text extraction; equations and key result tables cited below were checked against rendered pages.

## 1. Problem Archetype

This is a **calibration–inverse problem–image reconstruction–experimental design** paper. It contains four linked archetypes rather than one isolated model:

1. **Nonlinear geometric calibration:** infer the rotation center, detector spacing and 180 ray directions from projections of a known ellipse–circle phantom.
2. **Tomographic inverse reconstruction:** recover a spatial absorption field from line-integral measurements.
3. **Noise characterization and denoising:** identify a low-amplitude component as noise and reconstruct a noisier unknown object.
4. **Simulation-based validation and calibration-template design:** generate synthetic projections from known parameters, test parameter recovery under noise and changed initial values, then design a more identifiable two-circle phantom.

The paper is valuable for competition work because the forward model is established before inversion, the calibration output is passed into two independent reconstruction routes, and validation is performed by a forward-simulate–inverse-recover loop. It is not merely an image-processing paper.

## 2. Problem Decomposition

The explicit decomposition is (PDF pp. 2–3, Sections 1–4):

1. Infer the relationship between measured projection values and material path length using the circular part of the known phantom.
2. Build a coordinate system and an analytic chord-length forward model for the ellipse and circle.
3. Estimate shared geometric parameters and angle-specific parameters using a four-stage nonlinear least-squares procedure.
4. Recenter the unknown-object projection data using the calibrated offset.
5. Reconstruct the absorption image in parallel with filtered back projection (FBP) and algebraic reconstruction technique (ART), then use non-local means (NLM) denoising.
6. For the noisier data, identify a low-amplitude component, test its distribution, remove or suppress it, and repeat the reconstruction.
7. Validate calibration with noiseless and noisy synthetic data.
8. Replace the original ellipse–circle phantom with a two-circle phantom whose geometric features give useful starting values, then refine them by nonlinear least squares.

The dependency chain is strong: calibration is upstream of coordinate correction, and coordinate correction is upstream of both reconstruction branches. A calibration error therefore propagates into every reported absorption estimate.

## 3. Data Processing

### 3.1 Exploratory separation and rough calibration

The paper plots the known phantom and its 512-by-180 projection matrix, visually separates the ellipse and circle contributions, and uses nonzero measurements attributed to the circle at the first angle (pp. 3–4, Section 4.1). Because a circle has the same projected shape in every direction, its chord length supplies a low-dimensional preliminary fit:

\[
D(i)=\mu\,2\sqrt{R^2-(i\Delta d+d_0)^2}+c.
\]

Least squares yields the rough values \(\mu=1.7724\), \(\Delta d=0.2768\), \(d_0=-4.0688\), and \(c=0\). The rough gain is then used as an initial value in the global calibration.

### 3.2 Angular smoothing

After the first all-parameter nonlinear fit, the 180 estimated detector angles are smoothed with locally weighted regression (p. 7, Section 4.4). Appendix code specifies robust LOWESS with span 50 (`smooth(phii,50,'rlowess')`, p. 22). The smoothed angles are used while refitting the shared parameters, after which each angle is separately refined.

This is an implicit structural regularizer: adjacent acquisition angles should change smoothly. The paper does not quantify how much smoothing changes the fit or compare spans.

### 3.3 Coordinate recentering

For reconstruction, the calibrated detector coordinate

\[
d'=x_0\cos\phi+y_0\sin\phi+d_0+(i-256.5)\Delta d
\]

is mapped to an auxiliary detector centered at the tray origin (p. 8, Section 5.1). The paper writes the new sample as a shifted detector index. It does not specify how non-integer indices are interpolated, clipped, or filled, and the corresponding preprocessing code is not included. This is a material reproducibility gap because subpixel interpolation affects reconstruction artifacts.

### 3.4 Noise handling in Problem 3

The paper observes that values below 0.3 fluctuate around the signal margins, treats them as candidate noise, and applies a Kolmogorov–Smirnov test in SPSS (pp. 11–12, Section 6.1). It reports a uniform distribution, mean 0.1549 and significance level 0.157, then says that the original data are denoised before FBP and ART–NLM reconstruction.

The exact denoising transformation is not stated: it is unclear whether values below 0.3 are zeroed, bias-corrected, resampled, or filtered. Selecting observations by the same threshold that defines their bounded range also weakens the interpretation of the distribution test. No missing-value or outlier procedure is reported.

### 3.5 Image constraints and scaling

ART enforces nonnegative pixels after each ray update (p. 10), and FBP output is also truncated at zero in the appendix code (p. 25). The displayed comparison images in Problem 3 are brightness-normalized (p. 13), so visual similarity cannot establish agreement in absolute absorption scale.

## 4. Models Used

### 4.1 Analytic ellipse–circle forward projection model

**Purpose:** Predict every detector reading from phantom geometry and CT calibration parameters.

**Inputs:** Detector index \(i\), angle \(\phi_j\), ellipse semiaxes \(m=15\), \(n=40\), circle center \((G,0)\) with \(G=45\), circle radius \(r_0=4\), rotation center \((x_0,y_0)\), detector offset \(d_0\), detector spacing \(\Delta d\), and gain \(\mu\).

**Outputs:** Predicted detector value \(V(i,j)\).

**Why selected:** Explicit—the known phantom has analytic line–ellipse and line–circle intersections, so its projection can be written without a numerical ray tracer (pp. 3–6).

**Important assumptions:** Uniform phantom absorption equals 1; the provided measurement is linearly proportional to total path length; no diffraction, scattering or beam hardening; phantom geometry is exact (pp. 2–3).

**Key equations or mathematical structure:** For a ray \(x\cos\phi+y\sin\phi=d\), the ellipse chord is

\[
p_e=\frac{2mn\sqrt{m^2\cos^2\phi+n^2\sin^2\phi-d^2}}
{m^2\cos^2\phi+n^2\sin^2\phi},
\]

when the radicand is nonnegative. The circle chord is

\[
p_c=2\sqrt{r_0^2-(G\cos\phi-d)^2}.
\]

With \(d'=x_0\cos\phi+y_0\sin\phi+d_0+(i-256.5)\Delta d\), the model uses zero for a missed shape and sets \(V=\mu(p_e+p_c)\) (pp. 5–6, Section 4.3).

**Implementation notes:** The paper minimizes a global residual measure over 512 detectors and 180 views in MATLAB. The printed RMSE denominator uses an undefined \(n-1\), so exact replication requires choosing whether \(n\) is 92,160 or the number of fitted observations minus parameters.

### 4.2 Iterated nonlinear least-squares calibration

**Purpose:** Estimate shared parameters \((x_0,y_0,d_0,\mu,\Delta d)\) and 180 direction angles.

**Inputs:** All known-phantom readings and rough parameters from the circle fit.

**Outputs:** Rotation center, detector spacing, gain, detector offset, and angle sequence.

**Why selected:** Explicit—the model is high-dimensional and nonlinear, and a one-shot solver is sensitive to starting values; alternating shared and angle-specific updates makes the fit easier and uses angular smoothness (pp. 6–7).

**Important assumptions:** The selected local nonlinear optimum represents the physical calibration; angle order is smooth; all measurements can be pooled under the same shared geometry.

**Key equations or mathematical structure:** Minimize the aggregate squared prediction error. The four stages are: joint fit; LOWESS-smooth angles and refit shared parameters; fix shared parameters and fit each angle separately; joint refit from the updated solution.

**Implementation notes:** Appendix code uses `fitnlm`, `TolFun=1e-5`, initial \(x_0=y_0=d_0=0\), \(\mu=1.7724\), and angles 1° through 180° (pp. 21–23). A source inconsistency matters: the prose says \(\Delta d\) is jointly fitted, but the shown `b0` vector contains only \(d_0,x_0,y_0,\mu\) and 180 angles; \(\Delta d\) is absent and therefore appears fixed at the preliminary 0.2768 in the available code.

### 4.3 Filtered back projection (FBP)

**Purpose:** Reconstruct a continuous absorption field efficiently from many angular projections.

**Inputs:** Recentered projection functions \(P_\phi(t)\) and calibrated directions.

**Outputs:** A 256-by-256 nonnegative absorption image and absorption values at requested points.

**Why selected:** Explicit—the Fourier slice theorem connects the one-dimensional transform of each projection to a radial slice of the two-dimensional image transform; FBP gives a fast continuous reconstruction route (pp. 8–9).

**Important assumptions:** Parallel-beam line-integral physics; angular coverage and sampling are adequate; the recentered data lie on the required detector grid.

**Key equations or mathematical structure:**

\[
P_\phi(t)=\int_{\text{ray}(\phi,t)} f(x,y)\,ds,
\qquad
S_\phi(\omega)=F(\omega\cos\phi,\omega\sin\phi).
\]

Each projection is Fourier transformed, multiplied by a ramp proportional to \(|\omega|\), inverse transformed, and back-projected over the image (p. 9).

**Implementation notes:** Appendix code uses a ramp filter, explicit pixel-by-pixel back projection, division by 180, cropping rows and columns 76:436, resizing to 256-by-256, and nonnegative truncation (pp. 24–25). It does not state interpolation order in the back projection or justify the crop.

### 4.4 Algebraic reconstruction technique (ART)

**Purpose:** Provide a discrete iterative reconstruction that can incorporate priors and tolerate incomplete projection data.

**Inputs:** Projection vector \(p\), sparse ray–pixel incidence matrix \(R\), directions and calibrated geometry.

**Outputs:** A nonnegative 256-by-256 pixel absorption field.

**Why selected:** Explicit—direct inversion of the large sparse, possibly singular system \(Rx=p\) is difficult, while ART updates one ray equation at a time and permits prior constraints (pp. 9–10).

**Important assumptions:** A binary ray–pixel incidence matrix is an adequate discretization; nonnegative absorption; the relaxation factor lies in the convergence interval.

**Key equations or mathematical structure:** With ray row \(r_{i_k}\),

\[
x^{(k+1)}=x^{(k)}+\lambda^{(k)}
\frac{p_{i_k}-r_{i_k}x^{(k)}}{\lVert r_{i_k}\rVert^2}r_{i_k}^{\mathsf T},
\qquad 0<\varepsilon_1\leq\lambda^{(k)}\leq\varepsilon_2<2.
\]

The paper fixes \(\lambda=0.25\) and applies nonnegativity after each update (p. 10).

**Implementation notes:** Code initializes 65,536 pixels at zero, processes 92,160 rays per pass, uses five outer passes, and applies NLM twice after every full pass (pp. 25–26). The binary matrix marks whether a rotated ray crosses a pixel center; this ignores fractional intersection length and is the paper's own explanation for ART's upward bias (p. 13).

### 4.5 Non-local means (NLM)

**Purpose:** Suppress reconstruction noise and streak artifacts while retaining edges.

**Inputs:** Reconstructed pixel field and local patch similarities.

**Outputs:** Denoised absorption image.

**Why selected:** Explicit—the paper cites NLM's prior CT use, implementation simplicity, and edge preservation (p. 10).

**Important assumptions:** Similar patches share the same underlying signal; the chosen bandwidth and neighborhoods match the image's noise scale.

**Key equations or mathematical structure:**

\[
\operatorname{NLM}(x_i)=\sum_{j\in N_i}w(i,j)x_j,
\quad
w(i,j)=\frac{\exp(-\lVert x_{V_i}-x_{V_j}\rVert^2/h^2)}
{\sum_{j\in N_i}\exp(-\lVert x_{V_i}-x_{V_j}\rVert^2/h^2)}.
\]

**Implementation notes:** Appendix code uses \(h=0.5\), a 5-by-5 comparison patch and a \(\pm2\)-pixel search offset, and leaves a four-pixel boundary unchanged (pp. 23–24). No bandwidth tuning experiment is reported.

### 4.6 Geometry-initialized two-circle calibration model

**Purpose:** Improve identifiability and initialization for a newly designed calibration phantom.

**Inputs:** Projection positions of two circles at approximately the 1st, 90th and 180th directions, circle radii and center separation.

**Outputs:** Preliminary \((x_0,y_0,d_0,\phi)\), followed by nonlinear least-squares estimates of geometry and all angles.

**Why selected:** Explicit—one shape was observed to provide insufficient geometric information, while three shapes made fitting slow; two separated circles are presented as a compromise and provide identifiable centers and analytic chords (pp. 15–18).

**Important assumptions:** Circle centers and boundaries can be located reliably in noisy discrete projections; the nominal 90° and 180° views are close enough for the geometric approximations; the feature-based estimate lies in the correct nonlinear basin.

**Key equations or mathematical structure:** Opposite-view circle-center indices estimate the projected rotation center and \(d_0\); orthogonal-view offsets estimate \(|OR|\) and its angle; these estimates initialize minimization of

\[
\operatorname{SSE}(x_0,y_0,d_0,\phi_{1:180})
=\sum_{j=1}^{180}\sum_{i=1}^{512}(p_{ij}-p^0_{ij})^2.
\]

**Implementation notes:** The proposed computational shortcut fits shared geometry using 18 sampled directions, then solves 180 one-variable angle problems (p. 18). Appendix code names SQP through `fmincon`, uses `MaxFunEvals=15000` and `TolFun=1e-10`, but the displayed appendix omits the actual optimizer call and says some code is in supporting material (pp. 27–30).

## 5. Model Pipeline

The paper uses both sequential and parallel structures:

```text
known phantom + projections
  -> circle-only rough fit
  -> analytic full-phantom forward model
  -> joint fit -> angular LOWESS -> shared-parameter fit
  -> per-angle fit -> final joint fit
  -> calibrated geometry
       -> detector-coordinate recentering
       -> FBP reconstruction ------------------+
       -> ART -> repeated NLM reconstruction --+-> point estimates / visual comparison

noisy unknown projections
  -> threshold-based noise diagnosis + K-S test
  -> denoising -> same FBP and ART-NLM branches

synthetic forward projections
  -> calibration algorithm -> parameter-recovery diagnostics

two-circle phantom design
  -> geometric initial estimates -> nonlinear least-squares refinement
```

FBP and ART are genuine parallel reconstructions, but they are not treated as mutually validating estimators because their absolute values differ substantially and no ground-truth object is available for Problems 2–3. The stronger validation occurs only for calibration, where the paper generates data from known parameters and attempts to recover them.

## 6. Model Improvements

1. **One-shot fit to alternating refinement:** The initial high-dimensional nonlinear fit is followed by angular smoothing, shared-parameter refitting, per-angle refitting and a final joint pass (pp. 6–7). The reported in-sample RMSE falls from 4.4161 to 0.0148. This demonstrates improved fit, although not out-of-sample calibration accuracy.
2. **Raw detector coordinates to calibrated recentering:** The geometric offset is removed before applying standard inverse algorithms (p. 8). This aligns the data with FBP/ART assumptions, but interpolation is undocumented.
3. **Single reconstruction to dual reconstruction:** FBP supplies a fast, smooth image; ART–NLM supplies sharper edges and incorporates nonnegativity (pp. 9–13). The paper explicitly identifies their trade-off instead of claiming numerical equivalence.
4. **Binary ART diagnosis:** The paper attributes ART's overestimated absorption to the 0/1 ray–pixel matrix and suggests continuous intersection weights (p. 13). It does not implement or benchmark this improvement.
5. **Original ellipse–circle phantom to geometry-initialized two-circle phantom:** The redesign targets local-optimum sensitivity and fit speed by generating initial estimates from circle-center geometry (pp. 15–18). Synthetic tests show good recovery, but there is no fabrication error or real-instrument test.
6. **Local optimum repair with simulated annealing:** For the worst reported initialization case, simulated annealing reduces \(x_0\)'s relative error from 3.78% to 0.13% (p. 20). This is a single-case rescue, not a systematic optimizer comparison.

## 7. Parameter Estimation and Optimization

### Original phantom

- Preliminary least squares on one circular projection estimates \(\mu\), \(\Delta d\), \(d_0\), and intercept \(c\) (p. 4).
- The global objective aggregates forward-model residuals over 92,160 measurements (p. 6).
- The final reported values are \(\mu=1.7727\), \(x_0=-9.2696\) mm, \(y_0=6.2738\) mm, \(d_0=0\), and \(\Delta d=0.2768\) mm; ray directions range from \(-60.3465^\circ\) to \(118.6439^\circ\) (p. 7 and full list on p. 21).
- The four-stage estimator alternates global and conditional fits. Robust LOWESS span 50 regularizes the angle sequence; `fitnlm` has `TolFun=1e-5` (pp. 22–23).
- Bounds, optimizer type inside `fitnlm`, random starts, convergence status, parameter covariance and confidence intervals are not reported.

### Reconstruction

- ART uses relaxation \(\lambda=0.25\), five complete ray sweeps in code, zero initialization, nonnegative projection after every update, and two NLM passes after each sweep (pp. 10, 25–26).
- NLM uses \(h=0.5\), but no tuning criterion is provided (pp. 23–24).
- FBP uses a ramp filter and 180-view averaging; crop and resize choices are hard-coded (pp. 24–25).

### New phantom

- Geometry supplies starting values rather than final values, which is a sound separation between interpretable initialization and numerical refinement (pp. 17–18).
- The stated optimization has 183 variables: three shared geometric parameters plus 180 angles. The implementation reduces the shared fit to 18 sampled views, then estimates each angle separately (p. 18).
- The appendix specifies SQP, `MaxFunEvals=15000`, and `TolFun=1e-10`, but lacks a complete executable call and any parameter bounds (p. 30).

## 8. Validation

### 8.1 In-sample forward-fit residual

The original calibration fit reports RMSE 4.4161 after the first solve and 0.0148 after final refinement (p. 7, Table 2). This verifies that the fitted forward model reproduces the calibration data. It does not by itself verify that all parameters are identifiable or physically correct; different parameter combinations could fit similarly.

### 8.2 Exact synthetic recovery

The paper generates a 512-by-180 projection matrix from known parameters and recovers them. Table 5 reports near machine-precision differences and angle SSE \(9.8618\times10^{-17}\) (p. 13). This is a useful code-consistency test, but the simulation uses the same forward model as the estimator, so it cannot detect model misspecification.

There is an internal source inconsistency: the prose immediately before Table 5 states \(d_0=1, x_0=10, y_0=10, \mu=1.5\), whereas Table 5 and appendix code use \(d_0=5, x_0=-8, y_0=10, \mu=1.5\) (pp. 13 and 26). The table and code agree with each other.

### 8.3 Additive-noise recovery

Using synthetic measurements in approximately \((0,120)\), the paper adds uniform noise on \((-15,15)\) and \((-50,50)\). For the smaller noise, the recovered shared parameters are \((5.0189,-7.9957,10.0339,1.4986)\) versus \((5,-8,10,1.5)\), and angle RMSE is 0.0053 rad (p. 14). For the larger noise, results are \((5.0693,-8.0188,10.3614,1.4938)\) and angle RMSE 0.0191 rad (p. 15).

This is materially stronger than a purely qualitative robustness claim because ranges, outputs and metrics are given. However, only one realization per noise level is shown, no random seed or confidence interval is reported, and the largest-noise \(y_0\) relative error is about 3.61%, contradicting the abstract's unqualified statement that all parameter relative errors under artificial noise are below 1%.

### 8.4 Initial-value and redesigned-phantom tests

For the two-circle model, ten noiseless random geometry cases are reported; the average relative error column is very small, with its largest displayed value \(7.4111\times10^{-4}\), and angle errors are said to be below \(10^{-3}\) (p. 19, Table 8). Under Gaussian noise with variance 0.2, the initial angle is swept from \(-180^\circ\) to \(180^\circ\) in 3° increments. Sixty percent of runs have \(x_0\) relative error below 0.5%; the worst is 3.78%, and simulated annealing reduces that case to 0.13% (pp. 19–20).

This reveals local minima rather than proving initialization insensitivity. Only \(x_0\), one fixed geometry and apparently one noise realization are summarized. The statement that the model is insensitive to initial values is therefore stronger than the evidence.

### 8.5 Reconstruction validation

Problems 2–3 provide reconstructed images and ten requested-point values from FBP and ART, plus qualitative comments on smoothness, sharpness and speed (pp. 11–13). There is no reference image, held-out projection test, reprojection residual, PSNR/SSIM, edge metric, or repeated-noise analysis. The disagreement in absolute absorption values—often ART values are roughly two or more times FBP values—remains unresolved. Reconstruction validation is therefore much weaker than calibration validation.

## 9. Sensitivity and Robustness

The paper performs three robustness probes:

1. **Noise amplitude:** uniform noise is expanded from \((-15,15)\) to \((-50,50)\), increasing angle RMSE from 0.0053 to 0.0191 rad and visibly increasing shared-parameter errors (pp. 14–15).
2. **Geometry variation:** ten noiseless cases vary \(x_0,y_0\in[-15,15]\) and \(d_0\in[-2,2]\) for the redesigned phantom (p. 19).
3. **Initialization:** the initial angle is swept over 121 values at 3° spacing under Gaussian noise; local-optimum failures are exposed rather than hidden (pp. 19–20).

These experiments are concrete but are not a complete sensitivity analysis. Detector spacing, gain, angle increment, number of views, relaxation \(\lambda\), NLM bandwidth \(h\), LOWESS span, phantom manufacturing error and interpolation method are not varied. No interaction effects or uncertainty propagation from calibration to reconstructed point values are assessed. For future competition work, the most important missing experiment is an end-to-end perturbation: perturb calibration data, recalibrate, reconstruct the same object, and report how requested absorption values change.

## 10. Visualization Strategy

- **Forward-model diagnosis:** phantom geometry beside its projection heat map makes the circle/ellipse decomposition visible (p. 3, Figures 1–2).
- **Preliminary fit:** an observed-versus-fitted circular chord curve motivates the linear path-length relation (p. 4, Figure 3).
- **Coordinate geometry diagrams:** detector, ray and phantom sketches support the chord formulas and recentering logic (pp. 4–8, Figures 4–8).
- **Reconstruction comparison:** raw ART versus NLM and ART–NLM versus FBP images show the edge/smoothness trade-off (pp. 10–13, Figures 9–10 and 15–16).
- **Noise diagnosis:** a histogram and SPSS K-S output accompany the uniform-noise claim (p. 12, Figures 13–14).
- **Robustness evidence:** noisy projection heat maps and per-angle error plots show where calibration deteriorates (pp. 14–15, Figures 17–20).
- **Initialization failure visualization:** relative error versus initial angle exposes isolated local-optimum spikes (p. 19, Figure 24).

The sequence is competition-effective: geometry figure → equation → estimate → image/table → validation plot. Its main weakness is that several small plots lack readable axes or quantitative captions, and normalized image brightness can obscure scale disagreement.

## 11. Writing Structure

The paper follows a clear four-question structure: problem restatement, analysis, assumptions, model construction, solution, evaluation, then appendices. Each question begins with a modeling rationale and moves from equations to numeric outputs. The abstract reports both methods and primary calibration numbers.

Particularly effective writing choices are:

- explaining why a circle is isolated before writing the rough fit;
- stating why FBP and ART are both retained;
- explicitly diagnosing ART's binary-matrix bias;
- using validation as a separate fourth-question deliverable rather than burying it in a generic advantages section;
- placing extensive code and all 180 angles in appendices.

Weaknesses include notation corruption or ambiguity in several formulas, an undefined \(n\) in the RMSE, inconsistent simulation parameters between prose and table, over-strong words such as “证明” for limited numerical tests, and incomplete description of the Problem 3 denoising operation.

## 12. Strengths

1. **Forward–inverse coherence:** The same physical geometry connects calibration, coordinate correction, reconstruction and synthetic validation.
2. **Model-selection reasoning:** Circle symmetry, analytic chords, sparse-system difficulty, prior constraints, edge preservation, and the one-versus-three-shape design trade-off are stated rather than merely listing algorithms.
3. **Complementary reconstruction models:** FBP and ART represent genuinely different continuous and discrete formulations.
4. **Iterative calibration design:** Alternating global and angle-specific fits plus angle smoothing addresses dimensionality and structural regularity.
5. **Quantified calibration robustness:** Two explicit noise ranges, angle RMSE, shared-parameter estimates and an initialization sweep are substantially more useful than a single “robust” claim.
6. **Honest diagnostic insight:** The paper notices ART's upward bias and local-optimum failures.
7. **Traceable implementation detail:** Relaxation, NLM bandwidth, number of sweeps, LOWESS span and solver tolerances can be recovered from the appendix.
8. **Verified provenance:** The official display paper is matched to the official national first-prize list.

## 13. Weaknesses

1. **Linear measurement relation is under-justified:** The paper moves from a generic attenuation function to \(V=\mu p_t\). If the supplied data are already logarithmically transformed this may be appropriate, but that transformation is not established.
2. **Text–code mismatch for detector spacing:** The prose presents \(\Delta d\) as jointly optimized, while the shown `fitnlm` parameter vector omits it.
3. **In-sample fit is called reliability:** RMSE 0.0148 measures fit to the same 92,160 calibration readings and cannot rule out non-identifiability.
4. **Reconstruction lacks ground-truth validation:** FBP and ART disagree in magnitude, yet no reprojection error or independent truth selects between them.
5. **Problem 3 preprocessing is not reproducible:** The exact action after thresholding at 0.3 is missing, and the uniform distribution's support is not reported.
6. **Binary ART system matrix is coarse:** The paper itself identifies it as a likely cause of bias; a ray-length or area-overlap weight should have been implemented.
7. **Simulation is self-consistency validation:** Generating and recovering data with the same analytic model does not test violations such as beam hardening, scatter or phantom machining error.
8. **Robustness claims overreach:** At the larger uniform-noise level, \(y_0\)'s error is about 3.61%, inconsistent with the abstract's “below 1%” statement.
9. **Parameter inconsistency:** Section 7.1's prose gives a different \((d_0,x_0)\) from Table 5 and the code.
10. **Initialization test is partial:** It reports only \(x_0\) for one fixed geometry and one apparent noise realization; 40% of starts exceed the claimed 0.5% threshold.
11. **Hyperparameters are not tuned:** LOWESS span, ART relaxation and pass count, NLM bandwidth, crop and interpolation choices have no ablation.
12. **New-template code is incomplete:** The appendix shows objective and options but not a complete optimizer call; some code is deferred to unavailable supporting material.

## 14. Reusable Techniques

### Analytic calibration object

**When useful:** A black-box measurement system can observe an object with known geometry.

**Why useful:** Analytic projection or response formulas convert hardware calibration into parameter estimation and create synthetic validation data.

**Limitations:** Geometry and response physics must be accurate; unmodeled system effects can make a numerically excellent fit physically wrong.

### Geometry-derived initialization plus numerical refinement

**When useful:** A nonlinear estimator has local minima, while landmark positions yield approximate parameters.

**Why useful:** It combines interpretability and solver speed without treating a noisy geometric approximation as the final answer.

**Limitations:** Feature detection must be reliable, and multiple starts are still needed if symmetry leaves ambiguous basins.

### Alternating shared and local parameter fitting

**When useful:** Many groups or time points share global parameters but have one local parameter each.

**Why useful:** It reduces effective dimension and allows structural smoothing of local parameters.

**Limitations:** Alternation can converge to a local fixed point; report objective history and test multiple starts.

### Forward-simulate–inverse-recover validation

**When useful:** Real ground truth is unavailable but a forward model exists.

**Why useful:** It catches coding and identifiability failures and permits controlled noise experiments.

**Limitations:** It is an “inverse crime” if the same forward model generates and fits the data; add model mismatch and real-data residual tests.

### Dual continuous/discrete inverse solutions

**When useful:** A problem admits both transform-based and iterative reconstruction.

**Why useful:** The models expose different speed, prior, sharpness and discretization trade-offs.

**Limitations:** Side-by-side pictures are not validation; compare reprojection error, known targets or task-specific metrics.

### Ray-weight refinement

**When useful:** A binary incidence matrix biases an imaging or network-flow inverse problem.

**Why useful:** Continuous intersection-length weights better approximate the measurement integral.

**Limitations:** Computation and memory increase; sparse construction and sensitivity checks are needed.

## 15. Competition Takeaways

1. Start inverse problems with an explicit forward model and show how every calibration parameter enters it.
2. Use simple geometric invariants—here, circle symmetry—to obtain starting values before launching a high-dimensional optimizer.
3. When many local parameters follow a structural order, smooth or regularize them, then alternate with shared-parameter fitting; document the smoothing span and ablate it.
4. Treat two algorithms as complementary only after defining how they will be compared. If their values disagree, add a ground-truth, reprojection or hold-out criterion.
5. Build validation tables with perturbation range, random seed or repetitions, metric and failure cases. Do not reduce one noisy trial to “robust.”
6. Check every abstract-level numerical claim against the body; this paper's “all below 1%” statement does not survive the \((-50,50)\) noise table.
7. Compare prose, formulas and appendix code. Here, detector spacing is described as optimized but omitted from the shown optimizer vector.
8. A redesigned experimental object should target identifiability and solver initialization, not visual novelty. The explicit one/two/three-shape trade-off is highly reusable.

## 16. Traceability

| Claim | Claim type | Source page | Source section | Notes |
|---|---|---:|---|---|
| The paper solves calibration, two reconstructions, noisy reconstruction and phantom redesign | explicit | 2 | Sections 1–2 | Four requested tasks and proposed pipeline |
| Diffraction, scatter, beam hardening and phantom machining error are excluded | explicit | 2–3 | Section 3 | Modeling assumptions |
| Circle-only chord fitting gives \(\mu=1.7724\), \(\Delta d=0.2768\), \(d_0=-4.0688\), \(c=0\) | explicit | 3–4 | Section 4.1 | Preliminary fit |
| The analytic forward model sums ellipse and circle chord lengths after detector-offset correction | explicit | 5–6 | Section 4.3 | Formula visually checked |
| Calibration alternates a joint fit, LOWESS, shared-parameter fit, per-angle fit and final joint fit | explicit | 6–7 | Section 4.4 | Four-stage method |
| The final original-phantom fit reports center \((-9.2696,6.2738)\) mm and spacing 0.2768 mm | explicit | 7 | Section 4.5 | Table 1 and preceding text |
| RMSE decreases from 4.4161 to 0.0148 | explicit | 7 | Section 4.6, Table 2 | In-sample residual only |
| The shown code omits \(\Delta d\) from the fitted parameter vector despite the prose | criticism | 6–7, 22–23 | Section 4.4 and Appendix .3 | Source-code/prose inconsistency |
| FBP follows the Fourier slice theorem and a ramp-filtered back projection | explicit | 8–9 | Section 5.2 | Continuous branch |
| ART uses binary ray incidence, \(\lambda=0.25\), nonnegativity and five full passes in code | explicit | 9–10, 25–26 | Section 5.3 and Appendix .6 | Five passes comes from code |
| Binary ART weights are cited as the reason ART absorption values are high | explicit | 13 | Section 6.2 | Suggested continuous weights not implemented |
| Values below 0.3 are tested as uniform with mean 0.1549 and significance 0.157 | explicit | 12 | Section 6.1 | Exact subsequent transform is unspecified |
| Problem 2–3 reconstruction validation is weaker than calibration validation | criticism | 11–13 | Sections 5.3–6.2 | No truth/reprojection metric; branches disagree |
| Table 5/code parameters conflict with the prose immediately before Table 5 | criticism | 13, 26 | Section 7.1 and Appendix .7 | Table/code use \(d_0=5,x_0=-8\); prose says \(d_0=1,x_0=10\) |
| Uniform-noise ranges \((-15,15)\) and \((-50,50)\) give angle RMSE 0.0053 and 0.0191 rad | explicit | 14–15 | Section 7.2 | One reported realization per level |
| The large-noise \(y_0\) error is about 3.61%, contradicting the abstract's below-1% claim | criticism | 1, 15 | Abstract; Section 7.2, Table 7 | Computed from 10 versus 10.3614 |
| Two circles are chosen as a compromise between one-shape underfitting and three-shape computation | explicit | 16–17 | Section 7.3.2 | Direct model-selection rationale |
| Geometry estimates initialize a 183-variable nonlinear least-squares problem | explicit | 17–18 | Sections 7.3.2–7.3.3 | Three shared variables plus 180 angles |
| Sixty percent of initial angles yield \(x_0\) error below 0.5%; worst 3.78%, then SA gives 0.13% | explicit | 19–20 | Section 7.3.4 | Only \(x_0\) is summarized |
| The evidence does not justify broad initial-value insensitivity | criticism | 19–20 | Section 7.3.4 | One geometry/noise case and 40% above 0.5% |
| LOWESS span 50, NLM \(h=0.5\), ART five passes and SQP settings are recoverable from code | explicit | 22–30 | Appendices .3–.8 | Some new-template support code remains absent |

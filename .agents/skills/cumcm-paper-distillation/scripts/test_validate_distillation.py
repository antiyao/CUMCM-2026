#!/usr/bin/env python3

import tempfile
import importlib.util
from pathlib import Path

from validate_distillation import validate


VALID = """# Paper: 合成验证样例

## Metadata

- Distillation schema: 1.1
- Paper ID: synthetic_test
- Year: 2026
- Problem: C
- Award: unknown
- Provenance tier: L; synthetic fixture
- Source file: missing.pdf
- Source URL: unknown
- Verification source: unknown
- Pages: 10
- SHA-256: 0000000000000000000000000000000000000000000000000000000000000000
- Extraction method: embedded text
- Extraction quality: synthetic fixture
- Page convention: 1-based physical PDF pages
- Visually checked pages: 1, 5, 10
- Unresolved extraction ambiguities: none
- Supplemental artifacts: none identified

## 1. Problem Archetype

合成统计与优化问题。

## 2. Problem Decomposition

先拟合，再验证，最后决策。

## 3. Data Processing

训练期标准化，测试期不参与估计。

## 4. Models Used

使用线性回归建立基线。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 线性回归 | selected | 基线 | 解释简单 | 留出误差 | 正则化模型 | 证据有限 |

## 5. Model Pipeline

数据进入回归，预测进入优化。

## 6. Model Improvements

与均值基线比较。

## 7. Parameter Estimation and Optimization

普通最小二乘估计参数。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| beta | 斜率 | dimensionless | p.5 equation 1 | 0.5 | data-estimated | ordinary least squares | yes | 合成值 |

## 8. Validation

使用留出数据评价。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 短期预测 | L2 hold-out sanity check | hold-out | MAE | 1 | 优于基线 | 漂移未测试 | 单次切分 | 仅支持当前测试期 |

## 9. Sensitivity and Robustness

使用五点网格扰动斜率。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| beta | 0.5 | 0.4-0.6 | five-point grid | decision | stable | no | 仅支持给定范围 |

## 10. Visualization Strategy

绘制残差和敏感性曲线。

## 11. Writing Structure

按模型、验证和局限组织。

## 12. Strengths

训练和验证职责清楚。

## 13. Weaknesses

没有外部真实数据。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | available | synthetic scope | 非现实数据 |
| Code availability | partial | appendix pp.9-10 | 缺完整入口 |
| Dependency / environment information | not reported | full PDF pp.1-10 | 环境未知 |
| Random seed | not reported | appendix pp.9-10 | 随机过程不可重复 |
| Hard-coded constants | one found | code p.10 | 来源未说明 |
| Formula-to-code consistency | consistent | equation p.5 and code p.9 | 只核对一个模型 |
| Code-to-result consistency | not assessable | code and result reviewed | 缺运行产物 |
| Overall reproducibility | partially reproducible | full PDF pp.1-10 | 缺环境和种子 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 参数数量 | 三个参数 | 设计矩阵三列 | pass | p.5 equation 1 | 样本数更多 |

## 14. Reusable Techniques

### 时间留出

**When useful:** 时间序列预测。

**Why useful:** 防止未来信息进入训练。

**Limitations:** 仍需滚动验证。

## 15. Competition Takeaways

1. 先建立基线。
2. 按时间切分。
3. 记录参数来源。
4. 检查简单算术。
5. 限定结论边界。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 模型含三个参数 | explicit | 5 | 模型 | equation 1 | direct transcription | N/A | 合成来源 |
| 参数数量与设计矩阵一致 | criticism | 5 | 模型 | equation 1 | independent calculation | N/A | 检查通过 |
| 留出误差优于基线 | explicit | 7 | 验证 | table 2 | direct transcription | N/A | 单次切分 |
| 敏感性结论仅限给定范围 | interpretation | 8 | 稳健性 | figure 3 | derived interpretation | N/A | 不外推 |
| 在已审查范围内，未发现滚动验证 | criticism | 1-10 | 全文 | none found | derived interpretation | full PDF pp.1-10; validation pp.7-8; appendix code pp.9-10 reviewed | 合成来源 |
"""


def run_case(directory, name, text, schema="1.1"):
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return validate(path, schema, Path.cwd())


def main():
    repo_root = Path(__file__).resolve().parents[4]
    pipeline_path = repo_root / "literature" / "scripts" / "corpus_pipeline.py"
    spec = importlib.util.spec_from_file_location("cumcm_corpus_pipeline", pipeline_path)
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)

    with tempfile.TemporaryDirectory(prefix="cumcm-distillation-validator-") as temporary:
        directory = Path(temporary)
        errors, _, _ = run_case(directory, "valid.md", VALID)
        assert not errors, errors
        assert pipeline.analysis_is_complete(directory / "valid.md")

        invalid_scope = VALID.replace(
            "full PDF pp.1-10; validation pp.7-8; appendix code pp.9-10 reviewed",
            "N/A",
        )
        errors, _, _ = run_case(directory, "invalid-scope.md", invalid_scope)
        assert any("review scope" in error for error in errors), errors

        invalid_heading = VALID.replace("## 8. Validation", "## 8. Model Testing")
        errors, _, _ = run_case(directory, "invalid-heading.md", invalid_heading)
        assert any("section" in error for error in errors), errors
        assert not pipeline.analysis_is_complete(directory / "invalid-heading.md")

        invalid_source_type = VALID.replace("data-estimated", "guessed")
        errors, _, _ = run_case(directory, "invalid-source-type.md", invalid_source_type)
        assert any("source type" in error for error in errors), errors

        errors, _, _ = run_case(directory, "not-a-calibration-id.md", VALID, "1.0-calibration")
        assert any("restricted" in error for error in errors), errors

        missing_block = VALID.replace("### Numerical Sanity Checks", "### Numerical Review")
        path = directory / "missing-block.md"
        path.write_text(missing_block, encoding="utf-8")
        assert not pipeline.analysis_is_complete(path)

    print("PASS validator behavioral tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

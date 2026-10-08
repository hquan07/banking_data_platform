# DS4 BAF supervised candidate — 2026-10-09

## Evaluation design

- Version: `ds4-histgb-v1`
- Algorithm: scikit-learn `HistGradientBoostingClassifier`
- Source: BAF `Base.csv`, all 1,000,000 rows
- Features: all 30 source features (the label and month index are excluded)
- Training: months 0–5, 794,989 rows
- Threshold selection: month 6, 108,168 rows
- Final holdout: month 7, 96,843 rows
- Dataset SHA-256: `7bf10a37ce07e72e14c1b09e5efee3d27261baff4facc7da767b0474dcf9b809`
- Model SHA-256: `7ab242cf97351b71e28e6dabafdd128fab626a88412ece2afa4587bc8bc8e2b7`

The split uses the benchmark's discrete month index, not a fabricated calendar
timestamp. Month 6 selects the F1-maximizing threshold; it is not reused as the
reported holdout. The artifact and full metadata remain local under
`.runtime/model-candidates/ds4-histgb-v1/`.

## Month 7 holdout

| Metric | Value |
| --- | ---: |
| Fraud prevalence | 0.014746 |
| Decision threshold | 0.905924 |
| PR-AUC | 0.212450 |
| ROC-AUC | 0.896335 |
| Precision | 0.284261 |
| Recall | 0.293417 |
| F1 | 0.288766 |
| False-positive rate | 0.011057 |
| TP / FP / FN / TN | 419 / 1,055 / 1,009 / 94,360 |

PR-AUC is about 14.4 times the holdout fraud prevalence. The result demonstrates
useful ranking signal from the full BAF feature set, but recall remains below
30% at the validation-selected operating point.

## Decision

`CANDIDATE_NOT_DEPLOYED`. This candidate replaces the rejected fixed-threshold
idea as the reproducible DS4 baseline, but the streaming evaluator continues to
fail closed for DS4. Runtime promotion requires an explicit review, model
explanations, drift monitoring and an agreed precision/recall operating point.
The privacy-preserving synthetic benchmark result is not evidence of production
performance on real account applications.

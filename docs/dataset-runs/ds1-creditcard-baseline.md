# DS1 credit-card baseline — 2026-10-08

## Source verification

- Kaggle source: `mlg-ulb/creditcardfraud`
- License reported by Kaggle CLI: `DbCL-1.0`
- Local file: `datasets/raw/creditcard/creditcard.csv` (excluded from Git)
- SHA-256: `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`
- Rows: 284,807
- Columns: 31
- Missing required columns: none
- Observed fraud prevalence: 0.1727486%

The source has no account, customer, card, merchant, currency, channel or
location identifiers. No such values are derived or fabricated by the mapper.

## Offline Isolation Forest candidate

- Version: `ds1-isolation-v1`
- Features: `V1..V28`
- Training rows: 227,845 (`Time <= 145247`)
- Holdout rows: 56,962 (`Time >= 145248`)
- Contamination: 0.002
- Model SHA-256: `c26b522b0d64bffb93b803ea539c1e05fd6cc49223be74cc6e82477561bc9d1f`

Holdout results:

| Metric | Value |
| --- | ---: |
| PR-AUC | 0.060143 |
| Precision | 0.032787 |
| Recall | 0.026667 |
| False-positive rate | 0.001037 |
| TP / FP / FN / TN | 2 / 59 / 73 / 56,828 |

## Decision

`CANDIDATE_NOT_DEPLOYED`. Recall and precision are far too low for live use.
The artifact remains local under `.runtime/model-candidates/` and is not loaded
by the streaming engine. The result is retained as a reproducible unsupervised
baseline, not as evidence of production fraud-detection quality.

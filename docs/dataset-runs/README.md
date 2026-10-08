# Dataset integration status

| Dataset | Acquisition | Profile | Canary | Current gate |
| --- | --- | --- | --- | --- |
| DS1 Credit Card | Complete | Valid | Offline model evaluated | Candidate rejected for low precision/recall |
| DS3 PaySim | Complete | Valid | 1,000 events passed | Full replay is an operator workload decision |
| DS4 BAF Base | Complete | Valid | 1,000 events passed | Alert thresholds require source-specific calibration |

Raw CSVs, generated profiles and model binaries are local artifacts excluded
from Git. The per-source manifests in this directory record checksums,
reconciliation evidence and promotion decisions without committing datasets.

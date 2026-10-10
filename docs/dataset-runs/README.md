# Dataset integration status

| Dataset | Acquisition | Profile | Canary | Current gate |
| --- | --- | --- | --- | --- |
| DS1 Credit Card | Complete | Valid | 1,000-event canary passed; offline model evaluated | Candidate rejected for low precision/recall |
| DS3 PaySim | Complete | Valid | 91,501 events reconciled; 50 EPS/5-minute gate passed | Full replay is an operator workload decision |
| DS4 BAF Base | Complete | Valid | 1,000 events passed; supervised candidate audited | Candidate is not deployed to runtime |

Raw CSVs, generated profiles and model binaries are local artifacts excluded
from Git. The per-source manifests in this directory record checksums,
reconciliation evidence and promotion decisions without committing datasets.

# Dataset workspace

This directory is the local landing zone for public fraud benchmarks. Raw CSV
files are intentionally excluded from Git. The application does not download
or replay a dataset automatically.

## Sources and scope

`catalog.json` is the source-of-truth for provenance, access restrictions,
expected files, time semantics and entity limitations. In particular:

- DS1 and IEEE-CIS are anonymized transaction benchmarks. Their hidden fields
  must not be decoded or presented as real identities or coordinates.
- PaySim is a transaction simulator, despite being derived from aggregate
  patterns from a real mobile-money service.
- BAF is a privacy-preserving synthetic benchmark for account-opening fraud;
  it is not a payment stream.

These datasets are independent benchmarks. They have no shared customer,
account or timeline and must not be entity-joined into a single banking ledger.

## Acquisition

1. Install and authenticate the Kaggle CLI.
2. Accept the IEEE-CIS competition rules on Kaggle before downloading DS2.
3. Run one explicit download, for example:

   ```bash
   ./datasets/download.sh ds3
   ```

Use `all` only after reviewing disk requirements and each source's terms. The
files are stored under `datasets/raw/` and remain untracked.

Downloading a public benchmark does not make it production data. Preserve the
dataset ID and source row identifier on every derived event so dashboard and
evaluation results remain attributable to their source.

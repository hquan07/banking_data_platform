# Dataset workspace

This directory is the local landing zone for public fraud benchmarks. Raw CSV
files are intentionally excluded from Git. The application does not download
or replay a dataset automatically.

## Sources and scope

`catalog.json` is the source-of-truth for provenance, access restrictions,
expected files, time semantics and entity limitations. In particular:

- DS1 is an anonymized transaction benchmark. Its hidden fields must not be
  decoded or presented as real identities.
- PaySim is a transaction simulator, despite being derived from aggregate
  patterns from a real mobile-money service.
- BAF is a privacy-preserving synthetic benchmark for account-opening fraud;
  it is not a payment stream.

These datasets are independent benchmarks. They have no shared customer,
account or timeline and must not be entity-joined into a single banking ledger.

## Acquisition

1. Install and authenticate the Kaggle CLI.
2. Run one explicit download, for example:

   ```bash
   ./datasets/download.sh ds3
   ```

Use `all` only after reviewing disk requirements and each source's terms. The
files are stored under `datasets/raw/` and remain untracked.

Downloading a public benchmark does not make it production data. Preserve the
dataset ID and source row identifier on every derived event so dashboard and
evaluation results remain attributable to their source.

## Profiling

After downloading a source, generate a chunked profile before mapping it:

```bash
PYTHONPATH=. python datasets/profile_datasets.py ds1_creditcard
```

Use `all` only when all three sources are present. Profiles are local artifacts
under `datasets/profiles/`; they contain file checksums, row counts, schema
validation, null rates, inferred types, bounded cardinality and numeric ranges.
The command exits non-zero when a file is absent or violates its expected
minimum schema/row count.

For PaySim, reproduce the source-sequence audit before changing graph rules:

```bash
PYTHONPATH=. python datasets/audit_paysim_sequences.py
```

The audit distinguishes adjacent TRANSFER/CASH_OUT source rows from actual
participant linkage; those concepts must not be treated as equivalent.

## Canonical mapping

`schema_mapping.py` converts each source row to `benchmark-events` v1. The
contract deliberately keeps source-specific event types and relative time. It
does not invent missing account/customer IDs, currencies, locations or dates.
See `shared/benchmark_contract.md` for the wire format and leakage boundary for
ground-truth labels.

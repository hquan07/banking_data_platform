#!/usr/bin/env python3
"""Persist reconciliation evidence for one durable benchmark replay run."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.reconciliation.run import reconcile_benchmark_run


def main() -> int:
    from dotenv import load_dotenv
    import psycopg2

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--freshness-sla-seconds", type=int, default=300)
    parser.add_argument("--sample-limit", type=int, default=25)
    args = parser.parse_args()
    load_dotenv()
    connection = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5433")),
        dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"], connect_timeout=10,
    )
    try:
        checks = reconcile_benchmark_run(
            connection, args.run_id,
            freshness_sla_seconds=args.freshness_sla_seconds,
            sample_limit=args.sample_limit,
        )
    finally:
        connection.close()
    print(json.dumps({"run_id": args.run_id, "checks": checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

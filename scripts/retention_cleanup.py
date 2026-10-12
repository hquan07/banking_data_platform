#!/usr/bin/env python3
"""Plan or apply a source-scoped retention cleanup with durable audit."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from governance.retention import RetentionRuntime, parse_cutoff, validate_source


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run-first cleanup for one explicit source and cutoff.",
    )
    parser.add_argument("--source", required=True, help="Dataset/source, for example ds3_paysim")
    parser.add_argument("--cutoff", required=True, help="Timezone-aware ISO-8601 timestamp")
    parser.add_argument(
        "--apply-dry-run",
        metavar="EXECUTION_ID",
        help="Apply only if this completed dry-run still matches exactly",
    )
    parser.add_argument("--actor", default=os.environ.get("USER", "retention-cli"))
    return parser.parse_args()


def main() -> int:
    args = arguments()
    load_dotenv(REPOSITORY_ROOT / ".env")
    source = validate_source(args.source)
    cutoff = parse_cutoff(args.cutoff)
    runtime = RetentionRuntime.from_environment()
    try:
        plan = runtime.build_plan(source, cutoff)
        if args.apply_dry_run:
            result = runtime.apply(plan, args.actor, args.apply_dry_run)
        else:
            result = runtime.record_dry_run(plan, args.actor)
        print(json.dumps(result, indent=2, default=str, sort_keys=True))
        return 0
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())

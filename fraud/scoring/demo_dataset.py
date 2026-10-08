"""Generate reproducible synthetic labels for testing the ML *workflow* only.

The labels are scripted from the mock features and must never be presented as
measured fraud-detection performance on real transactions.
"""

import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


FIELDS = ("event_time", "amount", "hour_of_day", "velocity_1h", "diff_from_avg",
          "is_international", "is_fraud", "data_origin")


def generate_rows(count: int = 600, seed: int = 42) -> list[dict]:
    if count < 200:
        raise ValueError("at least 200 rows are required for a temporal holdout")
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        scripted_fraud = index % 17 == 0 or index % 29 == 0
        amount = round(rng.uniform(6500, 14000) if scripted_fraud else rng.uniform(20, 4500), 2)
        rows.append({
            "event_time": (start + timedelta(minutes=index)).isoformat(),
            "amount": amount,
            "hour_of_day": (index // 60) % 24,
            "velocity_1h": rng.randint(5, 12) if scripted_fraud else rng.randint(0, 4),
            "diff_from_avg": round(amount / 2000, 4),
            "is_international": int(scripted_fraud or rng.random() < 0.1),
            "is_fraud": int(scripted_fraud),
            "data_origin": "synthetic_demo",
        })
    return rows


def write_demo_csv(path: Path, count: int = 600, seed: int = 42) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(generate_rows(count, seed))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    write_demo_csv(args.output, args.rows, args.seed)
    print(f"Wrote {args.rows} synthetic_demo rows to {args.output}")


if __name__ == "__main__":
    main()

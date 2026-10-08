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


def generate_rows(count: int = 600, seed: int = 42,
                  start: datetime | None = None) -> list[dict]:
    if count < 200:
        raise ValueError("at least 200 rows are required for a temporal holdout")
    rng = random.Random(seed)
    start = start or datetime(2026, 1, 1, tzinfo=timezone.utc)
    if start.tzinfo is None:
        raise ValueError("start must be timezone-aware")
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


def write_demo_csv(path: Path, count: int = 600, seed: int = 42,
                   start: datetime | None = None) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(generate_rows(count, seed, start))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-time", default="2026-01-01T00:00:00Z",
                        help="Timezone-aware ISO-8601 start; choose a later period for monitoring")
    args = parser.parse_args()
    start = datetime.fromisoformat(args.start_time.replace("Z", "+00:00"))
    write_demo_csv(args.output, args.rows, args.seed, start)
    print(f"Wrote {args.rows} synthetic_demo rows to {args.output}")


if __name__ == "__main__":
    main()

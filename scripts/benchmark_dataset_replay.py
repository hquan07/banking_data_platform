#!/usr/bin/env python3
"""Run and reconcile a bounded dataset replay performance check."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_GROUPS = ("benchmark-processor-v2", "benchmark-graph-v1")
DEFAULT_API_PATHS = (
    "/api/health/ready",
    "/api/datasets/status",
    "/api/datasets/performance",
    "/api/datasets/balance-anomalies",
    "/api/datasets/behavior-distributions",
    "/api/graph/money-flow",
    "/api/graph/fraud-sequences",
)
DATASET_IDS = ("ds1_creditcard", "ds3_paysim", "ds4_baf")


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a percentile from no values")
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between zero and one")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def latency_summary(samples: list[float]) -> dict[str, float | int]:
    if not samples:
        return {"samples": 0}
    return {
        "samples": len(samples),
        "minimum_ms": round(min(samples), 3),
        "mean_ms": round(mean(samples), 3),
        "p50_ms": round(percentile(samples, 0.50), 3),
        "p95_ms": round(percentile(samples, 0.95), 3),
        "p99_ms": round(percentile(samples, 0.99), 3),
        "maximum_ms": round(max(samples), 3),
    }


def parse_consumer_group_lag(output: str) -> int:
    """Sum the LAG column from kafka-consumer-groups output."""
    header: list[str] | None = None
    lag_index = -1
    total = 0
    observed = False
    for raw_line in output.splitlines():
        fields = raw_line.split()
        if "GROUP" in fields and "LAG" in fields:
            header = fields
            lag_index = header.index("LAG")
            continue
        if header is None or len(fields) <= lag_index:
            continue
        try:
            total += int(fields[lag_index])
            observed = True
        except ValueError:
            continue
    if not observed:
        raise ValueError("Kafka consumer-group output contained no lag rows")
    return total


def parse_topic_offsets(output: str) -> dict[int, int]:
    offsets: dict[int, int] = {}
    for raw_line in output.splitlines():
        parts = raw_line.rsplit(":", 2)
        if len(parts) != 3:
            continue
        try:
            offsets[int(parts[1])] = int(parts[2])
        except ValueError:
            continue
    if not offsets:
        raise ValueError("Kafka offset output contained no partitions")
    return offsets


def parse_producer_summary(output: str) -> dict:
    for line in reversed(output.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "published" in value:
            return value
    raise ValueError("Dataset replay output contained no producer summary")


def _run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout


def consumer_lag(group: str) -> int:
    output = _run([
        "docker", "exec", "banking_kafka", "kafka-consumer-groups.sh",
        "--bootstrap-server", "localhost:9092", "--describe", "--group", group,
    ])
    return parse_consumer_group_lag(output)


def dlq_offsets() -> dict[int, int]:
    output = _run([
        "docker", "exec", "banking_kafka", "kafka-get-offsets.sh",
        "--bootstrap-server", "localhost:9092", "--topic", "benchmark-events-dlq",
    ])
    return parse_topic_offsets(output)


def postgres_counts(dataset_id: str) -> dict[str, int]:
    if dataset_id not in DATASET_IDS:
        raise ValueError(f"Unsupported dataset: {dataset_id}")
    sql = (
        "SELECT "
        f"(SELECT count(*) FROM benchmark_events WHERE dataset_id = '{dataset_id}'),"
        f"(SELECT count(*) FROM benchmark_evaluations WHERE dataset_id = '{dataset_id}' "
        "AND evaluator_version = 'benchmark-rules-v2'),"
        f"(SELECT count(*) FROM alerts WHERE dataset_id = '{dataset_id}');"
    )
    output = _run([
        "docker", "exec", "banking_postgres", "sh", "-c",
        'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"', "sh", sql,
    ]).strip()
    fields = output.split("|")
    if len(fields) != 3:
        raise ValueError(f"Unexpected PostgreSQL count output: {output!r}")
    return {"events": int(fields[0]), "evaluations": int(fields[1]), "alerts": int(fields[2])}


def _dotenv_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip("'\"")
    return None


def api_token(base_url: str, env_file: Path) -> str:
    existing = os.environ.get("PERF_API_TOKEN")
    if existing:
        return existing
    username = os.environ.get("PERF_API_USERNAME", "admin")
    password = os.environ.get("PERF_API_PASSWORD") or _dotenv_value(
        env_file, "DASHBOARD_ADMIN_PASSWORD",
    )
    if not password:
        raise ValueError("Set PERF_API_TOKEN or configure DASHBOARD_ADMIN_PASSWORD")
    request = Request(
        f"{base_url}/api/auth/login",
        data=urlencode({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read())["access_token"]


def measure_api(
    base_url: str,
    paths: Iterable[str],
    repetitions: int,
    token: str,
) -> dict[str, dict]:
    results: dict[str, dict] = {}
    headers = {"Authorization": f"Bearer {token}"}
    for path in paths:
        samples: list[float] = []
        failures: list[str] = []
        for _ in range(repetitions):
            started = time.perf_counter()
            request = Request(f"{base_url}{path}", headers=headers)
            try:
                with urlopen(request, timeout=30) as response:
                    response.read()
                    if response.status != 200:
                        failures.append(f"HTTP {response.status}")
            except (HTTPError, URLError, TimeoutError) as exc:
                failures.append(str(exc))
            else:
                samples.append((time.perf_counter() - started) * 1000)
        results[path] = {
            **latency_summary(samples),
            "failures": len(failures),
            "failure_examples": failures[:3],
        }
    return results


def sample_lags(groups: Iterable[str]) -> dict[str, int]:
    return {group: consumer_lag(group) for group in groups}


def run_benchmark(args: argparse.Namespace) -> dict:
    groups = tuple(args.consumer_group)
    api_paths = tuple(args.api_path)
    started_at = datetime.now(timezone.utc)
    counts_before = postgres_counts(args.dataset)
    dlq_before = dlq_offsets()
    initial_lag = sample_lags(groups)

    command = [
        "docker", "compose", "--profile", "dataset-replay", "run", "--rm",
        "-e", f"DATASET_ID={args.dataset}",
        "-e", f"DATASET_START_ROW={args.start_row}",
        "-e", f"DATASET_MAX_EVENTS={args.events}",
        "-e", f"DATASET_REPLAY_RATE={args.rate}",
        "dataset_replay",
    ]
    producer_started = time.monotonic()
    producer = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    lag_samples: list[dict] = []
    while producer.poll() is None:
        elapsed = time.monotonic() - producer_started
        lag_samples.append({"elapsed_seconds": round(elapsed, 3), **sample_lags(groups)})
        time.sleep(args.poll_interval)
    producer_output = producer.communicate()[0]
    producer_seconds = time.monotonic() - producer_started
    if producer.returncode:
        raise RuntimeError(f"Dataset replay failed ({producer.returncode}):\n{producer_output}")
    producer_summary = parse_producer_summary(producer_output)
    observed_rate = float(producer_summary.get(
        "observed_rate_eps", args.events / producer_seconds,
    ))

    drain_started = time.monotonic()
    drain_timed_out = False
    while True:
        current = sample_lags(groups)
        lag_samples.append({
            "elapsed_seconds": round(time.monotonic() - producer_started, 3),
            **current,
        })
        if all(value == 0 for value in current.values()):
            break
        if time.monotonic() - drain_started >= args.drain_timeout:
            drain_timed_out = True
            break
        time.sleep(args.poll_interval)
    drain_seconds = time.monotonic() - drain_started

    counts_after = postgres_counts(args.dataset)
    dlq_after = dlq_offsets()
    token = api_token(args.api_base_url, args.env_file)
    api_results = measure_api(args.api_base_url, api_paths, args.api_repetitions, token)
    dlq_delta = sum(dlq_after.values()) - sum(dlq_before.values())
    count_delta = {
        key: counts_after[key] - counts_before[key]
        for key in counts_before
    }
    peak_lag = {
        group: max(sample[group] for sample in lag_samples)
        for group in groups
    }
    api_failures = sum(result["failures"] for result in api_results.values())
    passed = all((
        producer_summary.get("published") == args.events,
        producer_summary.get("rejected") == 0,
        observed_rate >= args.rate * args.minimum_rate_ratio,
        all(value <= args.max_peak_lag for value in peak_lag.values()),
        count_delta["events"] == args.events,
        count_delta["evaluations"] == args.events,
        dlq_delta == 0,
        not drain_timed_out,
        api_failures == 0,
    ))
    return {
        "schema_version": 1,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "dataset_id": args.dataset,
            "start_row": args.start_row,
            "events": args.events,
            "target_rate_eps": args.rate,
            "minimum_rate_ratio": args.minimum_rate_ratio,
            "max_peak_lag": args.max_peak_lag,
            "poll_interval_seconds": args.poll_interval,
            "drain_timeout_seconds": args.drain_timeout,
        },
        "producer": {
            **producer_summary,
            "observed_rate_eps": round(observed_rate, 3),
            "rate_gate_eps": round(args.rate * args.minimum_rate_ratio, 3),
            "orchestration_elapsed_seconds": round(producer_seconds, 3),
        },
        "kafka": {
            "initial_lag": initial_lag,
            "peak_lag": peak_lag,
            "final_lag": {group: lag_samples[-1][group] for group in groups},
            "drain_seconds": round(drain_seconds, 3),
            "drain_timed_out": drain_timed_out,
            "dlq_offsets_before": dlq_before,
            "dlq_offsets_after": dlq_after,
            "dlq_delta": dlq_delta,
            "samples": lag_samples,
        },
        "postgres": {
            "before": counts_before,
            "after": counts_after,
            "delta": count_delta,
        },
        "api_latency": api_results,
        "passed": passed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=DATASET_IDS, default="ds3_paysim")
    parser.add_argument("--start-row", type=int, required=True)
    parser.add_argument("--events", type=int, default=15_000)
    parser.add_argument("--rate", type=float, default=50)
    parser.add_argument("--minimum-rate-ratio", type=float, default=0.95)
    parser.add_argument("--max-peak-lag", type=int, default=100)
    parser.add_argument("--poll-interval", type=float, default=5)
    parser.add_argument("--drain-timeout", type=float, default=300)
    parser.add_argument("--consumer-group", action="append", default=list(DEFAULT_GROUPS))
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--api-path", action="append", default=list(DEFAULT_API_PATHS))
    parser.add_argument("--api-repetitions", type=int, default=20)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.start_row < 0 or args.events <= 0 or args.rate <= 0:
        parser.error("start-row must be non-negative; events and rate must be positive")
    if args.poll_interval <= 0 or args.drain_timeout <= 0 or args.api_repetitions <= 0:
        parser.error("poll interval, drain timeout and API repetitions must be positive")
    if not 0 < args.minimum_rate_ratio <= 1:
        parser.error("minimum-rate-ratio must be greater than zero and at most one")
    if args.max_peak_lag < 0:
        parser.error("max-peak-lag must be non-negative")
    return args


def main() -> int:
    args = parse_args()
    report = run_benchmark(args)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Collect soak evidence and run allow-listed, recoverable Compose faults."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen


FAULT_SERVICES = {
    "kafka": "kafka",
    "spark-worker": "spark-worker",
    "postgres": "postgres",
    "neo4j": "neo4j",
}
DLQ_TOPICS = (
    "payment-events-dlq",
    "transfer-events-dlq",
    "benchmark-events-dlq",
)
RESTART_SERVICES = (
    "dashboard_backend",
    "live_ingestion",
    "payment_processor",
    "fraud_engine",
    "benchmark_processor",
    "graph_processor",
    "benchmark_graph_processor",
    "kafka",
    "postgres",
    "neo4j",
)
MANAGED_CONSUMER_GROUP_PATTERN = (
    "benchmark-graph-v1|benchmark-processor-v2|dashboard-stream-v1|"
    "neo4j-aml-v1|payment-retry-worker-v1|dashboard-benchmark-stream-v1"
)


def managed_lag_expression() -> str:
    return (
        "max(sum by (consumergroup) "
        f'(kafka_consumergroup_lag{{consumergroup=~"{MANAGED_CONSUMER_GROUP_PATTERN}"}}))'
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run(command: list[str], *, check: bool = True, timeout: float = 120) -> str:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n{result.stderr.strip()}"
        )
    return result.stdout


def parse_json_lines(value: str) -> list[dict[str, Any]]:
    rows = []
    for line in value.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def parse_topic_offsets(value: str) -> dict[int, int]:
    offsets = {}
    for line in value.splitlines():
        fields = line.rsplit(":", 2)
        if len(fields) != 3:
            continue
        try:
            offsets[int(fields[1])] = int(fields[2])
        except ValueError:
            continue
    if not offsets:
        raise ValueError("Kafka offset output contained no partitions")
    return offsets


def offset_total(offsets: dict[str, dict[int, int]]) -> int:
    return sum(value for topic in offsets.values() for value in topic.values())


@dataclass(frozen=True)
class FaultSpec:
    name: str
    at_seconds: float
    outage_seconds: float

    @property
    def service(self) -> str:
        return FAULT_SERVICES[self.name]


def parse_fault_spec(value: str) -> FaultSpec:
    try:
        name, schedule = value.split("@", 1)
        timing = schedule.split(":", 1)
        at_seconds = float(timing[0])
        outage_seconds = float(timing[1]) if len(timing) == 2 else 15.0
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(
            "fault must use NAME@OFFSET_SECONDS[:OUTAGE_SECONDS]"
        ) from None
    if name not in FAULT_SERVICES:
        raise argparse.ArgumentTypeError(
            f"fault name must be one of: {', '.join(FAULT_SERVICES)}"
        )
    if at_seconds < 0 or outage_seconds <= 0:
        raise argparse.ArgumentTypeError("fault offset must be non-negative and outage positive")
    return FaultSpec(name=name, at_seconds=at_seconds, outage_seconds=outage_seconds)


def http_json(url: str, timeout: float = 10) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout) as response:
            return {"ok": True, "status_code": response.status, "body": json.load(response)}
    except HTTPError as exc:
        try:
            body = json.load(exc)
        except Exception:
            body = {"detail": str(exc)}
        return {"ok": False, "status_code": exc.code, "body": body}
    except (URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "status_code": None, "error": str(exc)}


def prometheus_scalar(base_url: str, expression: str) -> float | None:
    payload = http_json(f"{base_url.rstrip('/')}/api/v1/query?query={quote(expression)}")
    if not payload["ok"]:
        return None
    result = payload["body"].get("data", {}).get("result", [])
    if not result:
        return None
    return float(result[0]["value"][1])


def dlq_offsets() -> dict[str, dict[int, int]]:
    result = {}
    for topic in DLQ_TOPICS:
        output = run([
            "docker", "exec", "banking_kafka", "kafka-get-offsets.sh",
            "--bootstrap-server", "localhost:9092", "--topic", topic,
        ])
        result[topic] = parse_topic_offsets(output)
    return result


def restart_counts() -> dict[str, int]:
    counts = {}
    for service in RESTART_SERVICES:
        container_id = run(["docker", "compose", "ps", "-q", service]).strip()
        if not container_id:
            counts[service] = -1
            continue
        value = run(["docker", "inspect", "-f", "{{.RestartCount}}", container_id]).strip()
        counts[service] = int(value)
    return counts


def resource_snapshot() -> list[dict[str, Any]]:
    output = run([
        "docker", "stats", "--no-stream", "--format",
        "{{json .}}",
    ])
    return parse_json_lines(output)


def compose_snapshot() -> list[dict[str, Any]]:
    return parse_json_lines(run(["docker", "compose", "ps", "--format", "json"]))


def sample_state(args: argparse.Namespace, started: float) -> dict[str, Any]:
    return {
        "observed_at": utc_now().isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "readiness": http_json(f"{args.api_base_url.rstrip('/')}/api/health/ready"),
        "metrics": {
            "accepted_events_per_second": prometheus_scalar(
                args.prometheus_url,
                'sum(rate(live_ingest_events_total{status="accepted"}[1m]))',
            ),
            "maximum_consumer_lag": prometheus_scalar(
                args.prometheus_url, managed_lag_expression(),
            ),
            "maximum_all_consumer_lag": prometheus_scalar(
                args.prometheus_url, "max(kafka_consumergroup_lag)",
            ),
            "maximum_processor_heartbeat_age_seconds": prometheus_scalar(
                args.prometheus_url, "max(banking_processor_heartbeat_age_seconds)",
            ),
            "processors_up": prometheus_scalar(
                args.prometheus_url, "sum(banking_processor_up)",
            ),
            "dlq_rate_5m": prometheus_scalar(
                args.prometheus_url,
                'sum(rate(kafka_topic_partition_current_offset{topic=~".*-dlq"}[5m]))',
            ),
        },
        "restart_counts": restart_counts(),
        "containers": compose_snapshot(),
        "resources": resource_snapshot(),
    }


def wait_service(service: str, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last = None
    while time.monotonic() < deadline:
        rows = parse_json_lines(run([
            "docker", "compose", "ps", "--format", "json", service,
        ], check=False))
        last = rows[0] if rows else None
        if last and last.get("State") == "running" and last.get("Health") in ("", "healthy"):
            return last
        time.sleep(2)
    raise TimeoutError(f"Service {service} did not recover: {last}")


def execute_fault(spec: FaultSpec, recovery_timeout: float) -> dict[str, Any]:
    started_at = utc_now()
    evidence = {
        "name": spec.name,
        "service": spec.service,
        "scheduled_at_seconds": spec.at_seconds,
        "outage_seconds": spec.outage_seconds,
        "started_at": started_at.isoformat(),
        "recovered": False,
    }
    try:
        run(["docker", "compose", "stop", "--timeout", "20", spec.service], timeout=60)
        evidence["stopped_at"] = utc_now().isoformat()
        time.sleep(spec.outage_seconds)
        run(["docker", "compose", "start", spec.service], timeout=120)
        evidence["service_state"] = wait_service(spec.service, recovery_timeout)
        evidence["recovered"] = True
    except Exception as exc:
        evidence["error"] = str(exc)
        try:
            run(["docker", "compose", "start", spec.service], check=False, timeout=120)
        except Exception:
            pass
    evidence["finished_at"] = utc_now().isoformat()
    evidence["elapsed_seconds"] = round((utc_now() - started_at).total_seconds(), 3)
    return evidence


def run_integrity_check() -> dict[str, Any]:
    result = subprocess.run(
        [
            "docker", "compose", "--profile", "operations", "run", "--rm",
            "--no-deps", "reconciliation",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]}
    return {"passed": result.returncode == 0, "return_code": result.returncode, "result": payload}


def append_json_line(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def run_soak(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or f"soak-{utc_now().strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    output_dir = args.output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    samples_path = output_dir / "samples.jsonl"
    started_at = utc_now()
    started = time.monotonic()
    dlq_before = dlq_offsets()
    restarts_before = restart_counts()
    faults = sorted(args.fault, key=lambda item: item.at_seconds)
    pending = list(faults)
    fault_results = []

    while True:
        elapsed = time.monotonic() - started
        while pending and elapsed >= pending[0].at_seconds:
            fault_results.append(execute_fault(pending.pop(0), args.fault_recovery_timeout))
            elapsed = time.monotonic() - started
        append_json_line(samples_path, sample_state(args, started))
        elapsed = time.monotonic() - started
        if elapsed >= args.duration_seconds:
            break
        time.sleep(min(args.sample_interval, max(0, args.duration_seconds - elapsed)))

    final_readiness = http_json(f"{args.api_base_url.rstrip('/')}/api/health/ready")
    final_lag = prometheus_scalar(args.prometheus_url, managed_lag_expression())
    final_all_consumer_lag = prometheus_scalar(
        args.prometheus_url, "max(kafka_consumergroup_lag)",
    )
    dlq_after = dlq_offsets()
    restarts_after = restart_counts()
    integrity = {"passed": True, "skipped": True} if args.skip_integrity else run_integrity_check()
    dlq_delta = offset_total(dlq_after) - offset_total(dlq_before)
    recovered = all(item["recovered"] for item in fault_results) and not pending
    passed = all((
        final_readiness["ok"],
        final_readiness.get("body", {}).get("status") == "ready",
        final_lag is not None and final_lag <= args.max_final_lag,
        dlq_delta == 0,
        integrity["passed"],
        recovered,
    ))
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "finished_at": utc_now().isoformat(),
        "configuration": {
            "duration_seconds": args.duration_seconds,
            "sample_interval_seconds": args.sample_interval,
            "max_final_lag": args.max_final_lag,
            "faults": [item.__dict__ for item in faults],
        },
        "evidence": {
            "samples": str(samples_path),
            "faults": fault_results,
            "final_readiness": final_readiness,
            "final_consumer_lag": final_lag,
            "final_all_consumer_lag": final_all_consumer_lag,
            "dlq_offsets_before": dlq_before,
            "dlq_offsets_after": dlq_after,
            "dlq_delta": dlq_delta,
            "restart_counts_before": restarts_before,
            "restart_counts_after": restarts_after,
            "integrity": integrity,
        },
        "passed": passed,
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=float, default=600)
    parser.add_argument("--sample-interval", type=float, default=15)
    parser.add_argument("--fault", action="append", type=parse_fault_spec, default=[])
    parser.add_argument("--fault-recovery-timeout", type=float, default=180)
    parser.add_argument("--max-final-lag", type=float, default=0)
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--prometheus-url", default="http://127.0.0.1:9090")
    parser.add_argument("--output-root", type=Path, default=Path(".runtime/soak"))
    parser.add_argument("--run-id")
    parser.add_argument("--skip-integrity", action="store_true")
    args = parser.parse_args()
    if args.duration_seconds <= 0 or args.sample_interval <= 0:
        parser.error("duration and sample interval must be positive")
    if args.fault_recovery_timeout <= 0 or args.max_final_lag < 0:
        parser.error("recovery timeout must be positive and max final lag non-negative")
    if any(item.at_seconds >= args.duration_seconds for item in args.fault):
        parser.error("every fault offset must occur before the soak duration")
    return args


def main() -> int:
    args = parse_args()
    report = run_soak(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

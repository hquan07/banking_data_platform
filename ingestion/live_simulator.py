"""Controlled demo source that sends current-time events through the live gateway."""

import json
import os
import random
import signal
import time
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

STOP_REQUESTED = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def event_ids(prefix: str) -> tuple[str, str]:
    suffix = uuid.uuid4().hex
    return f"{prefix}-{suffix}", f"trace-{suffix}"


def generate_payment(sequence: int, rng: random.Random) -> dict:
    event_id, trace_id = event_ids("demo-payment")
    account = f"DEMO_ACC_{rng.randint(1, 40):03d}"
    high_risk = sequence > 0 and sequence % 20 == 0
    return {
        "schema_version": 1,
        "event_id": event_id,
        "trace_id": trace_id,
        "payment_id": f"DEMO_PAY_{uuid.uuid4().hex}",
        "customer_id": account.replace("ACC", "CUS"),
        "account_id": account,
        "merchant_id": f"DEMO_MERCHANT_{rng.randint(1, 12):02d}",
        "amount": 20_000.00 if high_risk else round(rng.uniform(5.0, 900.0), 2),
        "currency": "USD",
        "payment_method": rng.choice(["CARD", "BANK_TRANSFER", "QR"]),
        "channel": rng.choice(["POS", "ONLINE", "ATM"]),
        "location": "VN",
        "device_id": f"DEMO_DEVICE_{rng.randint(1, 30):03d}",
        "timestamp": utc_now(),
        "status": "SUCCESS",
    }


def generate_transfer(sequence: int, rng: random.Random) -> dict:
    event_id, trace_id = event_ids("demo-transfer")
    cycle = sequence // 3
    edge = sequence % 3
    if cycle % 5 == 4:
        accounts = [f"DEMO_CYCLE_{cycle}_{index}" for index in range(3)]
        from_account = accounts[edge]
        to_account = accounts[(edge + 1) % 3]
        amount = "5000.00"
    else:
        from_number = rng.randint(1, 40)
        to_number = rng.randint(1, 39)
        if to_number >= from_number:
            to_number += 1
        from_account = f"DEMO_ACC_{from_number:03d}"
        to_account = f"DEMO_ACC_{to_number:03d}"
        amount = f"{rng.uniform(25.0, 800.0):.2f}"
    return {
        "schema_version": 1,
        "event_id": event_id,
        "trace_id": trace_id,
        "from_account_id": from_account,
        "to_account_id": to_account,
        "amount": amount,
        "currency": "USD",
        "timestamp": utc_now(),
    }


def post_event(gateway_url: str, api_key: str, event_type: str, payload: dict) -> dict:
    request = Request(
        f"{gateway_url.rstrip('/')}/v1/events/{event_type}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Live-Source-Key": api_key,
            "X-Source-System": "demo-live-simulator",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Gateway rejected {event_type}: HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Gateway unavailable: {exc.reason}") from exc


def request_stop(*_: object) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True


def run() -> None:
    gateway_url = os.environ.get("LIVE_GATEWAY_URL", "http://live_ingestion:8085")
    api_key = os.environ.get("LIVE_INGESTION_API_KEY", "integration-live-key-change-me")
    rate = float(os.environ.get("LIVE_SIMULATOR_RATE", "2"))
    max_events = int(os.environ.get("LIVE_SIMULATOR_MAX_EVENTS", "0"))
    payment_ratio = float(os.environ.get("LIVE_SIMULATOR_PAYMENT_RATIO", "0.8"))
    seed = int(os.environ.get("LIVE_SIMULATOR_SEED", "20261010"))
    if rate <= 0 or not 0 <= payment_ratio <= 1 or max_events < 0:
        raise ValueError("Simulator rate, ratio or max events is invalid")

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    rng = random.Random(seed)
    published = payment_count = transfer_count = 0
    delay = 1 / rate

    while not STOP_REQUESTED and (max_events == 0 or published < max_events):
        is_payment = rng.random() < payment_ratio
        event_type = "payments" if is_payment else "transfers"
        sequence = payment_count if is_payment else transfer_count
        payload = generate_payment(sequence, rng) if is_payment else generate_transfer(sequence, rng)
        try:
            result = post_event(gateway_url, api_key, event_type, payload)
            published += 1
            payment_count += int(is_payment)
            transfer_count += int(not is_payment)
            print(json.dumps({
                "status": result["status"], "topic": result["topic"],
                "event_id": result["event_id"], "published": published,
            }), flush=True)
            time.sleep(delay)
        except RuntimeError as exc:
            print(json.dumps({"status": "retrying", "error": str(exc)}), flush=True)
            time.sleep(min(5.0, max(1.0, delay)))

    print(json.dumps({
        "status": "stopped", "published": published,
        "payments": payment_count, "transfers": transfer_count,
    }), flush=True)


if __name__ == "__main__":
    run()

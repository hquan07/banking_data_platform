import json
import importlib.util
from pathlib import Path

import pandas as pd

from datasets.schema_mapping import DS1_FEATURES


REPLAY_PATH = Path(__file__).resolve().parents[2] / "kafka/producers/dataset_replay.py"
SPEC = importlib.util.spec_from_file_location("dataset_replay_under_test", REPLAY_PATH)
REPLAY_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY_MODULE)
replay = REPLAY_MODULE.replay


class FakeFuture:
    def get(self, timeout):
        return self


class FakeProducer:
    def __init__(self):
        self.messages = []

    def send(self, topic, key, value):
        self.messages.append((topic, key.decode(), json.loads(value)))
        return FakeFuture()

    def flush(self, timeout):
        return None


def _write_ds1(raw_dir):
    path = raw_dir / "creditcard"
    path.mkdir(parents=True)
    good = {"Time": 1, "Amount": 10, "Class": 0}
    good.update({name: 0 for name in DS1_FEATURES})
    bad = dict(good)
    bad["Class"] = 9
    pd.DataFrame([good, bad]).to_csv(path / "creditcard.csv", index=False)


def test_replay_publishes_valid_rows_and_routes_invalid_rows_to_dlq(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_ds1(raw_dir)
    producer = FakeProducer()

    result = replay(producer, "ds1_creditcard", raw_dir, rate=0)

    assert result == {
        "dataset_id": "ds1_creditcard",
        "start_row": 0,
        "scanned": 2,
        "published": 1,
        "rejected": 1,
    }
    assert producer.messages[0][0] == "benchmark-events"
    assert producer.messages[0][1] == "ds1_creditcard:0"
    assert producer.messages[1][0] == "benchmark-events-dlq"
    assert producer.messages[1][2]["source_row_id"] == "1"


def test_replay_honors_stable_start_row_and_limit(tmp_path):
    raw_dir = tmp_path / "raw"
    _write_ds1(raw_dir)
    producer = FakeProducer()

    result = replay(producer, "ds1_creditcard", raw_dir, rate=0, start_row=1, max_events=1)

    assert result["scanned"] == 1
    assert producer.messages[0][1] == "ds1_creditcard:1"

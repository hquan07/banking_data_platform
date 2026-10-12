#!/usr/bin/env python3
"""Rehearse an ordered, isolated restore of every durable pipeline store.

Raw backup material is kept in a process temporary directory.  Only the
sanitised manifest and report are persisted under ``.runtime/backups``.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DEFAULT_REPORT_DIR = ROOT / ".runtime/backups"
RESTORE_ORDER = (
    "kafka",
    "postgresql",
    "minio",
    "clickhouse",
    "neo4j",
    "spark-checkpoints",
    "reconciliation",
)
STORE_CHOICES = RESTORE_ORDER[:-1]
SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
APPLICATION_BUCKETS = ("banking-lake", "evidence", "checkpoints")
KAFKA_CONFIG_KEYS = (
    "cleanup.policy",
    "retention.ms",
    "min.insync.replicas",
    "max.message.bytes",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str, label: str) -> str:
    if not SAFE_NAME.fullmatch(value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


def _json_digest(value: Any) -> str:
    encoded = _canonical_json(value).encode()
    return hashlib.sha256(encoded).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: list[str],
    *,
    input_path: Path | None = None,
    input_bytes: bytes | None = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess[bytes]:
    if input_path is not None and input_bytes is not None:
        raise ValueError("Only one subprocess input source is allowed")
    stream = input_path.open("rb") if input_path else None
    try:
        result = subprocess.run(
            command,
            stdin=stream,
            input=input_bytes if stream is None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    finally:
        if stream:
            stream.close()
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"Command failed ({' '.join(command[:4])}): {detail}")
    return result


def _docker_exec(container: str, *command: str) -> list[str]:
    return ["docker", "exec", _safe_name(container, "container"), *command]


def _http_query(
    url: str,
    payload: bytes,
    *,
    user: str | None = None,
    password: str | None = None,
    content_type: str = "text/plain",
    timeout: int = 120,
) -> bytes:
    headers = {"Content-Type": content_type}
    if user is not None and password is not None:
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    request = Request(url, data=payload, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace").strip()
        raise RuntimeError(f"HTTP query failed ({exc.code}): {detail}") from exc


def _stage(name: str, operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    started = time.monotonic()
    result = operation()
    result.update(
        {
            "store": name,
            "status": "PASS",
            "duration_seconds": round(time.monotonic() - started, 3),
        }
    )
    return result


def rehearse_postgresql(temp_dir: Path, token: str) -> dict[str, Any]:
    from scripts.backup import rehearse_postgres_restore as postgres

    container = "banking_postgres"
    archive = postgres.create_backup(container, temp_dir, token)
    entries = postgres.inspect_archive(container, archive)
    database = _safe_name(f"recovery_{token.lower()}_{os.getpid()}", "database")
    source, restored = postgres.rehearse_restore(container, archive, database)
    differences = postgres.compare_counts(source, restored)
    if differences:
        raise RuntimeError(f"PostgreSQL row-count mismatch: {differences[:5]}")
    return {
        "artifact": {
            "bytes": archive.stat().st_size,
            "sha256": _sha256(archive),
            "restore_entries": entries,
        },
        "tables_checked": len(source),
        "source_rows": sum(source.values()),
        "restored_rows": sum(restored.values()),
        "temporary_database_removed": True,
    }


class ClickHouseClient:
    def __init__(self) -> None:
        self.url = os.environ.get("CLICKHOUSE_HTTP_URL", "http://127.0.0.1:8123/")
        from shared.runtime_secrets import get_secret

        self.user = os.environ.get(
            "CLICKHOUSE_BACKUP_USER", os.environ["CLICKHOUSE_USER"],
        )
        self.password = get_secret(
            "CLICKHOUSE_BACKUP_PASSWORD",
            default=get_secret("CLICKHOUSE_PASSWORD"),
            required=True,
        )

    def query(self, sql: str, data: bytes | None = None) -> bytes:
        body = sql.encode() if data is None else sql.encode() + b"\n" + data
        return _http_query(
            self.url, body, user=self.user, password=self.password, timeout=600,
        )


def _clickhouse_tables(client: ClickHouseClient, database: str) -> list[str]:
    escaped_database = database.replace("'", "''")
    sql = (
        "SELECT name FROM system.tables WHERE database = "
        f"'{escaped_database}' AND is_temporary = 0 ORDER BY name FORMAT JSONEachRow"
    )
    return [json.loads(line)["name"] for line in client.query(sql).splitlines()]


def rehearse_clickhouse(temp_dir: Path, token: str) -> dict[str, Any]:
    client = ClickHouseClient()
    source_db = _safe_name(os.environ["CLICKHOUSE_DB"], "ClickHouse database")
    configured_target = os.environ.get("CLICKHOUSE_RECOVERY_DB")
    target_db = _safe_name(
        configured_target or f"recovery_{token.lower()}_{os.getpid()}",
        "ClickHouse database",
    )
    fixed_target = configured_target is not None
    tables = _clickhouse_tables(client, source_db)
    if not tables:
        raise RuntimeError(f"ClickHouse database {source_db!r} has no tables")

    artifacts: list[dict[str, Any]] = []
    counts: dict[str, dict[str, int]] = {}
    if fixed_target:
        existing = _clickhouse_tables(client, target_db)
        if existing:
            raise RuntimeError(
                f"Dedicated ClickHouse recovery database is not empty: {existing}"
            )
    else:
        client.query(f"DROP DATABASE IF EXISTS `{target_db}` SYNC")
        client.query(f"CREATE DATABASE `{target_db}`")
    try:
        for table in tables:
            table = _safe_name(table, "ClickHouse table")
            ddl = client.query(
                f"SHOW CREATE TABLE `{source_db}`.`{table}` FORMAT TSVRaw"
            ).decode()
            qualified = re.compile(
                rf"CREATE TABLE\s+`?{re.escape(source_db)}`?\.`?{re.escape(table)}`?",
                re.IGNORECASE,
            )
            restored_ddl, replacements = qualified.subn(
                f"CREATE TABLE `{target_db}`.`{table}`", ddl, count=1,
            )
            if replacements != 1:
                raise RuntimeError(f"Could not scope ClickHouse DDL for {table}")
            client.query(restored_ddl)

            artifact = temp_dir / f"clickhouse_{table}.native"
            artifact.write_bytes(
                client.query(f"SELECT * FROM `{source_db}`.`{table}` FORMAT Native")
            )
            client.query(
                f"INSERT INTO `{target_db}`.`{table}` FORMAT Native", artifact.read_bytes(),
            )
            source_count = int(
                client.query(f"SELECT count() FROM `{source_db}`.`{table}`").decode()
            )
            restored_count = int(
                client.query(f"SELECT count() FROM `{target_db}`.`{table}`").decode()
            )
            counts[table] = {"source": source_count, "restored": restored_count}
            artifacts.append(
                {
                    "table": table,
                    "bytes": artifact.stat().st_size,
                    "sha256": _sha256(artifact),
                }
            )
        differences = {name: row for name, row in counts.items() if len(set(row.values())) > 1}
        if differences:
            raise RuntimeError(f"ClickHouse row-count mismatch: {differences}")
        return {
            "tables_checked": len(tables),
            "source_rows": sum(row["source"] for row in counts.values()),
            "restored_rows": sum(row["restored"] for row in counts.values()),
            "artifacts": artifacts,
            "temporary_database_removed": True,
        }
    finally:
        if fixed_target:
            for table in _clickhouse_tables(client, target_db):
                client.query(f"DROP TABLE IF EXISTS `{target_db}`.`{table}` SYNC")
        else:
            client.query(f"DROP DATABASE IF EXISTS `{target_db}` SYNC")


def _neo4j_commit(
    url: str,
    statement: str,
    parameters: dict[str, Any],
    *,
    user: str | None = None,
    password: str | None = None,
    timeout: int = 600,
) -> list[list[Any]]:
    payload = json.dumps(
        {"statements": [{"statement": statement, "parameters": parameters}]},
        separators=(",", ":"),
    ).encode()
    response = json.loads(
        _http_query(
            f"{url.rstrip('/')}/db/neo4j/tx/commit",
            payload,
            user=user,
            password=password,
            content_type="application/json",
            timeout=timeout,
        )
    )
    if response.get("errors"):
        raise RuntimeError(f"Neo4j query failed: {response['errors'][0].get('message')}")
    return [item["row"] for item in response["results"][0].get("data", [])]


def _batched(values: list[dict[str, Any]], size: int = 500):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def _neo4j_paged(
    url: str,
    statement: str,
    *,
    user: str | None = None,
    password: str | None = None,
    page_size: int = 5000,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    while True:
        page = _neo4j_commit(
            url,
            f"{statement} SKIP $skip LIMIT $limit",
            {"skip": len(rows), "limit": page_size},
            user=user,
            password=password,
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows


def _wait_for_neo4j(url: str, deadline_seconds: int = 90) -> None:
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        try:
            _neo4j_commit(url, "RETURN 1", {})
            return
        except (OSError, URLError, RuntimeError):
            time.sleep(1)
    raise TimeoutError("Temporary Neo4j did not become ready")


def rehearse_neo4j(temp_dir: Path, token: str) -> dict[str, Any]:
    del temp_dir  # Export is deliberately kept in memory, never under report storage.
    source_url = os.environ.get("NEO4J_HTTP_URL", "http://127.0.0.1:7474")
    source_user = os.environ["NEO4J_USER"]
    source_password = os.environ["NEO4J_PASSWORD"]
    before_counts = _neo4j_commit(
        source_url,
        "MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() "
        "RETURN nodes, count(r)",
        {}, user=source_user, password=source_password,
    )[0]
    source_nodes = _neo4j_paged(
        source_url,
        "MATCH (n) RETURN elementId(n), labels(n), properties(n) ORDER BY elementId(n)",
        user=source_user, password=source_password,
    )
    source_edges = _neo4j_paged(
        source_url,
        "MATCH (a)-[r]->(b) RETURN elementId(a), elementId(b), type(r), properties(r) "
        "ORDER BY elementId(a), elementId(r), elementId(b)",
        user=source_user, password=source_password,
    )
    after_counts = _neo4j_commit(
        source_url,
        "MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() "
        "RETURN nodes, count(r)",
        {}, user=source_user, password=source_password,
    )[0]
    if before_counts != after_counts or after_counts != [len(source_nodes), len(source_edges)]:
        raise RuntimeError(
            "Neo4j graph changed during export; quiesce graph processors and retry"
        )
    nodes = [
        {"id": row[0], "labels": row[1], "props": row[2]} for row in source_nodes
    ]
    edges = [
        {"start": row[0], "end": row[1], "type": row[2], "props": row[3]}
        for row in source_edges
    ]
    nodes.sort(key=lambda row: _canonical_json(row))
    edges.sort(key=lambda row: _canonical_json(row))
    source_digest = _json_digest({"nodes": nodes, "edges": edges})

    suffix = re.sub(r"[^a-z0-9]", "", token.lower())[-12:]
    container = _safe_name(f"recovery-neo4j-{suffix}", "temporary container")
    volume = _safe_name(f"recovery_neo4j_{suffix}", "temporary volume")
    _run(["docker", "rm", "-f", container], timeout=30) if _container_exists(container) else None
    _run(["docker", "volume", "rm", "-f", volume], timeout=30) if _volume_exists(volume) else None
    _run(["docker", "volume", "create", volume], timeout=30)
    try:
        _run(
            [
                "docker", "run", "-d", "--name", container,
                "-p", "127.0.0.1::7474", "-e", "NEO4J_AUTH=none",
                "-v", f"{volume}:/data", "neo4j:5.11",
            ],
            timeout=60,
        )
        port_output = _run(["docker", "port", container, "7474/tcp"], timeout=30)
        address = port_output.stdout.decode().strip().splitlines()[0]
        port = address.rsplit(":", 1)[1]
        target_url = f"http://127.0.0.1:{port}"
        _wait_for_neo4j(target_url)
        _neo4j_commit(
            target_url,
            "CREATE CONSTRAINT recovery_source IF NOT EXISTS "
            "FOR (n:RecoveryNode) REQUIRE n.source_id IS UNIQUE",
            {},
        )
        for batch in _batched(nodes):
            serialised = [
                {
                    "id": row["id"],
                    "labels_json": json.dumps(row["labels"], sort_keys=True),
                    "props_json": json.dumps(row["props"], sort_keys=True),
                }
                for row in batch
            ]
            _neo4j_commit(
                target_url,
                "UNWIND $rows AS row CREATE (:RecoveryNode {source_id: row.id, "
                "labels_json: row.labels_json, props_json: row.props_json})",
                {"rows": serialised},
            )
        for batch in _batched(edges):
            serialised = [
                {
                    "start": row["start"], "end": row["end"], "type": row["type"],
                    "props_json": json.dumps(row["props"], sort_keys=True),
                }
                for row in batch
            ]
            _neo4j_commit(
                target_url,
                "UNWIND $rows AS row MATCH (a:RecoveryNode {source_id: row.start}) "
                "MATCH (b:RecoveryNode {source_id: row.end}) "
                "CREATE (a)-[:RECOVERY_EDGE {source_type: row.type, "
                "props_json: row.props_json}]->(b)",
                {"rows": serialised},
            )
        restored_nodes_raw = _neo4j_paged(
            target_url,
            "MATCH (n:RecoveryNode) RETURN n.source_id, n.labels_json, n.props_json "
            "ORDER BY n.source_id",
        )
        restored_edges_raw = _neo4j_paged(
            target_url,
            "MATCH (a:RecoveryNode)-[r:RECOVERY_EDGE]->(b:RecoveryNode) "
            "RETURN a.source_id, b.source_id, r.source_type, r.props_json "
            "ORDER BY a.source_id, elementId(r), b.source_id",
        )
        restored_nodes = [
            {"id": row[0], "labels": json.loads(row[1]), "props": json.loads(row[2])}
            for row in restored_nodes_raw
        ]
        restored_edges = [
            {"start": row[0], "end": row[1], "type": row[2], "props": json.loads(row[3])}
            for row in restored_edges_raw
        ]
        restored_nodes.sort(key=lambda row: _canonical_json(row))
        restored_edges.sort(key=lambda row: _canonical_json(row))
        restored_digest = _json_digest({"nodes": restored_nodes, "edges": restored_edges})
        if source_digest != restored_digest:
            raise RuntimeError("Neo4j logical restore digest mismatch")
        return {
            "nodes": len(nodes),
            "relationships": len(edges),
            "logical_export_sha256": source_digest,
            "restored_sha256": restored_digest,
            "temporary_container_removed": True,
            "temporary_volume_removed": True,
        }
    finally:
        if _container_exists(container):
            _run(["docker", "rm", "-f", container], timeout=60)
        if _volume_exists(volume):
            _run(["docker", "volume", "rm", "-f", volume], timeout=60)


def _container_exists(name: str) -> bool:
    result = subprocess.run(
        ["docker", "container", "inspect", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    return result.returncode == 0


def _volume_exists(name: str) -> bool:
    result = subprocess.run(
        ["docker", "volume", "inspect", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    return result.returncode == 0


def _s3_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://127.0.0.1:9000"),
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        region_name="us-east-1",
    )


def _bucket_inventory(client, bucket: str) -> list[dict[str, Any]]:
    rows = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            head = client.head_object(Bucket=bucket, Key=item["Key"])
            rows.append(
                {
                    "key": item["Key"],
                    "bytes": item["Size"],
                    "etag": head["ETag"].strip('"'),
                    "content_type": head.get("ContentType"),
                    "metadata": head.get("Metadata", {}),
                }
            )
    return sorted(rows, key=lambda row: row["key"])


def rehearse_minio(temp_dir: Path, token: str) -> dict[str, Any]:
    del temp_dir
    client = _s3_client()
    available = {row["Name"] for row in client.list_buckets().get("Buckets", [])}
    missing = sorted(set(APPLICATION_BUCKETS) - available)
    if missing:
        raise RuntimeError(f"Missing MinIO buckets: {missing}")
    prefix = re.sub(r"[^a-z0-9-]", "", token.lower())[-18:]
    inventories: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(APPLICATION_BUCKETS):
        target = f"recovery-{prefix}-{index}"
        client.create_bucket(Bucket=target)
        try:
            before = _bucket_inventory(client, source)
            for item in before:
                client.copy_object(
                    Bucket=target,
                    Key=item["key"],
                    CopySource={"Bucket": source, "Key": item["key"]},
                    MetadataDirective="COPY",
                )
            after = _bucket_inventory(client, target)
            if before != after:
                raise RuntimeError(f"MinIO restore inventory mismatch for {source}")
            canary = f"recovery-canary:{token}:{source}".encode()
            canary_source = "__recovery_canary__/source"
            canary_copy = "__recovery_canary__/copy"
            client.put_object(Bucket=target, Key=canary_source, Body=canary)
            client.copy_object(
                Bucket=target,
                Key=canary_copy,
                CopySource={"Bucket": target, "Key": canary_source},
            )
            restored_canary = client.get_object(Bucket=target, Key=canary_copy)
            try:
                if restored_canary["Body"].read() != canary:
                    raise RuntimeError(f"MinIO canary copy mismatch for {source}")
            finally:
                restored_canary["Body"].close()
            inventories[source] = {
                "objects": len(before),
                "bytes": sum(item["bytes"] for item in before),
                "manifest_sha256": _json_digest(before),
            }
        finally:
            restored = _bucket_inventory(client, target)
            for offset in range(0, len(restored), 1000):
                batch = restored[offset:offset + 1000]
                if batch:
                    client.delete_objects(
                        Bucket=target,
                        Delete={"Objects": [{"Key": row["key"]} for row in batch]},
                    )
            client.delete_bucket(Bucket=target)
    return {
        "buckets": inventories,
        "objects": sum(row["objects"] for row in inventories.values()),
        "bytes": sum(row["bytes"] for row in inventories.values()),
        "temporary_buckets_removed": True,
    }


def rehearse_kafka(temp_dir: Path, token: str) -> dict[str, Any]:
    del temp_dir
    from kafka import KafkaAdminClient, KafkaConsumer
    from kafka.admin import NewTopic
    from kafka.admin.config_resource import ConfigResource, ConfigResourceType
    from kafka.structs import OffsetAndMetadata

    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9094")
    admin = KafkaAdminClient(bootstrap_servers=bootstrap, client_id="recovery-rehearsal")
    suffix = re.sub(r"[^a-z0-9]", "", token.lower())[-12:]
    temp_topics: list[str] = []
    temp_groups: list[str] = []
    topic_report: dict[str, dict[str, Any]] = {}
    try:
        topics = sorted(topic for topic in admin.list_topics() if not topic.startswith("__"))
        descriptions = {row["topic"]: row for row in admin.describe_topics(topics)}
        resources = [ConfigResource(ConfigResourceType.TOPIC, topic) for topic in topics]
        config_by_topic = _describe_kafka_configs(admin, resources)
        for index, topic in enumerate(topics):
            description = descriptions[topic]
            partitions = len(description["partitions"])
            replicas = len(description["partitions"][0]["replicas"])
            selected = {
                key: str(config_by_topic[topic][key])
                for key in KAFKA_CONFIG_KEYS
                if key in config_by_topic[topic] and config_by_topic[topic][key] is not None
            }
            target = f"recovery-{suffix}-{index}"
            admin.create_topics(
                [NewTopic(target, partitions, replicas, topic_configs=selected)],
                validate_only=False,
            )
            temp_topics.append(target)
            restored = _wait_for_kafka_topic(admin, target, partitions)
            restored_config = _describe_kafka_configs(
                admin,
                [ConfigResource(ConfigResourceType.TOPIC, target)]
            )
            restored_values = restored_config[target]
            config_diff = {
                key: {"source": value, "restored": str(restored_values[key])}
                for key, value in selected.items()
                if key not in restored_values or str(restored_values[key]) != value
            }
            if config_diff:
                raise RuntimeError(f"Kafka config restore mismatch for {topic}: {config_diff}")
            topic_report[topic] = {
                "partitions": partitions,
                "replication_factor": replicas,
                "configs": selected,
            }

        source_group_offsets: dict[str, dict[Any, OffsetAndMetadata]] = {}
        source_groups = admin.list_consumer_groups()
        for listing in source_groups:
            group_id = listing[0] if isinstance(listing, tuple) else listing.group_id
            if group_id.startswith("recovery-"):
                continue
            group_offsets: dict[Any, OffsetAndMetadata] = {}
            for partition, value in admin.list_consumer_group_offsets(group_id).items():
                if value.offset >= 0 and partition.topic in topics:
                    group_offsets[partition] = OffsetAndMetadata(value.offset, "")
            if group_offsets:
                source_group_offsets[group_id] = group_offsets

        offset_diff = []
        for index, (source_group, offsets) in enumerate(
            sorted(source_group_offsets.items())
        ):
            target_group = f"recovery-{suffix}-{index}"
            temp_groups.append(target_group)
            consumer = KafkaConsumer(
                bootstrap_servers=bootstrap,
                group_id=target_group,
                enable_auto_commit=False,
            )
            try:
                consumer.commit(offsets=offsets)
            finally:
                consumer.close()
            restored_offsets = admin.list_consumer_group_offsets(target_group)
            offset_diff.extend(
                {
                    "source_group": source_group,
                    "topic": partition.topic,
                    "partition": partition.partition,
                    "source": value.offset,
                    "restored": restored_offsets.get(partition).offset
                    if restored_offsets.get(partition) else None,
                }
                for partition, value in offsets.items()
                if restored_offsets.get(partition) is None
                or restored_offsets[partition].offset != value.offset
            )
        if offset_diff:
            raise RuntimeError(f"Kafka offset restore mismatch: {offset_diff[:5]}")
        return {
            "topics": topic_report,
            "topics_checked": len(topic_report),
            "consumer_groups_checked": len(source_group_offsets),
            "offsets_checked": sum(len(rows) for rows in source_group_offsets.values()),
            "configuration_manifest_sha256": _json_digest(topic_report),
            "temporary_topics_removed": True,
            "temporary_consumer_group_removed": True,
        }
    finally:
        if temp_topics:
            try:
                admin.delete_topics(temp_topics)
            except Exception:
                pass
        if temp_groups:
            try:
                admin.delete_consumer_groups(temp_groups)
            except Exception:
                pass
        admin.close()


def _describe_kafka_configs(admin, resources) -> dict[str, dict[str, str | None]]:
    """Normalise kafka-python-ng's protocol responses across broker versions."""
    response = admin.describe_configs(resources)
    if isinstance(response, dict):
        return {
            resource.name: {
                name: entry.value for name, entry in entries.items()
            }
            for resource, entries in response.items()
        }
    normalised: dict[str, dict[str, str | None]] = {}
    for broker_response in response:
        for resource in broker_response.resources:
            resource_name = getattr(resource, "resource_name", resource[3])
            config_entries = getattr(resource, "config_entries", resource[4])
            entries = {
                getattr(entry, "config_names", entry[0]):
                getattr(entry, "config_value", entry[1])
                for entry in config_entries
            }
            normalised[resource_name] = entries
    return normalised


def _wait_for_kafka_topic(admin, topic: str, partitions: int) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        rows = admin.describe_topics([topic])
        if rows:
            last = rows[0]
            if not last.get("error_code") and len(last.get("partitions", [])) == partitions:
                return last
        time.sleep(0.25)
    observed = len(last.get("partitions", [])) if last else None
    raise RuntimeError(
        f"Kafka partition restore mismatch for {topic}: "
        f"expected {partitions}, observed {observed}"
    )


def _volume_manifest(volume: str) -> list[str]:
    command = [
        "docker", "run", "--rm", "-v", f"{volume}:/data:ro", "busybox:1.36",
        "sh", "-c",
        "find /data -type f -exec sha256sum '{}' + | sed 's#  /data/#  #' | sort",
    ]
    output = _run(command, timeout=600).stdout.decode()
    return [line for line in output.splitlines() if line]


def rehearse_spark_checkpoints(temp_dir: Path, token: str) -> dict[str, Any]:
    source = _safe_name(
        os.environ.get(
            "SPARK_CHECKPOINT_VOLUME", "banking_data_platform_spark_checkpoints",
        ),
        "checkpoint volume",
    )
    if not _volume_exists(source):
        raise RuntimeError(f"Spark checkpoint volume does not exist: {source}")
    suffix = re.sub(r"[^a-z0-9]", "", token.lower())[-12:]
    target = _safe_name(f"recovery_spark_{suffix}", "temporary volume")
    archive = temp_dir / "spark-checkpoints.tar"
    before = _volume_manifest(source)
    _run(
        [
            "docker", "run", "--rm", "-v", f"{source}:/source:ro",
            "-v", f"{temp_dir.resolve()}:/backup", "busybox:1.36",
            "tar", "-C", "/source", "-cf", "/backup/spark-checkpoints.tar", ".",
        ],
        timeout=600,
    )
    after = _volume_manifest(source)
    if before != after:
        raise RuntimeError(
            "Spark checkpoints changed during snapshot; quiesce processors and retry"
        )
    if _volume_exists(target):
        _run(["docker", "volume", "rm", "-f", target], timeout=30)
    _run(["docker", "volume", "create", target], timeout=30)
    try:
        _run(
            [
                "docker", "run", "--rm", "-v", f"{target}:/restore",
                "-v", f"{temp_dir.resolve()}:/backup:ro", "busybox:1.36",
                "tar", "-C", "/restore", "-xf", "/backup/spark-checkpoints.tar",
            ],
            timeout=600,
        )
        restored = _volume_manifest(target)
        if before != restored:
            raise RuntimeError("Spark checkpoint restore manifest mismatch")
        return {
            "files": len(before),
            "archive_bytes": archive.stat().st_size,
            "archive_sha256": _sha256(archive),
            "manifest_sha256": _json_digest(before),
            "temporary_volume_removed": True,
        }
    finally:
        if _volume_exists(target):
            _run(["docker", "volume", "rm", "-f", target], timeout=60)


def run_reconciliation() -> dict[str, Any]:
    program = r'''
import json, os
import psycopg2
from shared.reconciliation.run import reconcile_benchmark_run
from shared.runtime_secrets import get_secret
connection = psycopg2.connect(host=os.environ["POSTGRES_HOST"], port=os.environ["POSTGRES_PORT"], dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"], password=get_secret("POSTGRES_PASSWORD", required=True))
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT run_id FROM pipeline_runs WHERE status = 'COMPLETED' AND EXISTS (SELECT 1 FROM pipeline_run_offsets o WHERE o.run_id = pipeline_runs.run_id) ORDER BY completed_at DESC NULLS LAST LIMIT 1")
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("No completed run with durable Kafka offsets is available")
    run_id = str(row[0])
    checks = reconcile_benchmark_run(connection, run_id, freshness_sla_seconds=0)
    with connection.cursor() as cursor:
        cursor.execute("SELECT store, metric, classification, expected_count, actual_count FROM pipeline_reconciliation_results WHERE run_id = %s ORDER BY store, metric", (run_id,))
        results = [{"store": r[0], "metric": r[1], "classification": r[2], "expected": r[3], "actual": r[4]} for r in cursor.fetchall()]
    print(json.dumps({"run_id": run_id, "checks": checks, "results": results}, sort_keys=True))
finally:
    connection.close()
'''
    output = _run(
        [
            "docker", "compose", "run", "--rm", "--no-deps", "--build",
            "reconciliation", "python", "-c", program,
        ],
        timeout=600,
    ).stdout.decode().strip().splitlines()
    if not output:
        raise RuntimeError("Reconciliation service produced no result")
    result = json.loads(output[-1])
    failures = [row for row in result["results"] if row["classification"] != "EXACT"]
    if failures:
        raise RuntimeError(f"Post-restore reconciliation failed: {failures[:5]}")
    return {
        "run_id": result["run_id"],
        "checks": len(result["checks"]),
        "results": result["results"],
    }


OPERATIONS: dict[str, Callable[[Path, str], dict[str, Any]]] = {
    "kafka": rehearse_kafka,
    "postgresql": rehearse_postgresql,
    "minio": rehearse_minio,
    "clickhouse": rehearse_clickhouse,
    "neo4j": rehearse_neo4j,
    "spark-checkpoints": rehearse_spark_checkpoints,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stores", nargs="+", choices=STORE_CHOICES, default=list(STORE_CHOICES),
        help="durable stores to rehearse; execution always follows restore order",
    )
    parser.add_argument("--skip-reconciliation", action="store_true")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    return parser


def main() -> int:
    from dotenv import load_dotenv

    args = build_parser().parse_args()
    load_dotenv(ROOT / ".env")
    selected = [name for name in STORE_CHOICES if name in set(args.stores)]
    run_id = uuid.uuid4().hex[:12]
    token = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + run_id[:4]
    report_dir = args.report_dir.resolve() / f"recovery_{token.lower()}"
    report_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    stages: list[dict[str, Any]] = []
    error: str | None = None
    with tempfile.TemporaryDirectory(prefix="banking-recovery-") as raw_dir:
        temporary = Path(raw_dir)
        try:
            for name in selected:
                print(f"[recovery] rehearsing {name}...", flush=True)
                stages.append(_stage(name, lambda name=name: OPERATIONS[name](temporary, token)))
            if not args.skip_reconciliation:
                print("[recovery] running post-restore reconciliation...", flush=True)
                stages.append(_stage("reconciliation", run_reconciliation))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            stages.append(
                {
                    "store": selected[len([row for row in stages if row['store'] in selected])]
                    if len([row for row in stages if row["store"] in selected]) < len(selected)
                    else "reconciliation",
                    "status": "FAIL",
                    "error": error,
                }
            )

    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": _utc_now(),
        "restore_order": list(RESTORE_ORDER),
        "selected_stores": selected,
        "raw_artifacts_persisted": False,
        "stage_manifests": stages,
    }
    report = {
        "status": "FAIL" if error else "PASS",
        "run_id": run_id,
        "created_at": _utc_now(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "report_directory": str(report_dir),
        "manifest_sha256": _json_digest(manifest),
        "stages": [
            {
                "store": row["store"],
                "status": row["status"],
                "duration_seconds": row.get("duration_seconds"),
                "error": row.get("error"),
            }
            for row in stages
        ],
    }
    (report_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (report_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if error:
        raise RuntimeError(error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

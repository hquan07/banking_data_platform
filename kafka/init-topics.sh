#!/usr/bin/env bash
set -euo pipefail

broker="banking_kafka:9092"

ensure_topic() {
  local topic="$1"
  local retention_ms="$2"
  local description

  kafka-topics.sh --bootstrap-server "$broker" --create --if-not-exists \
    --topic "$topic" --partitions 3 --replication-factor 1 \
    --config "retention.ms=$retention_ms"

  description=$(kafka-topics.sh --bootstrap-server "$broker" --describe --topic "$topic")
  if [[ "$description" != *"PartitionCount: 3"* || "$description" != *"ReplicationFactor: 1"* ]]; then
    echo "Unexpected partition/replication layout for $topic; refusing to alter it" >&2
    exit 1
  fi

  kafka-configs.sh --bootstrap-server "$broker" --entity-type topics \
    --entity-name "$topic" --alter --add-config "retention.ms=$retention_ms"
}

# Single-broker development stack: replication factor 1 is not high availability.
ensure_topic payment-events 604800000
ensure_topic payment-events-dlq 2592000000
ensure_topic payment-events-retry 604800000
ensure_topic fraud-events 2592000000
ensure_topic aml-events 2592000000
ensure_topic transfer-events 604800000
ensure_topic transfer-events-dlq 2592000000

# Pipeline degraded runbook

Use this runbook when a Prometheus alert or Platform Health reports a degraded
data path. Commands assume the repository root and the local Compose stack.
Never delete Kafka data, Spark checkpoints or database volumes as a recovery
step.

## First response

1. Record the alert name, labels, start time and current dashboard data scope.
2. Check platform readiness:

   ```bash
   curl -fsS http://127.0.0.1:8000/api/health/ready
   docker compose ps
   ```

3. Open Prometheus at `http://127.0.0.1:9090` and Grafana at
   `http://127.0.0.1:3000`. Confirm whether the signal is isolated or affects
   Kafka, Spark and storage together.
4. Do not mark data complete until consumer lag returns to zero and accepted
   events are reconciled with their serving stores.

## Spark worker or application missing

Alerts: `SparkWorkerMissing`, `SparkApplicationMissing`.

Diagnosis:

```bash
docker compose ps spark-master spark-worker payment_processor fraud_engine
docker compose logs --tail=200 spark-master spark-worker payment_processor fraud_engine
curl -fsS http://127.0.0.1:8080/json/
```

Expected state: at least one alive worker and active applications named
`PaymentStreamingProcessor` and `FraudDetectionEngine`.

Recovery:

1. Restart only the missing component. Start with the worker; restart a driver
   only if its application is absent.
2. Confirm the application registers once and does not enter a restart loop.
3. Verify Kafka consumer lag drains and Spark checkpoints continue from their
   existing locations.
4. Run the payment reconciliation command before closing the incident.

## Processor heartbeat stale or failed

Alerts: `ProcessorHeartbeatStale`, `ProcessorFailed`.

Diagnosis:

```bash
docker compose ps payment_processor fraud_engine benchmark_processor graph_processor benchmark_graph_processor
docker compose logs --tail=200 <affected-service>
```

Use `GET /api/operations/processors` with an authenticated dashboard token to
inspect heartbeat age and `last_error`. `missing` means no instance has ever
written a heartbeat; `stale` means the newest instance is older than the
configured 45-second threshold.

Recovery:

1. Check PostgreSQL connectivity and confirm `processor_heartbeats` exists.
2. Correct the dependency failure before restarting the affected service.
3. Confirm `banking_processor_up{processor="..."}` returns to `1` within one
   minute.
4. Check lag, DLQ growth and store reconciliation for the affected interval.

## Checkpoint age

Alert: `ProcessorCheckpointStale`.

1. Confirm the processor is running and consuming its assigned partitions.
2. Compare the checkpoint timestamp with Kafka lag and last successful batch.
3. Check checkpoint storage permissions and capacity.
4. Never remove a checkpoint to clear the alert. If a replacement checkpoint
   is required, stop the processor, preserve the old checkpoint and follow a
   reviewed replay plan with explicit offsets.

## Processor restart

Alert: `ProcessorRestartObserved`.

The metric counts durable processor instances, so a new instance indicates a
restart or replacement rather than an event-processing failure by itself.

1. Check the container restart count and previous logs.
2. Verify only one current instance is writing each consumer group.
3. Confirm its heartbeat is current and Kafka lag is draining.
4. Reconcile the restart window for duplicate or missing canonical events.

## Kafka consumer lag

Alert: `KafkaConsumerLagHigh`.

1. Identify the consumer group and topic in the alert labels.
2. Compare ingress rate, processor heartbeat age and Spark batch duration.
3. Confirm partitions are assigned and the processor is not restart-looping.
4. Reduce or stop an optional replay producer if it is exceeding the agreed
   processing rate. Do not reset group offsets to make lag disappear.
5. Close only after lag returns to zero or an approved steady-state threshold.

## DLQ growth

Alert: `KafkaDlqGrowth`.

1. Record the DLQ topic and offset increase.
2. Sample a bounded number of records without committing the production group.
3. Group failures by contract version and reason. Do not copy sensitive raw
   payloads into tickets or logs.
4. Fix the producer or validator first. Replay only reviewed records through
   the approved retry path with the same event identity.
5. Reconcile accepted, quarantined and replayed counts.

## Live source stalled after activity

Alert: `LiveSourceStalledAfterActivity`.

This warning fires only when the source had accepted traffic in the previous
30 minutes and then had none for five minutes. A source that has never sent an
event remains `configured · idle` and does not trigger this alert.

1. Check `http://127.0.0.1:8085/health/source` and the gateway Kafka failure
   counter.
2. Confirm source credentials and network reachability without exposing the
   source key.
3. Check Kafka broker health and ACK latency.
4. Once traffic resumes, verify the last accepted timestamp advances and
   reconcile the outage window.

## Data-integrity closure checklist

- Required services and Spark applications are ready.
- Latest processor heartbeats are current and no instance reports `failed`.
- Consumer lag has returned to zero after load stops.
- DLQ growth is explained and invalid records remain quarantined.
- PostgreSQL and ClickHouse payment IDs reconcile for the affected window.
- Any graph or benchmark-specific outputs are checked in their own namespace.
- Incident evidence records timestamps, commands used and final counts.

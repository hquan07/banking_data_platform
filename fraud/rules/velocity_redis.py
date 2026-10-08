import os

VELOCITY_SCRIPT = """
-- KEYS: event dedup marker, account sorted set; ARGV: event ID, UTC epoch ms.
-- -1 = duplicate, -2 = outside the five-minute event-time window.
if redis.call('EXISTS', KEYS[1]) == 1 then
    return -1
end
local event_ms = tonumber(ARGV[2])
local latest = redis.call('ZREVRANGE', KEYS[2], 0, 0, 'WITHSCORES')
local reference_ms = event_ms
if #latest > 0 and tonumber(latest[2]) > reference_ms then
    reference_ms = tonumber(latest[2])
end
local cutoff = reference_ms - 300000
if event_ms <= cutoff then
    redis.call('SET', KEYS[1], '1', 'EX', 604800)
    return -2
end
redis.call('ZADD', KEYS[2], 'NX', event_ms, ARGV[1])
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', cutoff)
redis.call('EXPIRE', KEYS[2], 600)
redis.call('SET', KEYS[1], '1', 'EX', 604800)
return redis.call('ZCARD', KEYS[2])
"""


def process_velocity_with_redis(df, epoch_id):
    """Count unique events in an account's five-minute event-time window."""

    def process_partition(rows):
        import redis

        client = redis.Redis(
            host=os.environ.get("REDIS_HOST", "banking_redis"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            decode_responses=True,
            socket_timeout=5,
        )
        for row in rows:
            count = client.eval(
                VELOCITY_SCRIPT,
                2,
                f"velocity:seen:{row.event_id}",
                f"velocity:{row.account_id}",
                row.event_id,
                row.event_ms,
            )
            if count > 5:
                print(f"Redis velocity threshold exceeded for {row.account_id}: {count}")

    from pyspark.sql.functions import col, unix_millis

    df.select("event_id", "account_id", unix_millis(col("event_time")).alias("event_ms")).foreachPartition(process_partition)

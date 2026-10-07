import os

VELOCITY_SCRIPT = """
if redis.call('SET', KEYS[1], '1', 'NX', 'EX', 604800) then
    local count = redis.call('HINCRBY', KEYS[2], 'count', 1)
    redis.call('HINCRBYFLOAT', KEYS[2], 'total_amount', ARGV[1])
    if redis.call('TTL', KEYS[2]) < 0 then
        redis.call('EXPIRE', KEYS[2], 300)
    end
    return count
end
return -1
"""


def process_velocity_with_redis(df, epoch_id):
    """Each event increments its account once, even if Spark retries a batch."""

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
                str(row.amount),
            )
            if count > 5:
                print(f"Redis velocity threshold exceeded for {row.account_id}: {count}")

    df.select("event_id", "account_id", "amount").foreachPartition(process_partition)

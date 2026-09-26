import json
import os
import time
import random
import uuid
import redis
from datetime import datetime, timezone
from kafka import KafkaProducer

def get_producer():
    return KafkaProducer(
        bootstrap_servers=[os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")],
        acks="all",
        retries=10,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

def simulate_payments():
    producer = get_producer()
    topic = 'payment-events'
    redis_client = redis.Redis(
        host=os.environ.get("REDIS_HOST", "banking_redis"),
        port=6379, decode_responses=True
    )
    print(f"Bắt đầu giả lập giao dịch gửi tới topic {topic}...")
    
    try:
        while True:
            # Lấy TPS từ Redis, mặc định 1 nếu không có
            tps_str = redis_client.get("mock_tps")
            tps = int(tps_str) if tps_str else 1
            if tps <= 0:
                time.sleep(1)
                continue
            
            # Tính thời gian chờ giữa mỗi transaction để rải đều trong 1 giây
            delay_per_tx = 1.0 / tps
            
            for _ in range(tps):
                start_time = time.time()
                tx = {
                    "trace_id": str(uuid.uuid4()),
                    "event_id": uuid.uuid4().hex,
                    "payment_id": f"PAY_{uuid.uuid4().hex[:12].upper()}",
                    "transaction_id": f"TX_{random.randint(10000, 99999)}",
                    "customer_id": f"CUS_{random.randint(1, 100)}",
                    "account_id": f"ACC_{random.randint(1, 100)}",
                    "merchant_id": f"MER_{random.randint(1, 500)}",
                    "amount": round(random.uniform(10.0, 50000.0), 2),
                    "currency": "USD",
                    "payment_method": random.choice(["CARD", "BANK_TRANSFER", "QR"]),
                    "channel": random.choice(["POS", "ONLINE", "ATM"]),
                    "device_id": f"DEV_{random.randint(1, 100)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "location": "VN"
                }
                producer.send(topic, tx)
                
                # Trừ hao thời gian tạo tx
                elapsed = time.time() - start_time
                sleep_time = max(0, delay_per_tx - elapsed)
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("Dừng giả lập.")
    finally:
        producer.close()

if __name__ == "__main__":
    simulate_payments()

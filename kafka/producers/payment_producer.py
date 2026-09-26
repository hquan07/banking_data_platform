import json
import os
import time
import random
import uuid
from datetime import datetime, timezone
from kafka import KafkaProducer

def get_producer():
    return KafkaProducer(
        bootstrap_servers=[os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")],
        acks="all",
        retries=10,
        enable_idempotence=True,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

def simulate_payments():
    producer = get_producer()
    topic = 'payment-events'
    print(f"Bắt đầu giả lập giao dịch gửi tới topic {topic}...")
    
    try:
        while True:
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
            print(f"Sent: {tx}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Dừng giả lập.")
    finally:
        producer.close()

if __name__ == "__main__":
    simulate_payments()

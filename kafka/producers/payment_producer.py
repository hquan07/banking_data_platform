import json
import time
import random
from kafka import KafkaProducer

def get_producer():
    return KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def simulate_payments():
    producer = get_producer()
    topic = 'payment-events'
    print(f"Bắt đầu giả lập giao dịch gửi tới topic {topic}...")
    
    try:
        while True:
            tx = {
                "transaction_id": f"TX_{random.randint(10000, 99999)}",
                "account_id": f"ACC_{random.randint(1, 100)}",
                "amount": round(random.uniform(10.0, 50000.0), 2),
                "timestamp": time.time(),
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

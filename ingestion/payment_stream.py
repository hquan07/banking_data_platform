import json
import time
import random
import uuid
import os
from datetime import datetime, timezone
from kafka import KafkaProducer
from faker import Faker
from database import get_connection
from shared.payment_contract import PAYMENT_TOPIC, SCHEMA_VERSION, normalize_payment_event

fake = Faker()

def get_accounts(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT account_id, customer_id FROM core_banking.account WHERE status = 'ACTIVE' LIMIT 1000")
        accounts = cur.fetchall()
    return accounts

def generate_payment_event(accounts):
    account = random.choice(accounts)
    account_id = account[0]
    customer_id = account[1]
    
    return normalize_payment_event({
        "schema_version": SCHEMA_VERSION,
        "event_id": uuid.uuid4().hex,
        "trace_id": str(uuid.uuid4()),
        "payment_id": f"PAY_{uuid.uuid4().hex[:12].upper()}",
        "customer_id": customer_id,
        "account_id": account_id,
        "merchant_id": f"MER_{random.randint(1, 500)}",
        "amount": round(random.uniform(5.0, 2000.0), 2),
        "currency": "USD",
        "payment_method": random.choice(["CARD", "BANK_TRANSFER", "QR"]),
        "channel": random.choice(["POS", "ONLINE", "ATM"]),
        "location": fake.city(),
        "device_id": f"DEV_{random.randint(1, 100)}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "CREATED"
    })

def run():
    print("Starting Payment Stream Simulator...")
    
    # Initialize Kafka Producer
    producer = KafkaProducer(
        bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"),
        acks="all",
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    # Get active accounts for simulation
    conn = get_connection()
    try:
        accounts = get_accounts(conn)
    finally:
        conn.close()
        
    if not accounts:
        print("No active accounts found in DB. Exiting.")
        return

    print(f"Loaded {len(accounts)} accounts. Pushing to Kafka topic 'payment-events'...")
    
    try:
        while True:
            event = generate_payment_event(accounts)
            producer.send(PAYMENT_TOPIC, key=event["payment_id"].encode("utf-8"), value=event).get(timeout=10)
            print(f"Sent: {event['payment_id']} - ${event['amount']}")
            
            # Simulate 1 to 5 events per second
            time.sleep(random.uniform(0.2, 1.0))
    except KeyboardInterrupt:
        print("Stopping simulator.")
    finally:
        producer.flush()
        producer.close()

if __name__ == "__main__":
    run()

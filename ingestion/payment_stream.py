import json
import time
import random
import uuid
from datetime import datetime
from kafka import KafkaProducer
from faker import Faker
from database import get_connection

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
    
    return {
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
        "timestamp": datetime.now().isoformat(),
        "status": "CREATED"
    }

def run():
    print("Starting Payment Stream Simulator...")
    
    # Initialize Kafka Producer
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
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
            producer.send('payment-events', value=event)
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

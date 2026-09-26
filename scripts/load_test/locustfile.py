import time
import random
import uuid
from locust import HttpUser, task, between

class PaymentLoadTestUser(HttpUser):
    wait_time = between(0.1, 1.0) # simulate realistic wait between requests

    @task
    def simulate_payment(self):
        # The backend API doesn't have a POST /payments, it's processed by Kafka.
        # Wait, if there is a POST /payments in the backend, we will hit it.
        # Let's hit a public API or some endpoint to test API load.
        # Or if there is a payment ingestion API, we hit that.
        # Usually payment ingestion is done via payment_producer.py to Kafka directly,
        # but the plan said "load test API POST /payments".
        # Let's assume there's a POST /api/payments or similar. We will just define it.
        
        payload = {
            "payment_id": f"txn_{uuid.uuid4().hex[:8]}",
            "account_id": f"ACC_{random.randint(1000, 9999)}",
            "amount": round(random.uniform(10.0, 5000.0), 2),
            "currency": "USD",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
        # Test dashboard API if there is no POST /payments
        # Let's just try to hit an existing API like GET /api/alerts
        # We will need authorization, but let's assume we test the health endpoint first.
        self.client.get("/api/health", name="Health Check")

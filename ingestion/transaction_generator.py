import random
import uuid
from faker import Faker
from database import get_connection
from psycopg2.extras import execute_values
from datetime import datetime, timedelta

fake = Faker()

def get_accounts(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT account_id, customer_id, balance FROM core_banking.account WHERE status = 'ACTIVE'")
        accounts = cur.fetchall()
    return accounts

def generate_transactions(accounts, num_transactions=5000):
    transactions = []
    if not accounts:
        print("No active accounts found!")
        return transactions

    for _ in range(num_transactions):
        account = random.choice(accounts)
        account_id = account[0]
        customer_id = account[1]
        
        transaction_type = random.choice(['DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'PAYMENT', 'FEE'])
        amount = round(random.uniform(5.0, 5000.0), 2)
        
        balance_before = float(account[2]) # Just mock, won't exactly reflect cumulative in this simple generator
        if transaction_type in ['WITHDRAWAL', 'TRANSFER', 'PAYMENT', 'FEE']:
            balance_after = balance_before - amount
        else:
            balance_after = balance_before + amount
            
        channel = random.choice(['BRANCH', 'ATM', 'MOBILE', 'INTERNET', 'POS'])
        status = random.choice(['SUCCESS'] * 9 + ['FAILED'])
        
        # Random timestamp within last 30 days
        days_ago = random.randint(0, 30)
        minutes_ago = random.randint(0, 1440)
        ts = datetime.now() - timedelta(days=days_ago, minutes=minutes_ago)
        
        transactions.append((
            f"TXN_{uuid.uuid4().hex[:12].upper()}",
            account_id,
            customer_id,
            transaction_type,
            amount,
            'USD',
            balance_before,
            balance_after,
            ts,
            channel,
            status,
            f"REF_{uuid.uuid4().hex[:8].upper()}"
        ))
    return transactions

def insert_transactions(conn, transactions):
    query = """
    INSERT INTO core_banking.transaction (
        transaction_id, account_id, customer_id, transaction_type, 
        amount, currency, balance_before, balance_after, 
        timestamp, channel, status, reference_id
    )
    VALUES %s
    ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, query, transactions)
    conn.commit()
    print(f"Inserted {len(transactions)} transactions.")

def run():
    print("Generating Transactions...")
    conn = get_connection()
    try:
        accounts = get_accounts(conn)
        transactions = generate_transactions(accounts, 5000)
        insert_transactions(conn, transactions)
    finally:
        conn.close()

if __name__ == "__main__":
    run()

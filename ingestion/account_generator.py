import random
import uuid
from faker import Faker
from database import get_connection
from psycopg2.extras import execute_values

fake = Faker()

def get_customers_and_branches(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT customer_id FROM core_banking.customer")
        customers = [row[0] for row in cur.fetchall()]
        
        cur.execute("SELECT branch_id FROM core_banking.branch")
        branches = [row[0] for row in cur.fetchall()]
        
    return customers, branches

def generate_accounts(customers, branches, num_accounts=1500):
    accounts = []
    if not customers or not branches:
        print("No customers or branches found!")
        return accounts
        
    for _ in range(num_accounts):
        account_type = random.choice(['SAVINGS', 'CHECKING', 'CURRENT', 'FIXED_DEPOSIT'])
        status = random.choice(['ACTIVE'] * 8 + ['INACTIVE', 'CLOSED'])
        balance = round(random.uniform(0, 50000), 2)
        
        accounts.append((
            f"ACC_{uuid.uuid4().hex[:10].upper()}",
            random.choice(customers),
            random.choice(branches),
            account_type,
            random.choice(['USD', 'EUR', 'VND']),
            balance,
            status
        ))
    return accounts

def generate_loans(customers, num_loans=200):
    loans = []
    if not customers:
        return loans
        
    for _ in range(num_loans):
        status = random.choice(['APPROVED', 'ACTIVE', 'PAID', 'DEFAULT', 'CLOSED'])
        principal = round(random.uniform(1000, 100000), 2)
        interest = round(random.uniform(3.0, 15.0), 2)
        term = random.choice([12, 24, 36, 48, 60])
        
        loans.append((
            f"LOAN_{uuid.uuid4().hex[:10].upper()}",
            random.choice(customers),
            f"PROD_{random.randint(1, 5)}",
            principal,
            interest,
            term,
            fake.date_this_decade(),
            fake.date_between(start_date='today', end_date='+5y'),
            status
        ))
    return loans

def insert_accounts(conn, accounts):
    query = """
    INSERT INTO core_banking.account (account_id, customer_id, branch_id, account_type, currency, balance, status)
    VALUES %s
    ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, query, accounts)
    conn.commit()
    print(f"Inserted {len(accounts)} accounts.")

def insert_loans(conn, loans):
    query = """
    INSERT INTO core_banking.loan (loan_id, customer_id, loan_product_id, principal_amount, interest_rate, term_months, start_date, maturity_date, status)
    VALUES %s
    ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, query, loans)
    conn.commit()
    print(f"Inserted {len(loans)} loans.")

def run():
    print("Generating Accounts and Loans...")
    conn = get_connection()
    try:
        customers, branches = get_customers_and_branches(conn)
        accounts = generate_accounts(customers, branches, 1500)
        loans = generate_loans(customers, 300)
        
        insert_accounts(conn, accounts)
        insert_loans(conn, loans)
    finally:
        conn.close()

if __name__ == "__main__":
    run()

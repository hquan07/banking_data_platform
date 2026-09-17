import random
import uuid
from faker import Faker
from database import get_connection
from psycopg2.extras import execute_values

fake = Faker()

def generate_branches(num_branches=50):
    branches = []
    for _ in range(num_branches):
        branches.append((
            f"BR_{uuid.uuid4().hex[:8].upper()}",
            fake.company() + " Branch",
            fake.city(),
            fake.country(),
            float(fake.latitude()),
            float(fake.longitude())
        ))
    return branches

def generate_customers(num_customers=1000):
    customers = []
    for _ in range(num_customers):
        customers.append((
            f"CUS_{uuid.uuid4().hex[:10].upper()}",
            fake.first_name(),
            fake.last_name(),
            fake.date_of_birth(minimum_age=18, maximum_age=80),
            random.choice(['MALE', 'FEMALE', 'OTHER']),
            fake.email(),
            fake.phone_number()[:20],
            fake.address().replace('\n', ', '),
            fake.country(),
            random.choice(['RETAIL'] * 9 + ['CORPORATE'])
        ))
    return customers

def insert_branches(conn, branches):
    query = """
    INSERT INTO core_banking.branch (branch_id, branch_name, city, country, latitude, longitude)
    VALUES %s
    ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, query, branches)
    conn.commit()
    print(f"Inserted {len(branches)} branches.")

def insert_customers(conn, customers):
    query = """
    INSERT INTO core_banking.customer (customer_id, first_name, last_name, date_of_birth, gender, email, phone, address, country, customer_type)
    VALUES %s
    ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, query, customers)
    conn.commit()
    print(f"Inserted {len(customers)} customers.")

def run():
    print("Generating Core Banking Data...")
    branches = generate_branches(50)
    customers = generate_customers(1000)
    
    conn = get_connection()
    try:
        insert_branches(conn, branches)
        insert_customers(conn, customers)
    finally:
        conn.close()

if __name__ == "__main__":
    run()

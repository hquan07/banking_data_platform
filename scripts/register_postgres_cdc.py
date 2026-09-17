import requests
import json
import time

DEBEZIUM_URL = "http://localhost:8083/connectors/"

CONNECTOR_CONFIG = {
    "name": "banking-postgres-connector",
    "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "tasks.max": "1",
        "database.hostname": "banking_postgres",
        "database.port": "5432",
        "database.user": "banking_user",
        "database.password": "banking_password",
        "database.dbname": "banking_data_platform",
        "database.server.name": "banking_cdc",
        "plugin.name": "pgoutput",
        "schema.include.list": "core_banking",
        "table.include.list": "core_banking.customer,core_banking.account,core_banking.transaction",
        "topic.prefix": "cdc",
        "slot.name": "debezium_slot"
    }
}

def register_connector():
    # Wait for debezium to be ready
    max_retries = 12
    for i in range(max_retries):
        try:
            response = requests.get(DEBEZIUM_URL)
            if response.status_code == 200:
                print("Debezium is up and running!")
                break
        except Exception:
            pass
        print(f"Waiting for Debezium API... ({i+1}/{max_retries})")
        time.sleep(5)
    
    # Register the connector
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    print("Registering Postgres CDC Connector...")
    
    try:
        response = requests.post(DEBEZIUM_URL, data=json.dumps(CONNECTOR_CONFIG), headers=headers)
        if response.status_code in [200, 201]:
            print("Connector registered successfully!")
            print(json.dumps(response.json(), indent=2))
        elif response.status_code == 409:
            print("Connector already exists.")
        else:
            print(f"Failed to register connector: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error registering connector: {e}")

if __name__ == "__main__":
    register_connector()

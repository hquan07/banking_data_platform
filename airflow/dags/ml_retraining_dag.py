from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import time
import random
import json
import os

default_args = {
    'owner': 'mlops',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def extract_historical_data(**kwargs):
    print("Extracting 30 days of historical data from ClickHouse / Postgres...")
    time.sleep(2)
    # Simulate extracting data
    records_extracted = random.randint(500000, 1000000)
    fraud_cases = int(records_extracted * 0.01)
    print(f"Extracted {records_extracted} transactions ({fraud_cases} labeled as fraud).")
    return {"records": records_extracted, "fraud": fraud_cases}

def train_isolation_forest(**kwargs):
    ti = kwargs['ti']
    data_stats = ti.xcom_pull(task_ids='extract_historical_data')
    print(f"Starting model training (Isolation Forest) with {data_stats['records']} records...")
    time.sleep(5) # Simulate training time
    
    # Simulate model metrics
    accuracy = random.uniform(0.92, 0.98)
    precision = random.uniform(0.85, 0.95)
    recall = random.uniform(0.70, 0.90)
    
    print(f"Training completed. Metrics: Accuracy={accuracy:.2f}, Precision={precision:.2f}, Recall={recall:.2f}")
    return {"accuracy": accuracy, "precision": precision, "recall": recall, "model_version": f"v1.0.{random.randint(10,99)}"}

def deploy_model(**kwargs):
    ti = kwargs['ti']
    metrics = ti.xcom_pull(task_ids='train_isolation_forest')
    
    print(f"Deploying model version {metrics['model_version']} to production MinIO bucket...")
    time.sleep(2)
    
    # Write a mock artifact
    os.makedirs("/opt/airflow/batch/models", exist_ok=True)
    with open(f"/opt/airflow/batch/models/model_{metrics['model_version']}.json", "w") as f:
        json.dump(metrics, f)
        
    print(f"Model deployed successfully! New model will be used by Spark Streaming jobs.")

with DAG(
    'ml_retraining_dag',
    default_args=default_args,
    description='Automated weekly AI retraining pipeline for Fraud Detection',
    schedule_interval='@weekly',
    catchup=False,
    tags=['mlops', 'fraud-detection'],
) as dag:

    t1 = PythonOperator(
        task_id='extract_historical_data',
        python_callable=extract_historical_data,
        provide_context=True
    )

    t2 = PythonOperator(
        task_id='train_isolation_forest',
        python_callable=train_isolation_forest,
        provide_context=True
    )

    t3 = PythonOperator(
        task_id='deploy_model',
        python_callable=deploy_model,
        provide_context=True
    )

    t1 >> t2 >> t3

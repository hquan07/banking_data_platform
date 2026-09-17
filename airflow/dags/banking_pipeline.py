from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'banking_core_batch_pipeline',
    default_args=default_args,
    description='Batch ETL Pipeline for Core Banking Data (Bronze to Gold)',
    schedule_interval=timedelta(days=1),
    catchup=False
)

# In a production environment, you would use SparkSubmitOperator.
# For this MVP, we use BashOperator to run the python script directly.
# Note: The Airflow container needs PySpark installed, or it should call an external Spark cluster.
run_customer_pipeline = BashOperator(
    task_id='run_customer_pipeline',
    bash_command='python /opt/airflow/batch/customer_pipeline.py',
    dag=dag,
)

run_transaction_pipeline = BashOperator(
    task_id='run_transaction_pipeline',
    bash_command='echo "Transaction pipeline would run here..."',
    dag=dag,
)

# Define task dependencies
run_customer_pipeline >> run_transaction_pipeline

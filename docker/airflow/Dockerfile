FROM apache/airflow:2.7.0-python3.11

USER airflow
RUN pip install --no-cache-dir \
    pyspark==3.5.0 \
    pandas==2.2.0 \
    pyarrow==15.0.0 \
    s3fs==2024.2.0 \
    great_expectations==0.18.8
USER airflow

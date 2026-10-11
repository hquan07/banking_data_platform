FROM python:3.12-slim

WORKDIR /workspace
ENV PYTHONPATH=/workspace

RUN pip install --no-cache-dir \
    kafka-python-ng==2.2.2 \
    psycopg2-binary==2.9.9 \
    clickhouse-driver==0.2.6 \
    python-dotenv==1.0.1

COPY scripts ./scripts
COPY shared ./shared

CMD ["python", "-m", "scripts.reconcile_payment_events"]

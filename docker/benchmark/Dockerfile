FROM python:3.12-slim

WORKDIR /workspace
ENV PYTHONPATH=/workspace
RUN pip install --no-cache-dir kafka-python-ng==2.2.2 psycopg2-binary==2.9.9
COPY kafka ./kafka
COPY fraud ./fraud
COPY shared ./shared

CMD ["python", "kafka/consumers/benchmark_processor.py"]

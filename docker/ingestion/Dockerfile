FROM python:3.12-slim

WORKDIR /workspace
ENV PYTHONPATH=/workspace
RUN pip install --no-cache-dir kafka-python-ng==2.2.2 redis==5.0.1 pandas==2.2.0
COPY kafka ./kafka
COPY shared ./shared
COPY datasets ./datasets

CMD ["python", "kafka/retry/payment_retry_worker.py"]

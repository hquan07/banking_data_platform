FROM python:3.12-slim

WORKDIR /workspace
RUN pip install --no-cache-dir kafka-python==2.0.2
COPY kafka ./kafka

CMD ["python", "kafka/producers/payment_producer.py"]

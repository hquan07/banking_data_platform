FROM python:3.12-slim

WORKDIR /workspace
ENV PYTHONPATH=/workspace
RUN pip install --no-cache-dir kafka-python-ng==2.2.2 redis==5.0.1
COPY kafka ./kafka
COPY shared ./shared

CMD ["python", "kafka/producers/payment_producer.py"]

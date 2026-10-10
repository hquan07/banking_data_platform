FROM python:3.12-slim

WORKDIR /workspace
ENV PYTHONPATH=/workspace

COPY ingestion/live_gateway/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY ingestion ./ingestion
COPY shared ./shared

CMD ["uvicorn", "ingestion.live_gateway.app:app", "--host", "0.0.0.0", "--port", "8085"]

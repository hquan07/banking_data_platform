FROM python:3.12-slim
WORKDIR /workspace
ENV PYTHONPATH=/workspace
RUN pip install --no-cache-dir kafka-python-ng==2.2.2 neo4j==5.14.1 psycopg2-binary==2.9.9
COPY aml ./aml
COPY fraud ./fraud
COPY shared ./shared
CMD ["python", "aml/graph/neo4j_pipeline.py"]

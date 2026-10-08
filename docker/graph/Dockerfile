FROM python:3.12-slim
WORKDIR /workspace
ENV PYTHONPATH=/workspace
RUN pip install --no-cache-dir kafka-python-ng==2.2.2 neo4j==5.14.1
COPY aml ./aml
COPY shared ./shared
CMD ["python", "aml/graph/neo4j_pipeline.py"]

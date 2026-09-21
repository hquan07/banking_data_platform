"""
Database connections module.
Manages connections to PostgreSQL, Neo4j, ClickHouse, Redis, and MinIO.
"""
import os
import json

# =============================================
# PostgreSQL
# =============================================
pg_conn = None
try:
    import psycopg2
    pg_conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "banking_postgres"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "banking_data_platform"),
        user=os.environ.get("POSTGRES_USER", ""),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )
    pg_conn.autocommit = True
except Exception as e:
    print(f"Postgres connection error: {e}")

# =============================================
# Neo4j
# =============================================
graph_driver = None
try:
    from neo4j import GraphDatabase
    NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j://banking_neo4j:7687")
    NEO4J_USER = os.environ.get("NEO4J_USER", "")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
    graph_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
except ImportError:
    print("neo4j module not installed")
except Exception as e:
    print(f"Neo4j connection error: {e}")

# =============================================
# ClickHouse
# =============================================
ch_client = None
try:
    from clickhouse_driver import Client
    ch_client = Client(
        host=os.environ.get("CLICKHOUSE_HOST", "banking_clickhouse"),
        port=int(os.environ.get("CLICKHOUSE_PORT", 9000)),
        user=os.environ.get("CLICKHOUSE_USER", ""),
        password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
        database=os.environ.get("CLICKHOUSE_DB", "banking_warehouse"),
    )
except Exception as e:
    print(f"ClickHouse connection error: {e}")

# =============================================
# Redis
# =============================================
redis_client = None
try:
    import redis as redis_module
    redis_client = redis_module.Redis(
        host=os.environ.get("REDIS_HOST", "banking_redis"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True,
    )
    redis_client.ping()
    print("Redis connected successfully.")
except Exception as e:
    print(f"Redis connection error: {e}")

# =============================================
# MinIO (S3-compatible)
# =============================================
EVIDENCE_BUCKET = "evidence"
_s3_client = None


def get_s3_client():
    """Lazy-initialize MinIO S3 client."""
    global _s3_client
    if _s3_client:
        return _s3_client
    try:
        import boto3
        from botocore.client import Config as BotoConfig

        _s3_client = boto3.client(
            "s3",
            endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://banking_minio:9000"),
            aws_access_key_id=os.environ.get("MINIO_ROOT_USER", ""),
            aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", ""),
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )
        try:
            _s3_client.head_bucket(Bucket=EVIDENCE_BUCKET)
        except Exception:
            _s3_client.create_bucket(Bucket=EVIDENCE_BUCKET)
        print("MinIO (S3) connected. Bucket 'evidence' ready.")
        return _s3_client
    except Exception as e:
        print(f"MinIO lazy init error: {e}")
        return None

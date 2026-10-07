"""Opt-in S3 round-trip check for the Compose MinIO service."""

import os
import uuid
from urllib.request import urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_E2E") != "1", reason="requires the running Docker Compose stack"
)


def test_evidence_bucket_round_trip_and_presigned_get():
    import boto3
    from botocore.config import Config
    from dotenv import load_dotenv

    load_dotenv()
    client = boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:9000",
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    bucket = "evidence"
    key = f"e2e/{uuid.uuid4().hex}.txt"
    payload = b"banking-data-platform-minio-e2e"

    client.head_bucket(Bucket=bucket)
    try:
        client.put_object(Bucket=bucket, Key=key, Body=payload, ContentType="text/plain")
        result = client.get_object(Bucket=bucket, Key=key)
        assert result["Body"].read() == payload

        url = client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=60
        )
        with urlopen(url, timeout=10) as response:
            assert response.read() == payload
    finally:
        client.delete_object(Bucket=bucket, Key=key)

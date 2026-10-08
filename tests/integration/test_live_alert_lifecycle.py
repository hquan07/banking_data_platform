"""Opt-in API test for case transitions, optimistic locking, search and audit."""

import json
import os
import uuid
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_E2E") != "1", reason="requires the running Docker Compose stack"
)


def test_case_lifecycle_and_stale_version():
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    suffix = uuid.uuid4().hex[:16]
    account_id = f"E2E_CASE_{suffix}"
    connection = psycopg2.connect(
        host="localhost", port=5433, dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    connection.autocommit = True
    evidence_key = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO alerts (event_id, account_id, rule_name) VALUES (%s, %s, 'E2E_CASE') "
                "RETURNING alert_id, version",
                (f"e2e-case-{suffix}", account_id),
            )
            alert_id, version = cursor.fetchone()

        login = Request(
            "http://localhost:8000/api/auth/login",
            data=urlencode({"username": "admin", "password": os.environ["DASHBOARD_ADMIN_PASSWORD"]}).encode(),
        )
        with urlopen(login, timeout=10) as response:
            token = json.load(response)["access_token"]

        def api(path, method="GET", body=None):
            request = Request(
                f"http://localhost:8000/api{path}",
                data=json.dumps(body).encode() if body is not None else None,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method=method,
            )
            with urlopen(request, timeout=10) as response:
                return json.load(response)

        search = api(f"/alerts?account_id={account_id}&limit=10")
        assert search["total"] == 1
        assert search["data"][0]["version"] == version

        changed = api(f"/alerts/{alert_id}/status", "POST", {
            "status": "INVESTIGATING", "version": version, "notes": "E2E investigation",
        })
        assert changed["version"] == version + 1
        with pytest.raises(HTTPError) as stale:
            api(f"/alerts/{alert_id}/status", "POST", {"status": "RESOLVED", "version": version})
        assert stale.value.code == 409

        resolved = api(f"/alerts/{alert_id}/status", "POST", {
            "status": "RESOLVED", "version": changed["version"],
        })
        assert resolved["version"] == version + 2
        presign = api(f"/evidence/presigned-url?alert_id={alert_id}&filename=proof-{suffix}.txt")
        evidence_key = presign["object_key"]
        assert presign["upload_url"].startswith("http://localhost:9000/")
        upload = Request(
            presign["upload_url"], data=b"e2e-evidence", method="PUT",
            headers={"Content-Type": "application/octet-stream"},
        )
        with urlopen(upload, timeout=10) as response:
            assert response.status == 200
        evidence = api(f"/alerts/{alert_id}/evidence/complete", "POST", {"object_key": evidence_key})
        assert evidence["version"] == version + 3
        repeated = api(f"/alerts/{alert_id}/evidence/complete", "POST", {"object_key": evidence_key})
        assert repeated["version"] == evidence["version"]
        history = api(f"/alerts/{alert_id}/history")
        assert [entry["new_status"] for entry in history] == ["INVESTIGATING", "RESOLVED", "RESOLVED"]
        assert history[-1]["action"] == "EVIDENCE_UPLOADED"
    finally:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM evidence_files WHERE alert_id IN "
                           "(SELECT alert_id FROM alerts WHERE event_id = %s)", (f"e2e-case-{suffix}",))
            cursor.execute("DELETE FROM alert_audit_log WHERE alert_id IN "
                           "(SELECT alert_id FROM alerts WHERE event_id = %s)", (f"e2e-case-{suffix}",))
            cursor.execute("DELETE FROM alerts WHERE event_id = %s", (f"e2e-case-{suffix}",))
        connection.close()
        if evidence_key:
            import boto3
            from botocore.config import Config

            boto3.client(
                "s3", endpoint_url="http://localhost:9000",
                aws_access_key_id=os.environ["MINIO_ROOT_USER"],
                aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            ).delete_object(Bucket="evidence", Key=evidence_key)

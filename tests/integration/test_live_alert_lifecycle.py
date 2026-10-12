"""Opt-in API test for case transitions, optimistic locking, search and audit."""

import json
import hashlib
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

        analyst_login = Request(
            "http://localhost:8000/api/auth/login",
            data=urlencode({"username": "analyst_1", "password": os.environ["DASHBOARD_ANALYST_PASSWORD"]}).encode(),
        )
        with urlopen(analyst_login, timeout=10) as response:
            analyst_token = json.load(response)["access_token"]

        def api(path, method="GET", body=None, auth_token=token):
            request = Request(
                f"http://localhost:8000/api{path}",
                data=json.dumps(body).encode() if body is not None else None,
                headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
                method=method,
            )
            with urlopen(request, timeout=10) as response:
                return json.load(response)

        search = api(f"/alerts?account_id={account_id}&limit=10")
        assert search["total"] == 1
        assert search["data"][0]["version"] == version
        assert search["data"][0]["priority"] == "P3"

        with pytest.raises(HTTPError) as outside_scope:
            api(f"/alerts/{alert_id}", auth_token=analyst_token)
        assert outside_scope.value.code == 403

        with pytest.raises(HTTPError) as invalid_due_date:
            api(f"/alerts/{alert_id}", "PATCH", {
                "version": version, "due_at": "2020-01-01T00:00:00Z",
            })
        assert invalid_due_date.value.code == 422

        case_metadata = api(f"/alerts/{alert_id}", "PATCH", {
            "version": version, "priority": "P1", "due_at": "2030-01-01T00:00:00Z",
        })
        version = case_metadata["version"]
        with pytest.raises(HTTPError) as stale_metadata:
            api(f"/alerts/{alert_id}", "PATCH", {"version": version - 1, "priority": "P2"})
        assert stale_metadata.value.code == 409

        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = 'analyst_1'")
            analyst_id = cursor.fetchone()[0]
        assigned = api(f"/alerts/{alert_id}/assignment", "POST", {
            "version": version, "assignee_id": analyst_id,
        })
        version = assigned["version"]
        with pytest.raises(HTTPError) as analyst_assignment:
            api(f"/alerts/{alert_id}/assignment", "POST", {
                "version": version, "assignee_id": analyst_id,
            }, auth_token=analyst_token)
        assert analyst_assignment.value.code == 403
        with pytest.raises(HTTPError) as analyst_export:
            api("/alerts/export", auth_token=analyst_token)
        assert analyst_export.value.code == 403
        detail = api(f"/alerts/{alert_id}", auth_token=analyst_token)
        assert detail["priority"] == "P1"
        assert detail["assignee_id"] == analyst_id

        changed = api(f"/alerts/{alert_id}/status", "POST", {
            "status": "INVESTIGATING", "version": version, "notes": "E2E investigation",
        }, auth_token=analyst_token)
        assert changed["version"] == version + 1
        version = changed["version"]
        with pytest.raises(HTTPError) as stale:
            api(f"/alerts/{alert_id}/comments", "POST", {
                "version": version - 1, "body": "stale comment",
            }, auth_token=analyst_token)
        assert stale.value.code == 409

        comment = api(f"/alerts/{alert_id}/comments", "POST", {
            "version": version, "body": "Reviewed source event and graph evidence.",
        }, auth_token=analyst_token)
        version = comment["version"]
        resolved = api(f"/alerts/{alert_id}/disposition", "POST", {
            "version": version, "disposition": "FALSE_POSITIVE",
            "resolution_code": "FALSE_POSITIVE",
        }, auth_token=analyst_token)
        version = resolved["version"]
        assert resolved["status"] == "RESOLVED"
        assert resolved["closed_by"] == analyst_id

        evidence_body = b"e2e-evidence"
        checksum = hashlib.sha256(evidence_body).hexdigest()
        presign = api(
            f"/evidence/presigned-url?{urlencode({'alert_id': alert_id, 'filename': f'proof-{suffix}.txt', 'checksum_sha256': checksum, 'content_type': 'text/plain'})}"
        )
        evidence_key = presign["object_key"]
        assert presign["upload_url"].startswith("http://localhost:9000/")
        upload = Request(
            presign["upload_url"], data=evidence_body, method="PUT",
            headers=presign["required_headers"],
        )
        with urlopen(upload, timeout=10) as response:
            assert response.status == 200
        evidence_payload = {
            "object_key": evidence_key, "version": version,
            "checksum_sha256": checksum, "content_type": "text/plain",
        }
        evidence = api(f"/alerts/{alert_id}/evidence/complete", "POST", evidence_payload)
        assert evidence["version"] == version + 1
        evidence_payload["version"] = evidence["version"]
        repeated = api(f"/alerts/{alert_id}/evidence/complete", "POST", evidence_payload)
        assert repeated["version"] == evidence["version"]
        detail = api(f"/alerts/{alert_id}")
        assert detail["comments"][0]["body"].startswith("Reviewed source event")
        assert detail["evidence"][0]["checksum_sha256"] == checksum
        assert detail["evidence"][0]["original_filename"] == f"proof-{suffix}.txt"
        assert detail["disposition"] == "FALSE_POSITIVE"
        assert detail["resolution_code"] == "FALSE_POSITIVE"
        history = api(f"/alerts/{alert_id}/history")
        assert [entry["action"] for entry in history] == [
            "CASE_METADATA_UPDATED", "CASE_ASSIGNED", "CASE_UPDATE", "COMMENT_ADDED",
            "CASE_DISPOSITION", "EVIDENCE_UPLOADED",
        ]
        assert history[-1]["action"] == "EVIDENCE_UPLOADED"
    finally:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM alert_comments WHERE alert_id IN "
                           "(SELECT alert_id FROM alerts WHERE event_id = %s)", (f"e2e-case-{suffix}",))
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

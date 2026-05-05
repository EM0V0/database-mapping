"""HTTP smoke tests verifying upload plumbing without billable completions."""

from __future__ import annotations

import io
import json


def test_health_reports_ok(flask_client):
    response = flask_client.get("/api/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"


def test_generate_sql_rejects_bad_json(flask_client):
    response = flask_client.post("/api/generate_sql", data="{not-json", content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_large_multipart_truncated_before_ai(flask_client):
    oversized = io.BytesIO(b"PK\x03\x04" + b"0" * (128 * 1024))

    targets = io.BytesIO(json.dumps({"name": "tgt", "fields": [{"name": "patient_id"}]}).encode())

    payload = flask_client.post(
        "/api/recommend",
        data={
            "source_file": (oversized, "alpha.xlsx"),
            "target_file": (targets, "target.json"),
        },
        content_type="multipart/form-data",
    )
    assert payload.status_code == 413


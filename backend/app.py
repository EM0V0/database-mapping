"""
Flask API for Visual Database Mapping (Vue SPA + intelligent mapping helpers).

Run from the backend folder: python app.py
Expose port 5000 by default — align with vue.config.js dev proxy.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import BadRequest, HTTPException, RequestEntityTooLarge

from ai_pipeline import generate_migration_sql, recommend_field_mappings, recommend_source_sheet_names
from config import get_cors_allowed_origins, get_max_upload_bytes
from validators import ValidationError, sanitize_field_mapping_payload, validate_source_catalog, validate_target_table

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent
STATIC_UPLOAD_DIR = BACKEND_ROOT / "uploads"
STATIC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = get_max_upload_bytes()

origins_config = get_cors_allowed_origins()
if origins_config == "*":
    logger.warning(
        "CORS_ALLOWED_ORIGINS=* – every browser origin may reach this API without credentialed locks. "
        "Use comma-separated HTTPS origins behind your reverse proxy in production deployments."
    )

CORS(
    app,
    resources={r"/api/*": {"origins": origins_config}},
    expose_headers=["X-Request-Id"],
)


@app.after_request
def attach_security_headers(response):
    """
    Lightweight defense-in-depth for JSON APIs without breaking dev-server proxies.

    CORP is deliberately omitted — modern SPAs hitting separate origin:port combos can fail fetch
    if `Cross-Origin-Resource-Policy` is too restrictive for your deployment footprint.
    """
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    return response


def _persist_temp(upload_file, suffix: str) -> Path:
    """Persist uploaded multipart payloads beneath backend/uploads."""
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    fd, raw_path = tempfile.mkstemp(prefix="dm_", suffix=suffix, dir=STATIC_UPLOAD_DIR)
    os.close(fd)
    upload_file.save(str(raw_path))
    return Path(raw_path)


def _assert_openxml_zip(path: Path) -> None:
    """Reject files that merely masquerade as `.xlsx` archives without the ZIP header."""
    with path.open("rb") as handle:
        signature = handle.read(4)
    if signature[:2] != b"PK":
        raise ValidationError("Spreadsheet uploads must be `.xlsx` Office Open XML (ZIP) files.")


def _load_json_part(upload_file) -> Any:
    raw = upload_file.read()
    if isinstance(raw, bytes):
        decoded = raw.decode("utf-8")
    elif isinstance(raw, str):
        decoded = raw
    else:
        raise ValidationError("JSON parts must deserialize from UTF-8 text.")
    return json.loads(decoded)


def _cleanup_path(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)  # type: ignore[arg-type]
    except OSError as exc:
        logger.warning("Temporary artefact cleanup failed (%s): %s", path, exc)


@app.errorhandler(RequestEntityTooLarge)
def payload_too_large(_):
    megabytes = max(1, app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024))
    return (
        jsonify(
            {"error": f"Request body exceeds configured MAX_CONTENT_LENGTH (~{megabytes} MB)."}
        ),
        413,
    )


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "database-mapping"})


@app.route("/api/recommend", methods=["POST"])
def recommend_source_tables_route():
    """
    Recommend Excel worksheet identifiers that correlate with target schema cues.

    Returns JSON array strings only when processing succeeds upstream.
    """
    xlsx_tmp: Path | None = None
    correlation = uuid.uuid4().hex[:12]
    response_headers = {"X-Request-Id": correlation}

    try:
        if "source_file" not in request.files or "target_file" not in request.files:
            return jsonify({"error": "Missing source_file or target_file multipart parts."}), 400

        source_blob = request.files["source_file"]
        target_blob = request.files["target_file"]

        if not getattr(source_blob, "filename", None):
            raise ValidationError("Uploaded spreadsheet must declare a concrete filename ending in `.xlsx`.")
        normalized_name = source_blob.filename.lower()
        if not normalized_name.endswith(".xlsx"):
            raise ValidationError("Source uploads currently accept `.xlsx` workbooks exclusively.")

        xlsx_tmp = _persist_temp(source_blob, ".xlsx")
        _assert_openxml_zip(xlsx_tmp)

        raw_target = _load_json_part(target_blob)
        if not isinstance(raw_target, dict):
            raise ValidationError("Target payload must deserialize to JSON object notation.")

        sanitized_target = validate_target_table(raw_target)
        sheets = recommend_source_sheet_names(str(xlsx_tmp), sanitized_target)

        outbound = jsonify(sheets)
        outbound.headers.update(response_headers)
        return outbound, 200
    except ValidationError as exc:
        logger.info("[%s] Validation rejected recommendation request: %s", correlation, exc)
        outbound = jsonify({"error": str(exc)})
        outbound.headers.update(response_headers)
        return outbound, getattr(exc, "status_code", 400)
    except HTTPException:
        raise
    except json.JSONDecodeError:
        logger.exception("[%s] Malformed JSON while parsing target workbook metadata", correlation)
        outbound = jsonify({"error": "Target workbook JSON malformed."})
        outbound.headers.update(response_headers)
        return outbound, 400
    except Exception:  # noqa: BLE001
        logger.exception("[%s] Recommendation pipeline exploded", correlation)
        outbound = jsonify(
            {
                "error": "Internal server error while deriving sheet correlation.",
                "reference": correlation,
            }
        )
        outbound.headers.update(response_headers)
        return outbound, 500
    finally:
        _cleanup_path(xlsx_tmp)


@app.route("/api/recommend_fields", methods=["POST"])
def recommend_fields_route():
    """
    Consume normalized JSON payloads describing catalogs and synthesize heuristic field alignment rows.
    """
    correlation = uuid.uuid4().hex[:12]
    response_headers = {"X-Request-Id": correlation}

    try:
        if "source_file" not in request.files or "target_file" not in request.files:
            return jsonify({"error": "Missing source_file or target_file multipart parts."}), 400

        raw_sources = _load_json_part(request.files["source_file"])
        raw_target = _load_json_part(request.files["target_file"])

        if not isinstance(raw_sources, list):
            raise ValidationError("source_file must deserialize to a JSON array of tables.")

        if not isinstance(raw_target, dict):
            raise ValidationError("target_file must deserialize to JSON object notation.")

        source_tables = validate_source_catalog(raw_sources)
        target_table = validate_target_table(raw_target)
        mappings = recommend_field_mappings(source_tables, target_table)

        outbound = jsonify(mappings)
        outbound.headers.update(response_headers)
        return outbound
    except ValidationError as exc:
        logger.info("[%s] Validation rejected field-mapping request: %s", correlation, exc)
        outbound = jsonify({"error": str(exc)})
        outbound.headers.update(response_headers)
        return outbound, getattr(exc, "status_code", 400)
    except HTTPException:
        raise
    except json.JSONDecodeError:
        logger.exception("[%s] Malformed JSON while parsing catalogs", correlation)
        outbound = jsonify({"error": "JSON payload malformed."})
        outbound.headers.update(response_headers)
        return outbound, 400
    except Exception:  # noqa: BLE001
        logger.exception("[%s] Field mapping pipeline exploded", correlation)
        outbound = jsonify(
            {
                "error": "Internal server error during mapping synthesis.",
                "reference": correlation,
            }
        )
        outbound.headers.update(response_headers)
        return outbound, 500


@app.route("/api/generate_sql", methods=["POST"])
def generate_sql_route():
    """
    Produce SQL migration sketches from sanitized mapping payloads – **always** human-review before EXEC.
    """
    correlation = uuid.uuid4().hex[:12]
    response_headers = {"X-Request-Id": correlation}

    try:
        try:
            payload = request.get_json(silent=False)
        except BadRequest as exc:
            raise ValidationError("Malformed JSON POST body.") from exc

        sanitized = sanitize_field_mapping_payload(payload)
        sql_blob = generate_migration_sql(sanitized)

        outbound = jsonify({"sql": sql_blob})
        outbound.headers.update(response_headers)
        return outbound
    except ValidationError as exc:
        logger.info("[%s] Validation rejected SQL generation: %s", correlation, exc)
        outbound = jsonify({"error": str(exc)})
        outbound.headers.update(response_headers)
        return outbound, getattr(exc, "status_code", 400)
    except Exception:  # noqa: BLE001
        logger.exception("[%s] SQL generation pipeline exploded", correlation)
        outbound = jsonify(
            {
                "error": "Internal server error while authoring SQL scaffolding.",
                "reference": correlation,
            }
        )
        outbound.headers.update(response_headers)
        return outbound, 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

"""
Input validation helpers for multipart uploads and JSON payloads exposed by the Flask API.

Defensive limits reduce memory exhaustion / JSON bomb / quadratic prompt expansion risks without
changing the authoring experience for nominal workloads.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Reasonable ergonomic defaults for spreadsheets and schema authoring UIs.
MAX_SOURCE_TABLE_COUNT = 200
MAX_FIELDS_PER_TABLE = 2_048
MAX_TARGET_FIELDS = MAX_FIELDS_PER_TABLE
MAX_MAPPING_ITEMS = 2_048
MAX_IDENTIFIER_LENGTH = 256
MAX_COMMENT_LENGTH = 16_384
MAX_TRANSFORMATION_RULE_LENGTH = 8_192

_IDENTIFIER_RE = re.compile(r"^[\w\-. ]+$", re.UNICODE)
_CONTROL_CHARS = {chr(i) for i in range(32)} | {"\ufeff"}
_PRINTABLE_WS = {"\t", "\n", "\r"}


class ValidationError(ValueError):
    """Raised when a client-sent payload violates published schema or size limits."""

    status_code = 400


def _normalize_text(value: str, *, maximum: int, allow_vertical_whitespace: bool = False) -> str:
    """Trim, reject obvious control chars, canonicalize NFC, clamp length."""
    if not isinstance(value, str):
        raise ValidationError("Text fields must be strings.")

    forbidden = _CONTROL_CHARS
    if allow_vertical_whitespace:
        forbidden = forbidden.difference(_PRINTABLE_WS)

    if any(ch in forbidden for ch in value):
        raise ValidationError("Forbidden control characters detected inside text fields.")

    trimmed = unicodedata.normalize("NFC", value).strip()
    if len(trimmed) > maximum:
        raise ValidationError(f"Strings must be shorter than or equal to {maximum} characters.")
    return trimmed


def _validate_identifier(identifier: str) -> str:
    safe = _normalize_text(identifier, maximum=MAX_IDENTIFIER_LENGTH)
    if not safe:
        raise ValidationError("Identifiers cannot be blank.")
    if not _IDENTIFIER_RE.fullmatch(safe):
        raise ValidationError(
            "Identifiers may only contain letters, numbers, spaces, hyphen, underscore, or dot."
        )
    return safe


def _sanitize_field_stub(field_stub: dict[str, Any]) -> dict[str, str]:
    if not isinstance(field_stub, dict):
        raise ValidationError("Each field must be an object with 'name'.")
    name_raw = field_stub.get("name")
    comment_raw = field_stub.get("comment", "")
    field_name = _validate_identifier(str(name_raw))
    comment_clean = ""
    if comment_raw is not None and str(comment_raw).strip():
        comment_clean = _normalize_text(
            str(comment_raw), maximum=MAX_COMMENT_LENGTH, allow_vertical_whitespace=True
        )
    return {"name": field_name, "comment": comment_clean}


def sanitize_table_descriptor(table_stub: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(table_stub, dict):
        raise ValidationError("Each source table payload must be a JSON object.")
    table_name = _validate_identifier(str(table_stub.get("name", "")))
    fields_raw = table_stub.get("fields", [])
    if not isinstance(fields_raw, list):
        raise ValidationError("Table.fields must be a JSON array.")
    if len(fields_raw) > MAX_FIELDS_PER_TABLE:
        raise ValidationError(f"Too many fields on table '{table_name}'.")

    fields: list[dict[str, str]] = []
    for field_stub in fields_raw:
        fields.append(_sanitize_field_stub(field_stub))
    return {"name": table_name, "fields": fields}


def validate_source_catalog(source_tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(source_tables) > MAX_SOURCE_TABLE_COUNT:
        raise ValidationError("Too many source tables in a single request.")
    return [sanitize_table_descriptor(table) for table in source_tables]


def validate_target_table(target_table: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(target_table, dict):
        raise ValidationError("Target table payload must be a JSON object.")
    table_name = _validate_identifier(str(target_table.get("name", "")))
    fields_raw = target_table.get("fields", [])
    if not isinstance(fields_raw, list):
        raise ValidationError("Target.fields must be a JSON array.")
    if len(fields_raw) > MAX_TARGET_FIELDS:
        raise ValidationError("Too many target fields.")

    fields: list[dict[str, str]] = []
    for field_stub in fields_raw:
        fields.append(_sanitize_field_stub(field_stub))
    return {"name": table_name, "fields": fields}


def sanitize_field_mapping_payload(payload: Any) -> list[dict[str, Any]]:
    """
    Ensure every mapping row matches UI shape and clamps transformation rules safely.
    """

    items: Any
    if isinstance(payload, dict):
        items = (
            payload.get("mappings")
            or payload.get("field_mappings")
            or payload.get("items")
            or []
        )
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValidationError("Field mapping payload must be a JSON array or mapping object.")

    if not isinstance(items, list):
        raise ValidationError("Top-level mappings collection must deserialize to list.")
    if len(items) > MAX_MAPPING_ITEMS:
        raise ValidationError("Too many field mappings.")

    sanitized: list[dict[str, Any]] = []
    for index, mapping in enumerate(items):
        try:
            source = mapping["source"]
            target = mapping["target"]
            rule = mapping.get("transformationRule") or mapping.get("transformation_rule") or ""

            sf = _validate_identifier(str(source["field"]))
            stbl = source["table"]
            tg = _validate_identifier(str(target["field"]))
            ttbl = target["table"]
            if not isinstance(stbl, dict) or not isinstance(ttbl, dict):
                raise ValidationError("Nested table metadata must be objects.")
            st_name = _validate_identifier(str(stbl.get("name", "")))
            tt_name = _validate_identifier(str(ttbl.get("name", "")))
            rule_text = ""
            if rule:
                rule_text = _normalize_text(
                    str(rule),
                    maximum=MAX_TRANSFORMATION_RULE_LENGTH,
                    allow_vertical_whitespace=True,
                )
        except (KeyError, TypeError) as exc:
            raise ValidationError(f"Mapping row #{index} is malformed.") from exc

        sanitized.append(
            {
                "source": {"field": sf, "table": {"name": st_name}},
                "target": {"field": tg, "table": {"name": tt_name}},
                "transformationRule": rule_text,
            }
        )
    return sanitized

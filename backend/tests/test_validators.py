"""Structural validation regressions unrelated to networked LLM calls."""

from __future__ import annotations

import pytest

from validators import ValidationError, sanitize_field_mapping_payload, validate_source_catalog, validate_target_table


def test_unicode_identifiers_round_trip():
    catalog = [{"name": "患者", "fields": [{"name": "主诉", "comment": "chief complaint\nnewline"}]}]
    sanitized = validate_source_catalog(catalog)
    assert sanitized[0]["name"] == "患者"
    assert sanitized[0]["fields"][0]["comment"].startswith("chief complaint")


def test_rejects_excessive_columns():
    monstrous = [{"name": "wide", "fields": [{"name": f"c{i}", "comment": ""} for i in range(4096)]}]
    with pytest.raises(ValidationError):
        validate_source_catalog(monstrous)


def test_trimmed_mappings_round_trip():
    payload = [
        {
            "source": {"field": "alpha", "table": {"name": "src"}},
            "target": {"field": "beta", "table": {"name": "tgt"}},
            "transformationRule": " trimmable ",
        }
    ]
    normalized = sanitize_field_mapping_payload(payload)
    assert normalized[0]["source"]["field"] == "alpha"
    assert normalized[0]["target"]["table"]["name"] == "tgt"


def test_field_mapping_requires_nested_shape():
    with pytest.raises(ValidationError):
        sanitize_field_mapping_payload([{"oops": True}])


def test_identifier_rejects_vertical_tab_in_column_name():
    with pytest.raises(ValidationError):
        validate_target_table({"name": "t", "fields": [{"name": "bad\vcol", "comment": ""}]})


def test_blank_table_name_detected():
    with pytest.raises(ValidationError):
        validate_source_catalog([{"name": " ", "fields": [{"name": "c1", "comment": ""}]}])

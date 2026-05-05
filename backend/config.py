"""
Application configuration loaded from environment variables.

Set OPENAI_API_KEY in backend/.env (see .env.example) before running workflows.
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

# Load backend/.env when present (cwd may be project root when running Flask).
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def get_openai_api_key() -> str:
    """Return the OpenAI (or compatible) API key."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy backend/.env.example to backend/.env and add your key."
        )
    return key


def get_openai_base_url() -> Optional[str]:
    """
    Optional custom base URL for OpenAI-compatible providers.

    Omit or leave empty for the official OpenAI API endpoint.
    """
    url = os.getenv("OPENAI_BASE_URL", "").strip()
    return url or None


def get_openai_model() -> str:
    """Chat model identifier (official or provider-specific slug)."""
    return os.getenv("OPENAI_MODEL", "gpt-4o").strip() or "gpt-4o"


def get_max_upload_bytes() -> int:
    """Upper bound for every multipart request body (Flask MAX_CONTENT_LENGTH)."""
    try:
        megabytes = int(os.getenv("MAX_UPLOAD_MB", "25"))
    except ValueError:
        megabytes = 25
    megabytes = max(1, min(megabytes, 200))
    return megabytes * 1024 * 1024


def get_cors_allowed_origins() -> list[str] | str:
    """
    Comma-separated allowlist (preferred in production). Use literal '*' only for local sandboxes.

    Empty string falls back to common Vue dev-server ports on localhost.
    """
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if raw == "*":
        return "*"
    if raw:
        return [entry.strip() for entry in raw.split(",") if entry.strip()]

    return [
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:8081",
        "http://localhost:8081",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


def get_max_llm_context_chars() -> int:
    """Hard clamp for serialized payloads passed into GPT-style prompts."""

    try:
        limit = int(os.getenv("MAX_LLM_PROMPT_CHARS", "350000"))
    except ValueError:
        limit = 350_000
    return max(10_000, min(limit, 1_500_000))


def get_llm_repair_attempts() -> int:
    """
    Parser / schema validation retries after prompting the model with concrete error feedback.

    Each pipeline (sheet picks, mappings, SQL) may perform up to this many repair rounds.
    """
    try:
        attempts = int(os.getenv("LLM_REPAIR_ATTEMPTS", "2"))
    except ValueError:
        attempts = 2
    return max(1, min(attempts, 8))


def get_llm_temperature_structure() -> float:
    """Low variance for rigid JSON artefacts (sheet ranking, mapping rows)."""
    try:
        value = float(os.getenv("LLM_TEMP_STRUCTURE", "0.12"))
    except ValueError:
        value = 0.12
    return max(0.0, min(value, 0.6))


def get_llm_temperature_sql() -> float:
    """Slightly higher variance acceptable for INSERT/SELECT composition."""
    try:
        value = float(os.getenv("LLM_TEMP_SQL", "0.22"))
    except ValueError:
        value = 0.22
    return max(0.0, min(value, 0.8))

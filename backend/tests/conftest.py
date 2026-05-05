"""
Pytest configuration for backend modules.

Inserts backend/ onto sys.path so `import app`, `validators`, etc. behave like production deploys.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture()
def flask_client(monkeypatch):
    """Tight multipart ceiling + Flask testing flag for deterministic security regressions."""

    from app import app as flask_application

    monkeypatch.setitem(flask_application.config, "MAX_CONTENT_LENGTH", 64 * 1024)
    flask_application.testing = True

    with flask_application.test_client() as client_proxy:
        yield client_proxy

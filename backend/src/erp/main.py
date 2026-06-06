"""Punto de entrada: `uvicorn erp.main:app`."""
from __future__ import annotations

from erp.infrastructure.web.app import create_app

app = create_app()

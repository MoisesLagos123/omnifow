"""Utilidades de tiempo. Toda la app usa UTC y este helper."""
from __future__ import annotations

from datetime import datetime, timezone


def datetime_utc() -> datetime:
    """Retorna el instante actual en UTC. Reemplaza el deprecado `datetime.utcnow()`."""
    return datetime.now(timezone.utc)

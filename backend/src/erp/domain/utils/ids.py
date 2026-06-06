"""Generación de UUID v7 (ordenable temporalmente)."""
from __future__ import annotations

from uuid import UUID

import uuid_utils


def new_uuid7() -> UUID:
    """Genera un UUID v7 estándar como `uuid.UUID` de stdlib."""
    return UUID(str(uuid_utils.uuid7()))

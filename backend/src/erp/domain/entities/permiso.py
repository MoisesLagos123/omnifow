"""Entidad `Permiso`. Acción atómica sobre un recurso (formato `recurso.accion`)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID

from erp.domain.exceptions import PermisoInvalidoError
from erp.domain.utils.ids import new_uuid7

# Patrón "recurso.accion" — letras minúsculas / dígitos / guion bajo a ambos lados.
_CODIGO_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


@dataclass
class Permiso:
    codigo: str
    descripcion: str | None = None
    id: UUID = field(default_factory=new_uuid7)

    def __post_init__(self) -> None:
        codigo = (self.codigo or "").strip().lower()
        if not _CODIGO_RE.match(codigo):
            raise PermisoInvalidoError(
                f"Código '{self.codigo}' inválido. Formato esperado: 'recurso.accion'"
            )
        if len(codigo) > 80:
            raise PermisoInvalidoError("El código no puede exceder 80 caracteres")
        object.__setattr__(self, "codigo", codigo)

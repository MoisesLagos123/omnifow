"""Use Case: Obtener Perfil (incluye permisos asignados)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import PerfilRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerPerfilCommand:
    contexto: ContextoSeguridad
    perfil_id: UUID


@dataclass(frozen=True)
class PermisoDTO:
    id: UUID
    codigo: str
    descripcion: str | None


@dataclass(frozen=True)
class ObtenerPerfilResult:
    id: UUID
    nombre: str
    descripcion: str | None
    activo: bool
    es_sistema: bool
    permisos: list[PermisoDTO]


class ObtenerPerfilUseCase:
    def __init__(self, *, uow: UnitOfWork, perfiles: PerfilRepository) -> None:
        self._uow = uow
        self._perfiles = perfiles

    @requires_permission("perfil.gestionar")
    def execute(self, cmd: ObtenerPerfilCommand) -> ObtenerPerfilResult:
        with self._uow:
            perfil = self._perfiles.obtener(cmd.perfil_id)
            if perfil is None:
                raise RecursoNoEncontradoError("Perfil no encontrado")
            permisos = self._perfiles.permisos_de(perfil.id)

        return ObtenerPerfilResult(
            id=perfil.id,
            nombre=perfil.nombre,
            descripcion=perfil.descripcion,
            activo=perfil.activo,
            es_sistema=perfil.es_sistema,
            permisos=[
                PermisoDTO(id=p.id, codigo=p.codigo, descripcion=p.descripcion) for p in permisos
            ],
        )

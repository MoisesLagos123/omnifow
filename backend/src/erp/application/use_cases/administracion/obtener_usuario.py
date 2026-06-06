"""Use Case: Obtener Usuario (detalle con perfiles + permisos efectivos)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.repositories import SucursalRepository, UsuarioRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import RecursoNoEncontradoError


@dataclass(frozen=True)
class ObtenerUsuarioCommand:
    contexto: ContextoSeguridad
    usuario_id: UUID


@dataclass(frozen=True)
class PerfilDTO:
    id: UUID
    nombre: str
    activo: bool


@dataclass(frozen=True)
class SucursalDeUsuarioDTO:
    id: UUID
    codigo: str
    nombre: str


@dataclass(frozen=True)
class ObtenerUsuarioResult:
    id: UUID
    rut: str
    email: str
    nombre: str
    activo: bool
    perfiles: list[PerfilDTO]
    permisos: list[str]
    sucursales: list[SucursalDeUsuarioDTO]


class ObtenerUsuarioUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        usuarios: UsuarioRepository,
        sucursales: "SucursalRepository | None" = None,
    ) -> None:
        self._uow = uow
        self._usuarios = usuarios
        self._sucursales = sucursales

    @requires_permission("usuario.gestionar")
    def execute(self, cmd: ObtenerUsuarioCommand) -> ObtenerUsuarioResult:
        with self._uow:
            usuario = self._usuarios.obtener(cmd.usuario_id)
            if usuario is None:
                raise RecursoNoEncontradoError("Usuario no encontrado")
            perfiles = self._usuarios.perfiles_de(usuario.id)
            permisos = self._usuarios.permisos_efectivos_de(usuario.id)
            sucursal_ids = self._usuarios.sucursales_de(usuario.id)
            sucursales_dto: list[SucursalDeUsuarioDTO] = []
            if sucursal_ids and self._sucursales is not None:
                entes = self._sucursales.listar_por_ids(sucursal_ids)
                entes.sort(key=lambda s: s.codigo)
                sucursales_dto = [
                    SucursalDeUsuarioDTO(id=s.id, codigo=s.codigo, nombre=s.nombre)
                    for s in entes
                ]

        return ObtenerUsuarioResult(
            id=usuario.id,
            rut=str(usuario.rut),
            email=usuario.email,
            nombre=usuario.nombre,
            activo=usuario.activo,
            perfiles=[PerfilDTO(id=p.id, nombre=p.nombre, activo=p.activo) for p in perfiles],
            permisos=permisos,
            sucursales=sucursales_dto,
        )

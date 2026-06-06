"""Use Case: Editar Perfil (nombre y/o descripcion) — sentinel UNSET para distinguir presencia."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Union
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import PerfilRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import (
    PerfilDuplicadoError,
    RecursoNoEncontradoError,
)


class _Unset:
    """Sentinel singleton para distinguir "campo no enviado" vs "enviado como null"."""

    _inst: "_Unset | None" = None

    def __new__(cls) -> "_Unset":
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Final[_Unset] = _Unset()

# Tipos pseudo-Option para los campos opcionalmente presentes.
OptStr = Union[str, None, _Unset]


@dataclass(frozen=True)
class EditarPerfilCommand:
    contexto: ContextoSeguridad
    perfil_id: UUID
    # `UNSET` = no enviado (no tocar); `None` = enviado explícitamente como null (borrar);
    # `str` = nuevo valor.
    nombre: OptStr = UNSET
    descripcion: OptStr = UNSET


@dataclass(frozen=True)
class EditarPerfilResult:
    id: UUID
    nombre: str
    descripcion: str | None
    activo: bool


class EditarPerfilUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        perfiles: PerfilRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._perfiles = perfiles
        self._audit = audit
        self._clock = clock

    @requires_permission("perfil.gestionar")
    def execute(self, cmd: EditarPerfilCommand) -> EditarPerfilResult:
        ahora = self._clock.now()
        with self._uow:
            perfil = self._perfiles.obtener(cmd.perfil_id)
            if perfil is None:
                raise RecursoNoEncontradoError("Perfil no encontrado")

            before = {"nombre": perfil.nombre, "descripcion": perfil.descripcion}

            if not isinstance(cmd.nombre, _Unset):
                nuevo_nombre = cmd.nombre
                if nuevo_nombre is None:
                    # nombre obligatorio: la entidad valida y lanza PerfilInvalidoError.
                    perfil.renombrar("", ahora)  # forzará error
                elif nuevo_nombre.strip().lower() != perfil.nombre.lower():
                    duplicado = self._perfiles.obtener_por_nombre(nuevo_nombre)
                    if duplicado is not None and duplicado.id != perfil.id:
                        raise PerfilDuplicadoError()
                    perfil.renombrar(nuevo_nombre, ahora)

            if not isinstance(cmd.descripcion, _Unset):
                perfil.actualizar_descripcion(cmd.descripcion, ahora)

            self._perfiles.guardar(perfil)

            self._audit.publicar(
                accion="perfil.editar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Perfil",
                recurso_id=perfil.id,
                before=before,
                after={"nombre": perfil.nombre, "descripcion": perfil.descripcion},
            )

            self._uow.commit()

        return EditarPerfilResult(
            id=perfil.id,
            nombre=perfil.nombre,
            descripcion=perfil.descripcion,
            activo=perfil.activo,
        )

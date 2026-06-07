"""Use Case: Crear Perfil (opcionalmente con permisos en una sola transacción)."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import PerfilRepository, PermisoRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.perfil import Perfil
from erp.domain.entities.permiso import Permiso
from erp.domain.exceptions import PerfilDuplicadoError, PermisoNoExisteError


@dataclass(frozen=True)
class CrearPerfilCommand:
    contexto: ContextoSeguridad
    nombre: str
    descripcion: str | None = None
    # `None` = sin asignación; lista (puede ser vacía) = reemplazo del set completo.
    permiso_ids: list[UUID] | None = None


@dataclass(frozen=True)
class PermisoAsignadoDTO:
    id: UUID
    codigo: str
    descripcion: str | None


@dataclass(frozen=True)
class CrearPerfilResult:
    id: UUID
    nombre: str
    descripcion: str | None
    activo: bool
    es_sistema: bool = False
    permisos: list[PermisoAsignadoDTO] = field(default_factory=list)


class CrearPerfilUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        perfiles: PerfilRepository,
        audit: AuditPublisher,
        clock: Clock,
        permisos: PermisoRepository | None = None,
    ) -> None:
        self._uow = uow
        self._perfiles = perfiles
        self._audit = audit
        self._clock = clock
        self._permisos = permisos

    @requires_permission("perfil.gestionar")
    def execute(self, cmd: CrearPerfilCommand) -> CrearPerfilResult:
        with self._uow:
            existente = self._perfiles.obtener_por_nombre(cmd.nombre)
            if existente is not None:
                raise PerfilDuplicadoError()

            perfil = Perfil(nombre=cmd.nombre, descripcion=cmd.descripcion)
            self._perfiles.guardar(perfil)

            permisos_asignados: list[Permiso] = []
            if cmd.permiso_ids is not None:
                if self._permisos is None:
                    # Configuración inválida del use case si se piden permisos pero no se inyectó el repo.
                    raise PermisoNoExisteError(
                        "No se puede asignar permisos: repositorio de permisos no disponible"
                    )
                ids_unicos = list({pid for pid in cmd.permiso_ids})
                if ids_unicos:
                    existentes = self._permisos.listar_por_ids(ids_unicos)
                    encontrados_ids = {p.id for p in existentes}
                    faltantes = [pid for pid in ids_unicos if pid not in encontrados_ids]
                    if faltantes:
                        raise PermisoNoExisteError(
                            "Uno o más permisos no existen",
                            details={
                                "permiso_ids_invalidos": [str(pid) for pid in faltantes]
                            },
                        )
                    permisos_asignados = existentes
                # Asigna (vacío = ningún permiso explícitamente).
                self._perfiles.asignar_permisos(perfil.id, ids_unicos)

            self._audit.publicar(
                accion="perfil.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Perfil",
                recurso_id=perfil.id,
                before=None,
                after={
                    "id": str(perfil.id),
                    "nombre": perfil.nombre,
                    "descripcion": perfil.descripcion,
                    "activo": perfil.activo,
                    "permisos": sorted(p.codigo for p in permisos_asignados),
                },
            )

            self._uow.commit()

        return CrearPerfilResult(
            id=perfil.id,
            nombre=perfil.nombre,
            descripcion=perfil.descripcion,
            activo=perfil.activo,
            es_sistema=perfil.es_sistema,
            permisos=[
                PermisoAsignadoDTO(id=p.id, codigo=p.codigo, descripcion=p.descripcion)
                for p in sorted(permisos_asignados, key=lambda p: p.codigo)
            ],
        )

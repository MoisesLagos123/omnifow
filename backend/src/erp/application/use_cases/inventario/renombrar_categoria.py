"""Use Case: Renombrar Categoría."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import CategoriaRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import (
    CategoriaDuplicadaError,
    RecursoNoEncontradoError,
)


@dataclass(frozen=True)
class RenombrarCategoriaCommand:
    contexto: ContextoSeguridad
    categoria_id: UUID
    nuevo_nombre: str


@dataclass(frozen=True)
class RenombrarCategoriaResult:
    id: UUID
    nombre: str


class RenombrarCategoriaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        categorias: CategoriaRepository,
        audit: AuditPublisher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._categorias = categorias
        self._audit = audit
        self._clock = clock

    @requires_permission("producto.gestionar")
    def execute(self, cmd: RenombrarCategoriaCommand) -> RenombrarCategoriaResult:
        ahora = self._clock.now()
        with self._uow:
            categoria = self._categorias.obtener(cmd.categoria_id)
            if categoria is None:
                raise RecursoNoEncontradoError("Categoría no encontrada")
            before = {"nombre": categoria.nombre}
            otra = self._categorias.obtener_por_nombre(cmd.nuevo_nombre)
            if otra is not None and otra.id != categoria.id:
                raise CategoriaDuplicadaError()
            categoria.renombrar(cmd.nuevo_nombre, ahora)
            self._categorias.guardar(categoria)
            self._audit.publicar(
                accion="categoria.renombrar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Categoria",
                recurso_id=categoria.id,
                before=before,
                after={"nombre": categoria.nombre},
            )
            self._uow.commit()
        return RenombrarCategoriaResult(id=categoria.id, nombre=categoria.nombre)

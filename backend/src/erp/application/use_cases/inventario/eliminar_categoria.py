"""Use Case: Eliminar Categoría (hard delete, solo si no está en uso)."""
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
    CategoriaEnUsoError,
    RecursoNoEncontradoError,
)


@dataclass(frozen=True)
class EliminarCategoriaCommand:
    contexto: ContextoSeguridad
    categoria_id: UUID


@dataclass(frozen=True)
class EliminarCategoriaResult:
    id: UUID


class EliminarCategoriaUseCase:
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
    def execute(self, cmd: EliminarCategoriaCommand) -> EliminarCategoriaResult:
        with self._uow:
            categoria = self._categorias.obtener(cmd.categoria_id)
            if categoria is None:
                raise RecursoNoEncontradoError("Categoría no encontrada")
            cantidad = self._categorias.cantidad_productos(categoria.id)
            if cantidad > 0:
                raise CategoriaEnUsoError(details={"productos": cantidad})
            before = {"id": str(categoria.id), "nombre": categoria.nombre}
            self._categorias.eliminar(categoria.id)
            self._audit.publicar(
                accion="categoria.eliminar",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Categoria",
                recurso_id=categoria.id,
                before=before,
                after=None,
            )
            self._uow.commit()
        return EliminarCategoriaResult(id=cmd.categoria_id)

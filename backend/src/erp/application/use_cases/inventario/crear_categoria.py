"""Use Case: Crear Categoría."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.adapters.security.rbac_decorator import requires_permission
from erp.application.ports.audit_publisher import AuditPublisher
from erp.application.ports.clock import Clock
from erp.application.ports.repositories import CategoriaRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.categoria import Categoria
from erp.domain.exceptions import CategoriaDuplicadaError


@dataclass(frozen=True)
class CrearCategoriaCommand:
    contexto: ContextoSeguridad
    nombre: str


@dataclass(frozen=True)
class CrearCategoriaResult:
    id: UUID
    nombre: str


class CrearCategoriaUseCase:
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
    def execute(self, cmd: CrearCategoriaCommand) -> CrearCategoriaResult:
        with self._uow:
            existente = self._categorias.obtener_por_nombre(cmd.nombre)
            if existente is not None:
                raise CategoriaDuplicadaError()
            categoria = Categoria(nombre=cmd.nombre)
            self._categorias.guardar(categoria)
            self._audit.publicar(
                accion="categoria.crear",
                resultado="OK",
                usuario_id=cmd.contexto.usuario_id,
                ip=cmd.contexto.ip,
                user_agent=cmd.contexto.user_agent,
                recurso_tipo="Categoria",
                recurso_id=categoria.id,
                before=None,
                after={"id": str(categoria.id), "nombre": categoria.nombre},
            )
            self._uow.commit()
        return CrearCategoriaResult(id=categoria.id, nombre=categoria.nombre)

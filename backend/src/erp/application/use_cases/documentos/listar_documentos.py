"""Use Case: Listar documentos tributarios (paginado con filtros)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from erp.application.ports.repositories import (
    DocumentoTributarioRepository,
    DocumentosPagina,
)
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import PermisoDenegadoError


@dataclass(frozen=True)
class ListarDocumentosQuery:
    contexto: ContextoSeguridad
    sucursal_id: UUID | None = None
    tipo: str | None = None            # BOLETA|FACTURA|NC|ND|GUIA
    estado_sii: str | None = None      # PENDIENTE|ACEPTADO|RECHAZADO|ANULADO
    folio: int | None = None           # búsqueda exacta
    rut_receptor: str | None = None    # búsqueda exacta normalizada
    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None
    q: str | None = None               # busca en razón social o folio como string
    page: int = 1
    page_size: int = 25


class ListarDocumentosUseCase:
    """Lista documentos tributarios con filtros y paginación.

    Filtra automáticamente por las sucursales donde el usuario puede operar
    (respeta `contexto.sucursales_permitidas`). Si no hay restricción, devuelve
    de todas las sucursales (filtradas adicionalmente por `sucursal_id` si se
    indica).
    """

    def __init__(
        self,
        *,
        uow: UnitOfWork,
        documentos: DocumentoTributarioRepository,
    ) -> None:
        self._uow = uow
        self._documentos = documentos

    def execute(self, query: ListarDocumentosQuery) -> DocumentosPagina:
        ctx = query.contexto
        if not ctx.tiene_permiso("documento.consultar"):
            raise PermisoDenegadoError(
                "Falta permiso 'documento.consultar'",
                details={"codigo_requerido": "documento.consultar"},
            )
        with self._uow:
            pagina = self._documentos.listar(
                sucursal_id=query.sucursal_id,
                tipo=query.tipo,
                estado_sii=query.estado_sii,
                folio=query.folio,
                rut_receptor=query.rut_receptor,
                fecha_desde=query.fecha_desde,
                fecha_hasta=query.fecha_hasta,
                q=query.q,
                page=query.page,
                page_size=query.page_size,
                sucursales_permitidas=ctx.sucursales_permitidas,
            )
        return pagina  # DocumentosPagina

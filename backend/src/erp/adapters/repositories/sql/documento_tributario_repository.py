"""Repositorio SQL de DocumentoTributario."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.db.mappers.documento_tributario import to_domain, to_orm
from erp.infrastructure.db.models.documento_tributario import DocumentoTributarioORM


class SqlDocumentoTributarioRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, documento: DocumentoTributario) -> None:
        existente = self._uow.session.get(DocumentoTributarioORM, documento.id)
        if existente is None:
            self._uow.session.add(to_orm(documento))
            return
        existente.estado_sii = documento.estado_sii.value
        existente.documento_referencia_id = documento.documento_referencia_id

    def obtener(self, documento_id: UUID) -> DocumentoTributario | None:
        orm = self._uow.session.get(DocumentoTributarioORM, documento_id)
        return to_domain(orm) if orm is not None else None

    def obtener_por_folio(
        self, sucursal_id: UUID, tipo: TipoDocumento, folio: int
    ) -> DocumentoTributario | None:
        stmt = select(DocumentoTributarioORM).where(
            DocumentoTributarioORM.sucursal_id == sucursal_id,
            DocumentoTributarioORM.tipo == tipo.value,
            DocumentoTributarioORM.folio == folio,
        )
        orm = self._uow.session.execute(stmt).scalar_one_or_none()
        return to_domain(orm) if orm is not None else None

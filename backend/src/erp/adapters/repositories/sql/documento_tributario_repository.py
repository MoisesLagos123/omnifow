"""Repositorio SQL de DocumentoTributario."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import DocumentoListItem, DocumentosPagina
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.db.mappers.documento_tributario import to_domain, to_orm
from erp.infrastructure.db.models.documento_tributario import DocumentoTributarioORM
from erp.infrastructure.db.models.sucursal import SucursalORM


class SqlDocumentoTributarioRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, documento: DocumentoTributario) -> None:
        existente = self._uow.session.get(DocumentoTributarioORM, documento.id)
        if existente is None:
            self._uow.session.add(to_orm(documento))
            # Flush inmediato: garantiza que el INSERT en
            # documentos_tributarios viaje a la DB AHORA, antes de que
            # cualquier otra entidad que tenga FK hacia este documento
            # (ej. Devolucion.nc_documento_id, Venta.documento_tributario_id)
            # haga su propio flush y SQLAlchemy intente insertarla primero.
            # Sin este flush, el orden de inserts en el flush global del
            # UoW puede romper la FK (caso real: anular venta).
            self._uow.session.flush()
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

    def obtener_nombre_sucursal(self, sucursal_id: UUID) -> str:
        row = self._uow.session.execute(
            select(SucursalORM.nombre).where(SucursalORM.id == sucursal_id)
        ).scalar_one_or_none()
        return row if row is not None else ""

    def listar(
        self,
        *,
        sucursal_id: UUID | None = None,
        tipo: str | None = None,
        estado_sii: str | None = None,
        folio: int | None = None,
        rut_receptor: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sucursales_permitidas: frozenset[UUID] = frozenset(),
    ) -> DocumentosPagina:
        base = (
            select(
                DocumentoTributarioORM,
                SucursalORM.nombre.label("sucursal_nombre"),
            )
            .join(SucursalORM, SucursalORM.id == DocumentoTributarioORM.sucursal_id)
        )
        count_base = select(func.count()).select_from(DocumentoTributarioORM)

        # Filtro de sucursales permitidas (seguridad)
        if sucursales_permitidas:
            base = base.where(
                DocumentoTributarioORM.sucursal_id.in_(sucursales_permitidas)
            )
            count_base = count_base.where(
                DocumentoTributarioORM.sucursal_id.in_(sucursales_permitidas)
            )

        if sucursal_id is not None:
            base = base.where(DocumentoTributarioORM.sucursal_id == sucursal_id)
            count_base = count_base.where(
                DocumentoTributarioORM.sucursal_id == sucursal_id
            )
        if tipo is not None:
            base = base.where(DocumentoTributarioORM.tipo == tipo)
            count_base = count_base.where(DocumentoTributarioORM.tipo == tipo)
        if estado_sii is not None:
            base = base.where(DocumentoTributarioORM.estado_sii == estado_sii)
            count_base = count_base.where(
                DocumentoTributarioORM.estado_sii == estado_sii
            )
        if folio is not None:
            base = base.where(DocumentoTributarioORM.folio == folio)
            count_base = count_base.where(DocumentoTributarioORM.folio == folio)
        if rut_receptor is not None:
            base = base.where(
                DocumentoTributarioORM.rut_receptor == rut_receptor.strip()
            )
            count_base = count_base.where(
                DocumentoTributarioORM.rut_receptor == rut_receptor.strip()
            )
        if fecha_desde is not None:
            base = base.where(DocumentoTributarioORM.emitido_en >= fecha_desde)
            count_base = count_base.where(
                DocumentoTributarioORM.emitido_en >= fecha_desde
            )
        if fecha_hasta is not None:
            base = base.where(DocumentoTributarioORM.emitido_en <= fecha_hasta)
            count_base = count_base.where(
                DocumentoTributarioORM.emitido_en <= fecha_hasta
            )
        if q:
            q_lower = q.lower().strip()
            q_like = f"%{q_lower}%"
            folio_q: int | None = None
            try:
                folio_q = int(q_lower)
            except ValueError:
                pass

            if folio_q is not None:
                _q_cond = or_(
                    DocumentoTributarioORM.folio == folio_q,
                    func.lower(
                        DocumentoTributarioORM.razon_social_receptor
                    ).like(q_like),
                )
                base = base.where(_q_cond)
                count_base = count_base.where(_q_cond)
            else:
                base = base.where(
                    func.lower(
                        DocumentoTributarioORM.razon_social_receptor
                    ).like(q_like)
                )
                count_base = count_base.where(
                    func.lower(
                        DocumentoTributarioORM.razon_social_receptor
                    ).like(q_like)
                )

        total = int(self._uow.session.execute(count_base).scalar_one())

        offset = (page - 1) * page_size
        rows = self._uow.session.execute(
            base.order_by(
                DocumentoTributarioORM.emitido_en.desc(),
                DocumentoTributarioORM.folio.desc(),
            )
            .limit(page_size)
            .offset(offset)
        ).all()

        items: list[DocumentoListItem] = []
        for doc_orm, suc_nombre in rows:
            items.append(
                DocumentoListItem(
                    id=doc_orm.id,
                    tipo=doc_orm.tipo,
                    folio=doc_orm.folio,
                    sucursal_id=doc_orm.sucursal_id,
                    sucursal_nombre=suc_nombre,
                    rut_receptor=doc_orm.rut_receptor,
                    razon_social_receptor=doc_orm.razon_social_receptor,
                    total_clp=doc_orm.total_clp,
                    estado_sii=doc_orm.estado_sii,
                    emitido_en=doc_orm.emitido_en,
                )
            )

        return DocumentosPagina(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

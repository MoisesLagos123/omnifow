"""Repositorio SQL para `notas_debito_meta`."""
from __future__ import annotations

from uuid import UUID

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.infrastructure.db.models.nota_debito_meta import NotaDebitoMetaORM


class SqlNotaDebitoMetaRepository:
    """Persiste y recupera la metadata de Notas de Débito."""

    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, documento_id: UUID, motivo: str) -> None:
        existente = self._uow.session.get(NotaDebitoMetaORM, documento_id)
        if existente is None:
            self._uow.session.add(
                NotaDebitoMetaORM(documento_id=documento_id, motivo=motivo)
            )
        else:
            existente.motivo = motivo

    def obtener_motivo(self, documento_id: UUID) -> str | None:
        orm = self._uow.session.get(NotaDebitoMetaORM, documento_id)
        return orm.motivo if orm is not None else None

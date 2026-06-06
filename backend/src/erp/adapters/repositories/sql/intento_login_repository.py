"""Repositorio SQL de IntentoLogin."""
from __future__ import annotations

from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.application.ports.repositories import IntentoLogin
from erp.infrastructure.db.models.intento_login import IntentoLoginORM


class SqlIntentoLoginRepository:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def guardar(self, intento: IntentoLogin) -> None:
        self._uow.session.add(
            IntentoLoginORM(
                email=intento.email,
                ip=intento.ip,
                ts=intento.ts,
                exitoso=intento.exitoso,
                user_agent=intento.user_agent,
            )
        )

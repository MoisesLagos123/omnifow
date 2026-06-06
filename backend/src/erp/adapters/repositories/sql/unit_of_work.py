"""UnitOfWork SQLAlchemy. Una sesión por scope."""
from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork no inicializado (use el context manager)")
        return self._session

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        try:
            if exc is not None:
                self.rollback()
        finally:
            if self._session is not None:
                self._session.close()
                self._session = None
        return None  # no suprime excepciones

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

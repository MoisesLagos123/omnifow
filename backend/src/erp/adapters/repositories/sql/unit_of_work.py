"""UnitOfWork SQLAlchemy.

Una sesión por scope con soporte de **re-entry anidado**: si un use case
abre el UoW y luego delega a otro use case que también lo abre, ambos
comparten la misma `Session`. Sólo el `__exit__` más externo cierra
realmente la sesión.

Esto permite componer use cases sin tener que reorganizar la lógica:
   with uow:                              # depth=1
       repo.obtener(...)
       otro_use_case.execute(...)         # internamente hace `with self._uow:` (depth=2)
       # al salir del delegado depth=1, la sesión NO se cierra
   # acá depth=0 → sesión cerrada
"""
from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        # Contador de re-entries: 0 = cerrado; >=1 = abierto, comparte sesión.
        self._depth = 0

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork no inicializado (use el context manager)")
        return self._session

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        if self._depth == 0:
            # Primera entrada: crea la sesión.
            self._session = self._session_factory()
        self._depth += 1
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        self._depth -= 1
        try:
            # Si hubo excepción en CUALQUIER nivel, hacemos rollback inmediato
            # — pero no cerramos hasta llegar al nivel 0 para evitar romper
            # frames superiores que aún esperan tener la sesión válida.
            if exc is not None and self._session is not None:
                # Sólo si la sesión sigue activa; si ya rolleó por una excepción
                # anidada anterior, el segundo rollback es no-op seguro.
                self.rollback()
        finally:
            # Cierre real sólo en el nivel más externo.
            if self._depth == 0 and self._session is not None:
                self._session.close()
                self._session = None
        return None  # no suprime excepciones

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

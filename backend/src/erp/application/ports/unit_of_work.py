"""Puerto Unit of Work — atomicidad por caso de uso."""
from __future__ import annotations

from types import TracebackType
from typing import Protocol


class UnitOfWork(Protocol):
    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...

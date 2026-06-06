"""Use Case: Listar Clientes (permiso `cliente.consultar` O `cliente.gestionar`)."""
from __future__ import annotations

from dataclasses import dataclass

from erp.application.ports.repositories import ClienteRepository, ClientesPagina
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import PermisoDenegadoError

_PERMISOS_LECTURA = ("cliente.consultar", "cliente.gestionar")


@dataclass(frozen=True)
class ListarClientesCommand:
    contexto: ContextoSeguridad
    q: str | None = None
    activo: bool | None = None
    limit: int = 50
    offset: int = 0


class ListarClientesUseCase:
    def __init__(
        self, *, uow: UnitOfWork, clientes: ClienteRepository
    ) -> None:
        self._uow = uow
        self._clientes = clientes

    def execute(self, cmd: ListarClientesCommand) -> ClientesPagina:
        if not any(cmd.contexto.tiene_permiso(p) for p in _PERMISOS_LECTURA):
            raise PermisoDenegadoError(
                "Falta permiso requerido: cliente.consultar o cliente.gestionar",
                details={"codigos_requeridos": list(_PERMISOS_LECTURA)},
            )
        with self._uow:
            return self._clientes.listar(
                q=cmd.q,
                activo=cmd.activo,
                limit=cmd.limit,
                offset=cmd.offset,
            )

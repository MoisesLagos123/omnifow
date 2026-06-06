"""Use Case: Obtener Cliente (permiso `cliente.consultar` O `cliente.gestionar`).

TODO: cuando exista el módulo Cuentas por Cobrar, enriquecer este resultado con
el saldo y el estado de cuenta del cliente (consulta de saldo / CxC).
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from erp.application.ports.repositories import ClienteRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.application.security.contexto import ContextoSeguridad
from erp.domain.entities.cliente import Cliente
from erp.domain.exceptions import PermisoDenegadoError, RecursoNoEncontradoError

_PERMISOS_LECTURA = ("cliente.consultar", "cliente.gestionar")


@dataclass(frozen=True)
class ObtenerClienteCommand:
    contexto: ContextoSeguridad
    cliente_id: UUID


@dataclass(frozen=True)
class ObtenerClienteResult:
    cliente: Cliente


class ObtenerClienteUseCase:
    def __init__(
        self, *, uow: UnitOfWork, clientes: ClienteRepository
    ) -> None:
        self._uow = uow
        self._clientes = clientes

    def execute(self, cmd: ObtenerClienteCommand) -> ObtenerClienteResult:
        if not any(cmd.contexto.tiene_permiso(p) for p in _PERMISOS_LECTURA):
            raise PermisoDenegadoError(
                "Falta permiso requerido: cliente.consultar o cliente.gestionar",
                details={"codigos_requeridos": list(_PERMISOS_LECTURA)},
            )
        with self._uow:
            cliente = self._clientes.obtener(cmd.cliente_id)
            if cliente is None:
                raise RecursoNoEncontradoError("Cliente no encontrado")
            return ObtenerClienteResult(cliente=cliente)

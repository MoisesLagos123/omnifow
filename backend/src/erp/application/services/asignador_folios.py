"""Domain service `AsignadorFolios`: reserva folios SII de forma atómica.

Decisiones (§0 CLAUDE.md, §9.2 arquitectura.html):
- Lock pesimista (`SELECT ... FOR UPDATE`) sobre la fila del `RangoFolios`
  activo correspondiente a `(sucursal, tipo_documento)`.
- Si no hay rango activo o está agotado → `RangoFoliosAgotadoError`.
- Debe ejecutarse dentro de un `UnitOfWork` ya abierto por el use case que
  emite el documento (`ProcesarVentaUseCase`, `EmitirNotaCreditoUseCase`,
  etc., aún por implementar).
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from erp.application.ports.repositories import RangoFoliosRepository
from erp.application.ports.unit_of_work import UnitOfWork
from erp.domain.exceptions import RangoFoliosAgotadoError
from erp.domain.value_objects.folio import Folio
from erp.domain.value_objects.tipo_documento import TipoDocumento


class AsignadorFolios(Protocol):
    def reservar(
        self, *, sucursal_id: UUID, tipo_documento: TipoDocumento
    ) -> Folio: ...


class AsignadorFoliosSQL:
    """Implementación SQL con lock pesimista.

    Asume que ya estamos dentro del UoW del use case llamador.
    """

    def __init__(
        self, *, uow: UnitOfWork, rangos: RangoFoliosRepository
    ) -> None:
        self._uow = uow
        self._rangos = rangos

    def reservar(
        self, *, sucursal_id: UUID, tipo_documento: TipoDocumento
    ) -> Folio:
        rango = self._rangos.obtener_activo_para_actualizar(
            sucursal_id, tipo_documento
        )
        if rango is None:
            raise RangoFoliosAgotadoError(
                "No hay rango activo para emitir",
                details={
                    "sucursal_id": str(sucursal_id),
                    "tipo_documento": tipo_documento.value,
                },
            )
        numero = rango.consumir()
        self._rangos.guardar(rango)
        return Folio(
            numero=numero,
            tipo=tipo_documento,
            sucursal_id=sucursal_id,
            rango_id=rango.id,
        )

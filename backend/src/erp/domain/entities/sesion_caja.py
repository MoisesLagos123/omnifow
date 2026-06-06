"""Entidad `SesionCaja`: ciclo de vida de una caja (apertura → cierre/arqueo).

Una `Caja` puede tener a lo sumo UNA sesión ABIERTA a la vez (garantizado a
nivel de dominio por el use case y a nivel DB por el índice único parcial
`uq_sesion_activa`). Montos en CLP entero (decisión §0).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from erp.domain.exceptions import SesionCajaInvalidaError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc


class EstadoSesionCaja(str, Enum):
    ABIERTA = "ABIERTA"
    CERRADA = "CERRADA"


def _validar_clp(valor: int, etiqueta: str) -> None:
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise SesionCajaInvalidaError(f"{etiqueta} debe ser entero (CLP)")
    if valor < 0:
        raise SesionCajaInvalidaError(f"{etiqueta} no puede ser negativo")


@dataclass
class SesionCaja:
    caja_id: UUID
    usuario_apertura_id: UUID
    monto_inicial_clp: int
    abierta_en: datetime = field(default_factory=datetime_utc)
    estado: EstadoSesionCaja = EstadoSesionCaja.ABIERTA
    cerrada_en: datetime | None = None
    usuario_cierre_id: UUID | None = None
    monto_final_declarado_clp: int | None = None
    monto_final_calculado_clp: int | None = None
    id: UUID = field(default_factory=new_uuid7)

    def __post_init__(self) -> None:
        _validar_clp(self.monto_inicial_clp, "El monto inicial")
        if self.estado is EstadoSesionCaja.CERRADA:
            # Coherencia mínima para sesiones reconstruidas como cerradas.
            if self.cerrada_en is None:
                raise SesionCajaInvalidaError(
                    "Una sesión cerrada requiere `cerrada_en`"
                )

    @property
    def esta_abierta(self) -> bool:
        return self.estado is EstadoSesionCaja.ABIERTA

    @property
    def diferencia_clp(self) -> int | None:
        """declarado − calculado. Positivo = sobrante, negativo = faltante.

        `None` mientras la sesión no esté cerrada.
        """
        if self.monto_final_declarado_clp is None or self.monto_final_calculado_clp is None:
            return None
        return self.monto_final_declarado_clp - self.monto_final_calculado_clp

    def cerrar(
        self,
        *,
        monto_declarado_clp: int,
        monto_calculado_clp: int,
        usuario_id: UUID,
        ahora: datetime,
    ) -> None:
        """Cierra la sesión registrando el arqueo.

        El `monto_calculado_clp` lo computa el use case a partir del monto
        inicial más ingresos en efectivo menos egresos en efectivo. La
        diferencia se deriva de `diferencia_clp`.
        """
        if self.estado is not EstadoSesionCaja.ABIERTA:
            raise SesionCajaInvalidaError("Solo se pueden cerrar sesiones abiertas")
        _validar_clp(monto_declarado_clp, "El monto declarado")
        _validar_clp(monto_calculado_clp, "El monto calculado")
        self.monto_final_declarado_clp = monto_declarado_clp
        self.monto_final_calculado_clp = monto_calculado_clp
        self.usuario_cierre_id = usuario_id
        self.cerrada_en = ahora
        self.estado = EstadoSesionCaja.CERRADA

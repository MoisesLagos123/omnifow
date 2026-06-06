"""Entidad `Producto`."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from erp.domain.exceptions import ProductoInvalidoError
from erp.domain.utils.ids import new_uuid7
from erp.domain.utils.time import datetime_utc

_SKU_RE = re.compile(r"^[A-Z0-9][A-Z0-9_\-]{2,39}$")
_BARRAS_RE = re.compile(r"^[A-Za-z0-9\-]{6,40}$")


@dataclass
class Producto:
    sku: str
    nombre: str
    precio_venta_clp: int
    codigo_barras: str | None = None
    categoria_id: UUID | None = None
    iva_porcentaje: int = 19
    controla_vencimiento: bool = False
    dias_alerta_vencimiento: int | None = None
    activo: bool = True
    id: UUID = field(default_factory=new_uuid7)
    version: int = 0
    creado_en: datetime = field(default_factory=datetime_utc)
    actualizado_en: datetime = field(default_factory=datetime_utc)

    def __post_init__(self) -> None:
        sku = (self.sku or "").strip().upper()
        if not _SKU_RE.match(sku):
            raise ProductoInvalidoError(
                "SKU inválido: 3-40 chars, A-Z/0-9/_/-, debe iniciar con letra o dígito"
            )
        nombre = (self.nombre or "").strip()
        if not nombre:
            raise ProductoInvalidoError("El nombre del producto es obligatorio")
        if len(nombre) > 200:
            raise ProductoInvalidoError("El nombre no puede exceder 200 caracteres")
        if not isinstance(self.precio_venta_clp, int) or isinstance(
            self.precio_venta_clp, bool
        ):
            raise ProductoInvalidoError("El precio debe ser un entero CLP")
        if self.precio_venta_clp <= 0:
            raise ProductoInvalidoError("El precio debe ser mayor que cero")
        if not isinstance(self.iva_porcentaje, int) or isinstance(
            self.iva_porcentaje, bool
        ):
            raise ProductoInvalidoError("El IVA debe ser un entero")
        if self.iva_porcentaje < 0 or self.iva_porcentaje > 100:
            raise ProductoInvalidoError("IVA fuera de rango (0-100)")
        if not isinstance(self.controla_vencimiento, bool):
            raise ProductoInvalidoError("controla_vencimiento debe ser booleano")
        if self.dias_alerta_vencimiento is not None:
            if not isinstance(self.dias_alerta_vencimiento, int) or isinstance(
                self.dias_alerta_vencimiento, bool
            ):
                raise ProductoInvalidoError(
                    "dias_alerta_vencimiento debe ser un entero o nulo"
                )
            if self.dias_alerta_vencimiento <= 0:
                raise ProductoInvalidoError(
                    "dias_alerta_vencimiento debe ser mayor que cero"
                )
        cb: str | None = None
        if self.codigo_barras is not None:
            cb_clean = self.codigo_barras.strip()
            if cb_clean:
                if not _BARRAS_RE.match(cb_clean):
                    raise ProductoInvalidoError(
                        "Código de barras inválido: 6-40 chars alfanuméricos"
                    )
                cb = cb_clean
        object.__setattr__(self, "sku", sku)
        object.__setattr__(self, "nombre", nombre)
        object.__setattr__(self, "codigo_barras", cb)

    def cambiar_precio(self, nuevo_precio_clp: int, ahora: datetime) -> None:
        if not isinstance(nuevo_precio_clp, int) or isinstance(nuevo_precio_clp, bool):
            raise ProductoInvalidoError("El precio debe ser un entero CLP")
        if nuevo_precio_clp <= 0:
            raise ProductoInvalidoError("El precio debe ser mayor que cero")
        self.precio_venta_clp = nuevo_precio_clp
        self.version += 1
        self.actualizado_en = ahora

    def renombrar(self, nuevo_nombre: str, ahora: datetime) -> None:
        nombre = (nuevo_nombre or "").strip()
        if not nombre:
            raise ProductoInvalidoError("El nombre del producto es obligatorio")
        if len(nombre) > 200:
            raise ProductoInvalidoError("El nombre no puede exceder 200 caracteres")
        self.nombre = nombre
        self.actualizado_en = ahora

    def cambiar_categoria(self, categoria_id: UUID | None, ahora: datetime) -> None:
        self.categoria_id = categoria_id
        self.actualizado_en = ahora

    def cambiar_codigo_barras(self, codigo: str | None, ahora: datetime) -> None:
        cb: str | None = None
        if codigo is not None:
            cb_clean = codigo.strip()
            if cb_clean:
                if not _BARRAS_RE.match(cb_clean):
                    raise ProductoInvalidoError(
                        "Código de barras inválido: 6-40 chars alfanuméricos"
                    )
                cb = cb_clean
        self.codigo_barras = cb
        self.actualizado_en = ahora

    def cambiar_iva(self, iva_porcentaje: int, ahora: datetime) -> None:
        if not isinstance(iva_porcentaje, int) or isinstance(iva_porcentaje, bool):
            raise ProductoInvalidoError("El IVA debe ser un entero")
        if iva_porcentaje < 0 or iva_porcentaje > 100:
            raise ProductoInvalidoError("IVA fuera de rango (0-100)")
        self.iva_porcentaje = iva_porcentaje
        self.actualizado_en = ahora

    def cambiar_control_vencimiento(
        self, controla: bool, ahora: datetime
    ) -> None:
        if not isinstance(controla, bool):
            raise ProductoInvalidoError("controla_vencimiento debe ser booleano")
        self.controla_vencimiento = controla
        self.actualizado_en = ahora

    def cambiar_dias_alerta_vencimiento(
        self, dias: int | None, ahora: datetime
    ) -> None:
        if dias is not None:
            if not isinstance(dias, int) or isinstance(dias, bool):
                raise ProductoInvalidoError(
                    "dias_alerta_vencimiento debe ser un entero o nulo"
                )
            if dias <= 0:
                raise ProductoInvalidoError(
                    "dias_alerta_vencimiento debe ser mayor que cero"
                )
        self.dias_alerta_vencimiento = dias
        self.actualizado_en = ahora

    def desactivar(self, ahora: datetime) -> None:
        self.activo = False
        self.actualizado_en = ahora

    def reactivar(self, ahora: datetime) -> None:
        self.activo = True
        self.actualizado_en = ahora

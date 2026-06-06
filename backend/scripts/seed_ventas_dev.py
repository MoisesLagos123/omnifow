"""Seed idempotente de ventas de desarrollo.

Hace 2 ventas en SC-CENTRO/C1 si hay sesión de caja activa:
- 1 BOLETA en efectivo (consumidor final).
- 1 FACTURA mixta (efectivo + transferencia) si existe al menos un cliente.

Idempotente: omite si ya hay ≥2 ventas confirmadas hoy en la caja activa.
Requiere haber corrido previamente:
    python scripts/seed_dev_user.py
    python scripts/seed_sucursales_dev.py
    python scripts/seed_inventario_dev.py
    python scripts/seed_perfiles_permisos.py
    python scripts/seed_clientes_dev.py
    python scripts/seed_caja_dev.py

Uso:
    python scripts/seed_ventas_dev.py
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from erp.adapters.repositories.sql.bodega_repository import SqlBodegaRepository
from erp.adapters.repositories.sql.caja_repository import SqlCajaRepository
from erp.adapters.repositories.sql.cliente_repository import SqlClienteRepository
from erp.adapters.repositories.sql.detalle_venta_repository import (
    SqlDetalleVentaRepository,
)
from erp.adapters.repositories.sql.documento_tributario_repository import (
    SqlDocumentoTributarioRepository,
)
from erp.adapters.repositories.sql.lote_inventario_repository import (
    SqlLoteInventarioRepository,
)
from erp.adapters.repositories.sql.mov_inventario_repository import (
    SqlMovInventarioRepository,
)
from erp.adapters.repositories.sql.movimiento_caja_repository import (
    SqlMovimientoCajaRepository,
)
from erp.adapters.repositories.sql.pago_repository import SqlPagoRepository
from erp.adapters.repositories.sql.producto_repository import SqlProductoRepository
from erp.adapters.repositories.sql.rango_folios_repository import (
    SqlRangoFoliosRepository,
)
from erp.adapters.repositories.sql.sesion_caja_repository import (
    SqlSesionCajaRepository,
)
from erp.adapters.repositories.sql.stock_repository import SqlStockRepository
from erp.adapters.repositories.sql.sucursal_repository import SqlSucursalRepository
from erp.adapters.repositories.sql.unit_of_work import SqlAlchemyUnitOfWork
from erp.adapters.repositories.sql.venta_repository import SqlVentaRepository
from erp.application.security.contexto import ContextoSeguridad
from erp.application.services.asignador_folios import AsignadorFoliosSQL
from erp.application.use_cases.venta.procesar_venta import (
    ItemVentaCommand,
    PagoVentaCommand,
    ProcesarVentaCommand,
    ProcesarVentaUseCase,
)
from erp.domain.entities.pago import TipoPago
from erp.domain.entities.sesion_caja import EstadoSesionCaja
from erp.domain.utils.time import datetime_utc
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.audit.audit_writer import SqlAuditWriter
from erp.infrastructure.config.settings import get_settings
from erp.infrastructure.db.engine import build_engine, build_session_factory
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.caja import CajaORM
from erp.infrastructure.db.models.cliente import ClienteORM
from erp.infrastructure.db.models.producto import ProductoORM
from erp.infrastructure.db.models.rango_folios import RangoFoliosORM
from erp.infrastructure.db.models.sesion_caja import SesionCajaORM
from erp.infrastructure.db.models.sucursal import SucursalORM
from erp.infrastructure.db.models.usuario import UsuarioORM
from erp.infrastructure.db.models.venta import VentaORM

ADMIN_EMAIL = "admin@minierp.cl"
SUCURSAL_CODIGO = "SC-CENTRO"


class _SystemClock:
    def now(self) -> datetime:
        return datetime_utc()


def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    # 1. Verificaciones de existencia
    with session_factory() as s:
        admin = (
            s.query(UsuarioORM).filter(UsuarioORM.email == ADMIN_EMAIL).one_or_none()
        )
        if admin is None:
            print(f"AVISO: {ADMIN_EMAIL} no existe. Corre seed_dev_user.py primero.")
            return
        sucursal = (
            s.query(SucursalORM)
            .filter(SucursalORM.codigo == SUCURSAL_CODIGO)
            .one_or_none()
        )
        if sucursal is None:
            print(f"AVISO: {SUCURSAL_CODIGO} no existe. Corre seed_sucursales_dev.py.")
            return
        caja = (
            s.query(CajaORM)
            .filter(CajaORM.sucursal_id == sucursal.id, CajaORM.activo.is_(True))
            .order_by(CajaORM.codigo)
            .first()
        )
        if caja is None:
            print(f"AVISO: sin cajas activas en {SUCURSAL_CODIGO}.")
            return
        sesion_activa = (
            s.query(SesionCajaORM)
            .filter(
                SesionCajaORM.caja_id == caja.id,
                SesionCajaORM.estado == EstadoSesionCaja.ABIERTA.value,
            )
            .one_or_none()
        )
        if sesion_activa is None:
            print(
                f"AVISO: sin sesión de caja ABIERTA en {caja.codigo}. "
                "Corre seed_caja_dev.py primero."
            )
            return
        # Preferimos la bodega "B1" (principal del seed de inventario). Si no
        # existe, caemos a la primera bodega activa alfabéticamente.
        bodega = (
            s.query(BodegaORM)
            .filter(
                BodegaORM.sucursal_id == sucursal.id,
                BodegaORM.activo.is_(True),
                BodegaORM.codigo == "B1",
            )
            .first()
        )
        if bodega is None:
            bodega = (
                s.query(BodegaORM)
                .filter(
                    BodegaORM.sucursal_id == sucursal.id,
                    BodegaORM.activo.is_(True),
                )
                .order_by(BodegaORM.codigo)
                .first()
            )
        if bodega is None:
            print(f"AVISO: sin bodegas activas en {SUCURSAL_CODIGO}.")
            return
        rango_boleta = (
            s.query(RangoFoliosORM)
            .filter(
                RangoFoliosORM.sucursal_id == sucursal.id,
                RangoFoliosORM.tipo_documento == TipoDocumento.BOLETA.value,
                RangoFoliosORM.activo.is_(True),
            )
            .first()
        )
        if rango_boleta is None:
            print(f"AVISO: sin rango BOLETA activo en {SUCURSAL_CODIGO}.")
            return
        productos = (
            s.query(ProductoORM)
            .filter(ProductoORM.activo.is_(True))
            .order_by(ProductoORM.sku)
            .limit(3)
            .all()
        )
        if len(productos) < 2:
            print("AVISO: se necesitan al menos 2 productos activos.")
            return

        # Idempotencia: si ya hay ≥2 ventas confirmadas en esta caja hoy → skip.
        ya_existen = (
            s.query(VentaORM)
            .filter(
                VentaORM.caja_id == caja.id,
                VentaORM.estado == "CONFIRMADA",
            )
            .count()
        )
        if ya_existen >= 2:
            print(
                f"Ya hay {ya_existen} ventas CONFIRMADAS en caja {caja.codigo}; "
                "no se crean más."
            )
            return

        cliente = s.query(ClienteORM).filter(ClienteORM.activo.is_(True)).first()
        rango_factura = (
            s.query(RangoFoliosORM)
            .filter(
                RangoFoliosORM.sucursal_id == sucursal.id,
                RangoFoliosORM.tipo_documento == TipoDocumento.FACTURA.value,
                RangoFoliosORM.activo.is_(True),
            )
            .first()
        )

        sucursal_id = sucursal.id
        caja_id = caja.id
        bodega_id = bodega.id
        admin_id = admin.id
        productos_data = [
            (p.id, p.precio_venta_clp, p.controla_vencimiento) for p in productos
        ]
        cliente_id = cliente.id if cliente is not None else None
        tiene_factura = rango_factura is not None

    # 2. Build use case y ejecutar
    contexto = ContextoSeguridad(
        usuario_id=admin_id,
        perfiles=("Sysadmin",),
        permisos=frozenset({"venta.crear", "venta.anular"}),
    )

    def _construir_uc(uow: SqlAlchemyUnitOfWork) -> ProcesarVentaUseCase:
        return ProcesarVentaUseCase(
            uow=uow,
            ventas=SqlVentaRepository(uow),
            detalles=SqlDetalleVentaRepository(uow),
            pagos=SqlPagoRepository(uow),
            documentos=SqlDocumentoTributarioRepository(uow),
            productos=SqlProductoRepository(uow),
            bodegas=SqlBodegaRepository(uow),
            sucursales=SqlSucursalRepository(uow),
            cajas=SqlCajaRepository(uow),
            clientes=SqlClienteRepository(uow),
            stock=SqlStockRepository(uow),
            mov_inventario=SqlMovInventarioRepository(uow),
            lotes=SqlLoteInventarioRepository(uow),
            sesiones_caja=SqlSesionCajaRepository(uow),
            movimientos_caja=SqlMovimientoCajaRepository(uow),
            asignador_folios=AsignadorFoliosSQL(
                uow=uow, rangos=SqlRangoFoliosRepository(uow)
            ),
            audit=SqlAuditWriter(uow),
            clock=_SystemClock(),
        )

    # Venta 1: BOLETA efectivo con 2 productos (cant=1 c/u)
    p1_id, p1_precio, _ = productos_data[0]
    p2_id, p2_precio, _ = productos_data[1]
    total_b = p1_precio + p2_precio
    uow1 = SqlAlchemyUnitOfWork(session_factory)
    uc1 = _construir_uc(uow1)
    cmd1 = ProcesarVentaCommand(
        contexto=contexto,
        sucursal_id=sucursal_id,
        caja_id=caja_id,
        tipo_documento=TipoDocumento.BOLETA,
        items=(
            ItemVentaCommand(
                producto_id=p1_id,
                bodega_id=bodega_id,
                cantidad=Decimal("1"),
                precio_unitario_clp=p1_precio,
            ),
            ItemVentaCommand(
                producto_id=p2_id,
                bodega_id=bodega_id,
                cantidad=Decimal("1"),
                precio_unitario_clp=p2_precio,
            ),
        ),
        pagos=(PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=total_b),),
    )
    res1 = uc1.execute(cmd1)
    print(
        f"+ Venta BOLETA folio {res1.documento.folio} total {res1.venta.total_clp} CLP"
    )

    # Venta 2: FACTURA si hay rango+cliente; sino otra BOLETA con pago mixto.
    p3_id, p3_precio, _ = productos_data[1]  # reutilizamos p2
    total_2 = p3_precio
    efectivo = total_2 // 2
    transfer = total_2 - efectivo
    pagos_2 = (
        PagoVentaCommand(tipo=TipoPago.EFECTIVO, monto_clp=efectivo),
        PagoVentaCommand(
            tipo=TipoPago.TRANSFERENCIA,
            monto_clp=transfer,
            referencia_externa="TR-001",
        ),
    )
    if tiene_factura and cliente_id is not None:
        tipo2 = TipoDocumento.FACTURA
    else:
        tipo2 = TipoDocumento.BOLETA
        cliente_id = None
    uow2 = SqlAlchemyUnitOfWork(session_factory)
    uc2 = _construir_uc(uow2)
    cmd2 = ProcesarVentaCommand(
        contexto=contexto,
        sucursal_id=sucursal_id,
        caja_id=caja_id,
        tipo_documento=tipo2,
        cliente_id=cliente_id,
        items=(
            ItemVentaCommand(
                producto_id=p3_id,
                bodega_id=bodega_id,
                cantidad=Decimal("1"),
                precio_unitario_clp=p3_precio,
            ),
        ),
        pagos=pagos_2,
    )
    res2 = uc2.execute(cmd2)
    print(
        f"+ Venta {tipo2.value} folio {res2.documento.folio} "
        f"total {res2.venta.total_clp} CLP (mixto)"
    )
    print("OK: seed de ventas aplicado.")


if __name__ == "__main__":
    main()

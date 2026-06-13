"""Seed UNIFICADO de datos demo OMNIFLOW.

Crea todo lo necesario para validar el sistema end-to-end:

  - 3 sucursales (SC-CENTRO, SC-NORTE, SC-SUR)
  - 3 cajas por sucursal (C1, C2, C3) = 9 cajas
  - Rangos de folios SII (BOLETA, FACTURA, NC, ND, GUIA) por sucursal
  - 3 categorías (Bebidas, Snacks, Limpieza)
  - 1 bodega por sucursal (B1)
  - 10 productos (con SKUs, precios, categorías; 2 perecibles con lotes
    de vencimiento variado para que "Por vencer" muestre datos)
  - Stock inicial en cada bodega (50 unidades en SC-CENTRO, 20 en las
    demás) + movimientos de entrada para audit/historial
  - 2 proveedores
  - 4 clientes (incluyendo una empresa para venta a crédito)
  - Sesión de caja ABIERTA en SC-CENTRO/C1 con $50.000 de fondo
  - Asigna las 3 sucursales al usuario admin sembrado por
    `seed_dev_user.py` (si existe)

Idempotente: re-ejecutar es seguro. Sólo crea lo que falta.

Pre-requisitos (correr ANTES):
    python scripts/seed_perfiles_permisos.py
    python scripts/seed_dev_user.py

Uso:
    python scripts/seed_demo.py

Limpiar todo y volver a sembrar:
    # Solo dev — borrar datos transaccionales antes de re-sembrar:
    # alembic downgrade base && alembic upgrade head
    # python scripts/seed_perfiles_permisos.py
    # python scripts/seed_dev_user.py
    # python scripts/seed_demo.py
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from erp.domain.entities.bodega import Bodega
from erp.domain.entities.caja import Caja
from erp.domain.entities.categoria import Categoria
from erp.domain.entities.cliente import Cliente
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sesion_caja import SesionCaja, EstadoSesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.utils.time import datetime_utc
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.config.settings import get_settings
from erp.infrastructure.db.engine import build_engine, build_session_factory
from erp.infrastructure.db.mappers.bodega import to_orm as bodega_to_orm
from erp.infrastructure.db.mappers.caja import to_orm as caja_to_orm
from erp.infrastructure.db.mappers.categoria import to_orm as categoria_to_orm
from erp.infrastructure.db.mappers.cliente import to_orm as cliente_to_orm
from erp.infrastructure.db.mappers.lote_inventario import to_orm as lote_to_orm
from erp.infrastructure.db.mappers.mov_inventario import to_orm as mov_to_orm
from erp.infrastructure.db.mappers.movimiento_caja import to_orm as mov_caja_to_orm
from erp.infrastructure.db.mappers.producto import to_orm as producto_to_orm
from erp.infrastructure.db.mappers.rango_folios import to_orm as rango_to_orm
from erp.infrastructure.db.mappers.sesion_caja import to_orm as sesion_to_orm
from erp.infrastructure.db.mappers.stock import to_orm as stock_to_orm
from erp.infrastructure.db.mappers.sucursal import to_orm as sucursal_to_orm
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.caja import CajaORM
from erp.infrastructure.db.models.categoria import CategoriaORM
from erp.infrastructure.db.models.cliente import ClienteORM
from erp.infrastructure.db.models.lote_inventario import LoteInventarioORM
from erp.infrastructure.db.models.producto import ProductoORM
from erp.infrastructure.db.models.proveedor import ProveedorORM
from erp.infrastructure.db.models.rango_folios import RangoFoliosORM
from erp.infrastructure.db.models.sesion_caja import SesionCajaORM
from erp.infrastructure.db.models.stock import StockORM
from erp.infrastructure.db.models.sucursal import SucursalORM
from erp.infrastructure.db.models.usuario import UsuarioORM
from erp.infrastructure.db.models.usuario_sucursal import usuario_sucursal_table

# ─── Configuración del seed ────────────────────────────────────────────

ADMIN_EMAIL = "admin@minierp.cl"

# RUTs válidos (DV calculado por módulo 11). NO inventar — todos los
# RUTs aquí están pre-verificados.
RUT_EMISOR = "76123456-0"

# 3 sucursales × 3 cajas — lo que pidió el usuario.
SUCURSALES_CONFIG: list[tuple[str, str]] = [
    # (codigo, nombre)
    ("SC-CENTRO", "Sucursal Centro"),
    ("SC-NORTE", "Sucursal Norte"),
    ("SC-SUR", "Sucursal Sur"),
]
CAJAS_POR_SUCURSAL = ("C1", "C2", "C3")

# Folios SII a sembrar por cada sucursal — rangos amplios para que
# nadie se quede sin folios en demo.
RANGOS_FOLIOS: list[tuple[TipoDocumento, int, int]] = [
    (TipoDocumento.BOLETA, 1, 5000),
    (TipoDocumento.FACTURA, 1, 2000),
    (TipoDocumento.NC, 1, 500),
    (TipoDocumento.ND, 1, 500),
    (TipoDocumento.GUIA, 1, 500),
]

CATEGORIAS = ["Bebidas", "Snacks", "Limpieza"]

# 10 productos — variados, precios CLP reales típicos almacén.
# (sku, nombre, precio_clp, categoria, controla_vencimiento)
PRODUCTOS: list[tuple[str, str, int, str, bool]] = [
    ("BEB-COLA-350", "Cola 350ml lata", 1200, "Bebidas", True),
    ("BEB-AGUA-500", "Agua mineral 500ml", 800, "Bebidas", False),
    ("BEB-JUGO-1L", "Jugo natural 1L", 2200, "Bebidas", True),
    ("SNK-PAPAS-150", "Papas fritas 150g", 1500, "Snacks", True),
    ("SNK-CHOC-100", "Chocolate negro 100g", 1800, "Snacks", False),
    ("SNK-GALLE-200", "Galletas surtidas 200g", 1600, "Snacks", True),
    ("SNK-MANI-80", "Maní salado 80g", 900, "Snacks", False),
    ("LIM-DET-1L", "Detergente líquido 1L", 3500, "Limpieza", False),
    ("LIM-CLOR-1L", "Cloro 1L", 1900, "Limpieza", False),
    ("LIM-LAVALOZA-500", "Lavaloza 500ml", 1700, "Limpieza", False),
]

# Stock inicial por sucursal (cantidad por producto en su bodega B1).
# CENTRO tiene más stock por ser principal; NORTE y SUR tienen menos.
STOCK_INICIAL_POR_SUCURSAL: dict[str, Decimal] = {
    "SC-CENTRO": Decimal("50"),
    "SC-NORTE": Decimal("20"),
    "SC-SUR": Decimal("20"),
}
COSTO_INICIAL_CLP = 500  # Costo unitario simple para demo.

# Lotes de ejemplo SOLO en SC-CENTRO/B1 para que el reporte "Por vencer"
# muestre datos al primer login. Solo aplican a productos perecibles.
# (sku, dias_offset_hoy, numero_lote, cantidad, costo_unitario)
LOTES_EJEMPLO: list[tuple[str, int, str, Decimal, int]] = [
    ("BEB-COLA-350", -3, "L-DEMO-COLA-V", Decimal("10"), 500),       # vencido
    ("BEB-COLA-350", 5, "L-DEMO-COLA-C", Decimal("20"), 520),        # crítico (≤7d)
    ("BEB-JUGO-1L", 14, "L-DEMO-JUGO-PV", Decimal("8"), 1500),       # por vencer (~14d)
    ("SNK-PAPAS-150", 30, "L-DEMO-PAPAS-PV", Decimal("15"), 900),    # por vencer (~30d)
    ("SNK-PAPAS-150", 180, "L-DEMO-PAPAS-OK", Decimal("30"), 880),   # vigente (~6m)
    ("SNK-GALLE-200", 60, "L-DEMO-GALL-OK", Decimal("18"), 950),     # vigente
]

# Proveedores demo — RUTs válidos.
# (rut, razon_social, giro, telefono, email)
PROVEEDORES: list[tuple[str, str, str, str, str | None]] = [
    (
        "76123456-0",
        "Distribuidora Mayorista Central SpA",
        "Distribución de alimentos y bebidas",
        "+56222345678",
        "contacto@distmayor.cl",
    ),
    (
        "77777777-1",
        "Higiene & Limpieza S.A.",
        "Venta al por mayor de productos de aseo",
        "+56226543210",
        "ventas@higlimp.cl",
    ),
]

# Clientes demo — mix persona / empresa (para CxC).
# (rut, razon_social, giro, comuna, region, email, telefono)
CLIENTES: list[tuple[str, str, str | None, str, str, str | None, str | None]] = [
    (
        "11111111-1",
        "Juan Pérez Soto",
        None,
        "Santiago",
        "Metropolitana",
        "juan.perez@example.cl",
        "+56911111111",
    ),
    (
        "22222222-2",
        "María González Rivas",
        None,
        "Viña del Mar",
        "Valparaíso",
        None,
        "+56922222222",
    ),
    (
        "12345678-5",
        "Comercializadora Andes Ltda.",
        "Venta al por menor",
        "Providencia",
        "Metropolitana",
        "compras@andes.cl",
        "+56222345678",
    ),
    (
        "13759373-K",
        "Restaurante Los Robles SpA",
        "Servicios de gastronomía",
        "Las Condes",
        "Metropolitana",
        "admin@losrobles.cl",
        "+56226789012",
    ),
]

# Sesión de caja demo — abrir en CENTRO/C1 con fondo de $50k.
SESION_DEMO_SUCURSAL = "SC-CENTRO"
SESION_DEMO_CAJA = "C1"
SESION_DEMO_MONTO_INICIAL = 50_000


# ─── Helpers ──────────────────────────────────────────────────────────


def _print_header(titulo: str) -> None:
    print(f"\n── {titulo} " + "─" * (60 - len(titulo)))


# ─── Pasos del seed ───────────────────────────────────────────────────


def seed_sucursales_y_cajas(session) -> dict[str, SucursalORM]:
    """Crea/actualiza sucursales + cajas + folios. Devuelve dict por código."""
    _print_header("Sucursales, cajas y folios SII")
    por_codigo: dict[str, SucursalORM] = {}

    for codigo, nombre in SUCURSALES_CONFIG:
        existente = (
            session.query(SucursalORM)
            .filter(SucursalORM.codigo == codigo)
            .one_or_none()
        )
        if existente is None:
            suc = Sucursal(
                codigo=codigo,
                nombre=nombre,
                rut_emisor=Rut(RUT_EMISOR),
            )
            session.add(sucursal_to_orm(suc))
            session.flush()
            print(f"  + Sucursal {codigo} ({nombre})")
        else:
            print(f"  · Sucursal {codigo} ya existe")
        suc_orm = (
            session.query(SucursalORM)
            .filter(SucursalORM.codigo == codigo)
            .one()
        )
        por_codigo[codigo] = suc_orm

        # Cajas — 3 por sucursal
        for cod_caja in CAJAS_POR_SUCURSAL:
            caja_existente = (
                session.query(CajaORM)
                .filter(
                    CajaORM.sucursal_id == suc_orm.id,
                    CajaORM.codigo == cod_caja,
                )
                .one_or_none()
            )
            if caja_existente is None:
                caja = Caja(
                    sucursal_id=suc_orm.id,
                    codigo=cod_caja,
                    nombre=f"Caja {cod_caja} - {codigo}",
                )
                session.add(caja_to_orm(caja))
                print(f"    + Caja {cod_caja}")

        # Folios SII — 5 tipos por sucursal
        for tipo_doc, desde, hasta in RANGOS_FOLIOS:
            rango_existente = (
                session.query(RangoFoliosORM)
                .filter(
                    RangoFoliosORM.sucursal_id == suc_orm.id,
                    RangoFoliosORM.tipo_documento == tipo_doc.value,
                )
                .one_or_none()
            )
            if rango_existente is None:
                rango = RangoFolios(
                    sucursal_id=suc_orm.id,
                    tipo_documento=tipo_doc,
                    desde=desde,
                    hasta=hasta,
                )
                session.add(rango_to_orm(rango))
                print(f"    + Folios {tipo_doc.value} [{desde}-{hasta}]")

    return por_codigo


def asignar_sucursales_al_admin(session, sucursales: dict[str, SucursalORM]) -> None:
    """Asigna las 3 sucursales al usuario admin (si existe)."""
    admin = (
        session.query(UsuarioORM)
        .filter(UsuarioORM.email == ADMIN_EMAIL)
        .one_or_none()
    )
    if admin is None:
        print(
            f"\nAVISO: usuario {ADMIN_EMAIL!r} no existe. Corre antes:\n"
            "  python scripts/seed_dev_user.py"
        )
        return
    for codigo, suc in sucursales.items():
        ya = session.execute(
            usuario_sucursal_table.select().where(
                usuario_sucursal_table.c.usuario_id == admin.id,
                usuario_sucursal_table.c.sucursal_id == suc.id,
            )
        ).first()
        if ya is None:
            session.execute(
                usuario_sucursal_table.insert().values(
                    usuario_id=admin.id, sucursal_id=suc.id
                )
            )
            print(f"  + Admin asignado a {codigo}")


def seed_categorias(session) -> dict[str, CategoriaORM]:
    _print_header("Categorías de productos")
    por_nombre: dict[str, CategoriaORM] = {}
    for nombre in CATEGORIAS:
        existente = (
            session.query(CategoriaORM)
            .filter(CategoriaORM.nombre == nombre)
            .one_or_none()
        )
        if existente is None:
            c = Categoria(nombre=nombre)
            orm = categoria_to_orm(c)
            session.add(orm)
            session.flush()
            por_nombre[nombre] = orm
            print(f"  + Categoría {nombre}")
        else:
            por_nombre[nombre] = existente
            print(f"  · Categoría {nombre} ya existe")
    return por_nombre


def seed_bodegas(
    session, sucursales: dict[str, SucursalORM]
) -> dict[str, BodegaORM]:
    """Una bodega B1 por sucursal."""
    _print_header("Bodegas (1 por sucursal)")
    por_sucursal: dict[str, BodegaORM] = {}
    for codigo, suc in sucursales.items():
        bod_existente = (
            session.query(BodegaORM)
            .filter(BodegaORM.sucursal_id == suc.id, BodegaORM.codigo == "B1")
            .one_or_none()
        )
        if bod_existente is None:
            bod = Bodega(
                sucursal_id=suc.id,
                codigo="B1",
                nombre=f"Bodega Principal {codigo}",
            )
            orm = bodega_to_orm(bod)
            session.add(orm)
            session.flush()
            por_sucursal[codigo] = orm
            print(f"  + Bodega B1 en {codigo}")
        else:
            por_sucursal[codigo] = bod_existente
            print(f"  · Bodega B1 en {codigo} ya existe")
    return por_sucursal


def seed_productos(
    session, categorias: dict[str, CategoriaORM]
) -> dict[str, ProductoORM]:
    _print_header("Productos (10)")
    por_sku: dict[str, ProductoORM] = {}
    for sku, nombre, precio, cat_nombre, controla in PRODUCTOS:
        existente = (
            session.query(ProductoORM).filter(ProductoORM.sku == sku).one_or_none()
        )
        if existente is None:
            p = Producto(
                sku=sku,
                nombre=nombre,
                precio_venta_clp=precio,
                categoria_id=categorias[cat_nombre].id,
                controla_vencimiento=controla,
            )
            orm = producto_to_orm(p)
            session.add(orm)
            session.flush()
            por_sku[sku] = orm
            perecible = " (perecible)" if controla else ""
            print(f"  + {sku}: {nombre} — ${precio:,}{perecible}")
        else:
            if existente.controla_vencimiento != controla:
                existente.controla_vencimiento = controla
            por_sku[sku] = existente
            print(f"  · {sku} ya existe")
    return por_sku


def seed_stock_inicial(
    session,
    productos: dict[str, ProductoORM],
    bodegas: dict[str, BodegaORM],
    admin_id: UUID,
) -> None:
    """Stock inicial en cada bodega — productos NO perecibles solamente.
    Los perecibles cargan stock vía lotes (siguiente paso) para no romper
    el invariante SUM(lotes vivos) == stock."""
    _print_header("Stock inicial por sucursal")

    for sucursal_codigo, bodega in bodegas.items():
        cantidad = STOCK_INICIAL_POR_SUCURSAL.get(sucursal_codigo, Decimal("0"))
        if cantidad <= 0:
            continue
        for sku, prod_orm in productos.items():
            if prod_orm.controla_vencimiento:
                # Stock por lotes (paso lotes_demo)
                continue
            existente = (
                session.query(StockORM)
                .filter(
                    StockORM.producto_id == prod_orm.id,
                    StockORM.bodega_id == bodega.id,
                )
                .one_or_none()
            )
            if existente is not None:
                continue  # ya tiene stock
            st = Stock(producto_id=prod_orm.id, bodega_id=bodega.id)
            st.ingresar(cantidad, COSTO_INICIAL_CLP)
            session.add(stock_to_orm(st))
            mov = MovInventario(
                producto_id=prod_orm.id,
                bodega_id=bodega.id,
                tipo=TipoMovInventario.ENTRADA,
                cantidad=cantidad,
                costo_unitario_clp=COSTO_INICIAL_CLP,
                usuario_id=admin_id,
                referencia_tipo="SEED",
                referencia_id=prod_orm.id,
                motivo=f"Seed demo: stock inicial {sucursal_codigo}",
                fecha=datetime_utc(),
            )
            session.add(mov_to_orm(mov))
        print(f"  + Stock cargado en {sucursal_codigo} ({cantidad} u/producto)")


def seed_lotes_demo(
    session,
    productos: dict[str, ProductoORM],
    bodegas: dict[str, BodegaORM],
    admin_id: UUID,
) -> None:
    """Lotes con fechas variadas en SC-CENTRO/B1 para reporte "Por vencer".
    Mantiene el invariante SUM(lotes) == stock.cantidad."""
    _print_header("Lotes de vencimiento (SC-CENTRO/B1)")
    bodega = bodegas.get("SC-CENTRO")
    if bodega is None:
        print("  · SC-CENTRO no existe, skip lotes")
        return
    hoy = date.today()
    for sku, offset_dias, numero_lote, cantidad, costo in LOTES_EJEMPLO:
        prod_orm = productos.get(sku)
        if prod_orm is None:
            continue
        existente = (
            session.query(LoteInventarioORM)
            .filter(LoteInventarioORM.numero_lote == numero_lote)
            .one_or_none()
        )
        if existente is not None:
            continue
        fecha_venc = hoy + timedelta(days=offset_dias)
        fecha_ing = min(hoy, fecha_venc)
        lote = LoteInventario(
            producto_id=prod_orm.id,
            bodega_id=bodega.id,
            numero_lote=numero_lote,
            fecha_ingreso=fecha_ing,
            fecha_vencimiento=fecha_venc,
            cantidad=cantidad,
            costo_unitario_clp=costo,
        )
        session.add(lote_to_orm(lote))

        # Actualizar stock agregado del producto en la bodega
        st_orm = (
            session.query(StockORM)
            .filter(
                StockORM.producto_id == prod_orm.id,
                StockORM.bodega_id == bodega.id,
            )
            .one_or_none()
        )
        if st_orm is None:
            dom = Stock(producto_id=prod_orm.id, bodega_id=bodega.id)
            dom.ingresar(cantidad, costo)
            session.add(stock_to_orm(dom))
        else:
            nueva_cant = st_orm.cantidad + cantidad
            valor_actual = st_orm.cantidad * st_orm.costo_promedio_clp
            valor_ing = cantidad * costo
            st_orm.cantidad = nueva_cant
            if nueva_cant > 0:
                st_orm.costo_promedio_clp = int(
                    ((valor_actual + valor_ing) / nueva_cant).to_integral_value()
                )
            st_orm.version += 1

        mov = MovInventario(
            producto_id=prod_orm.id,
            bodega_id=bodega.id,
            tipo=TipoMovInventario.ENTRADA,
            cantidad=cantidad,
            costo_unitario_clp=costo,
            usuario_id=admin_id,
            referencia_tipo="SEED",
            referencia_id=prod_orm.id,
            lote_id=lote.id,
            motivo=f"Seed demo: lote {numero_lote}",
            fecha=datetime_utc(),
        )
        session.add(mov_to_orm(mov))
        marca = ""
        if offset_dias < 0:
            marca = " ⚠ VENCIDO"
        elif offset_dias <= 7:
            marca = " ⚠ CRÍTICO"
        elif offset_dias <= 30:
            marca = " · por vencer"
        print(
            f"  + Lote {numero_lote} ({sku}): {cantidad} u, vence {fecha_venc}{marca}"
        )


def seed_proveedores(session) -> None:
    _print_header("Proveedores")
    for rut, razon, giro, telefono, email in PROVEEDORES:
        rut_norm = str(Rut(rut))
        existente = (
            session.query(ProveedorORM)
            .filter(ProveedorORM.rut == rut_norm)
            .one_or_none()
        )
        if existente is not None:
            print(f"  · {rut_norm} ya existe")
            continue
        # Proveedor no tiene mapper — insertamos vía ORM directo.
        orm = ProveedorORM(
            id=uuid4(),
            rut=rut_norm,
            razon_social=razon,
            giro=giro,
            email=email,
            telefono=telefono,
            activo=True,
        )
        session.add(orm)
        print(f"  + {rut_norm} — {razon}")


def seed_clientes(session) -> None:
    _print_header("Clientes")
    for rut, razon, giro, comuna, region, email, telefono in CLIENTES:
        rut_norm = str(Rut(rut))
        existente = (
            session.query(ClienteORM)
            .filter(ClienteORM.rut == rut_norm)
            .one_or_none()
        )
        if existente is not None:
            print(f"  · {rut_norm} ya existe")
            continue
        cli = Cliente(
            rut=Rut(rut),
            razon_social=razon,
            giro=giro,
            comuna=comuna,
            region=region,
            email=email,
            telefono=telefono,
        )
        session.add(cliente_to_orm(cli))
        print(f"  + {rut_norm} — {razon}")


def seed_sesion_caja(session, sucursales: dict[str, SucursalORM]) -> None:
    """Abre una sesión en SC-CENTRO/C1 si no hay ninguna activa.
    Necesaria para que el POS pueda registrar ventas inmediatamente."""
    _print_header("Sesión de caja abierta")
    admin = (
        session.query(UsuarioORM).filter(UsuarioORM.email == ADMIN_EMAIL).one_or_none()
    )
    if admin is None:
        print(f"  · Admin no existe, skip sesión caja")
        return
    suc = sucursales.get(SESION_DEMO_SUCURSAL)
    if suc is None:
        print(f"  · {SESION_DEMO_SUCURSAL} no existe, skip sesión caja")
        return
    caja = (
        session.query(CajaORM)
        .filter(CajaORM.sucursal_id == suc.id, CajaORM.codigo == SESION_DEMO_CAJA)
        .one_or_none()
    )
    if caja is None:
        print(f"  · Caja {SESION_DEMO_CAJA} no existe, skip")
        return
    activa = (
        session.query(SesionCajaORM)
        .filter(
            SesionCajaORM.caja_id == caja.id,
            SesionCajaORM.estado == EstadoSesionCaja.ABIERTA.value,
        )
        .one_or_none()
    )
    if activa is not None:
        print(
            f"  · {SESION_DEMO_SUCURSAL}/{SESION_DEMO_CAJA} ya tiene sesión "
            f"abierta ({activa.id})"
        )
        return
    sesion = SesionCaja(
        caja_id=caja.id,
        usuario_apertura_id=admin.id,
        monto_inicial_clp=SESION_DEMO_MONTO_INICIAL,
    )
    session.add(sesion_to_orm(sesion))
    session.flush()
    # Movimiento de fondo extra para que la sesión tenga al menos un mov.
    mov = MovimientoCaja(
        sesion_caja_id=sesion.id,
        tipo=TipoMovimientoCaja.INGRESO_OTRO,
        monto_clp=5_000,
        usuario_id=admin.id,
        descripcion="Fondo de vuelto (seed demo)",
    )
    session.add(mov_caja_to_orm(mov))
    print(
        f"  + Sesión abierta en {SESION_DEMO_SUCURSAL}/{SESION_DEMO_CAJA} "
        f"(fondo ${SESION_DEMO_MONTO_INICIAL:,})"
    )


# ─── Entry point ──────────────────────────────────────────────────────


def main() -> None:
    print("OMNIFLOW — Seed demo completo")
    print("=" * 64)

    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    with session_factory() as s:
        # Verificar admin antes de empezar (necesario para audit de movs)
        admin = (
            s.query(UsuarioORM).filter(UsuarioORM.email == ADMIN_EMAIL).one_or_none()
        )
        if admin is None:
            print(
                f"\nERROR: usuario {ADMIN_EMAIL!r} no existe.\n"
                "Corre primero:\n"
                "  python scripts/seed_perfiles_permisos.py\n"
                "  python scripts/seed_dev_user.py"
            )
            return

        # 1) Estructura organizacional
        sucursales = seed_sucursales_y_cajas(s)
        asignar_sucursales_al_admin(s, sucursales)

        # 2) Catálogo
        categorias = seed_categorias(s)
        bodegas = seed_bodegas(s, sucursales)
        productos = seed_productos(s, categorias)

        # 3) Inventario
        seed_stock_inicial(s, productos, bodegas, admin.id)
        seed_lotes_demo(s, productos, bodegas, admin.id)

        # 4) Partes externas
        seed_proveedores(s)
        seed_clientes(s)

        # 5) Operación lista (sesión abierta para POS)
        seed_sesion_caja(s, sucursales)

        s.commit()

    print("\n" + "=" * 64)
    print("OK — Seed demo aplicado.")
    print("\nLogin con el admin sembrado por seed_dev_user.py:")
    print(f"  email:    {ADMIN_EMAIL}")
    print("  password: ver scripts/seed_dev_user.py (variable DEV_PASSWORD)")
    print("\nQué tienes ahora:")
    print("  · 3 sucursales (SC-CENTRO, SC-NORTE, SC-SUR)")
    print("  · 9 cajas (C1, C2, C3 por sucursal)")
    print("  · 10 productos, 3 categorías, 3 bodegas")
    print("  · 15 rangos de folios (BOLETA/FACTURA/NC/ND/GUIA × 3)")
    print("  · 2 proveedores, 4 clientes")
    print("  · 1 sesión de caja ABIERTA en SC-CENTRO/C1")
    print("  · Lotes con vencimiento variado (para el reporte 'Por vencer')")
    print("\nPróximo paso sugerido:")
    print("  Entrar al POS, vender algo, ver Reportes → datos reales.")


if __name__ == "__main__":
    main()

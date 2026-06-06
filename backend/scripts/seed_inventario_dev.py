"""Seed idempotente de Inventario de desarrollo.

- Crea 3 categorías: Bebidas, Snacks, Limpieza.
- Crea 1 bodega por sucursal existente (CODIGO `B1`).
- Crea 5 productos de ejemplo con stock inicial en B1 de SC-CENTRO.
- Marca 2 productos como perecibles (controla_vencimiento) y crea lotes de
  ejemplo con fechas variadas (vencido, crítico, por vencer, vigente) en
  SC-CENTRO/B1 para que el reporte "por vencer" siempre muestre datos.

Uso:
    python scripts/seed_inventario_dev.py
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from erp.domain.entities.bodega import Bodega
from erp.domain.entities.categoria import Categoria
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.producto import Producto
from erp.domain.entities.stock import Stock
from erp.domain.utils.time import datetime_utc
from erp.infrastructure.config.settings import get_settings
from erp.infrastructure.db.engine import build_engine, build_session_factory
from erp.infrastructure.db.mappers.bodega import to_orm as bodega_to_orm
from erp.infrastructure.db.mappers.categoria import to_orm as categoria_to_orm
from erp.infrastructure.db.mappers.lote_inventario import to_orm as lote_to_orm
from erp.infrastructure.db.mappers.mov_inventario import to_orm as mov_to_orm
from erp.infrastructure.db.mappers.producto import to_orm as producto_to_orm
from erp.infrastructure.db.mappers.stock import to_orm as stock_to_orm
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.categoria import CategoriaORM
from erp.infrastructure.db.models.lote_inventario import LoteInventarioORM
from erp.infrastructure.db.models.producto import ProductoORM
from erp.infrastructure.db.models.stock import StockORM
from erp.infrastructure.db.models.sucursal import SucursalORM
from erp.infrastructure.db.models.usuario import UsuarioORM

CATEGORIAS = ["Bebidas", "Snacks", "Limpieza"]

# (sku, nombre, precio_clp, categoria_nombre, controla_vencimiento)
PRODUCTOS: list[tuple[str, str, int, str, bool]] = [
    ("COL-350", "Cola 350ml", 1200, "Bebidas", True),
    ("AGU-500", "Agua mineral 500ml", 800, "Bebidas", False),
    ("PAP-150", "Papas fritas 150g", 1500, "Snacks", True),
    ("CHO-100", "Chocolate 100g", 1800, "Snacks", False),
    ("DET-1L", "Detergente líquido 1L", 3500, "Limpieza", False),
]

STOCK_INICIAL = Decimal("50")
COSTO_INICIAL_CLP = 500

# Lotes de ejemplo para productos perecibles, relativos a HOY.
# (sku, dias_offset_vencimiento, numero_lote, cantidad, costo_unitario_clp)
LOTES_EJEMPLO: list[tuple[str, int, str, Decimal, int]] = [
    ("COL-350", -3, "L-VENCIDO-001", Decimal("10"), 500),      # vencido
    ("COL-350", 5, "L-CRITICO-002", Decimal("20"), 520),       # crítico (<=7d)
    ("PAP-150", 20, "L-PORVENCER-003", Decimal("15"), 900),    # por vencer (~20d)
    ("PAP-150", 180, "L-VIGENTE-004", Decimal("30"), 880),     # vigente (~6 meses)
]


def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    with session_factory() as s:
        # 1. Categorías
        cat_por_nombre: dict[str, CategoriaORM] = {}
        for nombre in CATEGORIAS:
            existente = (
                s.query(CategoriaORM).filter(CategoriaORM.nombre == nombre).one_or_none()
            )
            if existente is None:
                c = Categoria(nombre=nombre)
                orm = categoria_to_orm(c)
                s.add(orm)
                s.flush()
                cat_por_nombre[nombre] = orm
                print(f"Categoría creada: {nombre}")
            else:
                cat_por_nombre[nombre] = existente
                print(f"Categoría {nombre} ya existe.")

        # 2. Bodegas: una por sucursal
        sucursales = s.query(SucursalORM).all()
        if not sucursales:
            print(
                "AVISO: no hay sucursales. Corre primero scripts/seed_sucursales_dev.py"
            )
            return
        bodegas_por_sucursal: dict[str, BodegaORM] = {}
        for suc in sucursales:
            codigo_bodega = "B1"
            existente_b = (
                s.query(BodegaORM)
                .filter(BodegaORM.sucursal_id == suc.id, BodegaORM.codigo == codigo_bodega)
                .one_or_none()
            )
            if existente_b is None:
                bod = Bodega(
                    sucursal_id=suc.id,
                    codigo=codigo_bodega,
                    nombre=f"Bodega Principal {suc.codigo}",
                )
                orm = bodega_to_orm(bod)
                s.add(orm)
                s.flush()
                bodegas_por_sucursal[suc.codigo] = orm
                print(f"  + Bodega {codigo_bodega} creada en {suc.codigo}.")
            else:
                bodegas_por_sucursal[suc.codigo] = existente_b

        # 3. Productos
        prods_por_sku: dict[str, ProductoORM] = {}
        for sku, nombre, precio, cat_nombre, controla in PRODUCTOS:
            existente_p = (
                s.query(ProductoORM).filter(ProductoORM.sku == sku).one_or_none()
            )
            if existente_p is None:
                p = Producto(
                    sku=sku,
                    nombre=nombre,
                    precio_venta_clp=precio,
                    categoria_id=cat_por_nombre[cat_nombre].id,
                    controla_vencimiento=controla,
                )
                orm = producto_to_orm(p)
                s.add(orm)
                s.flush()
                prods_por_sku[sku] = orm
                print(f"  + Producto {sku} creado (perecible={controla}).")
            else:
                # Idempotente: asegurar el flag de control de vencimiento.
                if existente_p.controla_vencimiento != controla:
                    existente_p.controla_vencimiento = controla
                    print(f"  ~ Producto {sku}: controla_vencimiento={controla}")
                prods_por_sku[sku] = existente_p

        # 4. Stock inicial en SC-CENTRO/B1 (si existe)
        if "SC-CENTRO" in bodegas_por_sucursal:
            bodega = bodegas_por_sucursal["SC-CENTRO"]
            # Usuario admin para audit del mov
            admin = (
                s.query(UsuarioORM)
                .filter(UsuarioORM.email == "admin@minierp.cl")
                .one_or_none()
            )
            for sku, prod_orm in prods_por_sku.items():
                # Productos perecibles obtienen su stock vía lotes (paso 5) para
                # mantener el invariante SUM(lotes vivos) == stock.cantidad.
                if prod_orm.controla_vencimiento:
                    continue
                existente_st = (
                    s.query(StockORM)
                    .filter(
                        StockORM.producto_id == prod_orm.id,
                        StockORM.bodega_id == bodega.id,
                    )
                    .one_or_none()
                )
                if existente_st is None:
                    st = Stock(
                        producto_id=prod_orm.id,
                        bodega_id=bodega.id,
                    )
                    st.ingresar(STOCK_INICIAL, COSTO_INICIAL_CLP)
                    s.add(stock_to_orm(st))
                    if admin is not None:
                        mov = MovInventario(
                            producto_id=prod_orm.id,
                            bodega_id=bodega.id,
                            tipo=TipoMovInventario.ENTRADA,
                            cantidad=STOCK_INICIAL,
                            costo_unitario_clp=COSTO_INICIAL_CLP,
                            usuario_id=admin.id,
                            referencia_tipo="COMPRA",
                            referencia_id=prod_orm.id,
                            motivo="Seed inicial de inventario",
                            fecha=datetime_utc(),
                        )
                        s.add(mov_to_orm(mov))
                    print(f"  + Stock inicial {sku}: {STOCK_INICIAL} @ {COSTO_INICIAL_CLP}")

            # 5. Lotes de ejemplo para perecibles (SC-CENTRO/B1)
            hoy = date.today()
            for sku, offset_dias, numero_lote, cantidad, costo in LOTES_EJEMPLO:
                prod_orm = prods_por_sku.get(sku)
                if prod_orm is None:
                    continue
                existente_lote = (
                    s.query(LoteInventarioORM)
                    .filter(LoteInventarioORM.numero_lote == numero_lote)
                    .one_or_none()
                )
                if existente_lote is not None:
                    continue
                fecha_venc = hoy + timedelta(days=offset_dias)
                # fecha_ingreso no puede ser posterior al vencimiento.
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
                s.add(lote_to_orm(lote))

                # Stock agregado por bodega (suma de lotes vivos del producto).
                st = (
                    s.query(StockORM)
                    .filter(
                        StockORM.producto_id == prod_orm.id,
                        StockORM.bodega_id == bodega.id,
                    )
                    .one_or_none()
                )
                if st is None:
                    dom = Stock(producto_id=prod_orm.id, bodega_id=bodega.id)
                    dom.ingresar(cantidad, costo)
                    s.add(stock_to_orm(dom))
                else:
                    nueva_cant = st.cantidad + cantidad
                    valor_actual = st.cantidad * st.costo_promedio_clp
                    valor_ingreso = cantidad * costo
                    st.cantidad = nueva_cant
                    if nueva_cant > 0:
                        st.costo_promedio_clp = int(
                            ((valor_actual + valor_ingreso) / nueva_cant).to_integral_value()
                        )
                    st.version += 1

                if admin is not None:
                    mov = MovInventario(
                        producto_id=prod_orm.id,
                        bodega_id=bodega.id,
                        tipo=TipoMovInventario.ENTRADA,
                        cantidad=cantidad,
                        costo_unitario_clp=costo,
                        usuario_id=admin.id,
                        referencia_tipo="COMPRA",
                        referencia_id=prod_orm.id,
                        lote_id=lote.id,
                        motivo=f"Seed lote {numero_lote}",
                        fecha=datetime_utc(),
                    )
                    s.add(mov_to_orm(mov))
                print(
                    f"  + Lote {numero_lote} ({sku}): {cantidad} u, vence {fecha_venc}"
                )

        s.commit()
        print("OK: seed Inventario aplicado.")


if __name__ == "__main__":
    main()

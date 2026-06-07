"""Seed idempotente del catálogo de Permisos y Perfiles base.

Crea los permisos atómicos del sistema y los Perfiles sugeridos por CLAUDE.md
§3.2 con su set típico de permisos. Es seguro correrlo múltiples veces.

Uso:
    python scripts/seed_perfiles_permisos.py
"""
from __future__ import annotations

from erp.domain.entities.perfil import Perfil
from erp.domain.entities.permiso import Permiso
from erp.infrastructure.config.settings import get_settings
from erp.infrastructure.db.engine import build_engine, build_session_factory
from erp.infrastructure.db.mappers.perfil import to_orm as perfil_to_orm
from erp.infrastructure.db.mappers.permiso import to_orm as permiso_to_orm
from erp.infrastructure.db.models.perfil import PerfilORM
from erp.infrastructure.db.models.perfil_permiso import perfil_permiso_table
from erp.infrastructure.db.models.permiso import PermisoORM

# (codigo, descripcion)
PERMISOS_CATALOGO: list[tuple[str, str]] = [
    # Administración
    ("usuario.gestionar", "Crear, editar, desactivar usuarios y asignar perfiles"),
    ("perfil.gestionar", "Crear, editar, desactivar perfiles y asignar permisos"),
    ("permiso.ver", "Listar el catálogo de permisos"),
    ("audit.ver", "Visualizar el audit log"),
    ("config.global", "Modificar configuración global del sistema"),
    ("sucursal.gestionar", "Crear, editar, desactivar sucursales"),
    ("sucursal.ver", "Listar y consultar sucursales"),
    ("caja.gestionar", "Crear, editar, desactivar cajas en sucursales"),
    ("folio.gestionar", "Administrar rangos de folios SII"),
    # Ventas / POS
    ("venta.crear", "Procesar una venta en el POS"),
    ("venta.anular", "Anular una venta"),
    ("descuento.aprobar", "Aprobar descuentos sobre el precio"),
    ("precio.gestionar", "Gestionar precios de productos"),
    # Caja
    ("caja.operar", "Operar una sesión de caja (apertura/movimientos)"),
    ("caja.cerrar", "Cerrar y arquear la caja"),
    # Inventario
    ("inventario.ajustar", "Ajustar stock manualmente"),
    ("mercaderia.recepcionar", "Recepcionar mercadería desde compras"),
    ("stock.consultar", "Consultar stock disponible"),
    ("producto.gestionar", "Gestionar productos y categorías"),
    # Compras / Proveedores
    ("proveedor.gestionar", "Gestionar proveedores"),
    # Clientes
    ("cliente.consultar", "Consultar clientes y su estado de cuenta"),
    ("cliente.gestionar", "Crear, editar, desactivar y reactivar clientes"),
    # Devoluciones
    ("devolucion.autorizar", "Autorizar devoluciones de venta"),
    # Finanzas
    ("finanzas.ver", "Ver reportes financieros"),
    ("reportes.ver", "Ver reportes operacionales"),
    ("cxc.gestionar", "Gestionar cuentas por cobrar"),
    ("cxp.gestionar", "Gestionar cuentas por pagar"),
]

# Perfiles base. Mapean nombre -> (descripcion, lista de codigos de permisos)
PERFILES_BASE: list[tuple[str, str, list[str]]] = [
    (
        "Vendedor",
        "Cajero / Vendedor de POS",
        [
            "venta.crear",
            "stock.consultar",
            "cliente.consultar",
            "caja.operar",
            "sucursal.ver",
        ],
    ),
    (
        "Reponedor",
        "Reposición e ingreso de mercadería",
        [
            "inventario.ajustar",
            "mercaderia.recepcionar",
            "stock.consultar",
            "sucursal.ver",
        ],
    ),
    (
        "Jefe de Sucursal",
        "Supervisión operativa de la sucursal",
        [
            "venta.crear",
            "venta.anular",
            "stock.consultar",
            "cliente.consultar",
            "cliente.gestionar",
            "caja.operar",
            "caja.cerrar",
            "devolucion.autorizar",
            "descuento.aprobar",
            "inventario.ajustar",
            "mercaderia.recepcionar",
            "reportes.ver",
            "sucursal.ver",
        ],
    ),
    (
        "Contador",
        "Funciones contables y financieras",
        [
            "finanzas.ver",
            "reportes.ver",
            "cxc.gestionar",
            "cxp.gestionar",
            "audit.ver",
            "sucursal.ver",
        ],
    ),
    (
        "Administrador",
        "Administración de catálogos, sucursales y proveedores",
        [
            "precio.gestionar",
            "producto.gestionar",
            "proveedor.gestionar",
            "cliente.consultar",
            "cliente.gestionar",
            "reportes.ver",
            "stock.consultar",
            "sucursal.gestionar",
            "sucursal.ver",
            "caja.gestionar",
            "folio.gestionar",
            "venta.anular",
        ],
    ),
    (
        "Sysadmin",
        "Acceso total al sistema (incluye gestión de identidad)",
        [c for c, _ in PERMISOS_CATALOGO],
    ),
]


def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    with session_factory() as s:
        # 1. Asegurar permisos
        codigo_a_id: dict[str, str] = {}
        for codigo, descripcion in PERMISOS_CATALOGO:
            existente = (
                s.query(PermisoORM).filter(PermisoORM.codigo == codigo).one_or_none()
            )
            if existente is None:
                permiso = Permiso(codigo=codigo, descripcion=descripcion)
                s.add(permiso_to_orm(permiso))
                s.flush()
                codigo_a_id[codigo] = str(permiso.id)
            else:
                codigo_a_id[codigo] = str(existente.id)
                if existente.descripcion != descripcion:
                    existente.descripcion = descripcion

        # 2. Asegurar perfiles + asignaciones (idempotente: reemplaza set)
        es_sysadmin_nombre = "Sysadmin"
        todos_permiso_ids = list(codigo_a_id.values())

        for nombre, descripcion, codigos in PERFILES_BASE:
            es_sistema = nombre == es_sysadmin_nombre
            existente_perfil = (
                s.query(PerfilORM).filter(PerfilORM.nombre == nombre).one_or_none()
            )
            if existente_perfil is None:
                perfil = Perfil(nombre=nombre, descripcion=descripcion, es_sistema=es_sistema)
                s.add(perfil_to_orm(perfil))
                s.flush()
                perfil_id = perfil.id
            else:
                existente_perfil.descripcion = descripcion
                existente_perfil.activo = True
                existente_perfil.es_sistema = es_sistema
                perfil_id = existente_perfil.id

            # Sysadmin recibe TODOS los permisos existentes en la tabla (no solo los del catálogo).
            # Para otros perfiles: reemplaza el set con la lista definida en PERFILES_BASE.
            s.execute(
                perfil_permiso_table.delete().where(
                    perfil_permiso_table.c.perfil_id == perfil_id
                )
            )
            if es_sistema:
                permiso_ids = todos_permiso_ids
            else:
                permiso_ids = [codigo_a_id[c] for c in codigos if c in codigo_a_id]
            if permiso_ids:
                s.execute(
                    perfil_permiso_table.insert(),
                    [
                        {"perfil_id": perfil_id, "permiso_id": pid}
                        for pid in permiso_ids
                    ],
                )

        s.commit()
        print(
            f"OK: {len(PERMISOS_CATALOGO)} permisos y {len(PERFILES_BASE)} perfiles seedeados."
        )


if __name__ == "__main__":
    main()

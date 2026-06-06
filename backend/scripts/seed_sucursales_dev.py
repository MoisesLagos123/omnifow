"""Seed idempotente de sucursales / cajas / folios de desarrollo.

- Crea 2 sucursales: SC-CENTRO y SC-NORTE.
- Crea 1-2 cajas por sucursal.
- Crea un rango BOLETA por sucursal.
- Asigna ambas sucursales al usuario `admin@minierp.cl` (si existe).

Uso:
    python scripts/seed_sucursales_dev.py
"""
from __future__ import annotations

from erp.domain.entities.caja import Caja
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.sucursal import Sucursal
from erp.domain.value_objects.rut import Rut
from erp.domain.value_objects.tipo_documento import TipoDocumento
from erp.infrastructure.config.settings import get_settings
from erp.infrastructure.db.engine import build_engine, build_session_factory
from erp.infrastructure.db.mappers.caja import to_orm as caja_to_orm
from erp.infrastructure.db.mappers.rango_folios import to_orm as rango_to_orm
from erp.infrastructure.db.mappers.sucursal import to_orm as sucursal_to_orm
from erp.infrastructure.db.models.caja import CajaORM
from erp.infrastructure.db.models.rango_folios import RangoFoliosORM
from erp.infrastructure.db.models.sucursal import SucursalORM
from erp.infrastructure.db.models.usuario import UsuarioORM
from erp.infrastructure.db.models.usuario_sucursal import usuario_sucursal_table

ADMIN_EMAIL = "admin@minierp.cl"

SUCURSALES: list[tuple[str, str, str, list[str]]] = [
    # (codigo, nombre, rut_emisor, cajas)
    # RUT con DV calculado por módulo 11 (76123456-0 es el DV correcto)
    ("SC-CENTRO", "Sucursal Centro", "76123456-0", ["C1", "C2"]),
    ("SC-NORTE", "Sucursal Norte", "76123456-0", ["C1"]),
]


def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    with session_factory() as s:
        sucursal_ids: list[str] = []
        for codigo, nombre, rut_emisor, cajas_codigos in SUCURSALES:
            existente = (
                s.query(SucursalORM)
                .filter(SucursalORM.codigo == codigo)
                .one_or_none()
            )
            if existente is None:
                suc = Sucursal(
                    codigo=codigo,
                    nombre=nombre,
                    rut_emisor=Rut(rut_emisor),
                )
                s.add(sucursal_to_orm(suc))
                s.flush()
                sucursal_id = suc.id
                print(f"Sucursal creada: {codigo}")
            else:
                sucursal_id = existente.id
                print(f"Sucursal {codigo} ya existe.")
            sucursal_ids.append(str(sucursal_id))

            # Cajas
            for cod in cajas_codigos:
                caja_existente = (
                    s.query(CajaORM)
                    .filter(
                        CajaORM.sucursal_id == sucursal_id,
                        CajaORM.codigo == cod,
                    )
                    .one_or_none()
                )
                if caja_existente is None:
                    caja = Caja(
                        sucursal_id=sucursal_id,
                        codigo=cod,
                        nombre=f"Caja {cod} - {codigo}",
                    )
                    s.add(caja_to_orm(caja))
                    print(f"  + Caja {cod} creada en {codigo}.")

            # Rango BOLETA
            rango_existente = (
                s.query(RangoFoliosORM)
                .filter(
                    RangoFoliosORM.sucursal_id == sucursal_id,
                    RangoFoliosORM.tipo_documento == TipoDocumento.BOLETA.value,
                )
                .one_or_none()
            )
            if rango_existente is None:
                rango = RangoFolios(
                    sucursal_id=sucursal_id,
                    tipo_documento=TipoDocumento.BOLETA,
                    desde=1,
                    hasta=1000,
                )
                s.add(rango_to_orm(rango))
                print(f"  + Rango BOLETA 1-1000 creado en {codigo}.")

        # Asignación al admin
        admin = (
            s.query(UsuarioORM).filter(UsuarioORM.email == ADMIN_EMAIL).one_or_none()
        )
        if admin is None:
            print(
                f"AVISO: usuario {ADMIN_EMAIL} no existe. Corre primero "
                "scripts/seed_dev_user.py para asignarle sucursales."
            )
        else:
            for sid in sucursal_ids:
                ya = s.execute(
                    usuario_sucursal_table.select().where(
                        usuario_sucursal_table.c.usuario_id == admin.id,
                        usuario_sucursal_table.c.sucursal_id == sid,
                    )
                ).first()
                if ya is None:
                    s.execute(
                        usuario_sucursal_table.insert().values(
                            usuario_id=admin.id, sucursal_id=sid
                        )
                    )
                    print(f"  + Asignada {sid} a {ADMIN_EMAIL}")

        s.commit()
        print("OK: seed sucursales/cajas/folios aplicado.")


if __name__ == "__main__":
    main()

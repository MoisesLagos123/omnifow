"""Seed idempotente de una sesión de caja de desarrollo.

- Abre una sesión en la primera caja de la sucursal SC-CENTRO con monto inicial
  de 50.000 CLP (si no hay ya una sesión ABIERTA).
- Registra 1-2 movimientos de ejemplo (INGRESO_OTRO + EGRESO_GASTO).

Idempotente: si la caja ya tiene una sesión ABIERTA, no la duplica ni vuelve a
crear los movimientos. Requiere haber corrido antes:
    python scripts/seed_dev_user.py
    python scripts/seed_sucursales_dev.py

Uso:
    python scripts/seed_caja_dev.py
"""
from __future__ import annotations

from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja
from erp.infrastructure.config.settings import get_settings
from erp.infrastructure.db.engine import build_engine, build_session_factory
from erp.infrastructure.db.mappers.movimiento_caja import to_orm as mov_to_orm
from erp.infrastructure.db.mappers.sesion_caja import to_orm as sesion_to_orm
from erp.infrastructure.db.models.caja import CajaORM
from erp.infrastructure.db.models.movimiento_caja import MovimientoCajaORM
from erp.infrastructure.db.models.sesion_caja import SesionCajaORM
from erp.infrastructure.db.models.sucursal import SucursalORM
from erp.infrastructure.db.models.usuario import UsuarioORM

ADMIN_EMAIL = "admin@minierp.cl"
SUCURSAL_CODIGO = "SC-CENTRO"
MONTO_INICIAL_CLP = 50_000

MOVIMIENTOS_EJEMPLO: list[tuple[TipoMovimientoCaja, int, str]] = [
    (TipoMovimientoCaja.INGRESO_OTRO, 10_000, "Fondo extra de vuelto"),
    (TipoMovimientoCaja.EGRESO_GASTO, 3_500, "Compra de bolsas"),
]


def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    with session_factory() as s:
        admin = (
            s.query(UsuarioORM).filter(UsuarioORM.email == ADMIN_EMAIL).one_or_none()
        )
        if admin is None:
            print(
                f"AVISO: usuario {ADMIN_EMAIL} no existe. Corre primero "
                "scripts/seed_dev_user.py."
            )
            return

        sucursal = (
            s.query(SucursalORM)
            .filter(SucursalORM.codigo == SUCURSAL_CODIGO)
            .one_or_none()
        )
        if sucursal is None:
            print(
                f"AVISO: sucursal {SUCURSAL_CODIGO} no existe. Corre primero "
                "scripts/seed_sucursales_dev.py."
            )
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

        activa = (
            s.query(SesionCajaORM)
            .filter(
                SesionCajaORM.caja_id == caja.id,
                SesionCajaORM.estado == EstadoSesionCaja.ABIERTA.value,
            )
            .one_or_none()
        )
        if activa is not None:
            print(
                f"Caja {caja.codigo} ya tiene una sesión ABIERTA "
                f"({activa.id}); no se duplica."
            )
            return

        sesion = SesionCaja(
            caja_id=caja.id,
            usuario_apertura_id=admin.id,
            monto_inicial_clp=MONTO_INICIAL_CLP,
        )
        s.add(sesion_to_orm(sesion))
        s.flush()
        print(
            f"Sesión abierta en caja {caja.codigo} ({sesion.id}) con "
            f"monto inicial {MONTO_INICIAL_CLP} CLP."
        )

        for tipo, monto, descripcion in MOVIMIENTOS_EJEMPLO:
            mov = MovimientoCaja(
                sesion_caja_id=sesion.id,
                tipo=tipo,
                monto_clp=monto,
                usuario_id=admin.id,
                descripcion=descripcion,
            )
            s.add(mov_to_orm(mov))
            print(f"  + Movimiento {tipo.value} {monto} CLP — {descripcion}")

        # Confirmar que el flush no rompió ningún check (paranoia)
        _ = s.query(MovimientoCajaORM).count()

        s.commit()
        print("OK: seed de caja (operación) aplicado.")


if __name__ == "__main__":
    main()

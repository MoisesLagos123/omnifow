"""Seed idempotente de clientes de desarrollo.

Crea 4 clientes de ejemplo con RUTs válidos (DV correcto por módulo 11).
Es seguro correrlo múltiples veces (no duplica por RUT).

Uso:
    python scripts/seed_clientes_dev.py
"""
from __future__ import annotations

from erp.domain.entities.cliente import Cliente
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.config.settings import get_settings
from erp.infrastructure.db.engine import build_engine, build_session_factory
from erp.infrastructure.db.mappers.cliente import to_orm as cliente_to_orm
from erp.infrastructure.db.models.cliente import ClienteORM

# (rut, razon_social, giro, comuna, region, email, telefono)
# RUTs pre-validados (DV correcto): 11111111-1, 12345678-5, 22222222-2, 76123456-0
CLIENTES: list[tuple[str, str, str | None, str | None, str | None, str | None, str | None]] = [
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
        "12345678-5",
        "Comercializadora Andes Ltda.",
        "Venta al por menor",
        "Providencia",
        "Metropolitana",
        "contacto@andes.cl",
        "+56222345678",
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
        "76123456-0",
        "Distribuidora Norte SpA",
        "Distribución mayorista",
        "Antofagasta",
        "Antofagasta",
        "ventas@distnorte.cl",
        None,
    ),
]


def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    creados = 0
    with session_factory() as s:
        for rut, razon, giro, comuna, region, email, telefono in CLIENTES:
            rut_norm = str(Rut(rut))
            existente = (
                s.query(ClienteORM)
                .filter(ClienteORM.rut == rut_norm)
                .one_or_none()
            )
            if existente is not None:
                print(f"Cliente {rut_norm} ya existe.")
                continue
            cliente = Cliente(
                rut=Rut(rut),
                razon_social=razon,
                giro=giro,
                comuna=comuna,
                region=region,
                email=email,
                telefono=telefono,
            )
            s.add(cliente_to_orm(cliente))
            creados += 1
            print(f"  + Cliente creado: {rut_norm} - {razon}")

        s.commit()
        print(f"OK: seed clientes aplicado ({creados} creados).")


if __name__ == "__main__":
    main()

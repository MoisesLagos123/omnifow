"""Crea un usuario de desarrollo para probar el login.

Uso:
    python scripts/seed_dev_user.py

Crea: admin@minierp.cl / Admin12345! (RUT 11111111-1)
Si el usuario ya existe, no recrea, pero sí asegura el perfil Sysadmin.
Requiere haber corrido `seed_perfiles_permisos.py` previamente.
"""
from __future__ import annotations

from erp.adapters.security.argon2_hasher import Argon2idHasher
from erp.domain.entities.usuario import Usuario
from erp.domain.value_objects.rut import Rut
from erp.infrastructure.config.settings import get_settings
from erp.infrastructure.db.engine import build_engine, build_session_factory
from erp.infrastructure.db.mappers.usuario import to_orm
from erp.infrastructure.db.models.perfil import PerfilORM
from erp.infrastructure.db.models.usuario import UsuarioORM
from erp.infrastructure.db.models.usuario_perfil import usuario_perfil_table

EMAIL = "admin@minierp.cl"
PASSWORD = "Admin12345!"
RUT_VALOR = "11111111-1"
NOMBRE = "Administrador Dev"
PERFIL_NOMBRE = "Sysadmin"


def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    hasher = Argon2idHasher()

    with session_factory() as s:
        existente = s.query(UsuarioORM).filter(UsuarioORM.email == EMAIL).one_or_none()
        if existente is None:
            usuario = Usuario(
                rut=Rut(RUT_VALOR),
                email=EMAIL,
                nombre=NOMBRE,
                password_hash=hasher.hash(PASSWORD),
            )
            s.add(to_orm(usuario))
            s.flush()
            usuario_id = usuario.id
            print(f"Usuario seed creado: {EMAIL} (password: {PASSWORD})")
        else:
            usuario_id = existente.id
            print(f"Usuario {EMAIL} ya existe (id={usuario_id}).")

        sysadmin = s.query(PerfilORM).filter(PerfilORM.nombre == PERFIL_NOMBRE).one_or_none()
        if sysadmin is None:
            print(
                f"AVISO: el perfil '{PERFIL_NOMBRE}' no existe."
                " Corre primero scripts/seed_perfiles_permisos.py."
            )
            s.commit()
            return

        ya_asignado = s.execute(
            usuario_perfil_table.select().where(
                usuario_perfil_table.c.usuario_id == usuario_id,
                usuario_perfil_table.c.perfil_id == sysadmin.id,
            )
        ).first()
        if ya_asignado is None:
            s.execute(
                usuario_perfil_table.insert().values(
                    usuario_id=usuario_id, perfil_id=sysadmin.id
                )
            )
            print(f"Asignado perfil '{PERFIL_NOMBRE}' a {EMAIL}.")

        s.commit()


if __name__ == "__main__":
    main()

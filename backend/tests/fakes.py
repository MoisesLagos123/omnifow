"""Implementaciones fake/in-memory para tests unitarios."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import TracebackType
from typing import Any
from uuid import UUID

from erp.application.ports.repositories import (
    AuditLogEntry,
    AuditLogPagina,
    CategoriasPagina,
    ClientesPagina,
    CompraConDetalles,
    CompraListItem,
    ComprasPagina,
    CxCConAbonos,
    CxCListItem,
    CxCPagina,
    CxPConAbonos,
    CxPListItem,
    CxPPagina,
    DetalleDevolucionInfo,
    DevolucionConDetalles,
    DevolucionListItem,
    DevolucionesPagina,
    DocumentoListItem,
    DocumentosPagina,
    IntentoLogin,
    LotePorVencer,
    MovInventarioConDetalles,
    MovInventarioPagina,
    PasswordResetTokenRecord,
    PerfilConContadores,
    PerfilesPagina,
    ProductoPosListado,
    ProductosPagina,
    ProveedorConContadores,
    ProveedoresPagina,
    RefreshTokenRecord,
    ResumenTipoMovimiento,
    SesionCajaListItem,
    SesionesCajaPagina,
    StockPorBodega,
    SucursalConContadores,
    SucursalesPagina,
    UsuarioAsignadoResumen,
    UsuarioListado,
    UsuariosPagina,
    VentaListado,
    VentasPagina,
)
from erp.application.ports.token_provider import (
    DecodedRefreshToken,
    IssuedAccessToken,
    IssuedRefreshToken,
)
from erp.domain.exceptions import RefreshTokenInvalidoError
from erp.domain.entities.abono_cxc import AbonoCxC
from erp.domain.entities.abono_cxp import AbonoCxP
from erp.domain.entities.guia_despacho import DetalleGuiaDespacho, GuiaDespacho
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.compra import Compra, EstadoCompra
from erp.domain.entities.cuenta_por_cobrar import CuentaPorCobrar, EstadoCxC
from erp.domain.entities.cuenta_por_pagar import CuentaPorPagar, EstadoCxP
from erp.domain.entities.detalle_compra import DetalleCompra
from erp.domain.entities.proveedor import Proveedor
from erp.domain.entities.caja import Caja
from erp.domain.entities.categoria import Categoria
from erp.domain.entities.cliente import Cliente
from erp.domain.entities.detalle_venta import DetalleVenta
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.pago import Pago
from erp.domain.entities.perfil import Perfil
from erp.domain.entities.permiso import Permiso
from erp.domain.entities.producto import Producto
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.reserva_stock import EstadoReserva, ReservaStock
from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.usuario import Usuario
from erp.domain.entities.detalle_devolucion import DetalleDevolucion
from erp.domain.entities.devolucion import Devolucion
from erp.domain.entities.venta import EstadoVenta, Venta
from erp.domain.utils.ids import new_uuid7
from erp.domain.value_objects.tipo_documento import TipoDocumento


class FakeClock:
    def __init__(self, ts: datetime | None = None) -> None:
        self._ts = ts or datetime(2026, 5, 2, 12, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._ts

    def advance(self, **kwargs: float) -> None:
        self._ts = self._ts + timedelta(**kwargs)


class FakeUoW:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> "FakeUoW":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        if exc is not None and not self.committed:
            self.rolled_back = True
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class FakeUsuarioRepo:
    def __init__(self) -> None:
        self._by_email: dict[str, Usuario] = {}
        self._by_rut: dict[str, Usuario] = {}
        self._by_id: dict[UUID, Usuario] = {}
        # usuario_id -> set[perfil_id]
        self._asignaciones: dict[UUID, set[UUID]] = {}
        # usuario_id -> set[sucursal_id]
        self._sucursales_asig: dict[UUID, set[UUID]] = {}
        # perfil_id -> Perfil
        self.perfiles_db: dict[UUID, Perfil] = {}
        # perfil_id -> set[Permiso]
        self.permisos_por_perfil: dict[UUID, set[Permiso]] = {}

    def add(self, usuario: Usuario) -> None:
        self._by_email[usuario.email.lower()] = usuario
        self._by_rut[str(usuario.rut)] = usuario
        self._by_id[usuario.id] = usuario

    def obtener_por_email(self, email: str) -> Usuario | None:
        return self._by_email.get(email.strip().lower())

    def obtener_por_rut(self, rut: str) -> Usuario | None:
        return self._by_rut.get(rut.strip())

    def obtener(self, usuario_id: UUID) -> Usuario | None:
        return self._by_id.get(usuario_id)

    def guardar(self, usuario: Usuario) -> None:
        self._by_email[usuario.email.lower()] = usuario
        self._by_rut[str(usuario.rut)] = usuario
        self._by_id[usuario.id] = usuario

    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> UsuariosPagina:
        items = list(self._by_id.values())
        if q:
            ql = q.lower()
            items = [u for u in items if ql in u.email.lower() or ql in u.nombre.lower()]
        if activo is not None:
            items = [u for u in items if u.activo is activo]
        items.sort(key=lambda u: u.email)
        total = len(items)
        page = items[offset : offset + limit]
        return UsuariosPagina(
            items=[
                UsuarioListado(
                    id=u.id,
                    rut=str(u.rut),
                    email=u.email,
                    nombre=u.nombre,
                    activo=u.activo,
                    perfiles=[self.perfiles_db[pid].nombre for pid in self._asignaciones.get(u.id, set()) if pid in self.perfiles_db],
                )
                for u in page
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def perfiles_de(self, usuario_id: UUID) -> list[Perfil]:
        return [
            self.perfiles_db[pid]
            for pid in self._asignaciones.get(usuario_id, set())
            if pid in self.perfiles_db
        ]

    def permisos_efectivos_de(self, usuario_id: UUID) -> list[str]:
        codigos: set[str] = set()
        for pid in self._asignaciones.get(usuario_id, set()):
            perfil = self.perfiles_db.get(pid)
            if perfil is None or not perfil.activo:
                continue
            for permiso in self.permisos_por_perfil.get(pid, set()):
                codigos.add(permiso.codigo)
        return sorted(codigos)

    def asignar_perfiles(self, usuario_id: UUID, perfil_ids: list[UUID]) -> None:
        self._asignaciones[usuario_id] = set(perfil_ids)

    # --- Sucursales ---
    def sucursales_de(self, usuario_id: UUID) -> list[UUID]:
        return sorted(self._sucursales_asig.get(usuario_id, set()))

    def asignar_sucursales(
        self, usuario_id: UUID, sucursal_ids: list[UUID]
    ) -> None:
        self._sucursales_asig[usuario_id] = set(sucursal_ids)


class FakePerfilRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Perfil] = {}
        # Almacenamos permisos por perfil como dict[id→Permiso]: Permiso es dataclass mutable y no hashable.
        self._permisos: dict[UUID, dict[UUID, Permiso]] = {}
        self.usuarios_activos_por_perfil: dict[UUID, int] = {}
        # perfil_id -> lista de usuarios asignados (resumen) para mensajes de error
        self.usuarios_resumen_por_perfil: dict[UUID, list[UsuarioAsignadoResumen]] = {}
        # Catálogo de permisos (set por tests que necesitan trazabilidad real al asignar).
        self.catalogo_permisos: dict[UUID, Permiso] = {}

    def add(self, perfil: Perfil) -> None:
        self._by_id[perfil.id] = perfil

    def guardar(self, perfil: Perfil) -> None:
        self._by_id[perfil.id] = perfil

    def obtener(self, perfil_id: UUID) -> Perfil | None:
        return self._by_id.get(perfil_id)

    def obtener_por_nombre(self, nombre: str) -> Perfil | None:
        for p in self._by_id.values():
            if p.nombre.lower() == nombre.strip().lower():
                return p
        return None

    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> PerfilesPagina:
        items = list(self._by_id.values())
        if q:
            ql = q.lower()
            items = [
                p
                for p in items
                if ql in p.nombre.lower() or ql in (p.descripcion or "").lower()
            ]
        if activo is not None:
            items = [p for p in items if p.activo is activo]
        items.sort(key=lambda p: p.nombre)
        total = len(items)
        page = items[offset : offset + limit]
        return PerfilesPagina(
            items=[
                PerfilConContadores(
                    perfil=p,
                    cantidad_permisos=len(self._permisos.get(p.id, {})),
                    cantidad_usuarios=self.usuarios_activos_por_perfil.get(p.id, 0),
                )
                for p in page
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def listar_por_ids(self, perfil_ids: list[UUID]) -> list[Perfil]:
        return [self._by_id[pid] for pid in perfil_ids if pid in self._by_id]

    def permisos_de(self, perfil_id: UUID) -> list[Permiso]:
        return sorted(self._permisos.get(perfil_id, {}).values(), key=lambda p: p.codigo)

    def asignar_permisos(self, perfil_id: UUID, permiso_ids: list[UUID]) -> None:
        resueltos: dict[UUID, Permiso] = {}
        for i, pid in enumerate(permiso_ids):
            permiso = self.catalogo_permisos.get(pid)
            if permiso is None:
                # Permiso sintético para tests legacy que no setean catálogo.
                permiso = Permiso(codigo=f"x.y_{i}", id=pid)
            resueltos[permiso.id] = permiso
        self._permisos[perfil_id] = resueltos

    def cantidad_usuarios_activos(self, perfil_id: UUID) -> int:
        return self.usuarios_activos_por_perfil.get(perfil_id, 0)

    def usuarios_activos_resumen(
        self, perfil_id: UUID, *, limit: int = 10
    ) -> list[UsuarioAsignadoResumen]:
        return sorted(
            self.usuarios_resumen_por_perfil.get(perfil_id, []),
            key=lambda u: u.nombre,
        )[:limit]


class FakePermisoRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Permiso] = {}
        self._by_codigo: dict[str, Permiso] = {}

    def add(self, permiso: Permiso) -> None:
        self._by_id[permiso.id] = permiso
        self._by_codigo[permiso.codigo] = permiso

    def guardar(self, permiso: Permiso) -> None:
        self.add(permiso)

    def obtener(self, permiso_id: UUID) -> Permiso | None:
        return self._by_id.get(permiso_id)

    def obtener_por_codigo(self, codigo: str) -> Permiso | None:
        return self._by_codigo.get(codigo.strip().lower())

    def listar(self) -> list[Permiso]:
        return sorted(self._by_id.values(), key=lambda p: p.codigo)

    def listar_por_ids(self, permiso_ids: list[UUID]) -> list[Permiso]:
        return [self._by_id[pid] for pid in permiso_ids if pid in self._by_id]


class FakeRefreshRepo:
    def __init__(self) -> None:
        self.records: list[RefreshTokenRecord] = []

    def guardar(self, token: RefreshTokenRecord) -> None:
        self.records.append(token)

    def obtener_por_jti(self, jti: UUID) -> RefreshTokenRecord | None:
        for r in self.records:
            if r.jti == jti:
                return r
        return None

    def marcar_revocado(self, jti: UUID, ahora: datetime) -> None:
        for i, r in enumerate(self.records):
            if r.jti == jti and r.revocado_en is None:
                self.records[i] = RefreshTokenRecord(
                    jti=r.jti,
                    usuario_id=r.usuario_id,
                    emitido_en=r.emitido_en,
                    expira_en=r.expira_en,
                    ip=r.ip,
                    user_agent=r.user_agent,
                    revocado_en=ahora,
                )
                return

    def revocar_todos_de(self, usuario_id: UUID, ahora: datetime) -> None:
        for i, r in enumerate(self.records):
            if r.usuario_id == usuario_id and r.revocado_en is None:
                self.records[i] = RefreshTokenRecord(
                    jti=r.jti,
                    usuario_id=r.usuario_id,
                    emitido_en=r.emitido_en,
                    expira_en=r.expira_en,
                    ip=r.ip,
                    user_agent=r.user_agent,
                    revocado_en=ahora,
                )


class FakeIntentosRepo:
    def __init__(self) -> None:
        self.intentos: list[IntentoLogin] = []

    def guardar(self, intento: IntentoLogin) -> None:
        self.intentos.append(intento)


class FakeAuditPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publicar(
        self,
        *,
        accion: str,
        resultado: str,
        usuario_id: UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        recurso_tipo: str | None = None,
        recurso_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "accion": accion,
                "resultado": resultado,
                "usuario_id": usuario_id,
                "recurso_tipo": recurso_tipo,
                "recurso_id": recurso_id,
                "metadata": metadata,
                "before": before,
                "after": after,
            }
        )


class FakeHasher:
    """Hasher reversible-trivialmente (solo tests)."""

    def hash(self, password: str) -> str:
        return f"hashed::{password}"

    def verify(self, hashed: str, password: str) -> bool:
        return hashed == f"hashed::{password}"


class FakeTokenProvider:
    def issue_access(
        self,
        *,
        usuario_id: UUID,
        perfiles: list[str],
        permisos: list[str],
        sucursales: list[UUID],
    ) -> IssuedAccessToken:
        return IssuedAccessToken(
            token=f"access::{usuario_id}",
            expires_at=datetime(2026, 5, 2, 12, 15, tzinfo=timezone.utc),
            expires_in_seconds=900,
        )

    def issue_refresh(self, *, usuario_id: UUID) -> IssuedRefreshToken:
        jti = new_uuid7()
        return IssuedRefreshToken(
            token=f"refresh::{usuario_id}::{jti}",
            jti=jti,
            expires_at=datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc),
            expires_in_seconds=604800,
        )

    def decode_refresh(self, token: str) -> DecodedRefreshToken:
        # Formato esperado en tests: "refresh::<usuario_id>::<jti>"
        # o "refresh::<usuario_id>::<jti>::expired" para forzar exp pasado.
        if not token.startswith("refresh::"):
            raise RefreshTokenInvalidoError()
        parts = token.split("::")
        if len(parts) < 3:
            raise RefreshTokenInvalidoError()
        try:
            usuario_id = UUID(parts[1])
            jti = UUID(parts[2])
        except ValueError as exc:
            raise RefreshTokenInvalidoError() from exc
        # Por defecto el fake emite tokens con exp = 2026-05-09; permitimos
        # forzar uno expirado anteponiendo "expired" como 4to segmento.
        expired = len(parts) >= 4 and parts[3] == "expired"
        expires_at = (
            datetime(2020, 1, 1, tzinfo=timezone.utc)
            if expired
            else datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc)
        )
        return DecodedRefreshToken(
            usuario_id=usuario_id, jti=jti, expires_at=expires_at
        )


class FakeSucursalRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Sucursal] = {}
        # sucursal_id -> conteos arbitrarios para tests
        self.cajas_activas: dict[UUID, int] = {}
        self.usuarios_asignados: dict[UUID, int] = {}

    def add(self, sucursal: Sucursal) -> None:
        self._by_id[sucursal.id] = sucursal

    def guardar(self, sucursal: Sucursal) -> None:
        self._by_id[sucursal.id] = sucursal

    def obtener(self, sucursal_id: UUID) -> Sucursal | None:
        return self._by_id.get(sucursal_id)

    def obtener_por_codigo(self, codigo: str) -> Sucursal | None:
        for s in self._by_id.values():
            if s.codigo.upper() == codigo.strip().upper():
                return s
        return None

    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> SucursalesPagina:
        items = list(self._by_id.values())
        if q:
            ql = q.lower()
            items = [
                s for s in items if ql in s.nombre.lower() or ql in s.codigo.lower()
            ]
        if activo is not None:
            items = [s for s in items if s.activo is activo]
        items.sort(key=lambda s: s.codigo)
        total = len(items)
        page = items[offset : offset + limit]
        return SucursalesPagina(
            items=[
                SucursalConContadores(
                    sucursal=s,
                    cantidad_cajas_activas=self.cajas_activas.get(s.id, 0),
                    cantidad_usuarios_asignados=self.usuarios_asignados.get(s.id, 0),
                )
                for s in page
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def listar_por_ids(self, sucursal_ids: list[UUID]) -> list[Sucursal]:
        return [self._by_id[sid] for sid in sucursal_ids if sid in self._by_id]

    def cantidad_cajas_activas(self, sucursal_id: UUID) -> int:
        return self.cajas_activas.get(sucursal_id, 0)

    def cantidad_usuarios_asignados(self, sucursal_id: UUID) -> int:
        return self.usuarios_asignados.get(sucursal_id, 0)


class FakeCajaRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Caja] = {}

    def add(self, caja: Caja) -> None:
        self._by_id[caja.id] = caja

    def guardar(self, caja: Caja) -> None:
        self._by_id[caja.id] = caja

    def obtener(self, caja_id: UUID) -> Caja | None:
        return self._by_id.get(caja_id)

    def obtener_por_codigo(self, sucursal_id: UUID, codigo: str) -> Caja | None:
        for c in self._by_id.values():
            if c.sucursal_id == sucursal_id and c.codigo.upper() == codigo.strip().upper():
                return c
        return None

    def listar_por_sucursal(
        self, sucursal_id: UUID, *, activo: bool | None = None
    ) -> list[Caja]:
        items = [c for c in self._by_id.values() if c.sucursal_id == sucursal_id]
        if activo is not None:
            items = [c for c in items if c.activo is activo]
        items.sort(key=lambda c: c.codigo)
        return items

    def cantidad_sesiones_abiertas(self, caja_id: UUID) -> int:
        return 0


class FakeRangoFoliosRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, RangoFolios] = {}

    def add(self, rango: RangoFolios) -> None:
        self._by_id[rango.id] = rango

    def guardar(self, rango: RangoFolios) -> None:
        self._by_id[rango.id] = rango

    def obtener(self, rango_id: UUID) -> RangoFolios | None:
        return self._by_id.get(rango_id)

    def listar_por_sucursal(
        self,
        sucursal_id: UUID,
        *,
        tipo: TipoDocumento | None = None,
        activo: bool | None = None,
    ) -> list[RangoFolios]:
        items = [r for r in self._by_id.values() if r.sucursal_id == sucursal_id]
        if tipo is not None:
            items = [r for r in items if r.tipo_documento is tipo]
        if activo is not None:
            items = [r for r in items if r.activo is activo]
        items.sort(key=lambda r: (r.tipo_documento.value, r.desde))
        return items

    def obtener_activo_para(
        self, sucursal_id: UUID, tipo: TipoDocumento
    ) -> RangoFolios | None:
        candidatos = [
            r
            for r in self._by_id.values()
            if r.sucursal_id == sucursal_id
            and r.tipo_documento is tipo
            and r.activo
            and not r.agotado
        ]
        candidatos.sort(key=lambda r: r.desde)
        return candidatos[0] if candidatos else None

    def obtener_activo_para_actualizar(
        self, sucursal_id: UUID, tipo: TipoDocumento
    ) -> RangoFolios | None:
        # In-memory: sin lock real.
        return self.obtener_activo_para(sucursal_id, tipo)

    def existe_overlap(
        self,
        sucursal_id: UUID,
        tipo: TipoDocumento,
        desde: int,
        hasta: int,
        *,
        excluyendo_id: UUID | None = None,
    ) -> bool:
        for r in self._by_id.values():
            if r.sucursal_id != sucursal_id or r.tipo_documento is not tipo:
                continue
            if excluyendo_id is not None and r.id == excluyendo_id:
                continue
            if not (r.hasta < desde or r.desde > hasta):
                return True
        return False


# ---------------- Inventario ----------------

class FakeCategoriaRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Categoria] = {}
        self.productos_por_categoria: dict[UUID, int] = {}

    def add(self, c: Categoria) -> None:
        self._by_id[c.id] = c

    def guardar(self, c: Categoria) -> None:
        self._by_id[c.id] = c

    def obtener(self, categoria_id: UUID) -> Categoria | None:
        return self._by_id.get(categoria_id)

    def obtener_por_nombre(self, nombre: str) -> Categoria | None:
        n = nombre.strip().lower()
        for c in self._by_id.values():
            if c.nombre.lower() == n:
                return c
        return None

    def listar(
        self, *, q: str | None, limit: int, offset: int
    ) -> CategoriasPagina:
        items = list(self._by_id.values())
        if q:
            ql = q.lower()
            items = [c for c in items if ql in c.nombre.lower()]
        items.sort(key=lambda c: c.nombre)
        total = len(items)
        return CategoriasPagina(
            items=items[offset : offset + limit],
            total=total,
            limit=limit,
            offset=offset,
        )

    def cantidad_productos(self, categoria_id: UUID) -> int:
        return self.productos_por_categoria.get(categoria_id, 0)

    def eliminar(self, categoria_id: UUID) -> None:
        self._by_id.pop(categoria_id, None)


class FakeBodegaRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Bodega] = {}
        self.stock_por_bodega: dict[UUID, bool] = {}

    def add(self, b: Bodega) -> None:
        self._by_id[b.id] = b

    def guardar(self, b: Bodega) -> None:
        self._by_id[b.id] = b

    def obtener(self, bodega_id: UUID) -> Bodega | None:
        return self._by_id.get(bodega_id)

    def obtener_por_codigo(
        self, sucursal_id: UUID, codigo: str
    ) -> Bodega | None:
        c = codigo.strip().upper()
        for b in self._by_id.values():
            if b.sucursal_id == sucursal_id and b.codigo.upper() == c:
                return b
        return None

    def listar_por_sucursal(
        self, sucursal_id: UUID, *, activo: bool | None = None
    ) -> list[Bodega]:
        items = [b for b in self._by_id.values() if b.sucursal_id == sucursal_id]
        if activo is not None:
            items = [b for b in items if b.activo is activo]
        items.sort(key=lambda b: b.codigo)
        return items

    def tiene_stock(self, bodega_id: UUID) -> bool:
        return self.stock_por_bodega.get(bodega_id, False)


class FakeProductoRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Producto] = {}

    def add(self, p: Producto) -> None:
        self._by_id[p.id] = p

    def guardar(self, p: Producto) -> None:
        self._by_id[p.id] = p

    def obtener(self, producto_id: UUID) -> Producto | None:
        return self._by_id.get(producto_id)

    def obtener_por_sku(self, sku: str) -> Producto | None:
        s = sku.strip().upper()
        for p in self._by_id.values():
            if p.sku.upper() == s:
                return p
        return None

    def obtener_por_codigo_barras(self, codigo: str) -> Producto | None:
        c = codigo.strip()
        for p in self._by_id.values():
            if p.codigo_barras == c:
                return p
        return None

    def listar(
        self,
        *,
        q: str | None,
        categoria_id: UUID | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> ProductosPagina:
        items = list(self._by_id.values())
        if q:
            ql = q.lower()
            items = [
                p
                for p in items
                if ql in p.nombre.lower()
                or ql in p.sku.lower()
                or (p.codigo_barras and ql in p.codigo_barras.lower())
            ]
        if categoria_id is not None:
            items = [p for p in items if p.categoria_id == categoria_id]
        if activo is not None:
            items = [p for p in items if p.activo is activo]
        items.sort(key=lambda p: p.nombre)
        total = len(items)
        return ProductosPagina(
            items=items[offset : offset + limit],
            total=total,
            limit=limit,
            offset=offset,
        )


class FakeStockRepo:
    def __init__(self) -> None:
        self._by_key: dict[tuple[UUID, UUID], Stock] = {}
        # bodega_id -> sucursal_id (necesario para por_producto/stock_disponible)
        self.bodega_sucursal: dict[UUID, UUID] = {}
        # bodega_id -> activo flag (necesario para stock_disponible)
        self.bodega_activa: dict[UUID, bool] = {}

    def obtener(
        self, producto_id: UUID, bodega_id: UUID, *, for_update: bool = False
    ) -> Stock | None:
        return self._by_key.get((producto_id, bodega_id))

    def guardar(self, stock: Stock) -> None:
        self._by_key[(stock.producto_id, stock.bodega_id)] = stock

    def por_producto(self, producto_id: UUID) -> list[StockPorBodega]:
        return [
            StockPorBodega(
                bodega_id=s.bodega_id,
                sucursal_id=self.bodega_sucursal.get(s.bodega_id, new_uuid7()),
                cantidad=s.cantidad,
                costo_promedio_clp=s.costo_promedio_clp,
            )
            for (pid, _bid), s in self._by_key.items()
            if pid == producto_id
        ]

    def por_bodega(
        self, bodega_id: UUID, *, solo_con_stock: bool = True
    ) -> list[Stock]:
        items = [
            s for (_pid, bid), s in self._by_key.items() if bid == bodega_id
        ]
        if solo_con_stock:
            items = [s for s in items if s.cantidad > Decimal("0")]
        return items

    def stock_disponible(
        self, producto_id: UUID, sucursal_id: UUID
    ) -> Decimal:
        total = Decimal("0")
        for (pid, bid), s in self._by_key.items():
            if pid != producto_id:
                continue
            if self.bodega_sucursal.get(bid) != sucursal_id:
                continue
            if not self.bodega_activa.get(bid, True):
                continue
            total += s.cantidad
        return total


class FakeMovInventarioRepo:
    def __init__(self) -> None:
        self.movimientos: list[MovInventario] = []
        # Catálogos opcionales para enriquecer listar() con detalles legibles.
        # Tests que no los seteen recibirán strings vacíos.
        self.productos: dict[UUID, tuple[str, str]] = {}  # producto_id -> (sku, nombre)
        self.bodegas: dict[UUID, tuple[str, str]] = {}    # bodega_id -> (codigo, nombre)
        self.usuarios: dict[UUID, str] = {}               # usuario_id -> nombre

    def guardar(self, mov: MovInventario) -> None:
        self.movimientos.append(mov)

    def listar(
        self,
        *,
        producto_id: UUID | None,
        bodega_id: UUID | None,
        tipo: TipoMovInventario | None,
        desde: datetime | None,
        hasta: datetime | None,
        limit: int,
        offset: int,
    ) -> MovInventarioPagina:
        items = list(self.movimientos)
        if producto_id is not None:
            items = [m for m in items if m.producto_id == producto_id]
        if bodega_id is not None:
            items = [m for m in items if m.bodega_id == bodega_id]
        if tipo is not None:
            items = [m for m in items if m.tipo is tipo]
        if desde is not None:
            items = [m for m in items if m.fecha >= desde]
        if hasta is not None:
            items = [m for m in items if m.fecha <= hasta]
        items.sort(key=lambda m: m.fecha, reverse=True)
        total = len(items)
        page = items[offset : offset + limit]
        detalles = []
        for m in page:
            p_sku, p_nombre = self.productos.get(m.producto_id, ("", ""))
            b_codigo, b_nombre = self.bodegas.get(m.bodega_id, ("", ""))
            u_nombre = self.usuarios.get(m.usuario_id, "")
            detalles.append(
                MovInventarioConDetalles(
                    mov=m,
                    producto_sku=p_sku,
                    producto_nombre=p_nombre,
                    bodega_codigo=b_codigo,
                    bodega_nombre=b_nombre,
                    usuario_nombre=u_nombre,
                )
            )
        return MovInventarioPagina(
            items=detalles,
            total=total,
            limit=limit,
            offset=offset,
        )

    def obtener_por_transferencia(
        self, transferencia_id: UUID
    ) -> list[MovInventario]:
        return [
            m for m in self.movimientos if m.transferencia_id == transferencia_id
        ]

    def obtener_por_referencia(
        self, referencia_tipo: str, referencia_id: UUID
    ) -> list[MovInventario]:
        ref = referencia_tipo.strip().upper()
        return [
            m
            for m in self.movimientos
            if m.referencia_tipo == ref and m.referencia_id == referencia_id
        ]


# ---------------- Clientes ----------------

class FakeClienteRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Cliente] = {}

    def add(self, cliente: Cliente) -> None:
        self._by_id[cliente.id] = cliente

    def guardar(self, cliente: Cliente) -> None:
        self._by_id[cliente.id] = cliente

    def obtener(self, cliente_id: UUID) -> Cliente | None:
        return self._by_id.get(cliente_id)

    def obtener_por_rut(self, rut: str) -> Cliente | None:
        r = rut.strip().upper()
        for c in self._by_id.values():
            if str(c.rut).upper() == r:
                return c
        return None

    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> ClientesPagina:
        items = list(self._by_id.values())
        if q:
            ql = q.lower()
            items = [
                c
                for c in items
                if ql in c.razon_social.lower() or ql in str(c.rut).lower()
            ]
        if activo is not None:
            items = [c for c in items if c.activo is activo]
        items.sort(key=lambda c: c.razon_social)
        total = len(items)
        return ClientesPagina(
            items=items[offset : offset + limit],
            total=total,
            limit=limit,
            offset=offset,
        )


class FakeLoteInventarioRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, LoteInventario] = {}
        # Catálogos opcionales para enriquecer por_vencer().
        self.productos: dict[UUID, tuple[str, str]] = {}  # producto_id -> (sku, nombre)
        self.bodegas: dict[UUID, tuple[str, str]] = {}  # bodega_id -> (codigo, nombre)
        self.bodega_sucursal: dict[UUID, UUID] = {}  # bodega_id -> sucursal_id

    def add(self, lote: LoteInventario) -> None:
        self._by_id[lote.id] = lote

    def guardar(self, lote: LoteInventario) -> None:
        self._by_id[lote.id] = lote

    def obtener(self, lote_id: UUID) -> LoteInventario | None:
        return self._by_id.get(lote_id)

    def listar_por_producto_bodega(
        self,
        producto_id: UUID,
        bodega_id: UUID,
        *,
        solo_vivos: bool = True,
    ) -> list[LoteInventario]:
        items = [
            lote
            for lote in self._by_id.values()
            if lote.producto_id == producto_id and lote.bodega_id == bodega_id
        ]
        if solo_vivos:
            items = [
                lote
                for lote in items
                if not lote.agotado and lote.cantidad > Decimal("0")
            ]
        items.sort(key=lambda lote: lote.fecha_vencimiento)
        return items

    def por_vencer(
        self,
        *,
        dias: int,
        hoy: date,
        sucursal_id: UUID | None = None,
        bodega_id: UUID | None = None,
    ) -> list[LotePorVencer]:
        limite = hoy + timedelta(days=dias)
        filas: list[LotePorVencer] = []
        for lote in self._by_id.values():
            if lote.agotado or lote.cantidad <= Decimal("0"):
                continue
            if lote.fecha_vencimiento > limite:
                continue
            suc = self.bodega_sucursal.get(lote.bodega_id, new_uuid7())
            if sucursal_id is not None and suc != sucursal_id:
                continue
            if bodega_id is not None and lote.bodega_id != bodega_id:
                continue
            p_sku, p_nombre = self.productos.get(lote.producto_id, ("", ""))
            b_codigo, b_nombre = self.bodegas.get(lote.bodega_id, ("", ""))
            filas.append(
                LotePorVencer(
                    lote=lote,
                    producto_sku=p_sku,
                    producto_nombre=p_nombre,
                    bodega_codigo=b_codigo,
                    bodega_nombre=b_nombre,
                    sucursal_id=suc,
                )
            )
        filas.sort(key=lambda f: f.lote.fecha_vencimiento)
        return filas


# ---------------- Caja (operación) ----------------

class FakeSesionCajaRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, SesionCaja] = {}
        # bodega/caja metadata para enriquecer el listado.
        self.caja_meta: dict[UUID, tuple[str, str, UUID]] = {}  # caja_id -> (codigo, nombre, sucursal_id)

    def add(self, sesion: SesionCaja) -> None:
        self._by_id[sesion.id] = sesion

    def guardar(self, sesion: SesionCaja) -> None:
        self._by_id[sesion.id] = sesion

    def obtener(self, sesion_id: UUID) -> SesionCaja | None:
        return self._by_id.get(sesion_id)

    def obtener_activa(
        self, caja_id: UUID, *, for_update: bool = False
    ) -> SesionCaja | None:
        for s in self._by_id.values():
            if s.caja_id == caja_id and s.estado is EstadoSesionCaja.ABIERTA:
                return s
        return None

    def listar(
        self,
        *,
        caja_id: UUID | None = None,
        sucursal_id: UUID | None = None,
        estado: EstadoSesionCaja | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SesionesCajaPagina:
        items = list(self._by_id.values())
        if caja_id is not None:
            items = [s for s in items if s.caja_id == caja_id]
        if sucursal_id is not None:
            items = [
                s
                for s in items
                if self.caja_meta.get(s.caja_id, ("", "", new_uuid7()))[2]
                == sucursal_id
            ]
        if estado is not None:
            items = [s for s in items if s.estado is estado]
        if desde is not None:
            items = [s for s in items if s.abierta_en >= desde]
        if hasta is not None:
            items = [s for s in items if s.abierta_en <= hasta]
        items.sort(key=lambda s: s.abierta_en, reverse=True)
        total = len(items)
        page = items[offset : offset + limit]
        result_items: list[SesionCajaListItem] = []
        for s in page:
            codigo, nombre, suc = self.caja_meta.get(
                s.caja_id, ("", "", new_uuid7())
            )
            result_items.append(
                SesionCajaListItem(
                    sesion=s,
                    caja_codigo=codigo,
                    caja_nombre=nombre,
                    sucursal_id=suc,
                )
            )
        return SesionesCajaPagina(
            items=result_items, total=total, limit=limit, offset=offset
        )


class FakeMovimientoCajaRepo:
    def __init__(self) -> None:
        self.movimientos: list[MovimientoCaja] = []

    def guardar(self, movimiento: MovimientoCaja) -> None:
        self.movimientos.append(movimiento)

    def listar_por_sesion(self, sesion_id: UUID) -> list[MovimientoCaja]:
        items = [m for m in self.movimientos if m.sesion_caja_id == sesion_id]
        items.sort(key=lambda m: m.fecha)
        return items

    def resumen_por_tipo(
        self, sesion_id: UUID
    ) -> dict[TipoMovimientoCaja, ResumenTipoMovimiento]:
        resultado: dict[TipoMovimientoCaja, ResumenTipoMovimiento] = {}
        for m in self.movimientos:
            if m.sesion_caja_id != sesion_id:
                continue
            actual = resultado.get(m.tipo)
            if actual is None:
                resultado[m.tipo] = ResumenTipoMovimiento(
                    cantidad=1, total_clp=m.monto_clp
                )
            else:
                resultado[m.tipo] = ResumenTipoMovimiento(
                    cantidad=actual.cantidad + 1,
                    total_clp=actual.total_clp + m.monto_clp,
                )
        return resultado


# ---------------- Ventas (POS) ----------------

class FakeVentaRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Venta] = {}
        # cliente_id -> nombre (para enriquecer listado)
        self.clientes_nombre: dict[UUID, str] = {}
        # documento_id -> folio
        self.folios_por_doc: dict[UUID, int] = {}

    def add(self, venta: Venta) -> None:
        self._by_id[venta.id] = venta

    def guardar(self, venta: Venta) -> None:
        self._by_id[venta.id] = venta

    def obtener(self, venta_id: UUID) -> Venta | None:
        return self._by_id.get(venta_id)

    def listar(
        self,
        *,
        sucursal_id: UUID | None = None,
        caja_id: UUID | None = None,
        usuario_id: UUID | None = None,
        cliente_id: UUID | None = None,
        estado: EstadoVenta | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sucursales_permitidas: frozenset[UUID] | None = None,
    ) -> VentasPagina:
        items = list(self._by_id.values())
        if sucursal_id is not None:
            items = [v for v in items if v.sucursal_id == sucursal_id]
        elif sucursales_permitidas:
            items = [v for v in items if v.sucursal_id in sucursales_permitidas]
        if caja_id is not None:
            items = [v for v in items if v.caja_id == caja_id]
        if usuario_id is not None:
            items = [v for v in items if v.usuario_id == usuario_id]
        if cliente_id is not None:
            items = [v for v in items if v.cliente_id == cliente_id]
        if estado is not None:
            items = [v for v in items if v.estado is estado]
        if desde is not None:
            items = [v for v in items if v.fecha >= desde]
        if hasta is not None:
            items = [v for v in items if v.fecha <= hasta]
        if q:
            ql = q.lower()
            items = [
                v
                for v in items
                if v.cliente_id is not None
                and ql in self.clientes_nombre.get(v.cliente_id, "").lower()
            ]
        items.sort(key=lambda v: v.fecha, reverse=True)
        total = len(items)
        page = items[offset : offset + limit]
        listados: list[VentaListado] = []
        for v in page:
            cliente_nombre = (
                self.clientes_nombre.get(v.cliente_id)
                if v.cliente_id is not None
                else None
            )
            folio = (
                self.folios_por_doc.get(v.documento_tributario_id)
                if v.documento_tributario_id is not None
                else None
            )
            listados.append(
                VentaListado(
                    id=v.id,
                    fecha=v.fecha,
                    sucursal_id=v.sucursal_id,
                    caja_id=v.caja_id,
                    usuario_id=v.usuario_id,
                    cliente_id=v.cliente_id,
                    cliente_nombre=cliente_nombre,
                    estado=v.estado.value,
                    tipo_documento=v.tipo_documento.value,
                    total_clp=v.total_clp,
                    folio=folio,
                )
            )
        return VentasPagina(
            items=listados, total=total, limit=limit, offset=offset
        )


class FakeDetalleVentaRepo:
    def __init__(self) -> None:
        self.detalles: list[DetalleVenta] = []

    def guardar_lote(self, detalles: list[DetalleVenta]) -> None:
        self.detalles.extend(detalles)

    def listar_por_venta(self, venta_id: UUID) -> list[DetalleVenta]:
        return [d for d in self.detalles if d.venta_id == venta_id]


class FakePagoRepo:
    def __init__(self) -> None:
        self.pagos: list[Pago] = []

    def guardar_lote(self, pagos: list[Pago]) -> None:
        self.pagos.extend(pagos)

    def listar_por_venta(self, venta_id: UUID) -> list[Pago]:
        return [p for p in self.pagos if p.venta_id == venta_id]


class FakeDocumentoTributarioRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, DocumentoTributario] = {}
        # Optional override for sucursal names: sucursal_id -> nombre
        self._sucursal_nombres: dict[UUID, str] = {}

    def guardar(self, documento: DocumentoTributario) -> None:
        self._by_id[documento.id] = documento

    def obtener(self, documento_id: UUID) -> DocumentoTributario | None:
        return self._by_id.get(documento_id)

    def obtener_por_folio(
        self, sucursal_id: UUID, tipo: TipoDocumento, folio: int
    ) -> DocumentoTributario | None:
        for d in self._by_id.values():
            if (
                d.sucursal_id == sucursal_id
                and d.tipo is tipo
                and d.folio == folio
            ):
                return d
        return None

    def obtener_nombre_sucursal(self, sucursal_id: UUID) -> str:
        return self._sucursal_nombres.get(sucursal_id, "Sucursal Test")

    def listar(
        self,
        *,
        sucursal_id: UUID | None = None,
        tipo: str | None = None,
        estado_sii: str | None = None,
        folio: int | None = None,
        rut_receptor: str | None = None,
        fecha_desde: Any = None,
        fecha_hasta: Any = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sucursales_permitidas: frozenset[UUID] = frozenset(),
    ) -> "DocumentosPagina":
        from erp.application.ports.repositories import DocumentoListItem, DocumentosPagina

        docs = list(self._by_id.values())
        if sucursales_permitidas:
            docs = [d for d in docs if d.sucursal_id in sucursales_permitidas]
        if sucursal_id is not None:
            docs = [d for d in docs if d.sucursal_id == sucursal_id]
        if tipo is not None:
            docs = [d for d in docs if d.tipo.value == tipo]
        if estado_sii is not None:
            docs = [d for d in docs if d.estado_sii.value == estado_sii]
        if folio is not None:
            docs = [d for d in docs if d.folio == folio]
        if rut_receptor is not None:
            docs = [d for d in docs if d.rut_receptor == rut_receptor.strip()]
        if fecha_desde is not None:
            docs = [d for d in docs if d.emitido_en >= fecha_desde]
        if fecha_hasta is not None:
            docs = [d for d in docs if d.emitido_en <= fecha_hasta]
        if q:
            q_lower = q.lower().strip()

            def _matches(d: DocumentoTributario) -> bool:
                if str(d.folio) == q_lower:
                    return True
                if (
                    d.razon_social_receptor
                    and q_lower in d.razon_social_receptor.lower()
                ):
                    return True
                return False

            docs = [d for d in docs if _matches(d)]

        total = len(docs)
        docs.sort(key=lambda d: (d.emitido_en, d.folio), reverse=True)
        offset = (page - 1) * page_size
        page_docs = docs[offset : offset + page_size]
        items_out = [
            DocumentoListItem(
                id=d.id,
                tipo=d.tipo.value,
                folio=d.folio,
                sucursal_id=d.sucursal_id,
                sucursal_nombre=self._sucursal_nombres.get(
                    d.sucursal_id, "Sucursal Test"
                ),
                rut_receptor=d.rut_receptor,
                razon_social_receptor=d.razon_social_receptor,
                total_clp=d.total_clp,
                estado_sii=d.estado_sii.value,
                emitido_en=d.emitido_en,
            )
            for d in page_docs
        ]
        return DocumentosPagina(
            items=items_out, total=total, page=page, page_size=page_size
        )


class FakeNotaDebitoMetaRepo:
    """Fake in-memory para NotaDebitoMetaRepository."""

    def __init__(self) -> None:
        self._motivos: dict[UUID, str] = {}

    def guardar(self, documento_id: UUID, motivo: str) -> None:
        self._motivos[documento_id] = motivo

    def obtener_motivo(self, documento_id: UUID) -> str | None:
        return self._motivos.get(documento_id)


class FakePosProductoQueryRepo:
    def __init__(self) -> None:
        # (sucursal_id, producto_id) -> ProductoPosListado mapping is overkill;
        # tests setean directamente .items y este fake los filtra por q.
        self.items: list[ProductoPosListado] = []
        # producto_id -> sucursal_id donde "vive" (para filtro)
        self.sucursal_por_producto: dict[UUID, UUID] = {}

    def buscar(
        self, *, q: str, sucursal_id: UUID, limit: int = 20
    ) -> list[ProductoPosListado]:
        ql = q.lower().strip()
        if not ql:
            return []
        out: list[ProductoPosListado] = []
        for item in self.items:
            if (
                self.sucursal_por_producto.get(item.producto.id) != sucursal_id
                and item.producto.id in self.sucursal_por_producto
            ):
                continue
            p = item.producto
            if (
                ql in p.nombre.lower()
                or ql in p.sku.lower()
                or (p.codigo_barras and ql in p.codigo_barras.lower())
            ):
                out.append(item)
        return out[:limit]


class FakeReservaStockRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, ReservaStock] = {}

    def add(self, reserva: ReservaStock) -> None:
        self._by_id[reserva.id] = reserva

    def guardar(self, reserva: ReservaStock) -> None:
        self._by_id[reserva.id] = reserva

    def obtener(self, reserva_id: UUID) -> ReservaStock | None:
        return self._by_id.get(reserva_id)

    def cantidad_activa_para(
        self, producto_id: UUID, bodega_id: UUID
    ) -> Decimal:
        total = Decimal("0")
        for r in self._by_id.values():
            if (
                r.producto_id == producto_id
                and r.bodega_id == bodega_id
                and r.estado is EstadoReserva.ACTIVA
            ):
                total += r.cantidad
        return total

    def listar_activas_de_sesion(self, sesion_id: UUID) -> list[ReservaStock]:
        items = [
            r
            for r in self._by_id.values()
            if r.sesion_caja_id == sesion_id and r.estado is EstadoReserva.ACTIVA
        ]
        items.sort(key=lambda r: r.creado_en)
        return items

    def liberar_todas_de_sesion(self, sesion_id: UUID, ahora: datetime) -> int:
        count = 0
        for r in self._by_id.values():
            if (
                r.sesion_caja_id == sesion_id
                and r.estado is EstadoReserva.ACTIVA
            ):
                r.estado = EstadoReserva.LIBERADA
                r.resuelto_en = ahora
                count += 1
        return count


class FakeAuditLogRepo:
    """Fake repo del audit log para tests del viewer.

    No comparte estado con `FakeAuditPublisher` — los tests inyectan
    entradas directamente con `seed`.
    """

    def __init__(self) -> None:
        self._entries: list[AuditLogEntry] = []

    def seed(self, entry: AuditLogEntry) -> None:
        self._entries.append(entry)

    def listar(
        self,
        *,
        usuario_id: UUID | None,
        accion: str | None,
        recurso_tipo: str | None,
        recurso_id: UUID | None,
        resultado: str | None,
        desde: datetime | None,
        hasta: datetime | None,
        limit: int,
        offset: int,
    ) -> AuditLogPagina:
        items = list(self._entries)
        if usuario_id is not None:
            items = [e for e in items if e.usuario_id == usuario_id]
        if accion:
            items = [e for e in items if e.accion.startswith(accion)]
        if recurso_tipo:
            items = [e for e in items if e.recurso_tipo == recurso_tipo]
        if recurso_id is not None:
            items = [e for e in items if e.recurso_id == recurso_id]
        if resultado:
            items = [e for e in items if e.resultado == resultado]
        if desde is not None:
            items = [e for e in items if e.ts >= desde]
        if hasta is not None:
            items = [e for e in items if e.ts < hasta]
        items.sort(key=lambda e: e.ts, reverse=True)
        total = len(items)
        page = items[offset : offset + limit]
        return AuditLogPagina(items=page, total=total, limit=limit, offset=offset)

    def obtener(self, audit_id: UUID) -> AuditLogEntry | None:
        for e in self._entries:
            if e.id == audit_id:
                return e
        return None


class FakePasswordResetTokenRepo:
    """Fake in-memory para PasswordResetTokenRepository."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, PasswordResetTokenRecord] = {}

    def guardar(self, token: PasswordResetTokenRecord) -> None:
        self._by_id[token.id] = token

    def obtener_por_hash(self, token_hash: str) -> PasswordResetTokenRecord | None:
        for r in self._by_id.values():
            if r.token_hash == token_hash:
                return r
        return None

    def marcar_usado(self, token_id: UUID, ahora: datetime) -> None:
        record = self._by_id.get(token_id)
        if record is None or record.usado_en is not None:
            return
        self._by_id[token_id] = PasswordResetTokenRecord(
            id=record.id,
            usuario_id=record.usuario_id,
            token_hash=record.token_hash,
            emitido_en=record.emitido_en,
            expira_en=record.expira_en,
            usado_en=ahora,
            ip=record.ip,
            user_agent=record.user_agent,
        )


class FakeEmailSender:
    """Fake EmailSender que captura los envíos en memoria para asserts."""

    def __init__(self) -> None:
        self.enviados: list[dict[str, object]] = []
        # Si se pone en True, `enviar_*` levanta Exception — para probar
        # que el use case maneja errores de envío silenciosamente.
        self.fail: bool = False

    def enviar_reset_password(
        self,
        *,
        destinatario: str,
        nombre: str,
        link: str,
        ttl_minutos: int,
    ) -> None:
        if self.fail:
            raise RuntimeError("SMTP simulated failure")
        self.enviados.append(
            {
                "destinatario": destinatario,
                "nombre": nombre,
                "link": link,
                "ttl_minutos": ttl_minutos,
            }
        )


# ---------------- Proveedores ----------------

class FakeProveedorRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Proveedor] = {}
        # Contadores externos configurables para tests
        self.compras_count: dict[UUID, int] = {}
        self.cxp_pendientes: dict[UUID, int] = {}

    def add(self, proveedor: Proveedor) -> None:
        self._by_id[proveedor.id] = proveedor

    def guardar(self, proveedor: Proveedor) -> None:
        self._by_id[proveedor.id] = proveedor

    def obtener(self, proveedor_id: UUID) -> Proveedor | None:
        return self._by_id.get(proveedor_id)

    def obtener_por_rut(self, rut: str) -> Proveedor | None:
        r = rut.strip().upper()
        for p in self._by_id.values():
            if str(p.rut).upper() == r:
                return p
        return None

    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> ProveedoresPagina:
        items = list(self._by_id.values())
        if q:
            ql = q.lower()
            items = [
                p
                for p in items
                if ql in p.razon_social.lower() or ql in str(p.rut).lower()
            ]
        if activo is not None:
            items = [p for p in items if p.activo is activo]
        items.sort(key=lambda p: p.razon_social)
        total = len(items)
        page = items[offset : offset + limit]
        return ProveedoresPagina(
            items=[
                ProveedorConContadores(
                    proveedor=p,
                    cantidad_compras=self.compras_count.get(p.id, 0),
                    cxp_pendientes_clp=self.cxp_pendientes.get(p.id, 0),
                )
                for p in page
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def contar_compras(self, proveedor_id: UUID) -> int:
        return self.compras_count.get(proveedor_id, 0)

    def sumar_cxp_pendientes(self, proveedor_id: UUID) -> int:
        return self.cxp_pendientes.get(proveedor_id, 0)


# ---------------- Compras ----------------

class FakeCompraRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Compra] = {}
        self._detalles: dict[UUID, list[DetalleCompra]] = {}
        # Metadatos opcionales para enriquecer la respuesta
        self.proveedor_info: dict[UUID, tuple[str, str]] = {}  # proveedor_id -> (razon_social, rut)
        self.sucursal_info: dict[UUID, str] = {}  # sucursal_id -> codigo
        self.bodega_info: dict[UUID, str] = {}    # bodega_id -> codigo
        self.producto_info: dict[UUID, tuple[str, str]] = {}  # producto_id -> (sku, nombre)
        self.cxp_por_compra: dict[UUID, UUID] = {}  # compra_id -> cxp_id

    def add(self, compra: Compra, detalles: list[DetalleCompra] | None = None) -> None:
        self._by_id[compra.id] = compra
        self._detalles[compra.id] = detalles or []

    def guardar(self, compra: Compra, detalles: list[DetalleCompra]) -> None:
        self._by_id[compra.id] = compra
        if detalles:
            self._detalles[compra.id] = detalles

    def obtener(self, compra_id: UUID) -> CompraConDetalles | None:
        compra = self._by_id.get(compra_id)
        if compra is None:
            return None
        detalles = self._detalles.get(compra_id, [])
        prov_info = self.proveedor_info.get(compra.proveedor_id, ("", ""))
        det_producto_info: dict[UUID, tuple[str, str]] = {
            d.id: self.producto_info.get(d.producto_id, ("", ""))
            for d in detalles
        }
        return CompraConDetalles(
            compra=compra,
            detalles=detalles,
            proveedor_razon_social=prov_info[0],
            proveedor_rut=prov_info[1],
            sucursal_codigo=self.sucursal_info.get(compra.sucursal_id, ""),
            bodega_codigo=self.bodega_info.get(compra.bodega_id, ""),
            producto_info=det_producto_info,
            cxp_id=self.cxp_por_compra.get(compra_id),
        )

    def listar(
        self,
        *,
        proveedor_id: UUID | None,
        sucursal_id: UUID | None,
        estado: EstadoCompra | None,
        desde: date | None,
        hasta: date | None,
        limit: int,
        offset: int,
    ) -> ComprasPagina:
        items = list(self._by_id.values())
        if proveedor_id is not None:
            items = [c for c in items if c.proveedor_id == proveedor_id]
        if sucursal_id is not None:
            items = [c for c in items if c.sucursal_id == sucursal_id]
        if estado is not None:
            items = [c for c in items if c.estado is estado]
        if desde is not None:
            items = [c for c in items if c.fecha_documento >= desde]
        if hasta is not None:
            items = [c for c in items if c.fecha_documento <= hasta]
        items.sort(key=lambda c: c.fecha_documento, reverse=True)
        total = len(items)
        page = items[offset : offset + limit]
        result = []
        for c in page:
            prov_info = self.proveedor_info.get(c.proveedor_id, ("", ""))
            suc_codigo = self.sucursal_info.get(c.sucursal_id, "")
            result.append(
                CompraListItem(
                    id=c.id,
                    proveedor_razon_social=prov_info[0],
                    sucursal_codigo=suc_codigo,
                    numero_documento=c.numero_documento,
                    tipo_documento=c.tipo_documento.value,
                    fecha_documento=c.fecha_documento,
                    estado=c.estado.value,
                    condicion_pago=c.condicion_pago.value,
                    total_clp=c.total_clp,
                )
            )
        return ComprasPagina(items=result, total=total, limit=limit, offset=offset)


# ---------------- CxP ----------------

class FakeCxPRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, CuentaPorPagar] = {}
        self._abonos: dict[UUID, list[AbonoCxP]] = {}
        self.proveedor_info: dict[UUID, str] = {}  # proveedor_id -> razon_social
        self.compra_info: dict[UUID, str] = {}    # compra_id -> numero_documento

    def add(self, cxp: CuentaPorPagar) -> None:
        self._by_id[cxp.id] = cxp
        self._abonos.setdefault(cxp.id, [])

    def guardar(self, cxp: CuentaPorPagar) -> None:
        self._by_id[cxp.id] = cxp
        self._abonos.setdefault(cxp.id, [])

    def obtener(self, cxp_id: UUID, *, for_update: bool = False) -> CxPConAbonos | None:
        cxp = self._by_id.get(cxp_id)
        if cxp is None:
            return None
        abonos = self._abonos.get(cxp_id, [])
        return CxPConAbonos(
            cxp=cxp,
            abonos=abonos,
            proveedor_razon_social=self.proveedor_info.get(cxp.proveedor_id, ""),
            compra_numero_documento=self.compra_info.get(cxp.compra_id, ""),
        )

    def obtener_por_compra(self, compra_id: UUID) -> CuentaPorPagar | None:
        for cxp in self._by_id.values():
            if cxp.compra_id == compra_id:
                return cxp
        return None

    def listar(
        self,
        *,
        proveedor_id: UUID | None,
        estado: EstadoCxP | None,
        vencimiento_desde: date | None,
        vencimiento_hasta: date | None,
        limit: int,
        offset: int,
        hoy: date,
    ) -> CxPPagina:
        items = list(self._by_id.values())
        if proveedor_id is not None:
            items = [c for c in items if c.proveedor_id == proveedor_id]
        if estado is not None:
            items = [c for c in items if c.estado is estado]
        if vencimiento_desde is not None:
            items = [c for c in items if c.fecha_vencimiento >= vencimiento_desde]
        if vencimiento_hasta is not None:
            items = [c for c in items if c.fecha_vencimiento <= vencimiento_hasta]
        items.sort(key=lambda c: c.fecha_vencimiento)
        total = len(items)
        page = items[offset : offset + limit]
        result = []
        for c in page:
            result.append(
                CxPListItem(
                    id=c.id,
                    proveedor_razon_social=self.proveedor_info.get(c.proveedor_id, ""),
                    compra_numero_documento=self.compra_info.get(c.compra_id, ""),
                    monto_original_clp=c.monto_original_clp,
                    monto_saldo_clp=c.monto_saldo_clp,
                    fecha_vencimiento=c.fecha_vencimiento,
                    estado=c.estado.value,
                    dias_vencido=(hoy - c.fecha_vencimiento).days,
                )
            )
        return CxPPagina(items=result, total=total, limit=limit, offset=offset)

    def registrar_abono(self, abono: AbonoCxP) -> None:
        self._abonos.setdefault(abono.cxp_id, []).append(abono)


class FakeCxCRepo:
    def __init__(self) -> None:
        self._by_id: dict[UUID, CuentaPorCobrar] = {}
        self._abonos: dict[UUID, list[AbonoCxC]] = {}
        self.cliente_info: dict[UUID, str] = {}  # cliente_id -> razon_social
        self.venta_info: dict[UUID, tuple[str, str]] = {}  # venta_id -> (numero_doc, tipo_doc)

    def add(self, cxc: CuentaPorCobrar) -> None:
        self._by_id[cxc.id] = cxc
        self._abonos.setdefault(cxc.id, [])

    def guardar(self, cxc: CuentaPorCobrar) -> None:
        self._by_id[cxc.id] = cxc
        self._abonos.setdefault(cxc.id, [])

    def obtener(self, cxc_id: UUID, *, for_update: bool = False) -> CxCConAbonos | None:
        cxc = self._by_id.get(cxc_id)
        if cxc is None:
            return None
        abonos = self._abonos.get(cxc_id, [])
        venta_docs = self.venta_info.get(cxc.venta_id, ("", ""))
        return CxCConAbonos(
            cxc=cxc,
            abonos=abonos,
            cliente_razon_social=self.cliente_info.get(cxc.cliente_id, ""),
            venta_numero_documento=venta_docs[0],
            venta_tipo_documento=venta_docs[1],
        )

    def obtener_por_venta(self, venta_id: UUID) -> CuentaPorCobrar | None:
        for cxc in self._by_id.values():
            if cxc.venta_id == venta_id:
                return cxc
        return None

    def listar(
        self,
        *,
        cliente_id: UUID | None,
        estado: EstadoCxC | None,
        vencimiento_desde: date | None,
        vencimiento_hasta: date | None,
        limit: int,
        offset: int,
        hoy: date,
    ) -> CxCPagina:
        items = list(self._by_id.values())
        if cliente_id is not None:
            items = [c for c in items if c.cliente_id == cliente_id]
        if estado is not None:
            items = [c for c in items if c.estado is estado]
        if vencimiento_desde is not None:
            items = [c for c in items if c.fecha_vencimiento >= vencimiento_desde]
        if vencimiento_hasta is not None:
            items = [c for c in items if c.fecha_vencimiento <= vencimiento_hasta]
        items.sort(key=lambda c: c.fecha_vencimiento)
        total = len(items)
        page = items[offset : offset + limit]
        result = []
        for c in page:
            venta_docs = self.venta_info.get(c.venta_id, ("", ""))
            result.append(
                CxCListItem(
                    id=c.id,
                    venta_id=c.venta_id,
                    venta_numero_documento=venta_docs[0],
                    venta_tipo_documento=venta_docs[1],
                    cliente_razon_social=self.cliente_info.get(c.cliente_id, ""),
                    monto_original_clp=c.monto_original_clp,
                    monto_saldo_clp=c.monto_saldo_clp,
                    fecha_emision=c.fecha_emision,
                    fecha_vencimiento=c.fecha_vencimiento,
                    estado=c.estado.value,
                    dias_vencido=(hoy - c.fecha_vencimiento).days,
                )
            )
        return CxCPagina(items=result, total=total, limit=limit, offset=offset)

    def listar_por_cliente(
        self, cliente_id: UUID, *, solo_activas: bool = False
    ) -> list[CxCListItem]:
        from datetime import date as date_type  # noqa: PLC0415
        hoy = date_type.today()
        items = [c for c in self._by_id.values() if c.cliente_id == cliente_id]
        if solo_activas:
            items = [c for c in items if c.estado in (EstadoCxC.PENDIENTE, EstadoCxC.PARCIAL)]
        items.sort(key=lambda c: c.fecha_vencimiento)
        result = []
        for c in items:
            venta_docs = self.venta_info.get(c.venta_id, ("", ""))
            result.append(
                CxCListItem(
                    id=c.id,
                    venta_id=c.venta_id,
                    venta_numero_documento=venta_docs[0],
                    venta_tipo_documento=venta_docs[1],
                    cliente_razon_social=self.cliente_info.get(c.cliente_id, ""),
                    monto_original_clp=c.monto_original_clp,
                    monto_saldo_clp=c.monto_saldo_clp,
                    fecha_emision=c.fecha_emision,
                    fecha_vencimiento=c.fecha_vencimiento,
                    estado=c.estado.value,
                    dias_vencido=(hoy - c.fecha_vencimiento).days,
                )
            )
        return result

    def registrar_abono(self, abono: AbonoCxC) -> None:
        self._abonos.setdefault(abono.cxc_id, []).append(abono)


class FakeDevolucionRepo:
    """Repositorio in-memory de Devolución para tests unitarios."""

    def __init__(self) -> None:
        # devolucion_id -> (Devolucion, list[DetalleDevolucion])
        self._devoluciones: dict[UUID, tuple[Devolucion, list[DetalleDevolucion]]] = {}
        # devolucion_id -> nc_folio (simulado)
        self._nc_folios: dict[UUID, int] = {}
        # producto_id -> sku/nombre (para enriquecer detalles)
        self.producto_info: dict[UUID, tuple[str, str]] = {}

    def guardar(
        self, devolucion: Devolucion, detalles: list[DetalleDevolucion]
    ) -> None:
        self._devoluciones[devolucion.id] = (devolucion, list(detalles))

    def set_nc_folio(self, devolucion_id: UUID, folio: int) -> None:
        """Helper para tests: registra el folio NC asociado a una devolución."""
        self._nc_folios[devolucion_id] = folio

    def obtener(self, devolucion_id: UUID) -> DevolucionConDetalles | None:
        entry = self._devoluciones.get(devolucion_id)
        if entry is None:
            return None
        dev, detalles = entry
        nc_folio = self._nc_folios.get(devolucion_id, 0)
        detalles_info = [
            DetalleDevolucionInfo(
                detalle=d,
                producto_sku=self.producto_info.get(d.producto_id, ("", ""))[0],
                producto_nombre=self.producto_info.get(d.producto_id, ("", ""))[1],
            )
            for d in detalles
        ]
        return DevolucionConDetalles(
            devolucion=dev,
            detalles=detalles_info,
            nc_folio=nc_folio,
        )

    def listar_por_venta(self, venta_id: UUID) -> list[DevolucionConDetalles]:
        result = []
        for dev_id, (dev, detalles) in self._devoluciones.items():
            if dev.venta_id == venta_id:
                nc_folio = self._nc_folios.get(dev_id, 0)
                detalles_info = [
                    DetalleDevolucionInfo(
                        detalle=d,
                        producto_sku=self.producto_info.get(d.producto_id, ("", ""))[0],
                        producto_nombre=self.producto_info.get(d.producto_id, ("", ""))[1],
                    )
                    for d in detalles
                ]
                result.append(
                    DevolucionConDetalles(
                        devolucion=dev,
                        detalles=detalles_info,
                        nc_folio=nc_folio,
                    )
                )
        result.sort(key=lambda d: d.devolucion.fecha)
        return result

    def listar(
        self,
        *,
        sucursal_id: UUID | None,
        desde: Any | None,
        hasta: Any | None,
        usuario_id: UUID | None,
        limit: int,
        offset: int,
    ) -> DevolucionesPagina:
        items_all = [dev for dev, _detalles in self._devoluciones.values()]
        if sucursal_id is not None:
            items_all = [d for d in items_all if d.sucursal_id == sucursal_id]
        if desde is not None:
            items_all = [d for d in items_all if d.fecha >= desde]
        if hasta is not None:
            items_all = [d for d in items_all if d.fecha <= hasta]
        if usuario_id is not None:
            items_all = [d for d in items_all if d.usuario_id == usuario_id]
        items_all.sort(key=lambda d: d.fecha, reverse=True)
        total = len(items_all)
        page = items_all[offset : offset + limit]
        return DevolucionesPagina(
            items=[
                DevolucionListItem(
                    id=d.id,
                    venta_id=d.venta_id,
                    sucursal_id=d.sucursal_id,
                    caja_id=d.caja_id,
                    usuario_id=d.usuario_id,
                    fecha=d.fecha,
                    motivo=d.motivo,
                    monto_total_clp=d.monto_total_clp,
                    nc_folio=self._nc_folios.get(d.id, 0),
                    nc_documento_id=d.nc_documento_id,
                )
                for d in page
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def cantidad_devuelta_por_detalle_venta(
        self, detalle_venta_id: UUID
    ) -> Decimal:
        total = Decimal("0")
        for _dev, detalles in self._devoluciones.values():
            for d in detalles:
                if d.detalle_venta_id == detalle_venta_id:
                    total += d.cantidad
        return total


class FakeGuiaDespachoRepo:
    def __init__(self) -> None:
        # guia.id -> (guia, detalles)
        self._guias: dict[UUID, tuple[GuiaDespacho, list[DetalleGuiaDespacho]]] = {}

    def guardar(
        self, guia: GuiaDespacho, detalles: list[DetalleGuiaDespacho]
    ) -> None:
        self._guias[guia.id] = (guia, list(detalles))

    def obtener(self, guia_id: UUID) -> GuiaDespacho | None:
        entry = self._guias.get(guia_id)
        if entry is None:
            return None
        guia, detalles = entry
        guia.detalles = list(detalles)
        return guia

    def obtener_detalles(self, guia_id: UUID) -> list[DetalleGuiaDespacho]:
        entry = self._guias.get(guia_id)
        if entry is None:
            return []
        return list(entry[1])


class FakeReporteRepo:
    """Fake configurable del ReporteRepository para tests unitarios.

    Cada método retorna el valor que se le configura con `set_*`.
    Los tests configuran los valores directamente para aislar la lógica
    del use case de la query SQL.
    """

    def __init__(self) -> None:
        self._ventas: dict[str, int] = {"bruto": 0, "neto": 0, "iva": 0, "count": 0}
        self._devoluciones: dict[str, int] = {
            "bruto": 0,
            "neto": 0,
            "iva": 0,
            "count": 0,
        }
        self._cogs: int = 0
        self._cogs_dev: int = 0
        self._compras: dict[str, int] = {"bruto": 0, "iva": 0}
        self._gastos_caja: int = 0
        self._iva_nd: int = 0
        self._top_productos: list[dict[str, Any]] = []

    # Setters para configurar en tests
    def set_ventas(self, **kwargs: int) -> None:
        self._ventas.update(kwargs)

    def set_devoluciones(self, **kwargs: int) -> None:
        self._devoluciones.update(kwargs)

    def set_cogs(self, value: int) -> None:
        self._cogs = value

    def set_cogs_dev(self, value: int) -> None:
        self._cogs_dev = value

    def set_compras(self, **kwargs: int) -> None:
        self._compras.update(kwargs)

    def set_gastos_caja(self, value: int) -> None:
        self._gastos_caja = value

    def set_iva_nd(self, value: int) -> None:
        self._iva_nd = value

    def set_top_productos(self, items: list[dict[str, Any]]) -> None:
        self._top_productos = list(items)

    # Protocol methods
    def agregar_ventas_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> dict[str, int]:
        return dict(self._ventas)

    def agregar_devoluciones_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> dict[str, int]:
        return dict(self._devoluciones)

    def cogs_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> int:
        return self._cogs

    def cogs_devoluciones_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> int:
        return self._cogs_dev

    def agregar_compras_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> dict[str, int]:
        return dict(self._compras)

    def gastos_caja_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> int:
        return self._gastos_caja

    def iva_nd_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
    ) -> int:
        return self._iva_nd

    def top_productos_periodo(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        sucursales: frozenset[UUID],
        ordenar_por: str,
        limite: int,
    ) -> list[dict[str, Any]]:
        items = list(self._top_productos)
        if ordenar_por == "monto":
            items.sort(key=lambda x: int(x.get("total_bruto_clp", 0)), reverse=True)
        else:
            items.sort(key=lambda x: int(x.get("cantidad_neta", 0)), reverse=True)
        return items[:limite]

"""Puertos (Protocols) de repositorios."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from erp.domain.entities.abono_cxc import AbonoCxC
from erp.domain.entities.abono_cxp import AbonoCxP
from erp.domain.entities.bodega import Bodega
from erp.domain.entities.caja import Caja
from erp.domain.entities.categoria import Categoria
from erp.domain.entities.cliente import Cliente
from erp.domain.entities.compra import Compra, EstadoCompra
from erp.domain.entities.cuenta_por_cobrar import CuentaPorCobrar, EstadoCxC
from erp.domain.entities.cuenta_por_pagar import CuentaPorPagar, EstadoCxP
from erp.domain.entities.detalle_compra import DetalleCompra
from erp.domain.entities.detalle_venta import DetalleVenta
from erp.domain.entities.documento_tributario import DocumentoTributario
from erp.domain.entities.lote_inventario import LoteInventario
from erp.domain.entities.mov_inventario import MovInventario, TipoMovInventario
from erp.domain.entities.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from erp.domain.entities.pago import Pago
from erp.domain.entities.perfil import Perfil
from erp.domain.entities.permiso import Permiso
from erp.domain.entities.producto import Producto
from erp.domain.entities.proveedor import Proveedor
from erp.domain.entities.rango_folios import RangoFolios
from erp.domain.entities.reserva_stock import ReservaStock
from erp.domain.entities.sesion_caja import EstadoSesionCaja, SesionCaja
from erp.domain.entities.stock import Stock
from erp.domain.entities.sucursal import Sucursal
from erp.domain.entities.usuario import Usuario
from erp.domain.entities.venta import EstadoVenta, Venta
from erp.domain.value_objects.tipo_documento import TipoDocumento


# --- Auth/Usuario ---

@dataclass(frozen=True)
class UsuarioListado:
    """Item de listado paginado de usuarios."""

    id: UUID
    rut: str
    email: str
    nombre: str
    activo: bool
    perfiles: list[str]


@dataclass(frozen=True)
class UsuariosPagina:
    items: list[UsuarioListado]
    total: int
    limit: int
    offset: int


class UsuarioRepository(Protocol):
    def obtener_por_email(self, email: str) -> Usuario | None: ...
    def obtener_por_rut(self, rut: str) -> Usuario | None: ...
    def obtener(self, usuario_id: UUID) -> Usuario | None: ...
    def guardar(self, usuario: Usuario) -> None: ...
    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> UsuariosPagina: ...
    def perfiles_de(self, usuario_id: UUID) -> list[Perfil]: ...
    def permisos_efectivos_de(self, usuario_id: UUID) -> list[str]: ...
    def asignar_perfiles(self, usuario_id: UUID, perfil_ids: list[UUID]) -> None: ...
    def sucursales_de(self, usuario_id: UUID) -> list[UUID]: ...
    def asignar_sucursales(self, usuario_id: UUID, sucursal_ids: list[UUID]) -> None: ...


# --- RefreshToken / IntentoLogin ---

@dataclass(frozen=True)
class RefreshTokenRecord:
    jti: UUID
    usuario_id: UUID
    emitido_en: datetime
    expira_en: datetime
    ip: str | None
    user_agent: str | None
    revocado_en: datetime | None = None


@dataclass(frozen=True)
class PasswordResetTokenRecord:
    """Token de reset de contraseña enviado por email.

    NUNCA guardamos el token plano — solo su `token_hash` (SHA-256 hex).
    El plaintext viaja solo en el link enviado al email.
    """

    id: UUID
    usuario_id: UUID
    token_hash: str
    emitido_en: datetime
    expira_en: datetime
    usado_en: datetime | None
    ip: str | None
    user_agent: str | None


class PasswordResetTokenRepository(Protocol):
    def guardar(self, token: PasswordResetTokenRecord) -> None: ...

    def obtener_por_hash(self, token_hash: str) -> PasswordResetTokenRecord | None:
        """Lookup por hash para el flow de reset. Devuelve `None` si no
        existe; el caller valida `usado_en is None` y `expira_en > ahora`."""
        ...

    def marcar_usado(self, token_id: UUID, ahora: datetime) -> None:
        """Single-use: marca el token como consumido. Idempotente."""
        ...


class RefreshTokenRepository(Protocol):
    def guardar(self, token: RefreshTokenRecord) -> None: ...

    def obtener_por_jti(self, jti: UUID) -> RefreshTokenRecord | None:
        """Devuelve el registro o `None` si no existe. Incluye el campo
        `revocado_en` para que el caso de uso de refresh decida."""
        ...

    def marcar_revocado(self, jti: UUID, ahora: datetime) -> None:
        """Idempotente: marca `revocado_en = ahora` si todavía está activo;
        si ya estaba revocado, no hace nada (el caller decide si esto es
        un error o un OK silencioso)."""
        ...

    def revocar_todos_de(self, usuario_id: UUID, ahora: datetime) -> None:
        """Revoca TODOS los refresh activos de un usuario. Usado tras
        cambio de password / desactivación / acción admin de "cerrar todas
        las sesiones"."""
        ...


@dataclass(frozen=True)
class IntentoLogin:
    email: str
    ts: datetime
    exitoso: bool
    ip: str | None
    user_agent: str | None


class IntentoLoginRepository(Protocol):
    def guardar(self, intento: IntentoLogin) -> None: ...


# --- Perfil ---

@dataclass(frozen=True)
class PerfilConContadores:
    """Vista de perfil enriquecida con contadores para listados."""

    perfil: Perfil
    cantidad_permisos: int
    cantidad_usuarios: int  # solo usuarios activos


@dataclass(frozen=True)
class PerfilesPagina:
    items: list[PerfilConContadores]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class UsuarioAsignadoResumen:
    """Resumen mínimo de un usuario asignado a un perfil, para mensajes de error."""

    id: UUID
    nombre: str
    email: str


class PerfilRepository(Protocol):
    def guardar(self, perfil: Perfil) -> None: ...
    def obtener(self, perfil_id: UUID) -> Perfil | None: ...
    def obtener_por_nombre(self, nombre: str) -> Perfil | None: ...
    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> PerfilesPagina: ...
    def listar_por_ids(self, perfil_ids: list[UUID]) -> list[Perfil]: ...
    def permisos_de(self, perfil_id: UUID) -> list[Permiso]: ...
    def asignar_permisos(self, perfil_id: UUID, permiso_ids: list[UUID]) -> None: ...
    def cantidad_usuarios_activos(self, perfil_id: UUID) -> int: ...
    def usuarios_activos_resumen(
        self, perfil_id: UUID, *, limit: int = 10
    ) -> list[UsuarioAsignadoResumen]: ...


# --- Permiso ---

class PermisoRepository(Protocol):
    def guardar(self, permiso: Permiso) -> None: ...
    def obtener(self, permiso_id: UUID) -> Permiso | None: ...
    def obtener_por_codigo(self, codigo: str) -> Permiso | None: ...
    def listar(self) -> list[Permiso]: ...
    def listar_por_ids(self, permiso_ids: list[UUID]) -> list[Permiso]: ...


# --- Idempotencia ---

@dataclass(frozen=True)
class IdempotencyRecord:
    key: str
    endpoint: str
    usuario_id: UUID | None
    response_status: int
    response_body: dict[str, object]
    creado_en: datetime


class IdempotencyRepository(Protocol):
    def obtener(self, key: str, endpoint: str) -> IdempotencyRecord | None: ...
    def guardar(self, record: IdempotencyRecord) -> None: ...


# --- Sucursales / Cajas / Folios ---

@dataclass(frozen=True)
class SucursalConContadores:
    sucursal: Sucursal
    cantidad_cajas_activas: int
    cantidad_usuarios_asignados: int


@dataclass(frozen=True)
class SucursalesPagina:
    items: list[SucursalConContadores]
    total: int
    limit: int
    offset: int


class SucursalRepository(Protocol):
    def guardar(self, sucursal: Sucursal) -> None: ...
    def obtener(self, sucursal_id: UUID) -> Sucursal | None: ...
    def obtener_por_codigo(self, codigo: str) -> Sucursal | None: ...
    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> SucursalesPagina: ...
    def listar_por_ids(self, sucursal_ids: list[UUID]) -> list[Sucursal]: ...
    def cantidad_cajas_activas(self, sucursal_id: UUID) -> int: ...
    def cantidad_usuarios_asignados(self, sucursal_id: UUID) -> int: ...


class CajaRepository(Protocol):
    def guardar(self, caja: Caja) -> None: ...
    def obtener(self, caja_id: UUID) -> Caja | None: ...
    def obtener_por_codigo(self, sucursal_id: UUID, codigo: str) -> Caja | None: ...
    def listar_por_sucursal(
        self, sucursal_id: UUID, *, activo: bool | None = None
    ) -> list[Caja]: ...
    def cantidad_sesiones_abiertas(self, caja_id: UUID) -> int:
        """Cantidad de sesiones de caja en estado ABIERTA para la caja."""
        ...


class RangoFoliosRepository(Protocol):
    def guardar(self, rango: RangoFolios) -> None: ...
    def obtener(self, rango_id: UUID) -> RangoFolios | None: ...
    def listar_por_sucursal(
        self,
        sucursal_id: UUID,
        *,
        tipo: TipoDocumento | None = None,
        activo: bool | None = None,
    ) -> list[RangoFolios]: ...
    def obtener_activo_para(
        self, sucursal_id: UUID, tipo: TipoDocumento
    ) -> RangoFolios | None: ...
    def obtener_activo_para_actualizar(
        self, sucursal_id: UUID, tipo: TipoDocumento
    ) -> RangoFolios | None:
        """Igual que `obtener_activo_para`, pero adquiere lock pesimista
        (`SELECT ... FOR UPDATE`) sobre la fila. Requerido por
        `AsignadorFolios.reservar`.
        """
        ...
    def existe_overlap(
        self,
        sucursal_id: UUID,
        tipo: TipoDocumento,
        desde: int,
        hasta: int,
        *,
        excluyendo_id: UUID | None = None,
    ) -> bool: ...


# --- Clientes ---

@dataclass(frozen=True)
class ClientesPagina:
    items: list[Cliente]
    total: int
    limit: int
    offset: int


class ClienteRepository(Protocol):
    def guardar(self, cliente: Cliente) -> None: ...
    def obtener(self, cliente_id: UUID) -> Cliente | None: ...
    def obtener_por_rut(self, rut: str) -> Cliente | None: ...
    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> ClientesPagina: ...


# --- Inventario: Categorías ---

@dataclass(frozen=True)
class CategoriasPagina:
    items: list[Categoria]
    total: int
    limit: int
    offset: int


class CategoriaRepository(Protocol):
    def guardar(self, categoria: Categoria) -> None: ...
    def obtener(self, categoria_id: UUID) -> Categoria | None: ...
    def obtener_por_nombre(self, nombre: str) -> Categoria | None: ...
    def listar(
        self,
        *,
        q: str | None,
        limit: int,
        offset: int,
    ) -> CategoriasPagina: ...
    def cantidad_productos(self, categoria_id: UUID) -> int: ...
    def eliminar(self, categoria_id: UUID) -> None: ...


# --- Inventario: Bodegas ---

class BodegaRepository(Protocol):
    def guardar(self, bodega: Bodega) -> None: ...
    def obtener(self, bodega_id: UUID) -> Bodega | None: ...
    def obtener_por_codigo(
        self, sucursal_id: UUID, codigo: str
    ) -> Bodega | None: ...
    def listar_por_sucursal(
        self, sucursal_id: UUID, *, activo: bool | None = None
    ) -> list[Bodega]: ...
    def tiene_stock(self, bodega_id: UUID) -> bool: ...


# --- Inventario: Productos ---

@dataclass(frozen=True)
class StockPorBodega:
    bodega_id: UUID
    sucursal_id: UUID
    cantidad: Decimal
    costo_promedio_clp: int


@dataclass(frozen=True)
class ProductosPagina:
    items: list[Producto]
    total: int
    limit: int
    offset: int


class ProductoRepository(Protocol):
    def guardar(self, producto: Producto) -> None: ...
    def obtener(self, producto_id: UUID) -> Producto | None: ...
    def obtener_por_sku(self, sku: str) -> Producto | None: ...
    def obtener_por_codigo_barras(self, codigo: str) -> Producto | None: ...
    def listar(
        self,
        *,
        q: str | None,
        categoria_id: UUID | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> ProductosPagina: ...


# --- Inventario: Stock ---

class StockRepository(Protocol):
    def obtener(
        self, producto_id: UUID, bodega_id: UUID, *, for_update: bool = False
    ) -> Stock | None: ...
    def guardar(self, stock: Stock) -> None: ...
    def por_producto(self, producto_id: UUID) -> list[StockPorBodega]: ...
    def por_bodega(
        self, bodega_id: UUID, *, solo_con_stock: bool = True
    ) -> list[Stock]: ...
    def stock_disponible(
        self, producto_id: UUID, sucursal_id: UUID
    ) -> Decimal: ...


# --- Inventario: Movimientos ---

@dataclass(frozen=True)
class MovInventarioConDetalles:
    """MovInventario enriquecido con datos legibles del producto, bodega y usuario.

    Pensado para listados/UI: evita N+1 obligando al repositorio a hacer joins.
    """
    mov: MovInventario
    producto_sku: str
    producto_nombre: str
    bodega_codigo: str
    bodega_nombre: str
    usuario_nombre: str


@dataclass(frozen=True)
class MovInventarioPagina:
    items: list[MovInventarioConDetalles]
    total: int
    limit: int
    offset: int


class MovInventarioRepository(Protocol):
    def guardar(self, mov: MovInventario) -> None: ...
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
    ) -> MovInventarioPagina: ...
    def obtener_por_transferencia(
        self, transferencia_id: UUID
    ) -> list[MovInventario]: ...
    def obtener_por_referencia(
        self, referencia_tipo: str, referencia_id: UUID
    ) -> list[MovInventario]:
        """Lista los movimientos asociados a una referencia de negocio (VENTA,
        COMPRA, DEVOLUCION, AJUSTE). Útil para revertir egresos al anular.
        """
        ...


# --- Inventario: Lotes / Vencimiento ---

@dataclass(frozen=True)
class LotePorVencer:
    """Lote vivo enriquecido con datos de producto y bodega para el reporte."""

    lote: LoteInventario
    producto_sku: str
    producto_nombre: str
    bodega_codigo: str
    bodega_nombre: str
    sucursal_id: UUID


class LoteInventarioRepository(Protocol):
    def guardar(self, lote: LoteInventario) -> None: ...
    def obtener(self, lote_id: UUID) -> LoteInventario | None: ...
    def listar_por_producto_bodega(
        self,
        producto_id: UUID,
        bodega_id: UUID,
        *,
        solo_vivos: bool = True,
    ) -> list[LoteInventario]: ...
    def por_vencer(
        self,
        *,
        dias: int,
        hoy: date,
        sucursal_id: UUID | None = None,
        bodega_id: UUID | None = None,
    ) -> list[LotePorVencer]: ...


# --- Caja: Sesiones / Movimientos ---

@dataclass(frozen=True)
class SesionCajaListItem:
    """Sesión enriquecida con datos legibles de caja/sucursal para listados."""

    sesion: SesionCaja
    caja_codigo: str
    caja_nombre: str
    sucursal_id: UUID


@dataclass(frozen=True)
class SesionesCajaPagina:
    items: list[SesionCajaListItem]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class ResumenTipoMovimiento:
    """Agregado por tipo de movimiento (para el arqueo)."""

    cantidad: int
    total_clp: int


class SesionCajaRepository(Protocol):
    def guardar(self, sesion: SesionCaja) -> None: ...
    def obtener(self, sesion_id: UUID) -> SesionCaja | None: ...
    def obtener_activa(
        self, caja_id: UUID, *, for_update: bool = False
    ) -> SesionCaja | None:
        """Sesión ABIERTA de la caja, o None. Con `for_update` adquiere lock
        pesimista (`SELECT ... FOR UPDATE`) — requerido en la apertura para
        evitar la carrera de dos aperturas simultáneas.
        """
        ...
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
    ) -> SesionesCajaPagina: ...


class MovimientoCajaRepository(Protocol):
    def guardar(self, movimiento: MovimientoCaja) -> None: ...
    def listar_por_sesion(self, sesion_id: UUID) -> list[MovimientoCaja]: ...
    def resumen_por_tipo(
        self, sesion_id: UUID
    ) -> dict[TipoMovimientoCaja, ResumenTipoMovimiento]: ...


# --- Ventas / Pagos / Documentos ---

@dataclass(frozen=True)
class VentaListado:
    """Ítem resumido para el listado paginado de ventas."""

    id: UUID
    fecha: datetime
    sucursal_id: UUID
    caja_id: UUID
    usuario_id: UUID
    cliente_id: UUID | None
    cliente_nombre: str | None
    estado: str
    tipo_documento: str
    total_clp: int
    folio: int | None


@dataclass(frozen=True)
class VentasPagina:
    items: list[VentaListado]
    total: int
    limit: int
    offset: int


class VentaRepository(Protocol):
    def guardar(self, venta: Venta) -> None: ...
    def obtener(self, venta_id: UUID) -> Venta | None: ...
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
    ) -> VentasPagina: ...


class DetalleVentaRepository(Protocol):
    def guardar_lote(self, detalles: list[DetalleVenta]) -> None: ...
    def listar_por_venta(self, venta_id: UUID) -> list[DetalleVenta]: ...


class PagoRepository(Protocol):
    def guardar_lote(self, pagos: list[Pago]) -> None: ...
    def listar_por_venta(self, venta_id: UUID) -> list[Pago]: ...


class DocumentoTributarioRepository(Protocol):
    def guardar(self, documento: DocumentoTributario) -> None: ...
    def obtener(self, documento_id: UUID) -> DocumentoTributario | None: ...
    def obtener_por_folio(
        self, sucursal_id: UUID, tipo: TipoDocumento, folio: int
    ) -> DocumentoTributario | None: ...


# --- POS: búsqueda rápida de productos con stock ---

@dataclass(frozen=True)
class ProductoPosListado:
    """Producto enriquecido para búsqueda del POS (con stock agregado en sucursal)."""

    producto: Producto
    stock_disponible: Decimal


class PosProductoQueryRepository(Protocol):
    def buscar(
        self,
        *,
        q: str,
        sucursal_id: UUID,
        limit: int = 20,
    ) -> list[ProductoPosListado]: ...


# --- POS: Reservas de stock ---

class ReservaStockRepository(Protocol):
    def guardar(self, reserva: ReservaStock) -> None: ...
    def obtener(self, reserva_id: UUID) -> ReservaStock | None: ...
    def cantidad_activa_para(
        self, producto_id: UUID, bodega_id: UUID
    ) -> Decimal:
        """Suma de `cantidad` de reservas en estado ACTIVA para el par
        (producto, bodega). Devuelve `Decimal('0')` si no hay ninguna.
        """
        ...
    def listar_activas_de_sesion(self, sesion_id: UUID) -> list[ReservaStock]: ...
    def liberar_todas_de_sesion(self, sesion_id: UUID, ahora: datetime) -> int:
        """Marca como LIBERADA todas las reservas ACTIVAS de la sesión.

        Retorna la cantidad de reservas liberadas.
        """
        ...


# --- Audit Log (viewer) ---

@dataclass(frozen=True)
class AuditLogEntry:
    """Fila de la tabla `audit_log` expuesta al dominio/UI."""

    id: UUID
    ts: datetime
    usuario_id: UUID | None
    usuario_nombre: str | None
    usuario_email: str | None
    ip: str | None
    user_agent: str | None
    accion: str
    recurso_tipo: str | None
    recurso_id: UUID | None
    resultado: str
    metadata: dict[str, object] | None
    before: dict[str, object] | None
    after: dict[str, object] | None


@dataclass(frozen=True)
class AuditLogPagina:
    items: list[AuditLogEntry]
    total: int
    limit: int
    offset: int


class AuditLogRepository(Protocol):
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
    ) -> AuditLogPagina: ...

    def obtener(self, audit_id: UUID) -> AuditLogEntry | None: ...


# --- Proveedores ---

@dataclass(frozen=True)
class ProveedorConContadores:
    """Proveedor enriquecido con contadores para el detalle/listado."""

    proveedor: Proveedor
    cantidad_compras: int
    cxp_pendientes_clp: int


@dataclass(frozen=True)
class ProveedoresPagina:
    items: list[ProveedorConContadores]
    total: int
    limit: int
    offset: int


class ProveedorRepository(Protocol):
    def guardar(self, proveedor: Proveedor) -> None: ...
    def obtener(self, proveedor_id: UUID) -> Proveedor | None: ...
    def obtener_por_rut(self, rut: str) -> Proveedor | None: ...
    def listar(
        self,
        *,
        q: str | None,
        activo: bool | None,
        limit: int,
        offset: int,
    ) -> ProveedoresPagina: ...
    def contar_compras(self, proveedor_id: UUID) -> int: ...
    def sumar_cxp_pendientes(self, proveedor_id: UUID) -> int: ...


# --- Compras ---

@dataclass(frozen=True)
class CompraConDetalles:
    """Compra enriquecida con detalles expandidos (para obtener)."""

    compra: Compra
    detalles: list[DetalleCompra]
    proveedor_razon_social: str
    proveedor_rut: str
    sucursal_codigo: str
    bodega_codigo: str
    # Datos de producto por detalle: detalle_id -> (sku, nombre)
    producto_info: dict[UUID, tuple[str, str]]
    cxp_id: UUID | None


@dataclass(frozen=True)
class CompraListItem:
    """Ítem de lista paginada de compras."""

    id: UUID
    proveedor_razon_social: str
    sucursal_codigo: str
    numero_documento: str
    tipo_documento: str
    fecha_documento: date
    estado: str
    condicion_pago: str
    total_clp: int


@dataclass(frozen=True)
class ComprasPagina:
    items: list[CompraListItem]
    total: int
    limit: int
    offset: int


class CompraRepository(Protocol):
    def guardar(self, compra: Compra, detalles: list[DetalleCompra]) -> None: ...
    def obtener(self, compra_id: UUID) -> CompraConDetalles | None: ...
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
    ) -> ComprasPagina: ...


# --- CuentaPorPagar ---

@dataclass(frozen=True)
class CxPConAbonos:
    """CxP enriquecida con abonos y datos de proveedor."""

    cxp: CuentaPorPagar
    abonos: list[AbonoCxP]
    proveedor_razon_social: str
    compra_numero_documento: str


@dataclass(frozen=True)
class CxPListItem:
    """Ítem de lista paginada de CxP."""

    id: UUID
    proveedor_razon_social: str
    compra_numero_documento: str
    monto_original_clp: int
    monto_saldo_clp: int
    fecha_vencimiento: date
    estado: str
    dias_vencido: int


@dataclass(frozen=True)
class CxPPagina:
    items: list[CxPListItem]
    total: int
    limit: int
    offset: int


class CuentaPorPagarRepository(Protocol):
    def guardar(self, cxp: CuentaPorPagar) -> None: ...
    def obtener(self, cxp_id: UUID, *, for_update: bool = False) -> CxPConAbonos | None: ...
    def obtener_por_compra(self, compra_id: UUID) -> CuentaPorPagar | None: ...
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
    ) -> CxPPagina: ...
    def registrar_abono(self, abono: AbonoCxP) -> None: ...


# --- CuentaPorCobrar ---

@dataclass(frozen=True)
class CxCConAbonos:
    """CxC enriquecida con abonos y datos de cliente y venta."""

    cxc: CuentaPorCobrar
    abonos: list[AbonoCxC]
    cliente_razon_social: str
    venta_numero_documento: str
    venta_tipo_documento: str


@dataclass(frozen=True)
class CxCListItem:
    """Ítem de lista paginada de CxC."""

    id: UUID
    venta_id: UUID
    venta_numero_documento: str
    venta_tipo_documento: str
    cliente_razon_social: str
    monto_original_clp: int
    monto_saldo_clp: int
    fecha_emision: date
    fecha_vencimiento: date
    estado: str
    dias_vencido: int


@dataclass(frozen=True)
class CxCPagina:
    items: list[CxCListItem]
    total: int
    limit: int
    offset: int


class CuentaPorCobrarRepository(Protocol):
    def guardar(self, cxc: CuentaPorCobrar) -> None: ...
    def obtener(self, cxc_id: UUID, *, for_update: bool = False) -> CxCConAbonos | None: ...
    def obtener_por_venta(self, venta_id: UUID) -> CuentaPorCobrar | None: ...
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
    ) -> CxCPagina: ...
    def listar_por_cliente(
        self, cliente_id: UUID, *, solo_activas: bool = False
    ) -> list[CxCListItem]: ...
    def registrar_abono(self, abono: AbonoCxC) -> None: ...

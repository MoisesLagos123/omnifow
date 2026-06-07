"""DTOs Pydantic para la API HTTP."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    id: UUID
    email: str
    nombre: str
    rut: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse
    perfiles: list[str]
    permisos: list[str]


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    """Misma forma que LoginResponse — el frontend reusa el mismo
    `setSession` con esta respuesta."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse
    perfiles: list[str]
    permisos: list[str]


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class CambiarPasswordRequest(BaseModel):
    password_actual: str = Field(min_length=1, max_length=256)
    # min 12 lo valida el use case (con mensaje ERR_PASSWORD_INVALIDA).
    # Pydantic deja pasar cualquier longitud para que el error venga del
    # dominio con su código apropiado.
    password_nueva: str = Field(min_length=1, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    password_nueva: str = Field(min_length=1, max_length=256)


class CambiarPasswordResponse(BaseModel):
    """Misma forma que LoginResponse — el frontend reusa setSession con esta
    respuesta y mantiene la sesión actual viva (las otras sesiones del
    usuario quedan revocadas)."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse
    perfiles: list[str]
    permisos: list[str]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


# ---------------- Administración ----------------

class CrearUsuarioRequest(BaseModel):
    rut: str = Field(min_length=1, max_length=12)
    email: EmailStr
    nombre: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=12, max_length=256)
    perfil_ids: list[UUID] = Field(min_length=1)


class EditarUsuarioRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None


class UsuarioListItem(BaseModel):
    id: UUID
    rut: str
    email: str
    nombre: str
    activo: bool
    perfiles: list[str]


class UsuarioPaginaResponse(BaseModel):
    items: list[UsuarioListItem]
    total: int
    limit: int
    offset: int


class PerfilEnUsuarioDTO(BaseModel):
    id: UUID
    nombre: str
    activo: bool


class _SucursalEnUsuarioDTO(BaseModel):
    id: UUID
    codigo: str
    nombre: str


class UsuarioDetalleResponse(BaseModel):
    id: UUID
    rut: str
    email: str
    nombre: str
    activo: bool
    perfiles: list[PerfilEnUsuarioDTO]
    permisos: list[str]
    sucursales: list[_SucursalEnUsuarioDTO] = Field(default_factory=list)


class CrearPerfilRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=2000)
    # Opcional: si se envía (incluso lista vacía), se asignan atómicamente al crear.
    permiso_ids: list[UUID] | None = None


class EditarPerfilRequest(BaseModel):
    # PATCH semantics: si el campo no aparece en el JSON, no se toca.
    # Si aparece como null, se "borra" (descripcion → None; nombre validado por entidad).
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=2000)


class PerfilResponse(BaseModel):
    id: UUID
    nombre: str
    descripcion: str | None
    activo: bool
    es_sistema: bool = False
    # Nuevos contadores (sólo en listados; siempre presentes para no romper el shape).
    cantidad_permisos: int = 0
    cantidad_usuarios: int = 0


class PerfilPaginaResponse(BaseModel):
    items: list[PerfilResponse]
    total: int
    limit: int
    offset: int


class PermisoResponse(BaseModel):
    id: UUID
    codigo: str
    descripcion: str | None


class PerfilDetalleResponse(BaseModel):
    id: UUID
    nombre: str
    descripcion: str | None
    activo: bool
    es_sistema: bool = False
    permisos: list[PermisoResponse]


class AsignarPermisosRequest(BaseModel):
    permiso_ids: list[UUID]


class AsignarPerfilesRequest(BaseModel):
    perfil_ids: list[UUID]


class CrearUsuarioResponse(BaseModel):
    id: UUID
    email: str
    rut: str
    nombre: str
    perfiles: list[str]


# ---------------- Sucursales ----------------

class SucursalDeUsuarioResponse(BaseModel):
    id: UUID
    codigo: str
    nombre: str


class UsuarioDetalleConSucursalesResponse(BaseModel):
    id: UUID
    rut: str
    email: str
    nombre: str
    activo: bool
    perfiles: list[PerfilEnUsuarioDTO]
    permisos: list[str]
    sucursales: list[SucursalDeUsuarioResponse]


class AsignarSucursalesRequest(BaseModel):
    sucursal_ids: list[UUID]


class CrearSucursalRequest(BaseModel):
    codigo: str = Field(min_length=3, max_length=20)
    nombre: str = Field(min_length=1, max_length=150)
    rut_emisor: str = Field(min_length=3, max_length=12)
    direccion: str | None = Field(default=None, max_length=500)
    comuna: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=80)


class EditarSucursalRequest(BaseModel):
    # PATCH semantics: ausente = no toca; null permitido sólo en dirección/comuna/region.
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    rut_emisor: str | None = Field(default=None, min_length=3, max_length=12)
    direccion: str | None = Field(default=None, max_length=500)
    comuna: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=80)


class SucursalResponse(BaseModel):
    id: UUID
    codigo: str
    nombre: str
    rut_emisor: str
    direccion: str | None
    comuna: str | None
    region: str | None
    activo: bool


class SucursalListItem(BaseModel):
    id: UUID
    codigo: str
    nombre: str
    rut_emisor: str
    activo: bool
    cantidad_cajas_activas: int
    cantidad_usuarios_asignados: int


class SucursalPaginaResponse(BaseModel):
    items: list[SucursalListItem]
    total: int
    limit: int
    offset: int


class CajaResponse(BaseModel):
    id: UUID
    sucursal_id: UUID
    codigo: str
    nombre: str
    activo: bool


class RangoFoliosResponse(BaseModel):
    id: UUID
    sucursal_id: UUID
    tipo_documento: str
    desde: int
    hasta: int
    proximo: int
    activo: bool


class SucursalDetalleResponse(BaseModel):
    sucursal: SucursalResponse
    cajas: list[CajaResponse]
    rangos_folios: list[RangoFoliosResponse]


class CrearCajaRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=150)


class EditarCajaRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)


class CrearRangoFoliosRequest(BaseModel):
    tipo_documento: str = Field(min_length=1, max_length=20)
    desde: int = Field(gt=0)
    hasta: int = Field(gt=0)


# ---------------- Inventario ----------------

class CategoriaResponse(BaseModel):
    id: UUID
    nombre: str


class CrearCategoriaRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)


class RenombrarCategoriaRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)


class CategoriasPaginaResponse(BaseModel):
    items: list[CategoriaResponse]
    total: int
    limit: int
    offset: int


class BodegaResponse(BaseModel):
    id: UUID
    sucursal_id: UUID
    codigo: str
    nombre: str
    activo: bool


class CrearBodegaRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=150)


class EditarBodegaRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)


class ProductoResponse(BaseModel):
    id: UUID
    sku: str
    codigo_barras: str | None
    nombre: str
    categoria_id: UUID | None
    precio_venta_clp: int
    iva_porcentaje: int
    controla_vencimiento: bool
    dias_alerta_vencimiento: int | None
    activo: bool


class CrearProductoRequest(BaseModel):
    sku: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=1, max_length=200)
    precio_venta_clp: int = Field(gt=0)
    codigo_barras: str | None = Field(default=None, min_length=6, max_length=40)
    categoria_id: UUID | None = None
    iva_porcentaje: int = Field(default=19, ge=0, le=100)
    controla_vencimiento: bool = False
    dias_alerta_vencimiento: int | None = Field(default=None, gt=0, le=3650)


class EditarProductoRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    categoria_id: UUID | None = None
    codigo_barras: str | None = Field(default=None, max_length=40)
    iva_porcentaje: int | None = Field(default=None, ge=0, le=100)
    controla_vencimiento: bool | None = None
    dias_alerta_vencimiento: int | None = Field(default=None, gt=0, le=3650)
    activo: bool | None = None


class CambiarPrecioRequest(BaseModel):
    precio_venta_clp: int = Field(gt=0)


class ProductosPaginaResponse(BaseModel):
    items: list[ProductoResponse]
    total: int
    limit: int
    offset: int


class StockPorBodegaResponse(BaseModel):
    bodega_id: UUID
    sucursal_id: UUID
    cantidad: str  # Decimal serializado
    costo_promedio_clp: int


class ProductoDetalleResponse(BaseModel):
    producto: ProductoResponse
    stock: list[StockPorBodegaResponse]


class StockDisponibleResponse(BaseModel):
    producto_id: UUID
    sucursal_id: UUID | None
    total: str
    detalle_por_bodega: list[StockPorBodegaResponse]


class AjustarStockRequest(BaseModel):
    producto_id: UUID
    bodega_id: UUID
    cantidad_nueva: str  # Decimal en string
    motivo: str = Field(min_length=1, max_length=500)


class AjustarStockResponse(BaseModel):
    producto_id: UUID
    bodega_id: UUID
    cantidad_anterior: str
    cantidad_nueva: str
    delta: str
    mov_id: UUID


class RecepcionItemRequest(BaseModel):
    producto_id: UUID
    bodega_id: UUID
    cantidad: str
    costo_unitario_clp: int = Field(ge=0)
    # Solo aplican a productos con controla_vencimiento = true.
    numero_lote: str | None = Field(default=None, max_length=60)
    fecha_elaboracion: date | None = None
    fecha_vencimiento: date | None = None
    fecha_ingreso: date | None = None


class RecepcionarMercaderiaRequest(BaseModel):
    items: list[RecepcionItemRequest] = Field(min_length=1)
    compra_id: UUID | None = None


class RecepcionItemResponse(BaseModel):
    producto_id: UUID
    bodega_id: UUID
    cantidad_ingresada: str
    nueva_cantidad: str
    nuevo_costo_promedio_clp: int
    mov_id: UUID
    lote_id: UUID | None = None


class RecepcionarMercaderiaResponse(BaseModel):
    items: list[RecepcionItemResponse]


class TransferirStockRequest(BaseModel):
    producto_id: UUID
    bodega_origen_id: UUID
    bodega_destino_id: UUID
    cantidad: str
    motivo: str | None = Field(default=None, max_length=500)


class TransferirStockResponse(BaseModel):
    transferencia_id: UUID
    mov_salida_id: UUID
    mov_entrada_id: UUID
    nueva_cantidad_origen: str
    nueva_cantidad_destino: str
    costo_unitario_clp: int


class MovInventarioResponse(BaseModel):
    id: UUID
    producto_id: UUID
    producto_sku: str
    producto_nombre: str
    bodega_id: UUID
    bodega_codigo: str
    bodega_nombre: str
    tipo: str
    cantidad: str
    costo_unitario_clp: int | None
    referencia_tipo: str | None
    referencia_id: UUID | None
    transferencia_id: UUID | None
    lote_id: UUID | None
    usuario_id: UUID
    usuario_nombre: str
    motivo: str | None
    fecha: str  # ISO


class MovimientosPaginaResponse(BaseModel):
    items: list[MovInventarioResponse]
    total: int
    limit: int
    offset: int


# ---------------- Inventario: Reporte por vencer ----------------

class LotePorVencerItemResponse(BaseModel):
    producto_id: UUID
    producto_sku: str
    producto_nombre: str
    bodega_id: UUID
    bodega_codigo: str
    bodega_nombre: str
    sucursal_id: UUID
    lote_id: UUID
    numero_lote: str | None
    fecha_vencimiento: date
    dias_restantes: int
    cantidad: str
    costo_unitario_clp: int
    valor_en_riesgo_clp: int
    urgencia: str  # VENCIDO | CRITICO | POR_VENCER


class ReportePorVencerResponse(BaseModel):
    dias: int
    items: list[LotePorVencerItemResponse]
    total_valor_en_riesgo_clp: int
    total_lotes_criticos: int
    total_lotes_vencidos: int


# ---------------- Clientes ----------------

class CrearClienteRequest(BaseModel):
    rut: str = Field(min_length=3, max_length=12)
    razon_social: str = Field(min_length=2, max_length=200)
    giro: str | None = Field(default=None, max_length=150)
    direccion: str | None = Field(default=None, max_length=500)
    comuna: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=80)
    email: EmailStr | None = Field(default=None)
    telefono: str | None = Field(default=None, max_length=40)


class EditarClienteRequest(BaseModel):
    # PATCH semantics: ausente = no toca; razon_social no admite null.
    # El RUT no es editable (identificador estable) — no aparece aquí.
    razon_social: str | None = Field(default=None, min_length=2, max_length=200)
    giro: str | None = Field(default=None, max_length=150)
    direccion: str | None = Field(default=None, max_length=500)
    comuna: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=80)
    email: EmailStr | None = Field(default=None)
    telefono: str | None = Field(default=None, max_length=40)


class ClienteResponse(BaseModel):
    id: UUID
    rut: str
    razon_social: str
    giro: str | None
    direccion: str | None
    comuna: str | None
    region: str | None
    email: str | None
    telefono: str | None
    activo: bool


class ClienteListItem(BaseModel):
    id: UUID
    rut: str
    razon_social: str
    email: str | None
    telefono: str | None
    activo: bool


class ClientesPaginaResponse(BaseModel):
    items: list[ClienteListItem]
    total: int
    limit: int
    offset: int


# ---------------- Caja (operación) ----------------

class AbrirSesionCajaRequest(BaseModel):
    monto_inicial_clp: int = Field(ge=0)


class SesionCajaResponse(BaseModel):
    id: UUID
    caja_id: UUID
    usuario_apertura_id: UUID
    monto_inicial_clp: int
    abierta_en: datetime
    estado: str
    cerrada_en: datetime | None = None
    usuario_cierre_id: UUID | None = None
    monto_final_declarado_clp: int | None = None
    monto_final_calculado_clp: int | None = None
    diferencia_clp: int | None = None


class RegistrarMovimientoCajaRequest(BaseModel):
    tipo: str = Field(pattern="^(INGRESO_VENTA|INGRESO_OTRO|EGRESO_GASTO|EGRESO_RETIRO|EGRESO_DEVOLUCION)$")
    monto_clp: int = Field(gt=0)
    descripcion: str = Field(default="", max_length=500)
    referencia_id: UUID | None = Field(default=None)


class MovimientoCajaResponse(BaseModel):
    id: UUID
    sesion_caja_id: UUID
    tipo: str
    monto_clp: int
    descripcion: str
    referencia_id: UUID | None
    usuario_id: UUID
    fecha: datetime


class ResumenTipoMovimientoResponse(BaseModel):
    tipo: str
    cantidad: int
    total_clp: int


class CerrarSesionCajaRequest(BaseModel):
    monto_declarado_clp: int = Field(ge=0)


class ArqueoResponse(BaseModel):
    sesion_id: UUID
    caja_id: UUID
    abierta_en: datetime
    cerrada_en: datetime
    usuario_cierre_id: UUID
    monto_inicial_clp: int
    total_ingresos_efectivo_clp: int
    total_egresos_efectivo_clp: int
    monto_calculado_clp: int
    monto_declarado_clp: int
    diferencia_clp: int
    desglose: list[ResumenTipoMovimientoResponse]
    reservas_liberadas: int = 0


class TotalPorTipoResponse(BaseModel):
    cantidad: int
    total_clp: int


class TotalesSesionResponse(BaseModel):
    por_tipo: dict[str, TotalPorTipoResponse]
    ingresos_clp: int
    egresos_clp: int
    calculado_clp: int


class SesionActivaResponse(BaseModel):
    sesion: SesionCajaResponse
    movimientos: list[MovimientoCajaResponse]
    totales: TotalesSesionResponse


class ReporteSesionCajaResponse(BaseModel):
    sesion_id: UUID
    caja_id: UUID
    estado: str
    usuario_apertura_id: UUID
    abierta_en: datetime
    cerrada_en: datetime | None
    usuario_cierre_id: UUID | None
    monto_inicial_clp: int
    total_ingresos_efectivo_clp: int
    total_egresos_efectivo_clp: int
    monto_calculado_clp: int
    monto_declarado_clp: int | None
    diferencia_clp: int | None
    movimientos: list[MovimientoCajaResponse]
    desglose: list[ResumenTipoMovimientoResponse]


class SesionCajaListItemResponse(BaseModel):
    id: UUID
    caja_id: UUID
    caja_codigo: str
    caja_nombre: str
    sucursal_id: UUID
    estado: str
    usuario_apertura_id: UUID
    abierta_en: datetime
    cerrada_en: datetime | None
    monto_inicial_clp: int
    monto_final_declarado_clp: int | None
    monto_final_calculado_clp: int | None
    diferencia_clp: int | None


class SesionesCajaPaginaResponse(BaseModel):
    items: list[SesionCajaListItemResponse]
    total: int
    limit: int
    offset: int


# ---------------- Ventas (POS) ----------------

class ItemVentaRequest(BaseModel):
    producto_id: UUID
    bodega_id: UUID
    cantidad: str  # Decimal serializado como string (consistente con resto)
    precio_unitario_clp: int = Field(ge=0)
    # Reserva opcional pre-creada al agregar el item al carrito.
    reserva_id: UUID | None = None


class PagoVentaRequest(BaseModel):
    tipo: str = Field(pattern="^(EFECTIVO|TRANSFERENCIA|DEBITO|CREDITO)$")
    monto_clp: int = Field(gt=0)
    referencia_externa: str | None = Field(default=None, max_length=80)
    ultimos_4_digitos: str | None = Field(default=None, min_length=4, max_length=4)


class ProcesarVentaRequest(BaseModel):
    sucursal_id: UUID
    caja_id: UUID
    tipo_documento: str = Field(pattern="^(BOLETA|FACTURA)$")
    items: list[ItemVentaRequest] = Field(min_length=1)
    pagos: list[PagoVentaRequest] = Field(default_factory=list)
    cliente_id: UUID | None = None
    # Crédito
    condicion_pago: str = Field(
        default="CONTADO", pattern="^(CONTADO|CREDITO)$"
    )
    monto_credito_clp: int = Field(default=0, ge=0)
    dias_credito: int = Field(default=0, ge=0, le=365)


class DetalleVentaResponse(BaseModel):
    id: UUID
    producto_id: UUID
    # producto_sku y producto_nombre se llenan desde ProductoRepository en el
    # adapter — sin ellos el comprobante térmico de venta queda con filas
    # vacías ("Detalle" sin items visibles).
    producto_sku: str = ""
    producto_nombre: str = ""
    bodega_id: UUID | None
    lote_id: UUID | None
    cantidad: str
    precio_unitario_clp: int
    costo_unitario_clp: int
    iva_porcentaje: int
    neto_clp: int
    iva_clp: int
    subtotal_bruto_clp: int
    # Alias del bruto para el frontend (PrintableReceipt usa `subtotal_clp`).
    subtotal_clp: int


class PagoResponse(BaseModel):
    id: UUID
    tipo: str
    monto_clp: int
    referencia_externa: str | None
    ultimos_4_digitos: str | None


class DocumentoTributarioResponse(BaseModel):
    id: UUID
    tipo: str
    folio: int
    sucursal_id: UUID
    rut_emisor: str
    rut_receptor: str | None
    razon_social_receptor: str | None
    venta_id: UUID | None
    documento_referencia_id: UUID | None
    subtotal_clp: int
    iva_clp: int
    total_clp: int
    estado_sii: str
    emitido_en: datetime


class VentaResponse(BaseModel):
    id: UUID
    sucursal_id: UUID
    caja_id: UUID
    usuario_id: UUID
    cliente_id: UUID | None
    tipo_documento: str
    estado: str
    subtotal_clp: int
    iva_clp: int
    total_clp: int
    fecha: datetime
    anulada_en: datetime | None
    motivo_anulacion: str | None
    documento_tributario_id: UUID | None


class VentaDetalleResponse(BaseModel):
    venta: VentaResponse
    detalles: list[DetalleVentaResponse]
    pagos: list[PagoResponse]
    documento: DocumentoTributarioResponse | None
    movimientos_caja_ids: list[UUID] = Field(default_factory=list)


class VentaListItem(BaseModel):
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


class VentasPaginaResponse(BaseModel):
    items: list[VentaListItem]
    total: int
    limit: int
    offset: int


class AnularVentaRequest(BaseModel):
    motivo: str | None = Field(default=None, max_length=500)


class AnularVentaResponse(BaseModel):
    venta: VentaResponse
    nota_credito: DocumentoTributarioResponse
    movimientos_inventario_ids: list[UUID]
    movimientos_caja_ids: list[UUID]


class ProductoPosListItem(BaseModel):
    id: UUID
    sku: str
    codigo_barras: str | None
    nombre: str
    precio_venta_clp: int
    iva_porcentaje: int
    controla_vencimiento: bool
    stock_disponible: str  # Decimal serializado


class ProductoPosListResponse(BaseModel):
    items: list[ProductoPosListItem]


# ---------------- Reservas de stock (POS) ----------------

class ReservarStockRequest(BaseModel):
    caja_id: UUID
    producto_id: UUID
    bodega_id: UUID
    cantidad: str  # Decimal serializado como string


class AjustarReservaRequest(BaseModel):
    cantidad: str  # Decimal serializado como string


class ReservaStockResponse(BaseModel):
    id: UUID
    sesion_caja_id: UUID
    usuario_id: UUID
    producto_id: UUID
    bodega_id: UUID
    cantidad: str
    estado: str
    creado_en: datetime
    resuelto_en: datetime | None


class ReservasStockListResponse(BaseModel):
    items: list[ReservaStockResponse]


# ---------------- Audit Log ----------------

class AuditLogResponse(BaseModel):
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


class AuditLogPaginaResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int


# ---------------- Proveedores ----------------

class CrearProveedorRequest(BaseModel):
    rut: str = Field(min_length=1)
    razon_social: str = Field(min_length=1, max_length=200)
    giro: str | None = None
    direccion: str | None = None
    email: EmailStr | None = None
    telefono: str | None = None


class ActualizarProveedorRequest(BaseModel):
    razon_social: str | None = None
    giro: str | None = None
    direccion: str | None = None
    email: EmailStr | None = None
    telefono: str | None = None


class ProveedorResponse(BaseModel):
    id: UUID
    rut: str
    razon_social: str
    giro: str | None
    direccion: str | None
    email: str | None
    telefono: str | None
    activo: bool
    cantidad_compras: int
    cxp_pendientes_clp: int
    creado_en: datetime
    actualizado_en: datetime


class ProveedoresPaginaResponse(BaseModel):
    items: list[ProveedorResponse]
    total: int
    limit: int
    offset: int


# ---------------- Compras ----------------

class CrearCompraDetalleRequest(BaseModel):
    producto_id: UUID
    cantidad: str  # Decimal serializado como string
    costo_unitario_clp: int = Field(ge=0)
    fecha_vencimiento: date | None = None
    numero_lote: str | None = None
    fecha_elaboracion: date | None = None


class CrearCompraRequest(BaseModel):
    proveedor_id: UUID
    sucursal_id: UUID
    bodega_id: UUID
    numero_documento: str = Field(min_length=1, max_length=80)
    tipo_documento: str
    fecha_documento: date
    condicion_pago: str
    dias_credito: int = Field(default=0, ge=0, le=365)
    observaciones: str | None = None
    items: list[CrearCompraDetalleRequest] = Field(min_length=1)


class AnularCompraRequest(BaseModel):
    motivo: str | None = None


class CompraDetalleResponse(BaseModel):
    id: UUID
    producto_id: UUID
    producto_sku: str
    producto_nombre: str
    cantidad: str
    costo_unitario_clp: int
    subtotal_clp: int
    fecha_vencimiento: date | None
    numero_lote: str | None


class CompraResponse(BaseModel):
    id: UUID
    proveedor_id: UUID
    proveedor_razon_social: str
    proveedor_rut: str
    sucursal_id: UUID
    sucursal_codigo: str
    bodega_id: UUID
    bodega_codigo: str
    numero_documento: str
    tipo_documento: str
    fecha_documento: date
    fecha_recepcion: datetime
    usuario_id: UUID
    estado: str
    condicion_pago: str
    dias_credito: int
    subtotal_neto_clp: int
    iva_clp: int
    total_clp: int
    observaciones: str | None
    items: list[CompraDetalleResponse]
    cxp_id: UUID | None
    creado_en: datetime


class CompraListItemResponse(BaseModel):
    id: UUID
    proveedor_razon_social: str
    sucursal_codigo: str
    numero_documento: str
    tipo_documento: str
    fecha_documento: date
    estado: str
    condicion_pago: str
    total_clp: int


class ComprasPaginaResponse(BaseModel):
    items: list[CompraListItemResponse]
    total: int
    limit: int
    offset: int


# ---------------- CxP ----------------

class RegistrarAbonoRequest(BaseModel):
    monto_clp: int = Field(ge=1)
    fecha_pago: date
    tipo_pago: str
    referencia: str | None = None
    observaciones: str | None = None


class AbonoResponse(BaseModel):
    id: UUID
    monto_clp: int
    fecha_pago: date
    tipo_pago: str
    referencia: str | None
    usuario_id: UUID
    observaciones: str | None
    creado_en: datetime


class CxPResponse(BaseModel):
    id: UUID
    compra_id: UUID
    proveedor_id: UUID
    proveedor_razon_social: str
    monto_original_clp: int
    monto_saldo_clp: int
    fecha_emision: date
    fecha_vencimiento: date
    estado: str
    abonos: list[AbonoResponse]
    creado_en: datetime


class CxPListItemResponse(BaseModel):
    id: UUID
    proveedor_razon_social: str
    compra_numero_documento: str
    monto_original_clp: int
    monto_saldo_clp: int
    fecha_vencimiento: date
    estado: str
    dias_vencido: int


class CxPPaginaResponse(BaseModel):
    items: list[CxPListItemResponse]
    total: int
    limit: int
    offset: int


# ---------------- CxC ----------------

class RegistrarAbonoCxCRequest(BaseModel):
    monto_clp: int = Field(ge=1)
    fecha_pago: date
    tipo_pago: str
    referencia: str | None = None
    observaciones: str | None = None


class AbonoCxCResponse(BaseModel):
    id: UUID
    monto_clp: int
    fecha_pago: date
    tipo_pago: str
    referencia: str | None
    usuario_id: UUID
    observaciones: str | None
    creado_en: datetime


class CxCResponse(BaseModel):
    id: UUID
    venta_id: UUID
    cliente_id: UUID
    cliente_razon_social: str
    venta_numero_documento: str
    venta_tipo_documento: str
    monto_original_clp: int
    monto_saldo_clp: int
    fecha_emision: date
    fecha_vencimiento: date
    estado: str
    abonos: list[AbonoCxCResponse]
    creado_en: datetime


class CxCListItemResponse(BaseModel):
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


class CxCPaginaResponse(BaseModel):
    items: list[CxCListItemResponse]
    total: int
    limit: int
    offset: int


# ---------------- Devoluciones ----------------

class DevolucionItemRequest(BaseModel):
    detalle_venta_id: UUID
    cantidad: str  # Decimal serializado como string


class CrearDevolucionRequest(BaseModel):
    items: list[DevolucionItemRequest] = Field(min_length=1)
    motivo: str | None = Field(default=None, max_length=500)


class DetalleDevolucionResponse(BaseModel):
    id: UUID
    detalle_venta_id: UUID
    producto_id: UUID
    producto_sku: str
    producto_nombre: str
    cantidad: str
    precio_unitario_clp: int
    subtotal_clp: int


class DevolucionResponse(BaseModel):
    id: UUID
    venta_id: UUID
    sucursal_id: UUID
    caja_id: UUID
    usuario_id: UUID
    fecha: datetime
    motivo: str | None
    monto_neto_clp: int
    iva_clp: int
    monto_total_clp: int
    nc_folio: int
    nc_documento_id: UUID
    items: list[DetalleDevolucionResponse]
    venta_estado_final: str
    creado_en: datetime


class DevolucionListItemResponse(BaseModel):
    id: UUID
    venta_id: UUID
    sucursal_id: UUID
    fecha: datetime
    motivo: str | None
    monto_total_clp: int
    nc_folio: int
    nc_documento_id: UUID


class DevolucionesPaginaResponse(BaseModel):
    items: list[DevolucionListItemResponse]
    total: int
    limit: int
    offset: int


# ---------------- Documentos Tributarios (GET listar/obtener) ----------------

class DocumentoListItemResponse(BaseModel):
    id: UUID
    tipo: str
    folio: int
    sucursal_id: UUID
    sucursal_nombre: str
    rut_receptor: str | None
    razon_social_receptor: str | None
    total_clp: int
    estado_sii: str
    emitido_en: datetime


class DocumentosPaginaResponse(BaseModel):
    items: list[DocumentoListItemResponse]
    total: int
    page: int
    page_size: int


class DetalleVentaDocResponse(BaseModel):
    """Línea de venta dentro del detalle de un documento."""
    id: UUID
    producto_id: UUID
    cantidad: str
    precio_unitario_clp: int
    neto_clp: int
    iva_clp: int
    subtotal_bruto_clp: int


class PagoDocResponse(BaseModel):
    """Pago dentro del detalle de un documento."""
    id: UUID
    tipo: str
    monto_clp: int
    referencia_externa: str | None
    ultimos_4_digitos: str | None


class VentaDocResponse(BaseModel):
    """Venta resumida incluida en el detalle del documento."""
    id: UUID
    fecha: datetime
    caja_id: UUID
    usuario_id: UUID
    detalles: list[DetalleVentaDocResponse]
    pagos: list[PagoDocResponse]


class DocumentoDetalleResponse(BaseModel):
    """Shape completo del GET /documentos/{id}."""
    id: UUID
    tipo: str
    folio: int
    sucursal_id: UUID
    sucursal_nombre: str
    rut_emisor: str
    rut_receptor: str | None
    razon_social_receptor: str | None
    subtotal_clp: int
    iva_clp: int
    total_clp: int
    documento_referencia_id: UUID | None
    documento_referencia_folio: int | None
    documento_referencia_tipo: str | None
    estado_sii: str
    emitido_en: datetime
    # Según tipo — null cuando no aplica
    venta: VentaDocResponse | None


# ---------------- Guía de Despacho (POST emisión) ----------------

class ItemGuiaRequest(BaseModel):
    producto_id: UUID
    cantidad: int = Field(gt=0)
    precio_unitario_clp: int = Field(gt=0)


class EmitirGuiaDespachoRequest(BaseModel):
    sucursal_id: UUID
    bodega_origen_id: UUID
    tipo_traslado: str = Field(pattern="^(VENTA|TRASLADO_INTERNO|OTRO)$")
    direccion_destino: str = Field(min_length=3, max_length=200)
    rut_receptor: str | None = Field(default=None, max_length=12)
    razon_social_receptor: str | None = Field(default=None, max_length=200)
    patente_vehiculo: str | None = Field(default=None, max_length=10)
    observaciones: str | None = Field(default=None, max_length=500)
    detalles: list[ItemGuiaRequest] = Field(min_length=1)


class DetalleGuiaDespachoResponse(BaseModel):
    id: UUID
    producto_id: UUID
    cantidad: int
    precio_unitario_clp: int
    subtotal_clp: int
    iva_clp: int
    total_clp: int


class EmitirGuiaDespachoResponse(BaseModel):
    id: UUID
    tipo: str
    folio: int
    sucursal_id: UUID
    bodega_origen_id: UUID
    tipo_traslado: str
    rut_receptor: str | None
    razon_social_receptor: str | None
    direccion_destino: str
    patente_vehiculo: str | None
    observaciones: str | None
    subtotal_clp: int
    iva_clp: int
    total_clp: int
    estado_sii: str
    emitido_en: datetime
    detalles: list[DetalleGuiaDespachoResponse]


# ---------------------------------------------------------------------------
# Reportes Financieros
# ---------------------------------------------------------------------------


class PeriodoResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date


class IngresosResponse(BaseModel):
    ventas_bruto_clp: int
    ventas_neto_clp: int
    ventas_iva_clp: int
    devoluciones_bruto_clp: int
    devoluciones_neto_clp: int
    devoluciones_iva_clp: int
    ingresos_netos_clp: int


class CostosResponse(BaseModel):
    cogs_clp: int
    cogs_devoluciones_clp: int
    cogs_neto_clp: int


class EgresosResponse(BaseModel):
    compras_bruto_clp: int
    compras_iva_clp: int
    gastos_caja_clp: int


class UtilidadResponse(BaseModel):
    bruta_clp: int
    neta_clp: int
    margen_bruto_pct: float
    margen_neto_pct: float


class IvaReporteResponse(BaseModel):
    debito_clp: int
    credito_clp: int
    neto_clp: int


class VolumenResponse(BaseModel):
    ventas_count: int
    devoluciones_count: int
    ticket_promedio_clp: int


class ResumenFinancieroResponse(BaseModel):
    periodo: PeriodoResponse
    sucursal_id: UUID | None
    ingresos: IngresosResponse
    costos: CostosResponse
    egresos: EgresosResponse
    utilidad: UtilidadResponse
    iva: IvaReporteResponse
    volumen: VolumenResponse


class TopProductoItemResponse(BaseModel):
    producto_id: UUID
    producto_sku: str
    producto_nombre: str
    categoria_nombre: str | None
    cantidad_vendida: int
    cantidad_devuelta: int
    cantidad_neta: int
    total_bruto_clp: int
    total_neto_clp: int
    participacion_pct: float


class TopProductosResponse(BaseModel):
    periodo: PeriodoResponse
    sucursal_id: UUID | None
    ordenar_por: str
    items: list[TopProductoItemResponse]
    total_periodo_clp: int

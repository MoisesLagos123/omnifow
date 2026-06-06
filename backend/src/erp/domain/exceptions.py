"""Excepciones tipadas de dominio. Cada una lleva `code` (catálogo §12) y `message` en español."""
from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base de errores de dominio. Subclases definen `code` y default `message`."""

    code: str = "ERR_INTERNO"
    http_status: int = 500
    default_message: str = "Error interno"

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.details = details or {}


# --- Autenticación ---
class AuthInvalidaError(DomainError):
    code = "ERR_AUTH_INVALIDA"
    http_status = 401
    default_message = "Credenciales inválidas"


class AuthBloqueadaError(DomainError):
    code = "ERR_AUTH_BLOQUEADA"
    http_status = 423
    default_message = "Cuenta bloqueada temporalmente"


class RefreshTokenInvalidoError(DomainError):
    """Refresh token con firma rota, payload inválido, tipo incorrecto, o
    no se encuentra el jti en la tabla de tokens emitidos."""

    code = "ERR_REFRESH_INVALIDO"
    http_status = 401
    default_message = "Sesión inválida. Vuelve a iniciar sesión."


class RefreshTokenRevocadoError(DomainError):
    """El refresh ya fue usado (rotación) o fue revocado por logout
    explícito / cambio de password / acción admin."""

    code = "ERR_REFRESH_REVOCADO"
    http_status = 401
    default_message = "La sesión fue cerrada. Vuelve a iniciar sesión."


class RefreshTokenExpiradoError(DomainError):
    """El refresh está fuera de su ventana de validez."""

    code = "ERR_REFRESH_EXPIRADO"
    http_status = 401
    default_message = "La sesión expiró. Vuelve a iniciar sesión."


class PasswordActualIncorrectaError(DomainError):
    """La contraseña actual provista no coincide con la del usuario.

    Se devuelve como 400 (no 401) porque el usuario sí está autenticado;
    lo que falla es la verificación de la password vieja para cambiarla.
    """

    code = "ERR_PASSWORD_ACTUAL_INCORRECTA"
    http_status = 400
    default_message = "La contraseña actual no es correcta"


class ResetTokenInvalidoError(DomainError):
    """El token de reset no existe, está mal formado, o el hash no
    coincide con ningún token emitido."""

    code = "ERR_RESET_TOKEN_INVALIDO"
    http_status = 400
    default_message = "El enlace de recuperación es inválido o ya fue usado"


class ResetTokenExpiradoError(DomainError):
    """El token está fuera de su ventana de validez (default 1h)."""

    code = "ERR_RESET_TOKEN_EXPIRADO"
    http_status = 400
    default_message = "El enlace de recuperación expiró. Solicita uno nuevo."


class ResetTokenUsadoError(DomainError):
    """El token ya fue usado (single-use)."""

    code = "ERR_RESET_TOKEN_USADO"
    http_status = 400
    default_message = "Este enlace ya fue usado. Solicita uno nuevo si necesitas restablecer la contraseña."


# --- Validación / RUT ---
class PasswordInvalidaError(DomainError):
    """La nueva contraseña no cumple la política mínima.

    Se declara tras `DomainError` y no extiende `ValidacionError` para
    evitar referencias forward (ese class está más abajo). Mantiene
    `http_status=400` igual que `ValidacionError`.
    """

    code = "ERR_PASSWORD_INVALIDA"
    http_status = 400
    default_message = "La contraseña no cumple los requisitos mínimos"


class ValidacionError(DomainError):
    code = "ERR_VALIDACION"
    http_status = 422
    default_message = "Datos inválidos"


class RutInvalidoError(ValidacionError):
    default_message = "RUT inválido"


# --- Recurso ---
class RecursoNoEncontradoError(DomainError):
    code = "ERR_RECURSO_NO_ENCONTRADO"
    http_status = 404
    default_message = "Recurso no encontrado"


# --- Autorización (RBAC) ---
class PermisoDenegadoError(DomainError):
    code = "ERR_PERMISO_DENEGADO"
    http_status = 403
    default_message = "Permiso denegado"


# --- Administración: Perfiles / Permisos / Usuarios ---
class PerfilDuplicadoError(DomainError):
    code = "ERR_PERFIL_DUPLICADO"
    http_status = 409
    default_message = "Ya existe un perfil con ese nombre"


class PerfilEnUsoError(DomainError):
    code = "ERR_PERFIL_EN_USO"
    http_status = 409
    default_message = "El perfil tiene usuarios activos asignados"


class PerfilYaActivoError(DomainError):
    code = "ERR_PERFIL_YA_ACTIVO"
    http_status = 409
    default_message = "El perfil ya se encuentra activo"


class PerfilInvalidoError(ValidacionError):
    code = "ERR_PERFIL_INVALIDO"
    default_message = "Perfil inválido"


class PermisoNoExisteError(DomainError):
    code = "ERR_PERMISO_NO_EXISTE"
    http_status = 404
    default_message = "El permiso indicado no existe"


class PermisoInvalidoError(ValidacionError):
    code = "ERR_PERMISO_INVALIDO"
    default_message = "Código de permiso inválido (formato esperado: recurso.accion)"


class UsuarioDuplicadoError(DomainError):
    code = "ERR_USUARIO_DUPLICADO"
    http_status = 409
    default_message = "Ya existe un usuario con ese email o RUT"


class UsuarioInvalidoError(ValidacionError):
    code = "ERR_USUARIO_INVALIDO"
    default_message = "Datos de usuario inválidos"


class IdempotencyKeyConflictError(DomainError):
    code = "ERR_IDEMPOTENCY_CONFLICT"
    http_status = 409
    default_message = "Conflicto en clave de idempotencia"


# --- Sucursales / Cajas / Folios ---
class SucursalInvalidaError(ValidacionError):
    code = "ERR_SUCURSAL_INVALIDA"
    http_status = 400
    default_message = "Datos de sucursal inválidos"


class SucursalDuplicadaError(DomainError):
    code = "ERR_SUCURSAL_DUPLICADA"
    http_status = 409
    default_message = "Ya existe una sucursal con ese código"


class SucursalEnUsoError(DomainError):
    code = "ERR_SUCURSAL_EN_USO"
    http_status = 409
    default_message = "La sucursal tiene cajas activas o usuarios asignados"


class CajaInvalidaError(ValidacionError):
    code = "ERR_CAJA_INVALIDA"
    http_status = 400
    default_message = "Datos de caja inválidos"


class CajaDuplicadaError(DomainError):
    code = "ERR_CAJA_DUPLICADA"
    http_status = 409
    default_message = "Ya existe una caja con ese código en la sucursal"


class RangoFoliosInvalidoError(ValidacionError):
    code = "ERR_RANGO_INVALIDO"
    http_status = 400
    default_message = "Rango de folios inválido"


class RangoFoliosAgotadoError(DomainError):
    code = "ERR_FOLIOS_AGOTADOS"
    http_status = 409
    default_message = "No hay folios disponibles para emitir el documento"


# --- Inventario: Categorías ---
class CategoriaInvalidaError(ValidacionError):
    code = "ERR_CATEGORIA_INVALIDA"
    http_status = 400
    default_message = "Datos de categoría inválidos"


class CategoriaDuplicadaError(DomainError):
    code = "ERR_CATEGORIA_DUPLICADA"
    http_status = 409
    default_message = "Ya existe una categoría con ese nombre"


class CategoriaEnUsoError(DomainError):
    code = "ERR_CATEGORIA_EN_USO"
    http_status = 409
    default_message = "La categoría tiene productos asociados"


# --- Inventario: Bodegas ---
class BodegaInvalidaError(ValidacionError):
    code = "ERR_BODEGA_INVALIDA"
    http_status = 400
    default_message = "Datos de bodega inválidos"


class BodegaDuplicadaError(DomainError):
    code = "ERR_BODEGA_DUPLICADA"
    http_status = 409
    default_message = "Ya existe una bodega con ese código en la sucursal"


class BodegaEnUsoError(DomainError):
    code = "ERR_BODEGA_EN_USO"
    http_status = 409
    default_message = "La bodega tiene stock asociado y no puede desactivarse"


# --- Inventario: Productos ---
class ProductoInvalidoError(ValidacionError):
    code = "ERR_PRODUCTO_INVALIDO"
    http_status = 400
    default_message = "Datos de producto inválidos"


class ProductoDuplicadoError(DomainError):
    code = "ERR_PRODUCTO_DUPLICADO"
    http_status = 409
    default_message = "Ya existe un producto con ese SKU o código de barras"


# --- Inventario: Stock / Movimientos ---
class StockInsuficienteError(DomainError):
    code = "ERR_STOCK_INSUFICIENTE"
    http_status = 409
    default_message = "Stock insuficiente"


class MovInventarioInvalidoError(ValidacionError):
    code = "ERR_MOV_INVENTARIO_INVALIDO"
    http_status = 400
    default_message = "Movimiento de inventario inválido"


class TransferenciaInvalidaError(ValidacionError):
    code = "ERR_TRANSFERENCIA_INVALIDA"
    http_status = 400
    default_message = "Transferencia de stock inválida"


# --- Inventario: Lotes / Vencimiento ---
class LoteInvalidoError(ValidacionError):
    code = "ERR_LOTE_INVALIDO"
    http_status = 400
    default_message = "Datos de lote de inventario inválidos"


class VencimientoRequeridoError(ValidacionError):
    code = "ERR_VENCIMIENTO_REQUERIDO"
    http_status = 400
    default_message = (
        "El producto controla vencimiento: la fecha de vencimiento es obligatoria"
    )


# --- Clientes ---
class ClienteInvalidoError(ValidacionError):
    code = "ERR_CLIENTE_INVALIDO"
    http_status = 400
    default_message = "Datos de cliente inválidos"


class ClienteDuplicadoError(DomainError):
    code = "ERR_CLIENTE_DUPLICADO"
    http_status = 409
    default_message = "Ya existe un cliente con ese RUT"


# --- Caja operacional ---
class SesionCajaInvalidaError(ValidacionError):
    code = "ERR_SESION_CAJA_INVALIDA"
    http_status = 400
    default_message = "Datos de sesión de caja inválidos"


class SesionCajaYaAbiertaError(DomainError):
    code = "ERR_SESION_CAJA_YA_ABIERTA"
    http_status = 409
    default_message = "Ya existe una sesión de caja abierta para esta caja"


class SesionCajaNoActivaError(DomainError):
    code = "ERR_SESION_CAJA_NO_ACTIVA"
    http_status = 409
    default_message = "No hay una sesión de caja abierta"


class MovimientoCajaInvalidoError(ValidacionError):
    code = "ERR_MOVIMIENTO_CAJA_INVALIDO"
    http_status = 400
    default_message = "Movimiento de caja inválido"


# --- Ventas / POS ---
class VentaInvalidaError(ValidacionError):
    code = "ERR_VENTA_INVALIDA"
    http_status = 400
    default_message = "Datos de venta inválidos"


class PagoInvalidoError(ValidacionError):
    code = "ERR_PAGO_INVALIDO"
    http_status = 400
    default_message = "Datos de pago inválidos"


class PagosNoCuadranError(DomainError):
    code = "ERR_PAGOS_NO_CUADRAN"
    http_status = 400
    default_message = "La suma de pagos no coincide con el total de la venta"


class DocumentoTributarioInvalidoError(ValidacionError):
    code = "ERR_DOC_TRIBUTARIO_INVALIDO"
    http_status = 400
    default_message = "Datos del documento tributario inválidos"


class FacturaRequiereClienteError(DomainError):
    code = "ERR_FACTURA_REQUIERE_CLIENTE"
    http_status = 400
    default_message = (
        "La emisión de una Factura requiere un cliente identificado (RUT y razón social)"
    )


class VentaYaAnuladaError(DomainError):
    code = "ERR_VENTA_YA_ANULADA"
    http_status = 409
    default_message = "La venta ya se encuentra anulada"


class EstadoVentaInvalidoError(DomainError):
    code = "ERR_ESTADO_VENTA_INVALIDO"
    http_status = 409
    default_message = "La venta no está en un estado válido para esta operación"


# --- Reservas de stock (POS) ---
class ReservaStockInvalidaError(ValidacionError):
    code = "ERR_RESERVA_INVALIDA"
    http_status = 400
    default_message = "Datos de reserva de stock inválidos"


class ReservaNoEncontradaError(DomainError):
    code = "ERR_RESERVA_NO_ENCONTRADA"
    http_status = 404
    default_message = "Reserva de stock no encontrada"


class ReservaEstadoInvalidoError(DomainError):
    code = "ERR_RESERVA_ESTADO_INVALIDO"
    http_status = 409
    default_message = "La reserva no está en un estado válido para esta operación"

"""Modelos ORM SQLAlchemy. Importar aquí garantiza que Alembic los detecte."""
from erp.infrastructure.db.models.base import Base
from erp.infrastructure.db.models.audit_log import AuditLogORM
from erp.infrastructure.db.models.bodega import BodegaORM
from erp.infrastructure.db.models.caja import CajaORM
from erp.infrastructure.db.models.categoria import CategoriaORM
from erp.infrastructure.db.models.cliente import ClienteORM
from erp.infrastructure.db.models.detalle_venta import DetalleVentaORM
from erp.infrastructure.db.models.documento_tributario import DocumentoTributarioORM
from erp.infrastructure.db.models.intento_login import IntentoLoginORM
from erp.infrastructure.db.models.lote_inventario import LoteInventarioORM
from erp.infrastructure.db.models.mov_inventario import MovInventarioORM
from erp.infrastructure.db.models.movimiento_caja import MovimientoCajaORM
from erp.infrastructure.db.models.pago import PagoORM
from erp.infrastructure.db.models.perfil import PerfilORM
from erp.infrastructure.db.models.perfil_permiso import perfil_permiso_table
from erp.infrastructure.db.models.permiso import PermisoORM
from erp.infrastructure.db.models.producto import ProductoORM
from erp.infrastructure.db.models.rango_folios import RangoFoliosORM
from erp.infrastructure.db.models.refresh_token import RefreshTokenORM
from erp.infrastructure.db.models.reserva_stock import ReservaStockORM
from erp.infrastructure.db.models.sesion_caja import SesionCajaORM
from erp.infrastructure.db.models.stock import StockORM
from erp.infrastructure.db.models.sucursal import SucursalORM
from erp.infrastructure.db.models.usuario import UsuarioORM
from erp.infrastructure.db.models.venta import VentaORM
from erp.infrastructure.db.models.usuario_perfil import usuario_perfil_table
from erp.infrastructure.db.models.usuario_sucursal import usuario_sucursal_table

__all__ = [
    "Base",
    "AuditLogORM",
    "BodegaORM",
    "CajaORM",
    "CategoriaORM",
    "ClienteORM",
    "DetalleVentaORM",
    "DocumentoTributarioORM",
    "IntentoLoginORM",
    "LoteInventarioORM",
    "MovInventarioORM",
    "MovimientoCajaORM",
    "PagoORM",
    "PerfilORM",
    "PermisoORM",
    "ProductoORM",
    "RangoFoliosORM",
    "RefreshTokenORM",
    "ReservaStockORM",
    "SesionCajaORM",
    "StockORM",
    "SucursalORM",
    "UsuarioORM",
    "VentaORM",
    "perfil_permiso_table",
    "usuario_perfil_table",
    "usuario_sucursal_table",
]

/**
 * Permisos requeridos para mostrar cada sección de navegación.
 *
 * Fuente única de verdad — la sidebar del layout y el dashboard de Inicio
 * deben importar desde aquí para que los accesos rápidos coincidan
 * EXACTAMENTE con lo que el usuario ve en el menú lateral.
 *
 * Regla: si un perfil ve un módulo en el sidebar, también debería verlo
 * como acceso rápido en Inicio, y viceversa.
 */

/** Abre el grupo "Administración" del sidebar. */
export const ADMIN_PERMS = [
  "usuario.gestionar",
  "perfil.gestionar",
  "permiso.ver",
  "sucursal.gestionar",
  "audit.ver",
] as const;

/** Sub-item Audit log. */
export const AUDIT_PERMS = ["audit.ver"] as const;

/** Sub-item Usuarios dentro de Administración. */
export const USUARIO_PERMS = ["usuario.gestionar"] as const;
/** Sub-item Perfiles. */
export const PERFIL_PERMS = ["perfil.gestionar"] as const;
/** Sub-item Permisos. */
export const PERMISO_PERMS = ["permiso.ver"] as const;
/** Sub-item Sucursales (también lo usa el dashboard). */
export const SUCURSAL_PERMS = ["sucursal.gestionar", "sucursal.ver"] as const;

/** Inventario (productos, bodegas, stock view…). */
export const INV_PERMS = ["stock.consultar", "producto.gestionar"] as const;
/** Recepción de mercadería. */
export const RECEPCION_PERMS = ["mercaderia.recepcionar"] as const;
/** Ajustes y transferencias de stock. */
export const AJUSTE_PERMS = ["inventario.ajustar"] as const;
/** Lectura de stock (movimientos, por vencer). */
export const STOCK_VIEW_PERMS = ["stock.consultar"] as const;

/** Operación de caja (apertura/cierre/movimientos). */
export const CAJA_PERMS = ["caja.operar"] as const;

/** Gestión / consulta de clientes. */
export const CLIENTE_PERMS = [
  "cliente.consultar",
  "cliente.gestionar",
] as const;

/** POS — vender o anular ventas. */
export const POS_PERMS = ["venta.crear", "venta.anular"] as const;

/** Consulta de proveedores (lectura). */
export const PROVEEDOR_CONSULTAR_PERMS = [
  "proveedor.consultar",
  "proveedor.gestionar",
] as const;

/** Gestión de proveedores (CRUD). */
export const PROVEEDOR_GESTIONAR_PERMS = ["proveedor.gestionar"] as const;

/** Consulta de compras (lectura). */
export const COMPRA_CONSULTAR_PERMS = ["compra.consultar"] as const;

/** Crear nueva compra. */
export const COMPRA_CREAR_PERMS = ["compra.crear"] as const;

/** Consulta de CxP (lectura). */
export const CXP_CONSULTAR_PERMS = [
  "cxp.consultar",
  "cxp.gestionar",
] as const;

/** Gestión de CxP (registrar abonos). */
export const CXP_GESTIONAR_PERMS = ["cxp.gestionar"] as const;

/** Permiso para vender a crédito. */
export const VENTA_CREDITO_PERMS = ["venta.credito"] as const;

/** Consulta de CxC — clientes (lectura). */
export const CXC_CONSULTAR_PERMS = [
  "cxc.consultar",
  "cxc.gestionar",
] as const;

/** Gestión de CxC — registrar abonos de clientes. */
export const CXC_GESTIONAR_PERMS = ["cxc.gestionar"] as const;

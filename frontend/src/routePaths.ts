/**
 * Constantes de rutas centralizadas. Importa siempre desde aquí; nunca duplicar
 * literales de path en componentes.
 */
export const ROUTES = {
  LOGIN: "/login",
  HOME: "/",
  ADMIN: "/admin",
  ADMIN_USUARIOS: "/admin/usuarios",
  ADMIN_USUARIO_NUEVO: "/admin/usuarios/nuevo",
  ADMIN_USUARIO_DETALLE: (id: string) => `/admin/usuarios/${id}`,
  ADMIN_PERFILES: "/admin/perfiles",
  ADMIN_PERFIL_NUEVO: "/admin/perfiles/nuevo",
  ADMIN_PERFIL_DETALLE: (id: string) => `/admin/perfiles/${id}`,
  ADMIN_PERMISOS: "/admin/permisos",
  ADMIN_AUDIT: "/admin/audit",
  FORGOT_PASSWORD: "/password/forgot",
  RESET_PASSWORD: "/password/reset",
  ADMIN_SUCURSALES: "/admin/sucursales",
  ADMIN_SUCURSAL_NUEVA: "/admin/sucursales/nueva",
  ADMIN_SUCURSAL_DETALLE: (id: string) => `/admin/sucursales/${id}`,
  ADMIN_SUCURSAL_EDITAR: (id: string) => `/admin/sucursales/${id}/editar`,
  // Inventario
  INVENTARIO: "/inventario",
  INVENTARIO_PRODUCTOS: "/inventario/productos",
  INVENTARIO_PRODUCTO_NUEVO: "/inventario/productos/nuevo",
  INVENTARIO_PRODUCTO_DETALLE: (id: string) => `/inventario/productos/${id}`,
  INVENTARIO_PRODUCTO_EDITAR: (id: string) =>
    `/inventario/productos/${id}/editar`,
  INVENTARIO_CATEGORIAS: "/inventario/categorias",
  INVENTARIO_BODEGAS: "/inventario/bodegas",
  INVENTARIO_RECEPCION: "/inventario/recepcion",
  INVENTARIO_TRANSFERENCIAS: "/inventario/transferencias",
  INVENTARIO_AJUSTES: "/inventario/ajustes",
  INVENTARIO_MOVIMIENTOS: "/inventario/movimientos",
  INVENTARIO_POR_VENCER: "/inventario/por-vencer",
  // Caja (operación)
  CAJA: "/caja",
  CAJA_SESIONES: "/caja/sesiones",
  CAJA_SESION_DETALLE: (id: string) => `/caja/sesiones/${id}`,
  // POS y Ventas
  POS: "/pos",
  VENTAS: "/ventas",
  VENTA_DETALLE: (id: string) => `/ventas/${id}`,
  // Clientes
  CLIENTES: "/clientes",
  CLIENTE_NUEVO: "/clientes/nuevo",
  CLIENTE_DETALLE: (id: string) => `/clientes/${id}`,
  CLIENTE_EDITAR: (id: string) => `/clientes/${id}/editar`,
  // Proveedores
  ADMIN_PROVEEDORES: "/admin/proveedores",
  ADMIN_PROVEEDOR_NUEVO: "/admin/proveedores/nuevo",
  ADMIN_PROVEEDOR_DETALLE: (id: string) => `/admin/proveedores/${id}`,
  ADMIN_PROVEEDOR_EDITAR: (id: string) => `/admin/proveedores/${id}/editar`,
  // Compras
  COMPRAS: "/compras",
  COMPRA_NUEVA: "/compras/nueva",
  COMPRA_DETALLE: (id: string) => `/compras/${id}`,
  // CxP
  CXP: "/cxp",
  CXP_DETALLE: (id: string) => `/cxp/${id}`,
  // CxC
  CXC: "/cxc",
  CXC_DETALLE: (id: string) => `/cxc/${id}`,
  // Devoluciones
  DEVOLUCIONES: "/devoluciones",
  DEVOLUCION_DETALLE: (id: string) => `/devoluciones/${id}`,
  // Documentos tributarios
  DOCUMENTOS: "/documentos",
  DOCUMENTO_DETALLE: (id: string) => `/documentos/${id}`,
} as const;

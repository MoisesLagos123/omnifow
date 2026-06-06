import { useEffect } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { setOnAuthExpired } from "./api/client";
import { useAuthStore } from "./auth/store";
import { useToast } from "./components/ui/Toast";
import { LoginPage } from "./modules/login/LoginPage";
import { ForgotPasswordPage } from "./modules/login/ForgotPasswordPage";
import { ResetPasswordPage } from "./modules/login/ResetPasswordPage";
import { HomePage } from "./modules/home/HomePage";
import { RequireAuth } from "./auth/RequireAuth";
import { RequirePermission } from "./auth/RequirePermission";
import { AuthenticatedLayout } from "./components/layout/AuthenticatedLayout";
import { UsuariosPage } from "./modules/administracion/UsuariosPage";
import { CrearUsuarioPage } from "./modules/administracion/CrearUsuarioPage";
import { EditarUsuarioPage } from "./modules/administracion/EditarUsuarioPage";
import { PerfilesPage } from "./modules/administracion/PerfilesPage";
import { EditarPerfilPage } from "./modules/administracion/EditarPerfilPage";
import { PermisosPage } from "./modules/administracion/PermisosPage";
import { AuditLogPage } from "./modules/administracion/AuditLogPage";
import { SucursalesPage } from "./modules/sucursales/SucursalesPage";
import { EditarSucursalPage } from "./modules/sucursales/EditarSucursalPage";
import { SucursalDetallePage } from "./modules/sucursales/SucursalDetallePage";
import { ProductosPage } from "./modules/inventario/ProductosPage";
import { EditarProductoPage } from "./modules/inventario/EditarProductoPage";
import { ProductoDetallePage } from "./modules/inventario/ProductoDetallePage";
import { CategoriasPage } from "./modules/inventario/CategoriasPage";
import { BodegasPage } from "./modules/inventario/BodegasPage";
import { RecepcionPage } from "./modules/inventario/RecepcionPage";
import { TransferenciasPage } from "./modules/inventario/TransferenciasPage";
import { AjustesPage } from "./modules/inventario/AjustesPage";
import { MovimientosPage } from "./modules/inventario/MovimientosPage";
import { PorVencerPage } from "./modules/inventario/PorVencerPage";
import { ClientesPage } from "./modules/clientes/ClientesPage";
import { EditarClientePage } from "./modules/clientes/EditarClientePage";
import { ClienteDetallePage } from "./modules/clientes/ClienteDetallePage";
import { ProveedoresPage } from "./modules/compras/ProveedoresPage";
import { EditarProveedorPage } from "./modules/compras/EditarProveedorPage";
import { ProveedorDetallePage } from "./modules/compras/ProveedorDetallePage";
import { ComprasPage } from "./modules/compras/ComprasPage";
import { NuevaCompraPage } from "./modules/compras/NuevaCompraPage";
import { CompraDetallePage } from "./modules/compras/CompraDetallePage";
import { CxPPage } from "./modules/compras/CxPPage";
import { CxPDetallePage } from "./modules/compras/CxPDetallePage";
import { CajaOperacionPage } from "./modules/caja/CajaOperacionPage";
import { SesionesPage } from "./modules/caja/SesionesPage";
import { SesionDetallePage } from "./modules/caja/SesionDetallePage";
import { PosPage } from "./modules/pos/PosPage";
import { VentasPage } from "./modules/pos/VentasPage";
import { VentaDetallePage } from "./modules/pos/VentaDetallePage";
import { ROUTES } from "./routePaths";

const ADMIN_PERMS = [
  "usuario.gestionar",
  "perfil.gestionar",
  "sucursal.gestionar",
  "sucursal.ver",
] as const;
const SUCURSAL_PERMS = ["sucursal.gestionar", "sucursal.ver"] as const;
const INV_READ_PERMS = ["stock.consultar", "producto.gestionar"] as const;
const CLIENTE_READ_PERMS = ["cliente.consultar", "cliente.gestionar"] as const;
const VENTA_READ_PERMS = ["venta.crear", "venta.anular"] as const;
const PROVEEDOR_READ_PERMS = ["proveedor.consultar", "proveedor.gestionar"] as const;
const COMPRA_READ_PERMS = ["compra.consultar"] as const;
const CXP_READ_PERMS = ["cxp.consultar", "cxp.gestionar"] as const;

function AdminGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      anyOf={ADMIN_PERMS}
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

const AUDIT_GUARD_PERMS = ["audit.ver"] as const;

function AuditGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      anyOf={AUDIT_GUARD_PERMS}
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function SucursalGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      anyOf={SUCURSAL_PERMS}
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function InventarioReadGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      anyOf={INV_READ_PERMS}
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function ProductoGestionGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      code="producto.gestionar"
      fallback={<Navigate to={ROUTES.INVENTARIO_PRODUCTOS} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function MercaderiaGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      code="mercaderia.recepcionar"
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function AjusteGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      code="inventario.ajustar"
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function StockViewGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      code="stock.consultar"
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function CajaOperarGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      code="caja.operar"
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function ClienteReadGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      anyOf={CLIENTE_READ_PERMS}
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function VentaCrearGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      code="venta.crear"
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function VentaReadGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      anyOf={VENTA_READ_PERMS}
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function ClienteGestionGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      code="cliente.gestionar"
      fallback={<Navigate to={ROUTES.CLIENTES} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function ProveedorReadGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      anyOf={PROVEEDOR_READ_PERMS}
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function ProveedorGestGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      code="proveedor.gestionar"
      fallback={<Navigate to={ROUTES.ADMIN_PROVEEDORES} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function CompraReadGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      anyOf={COMPRA_READ_PERMS}
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function CompraCreateGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      code="compra.crear"
      fallback={<Navigate to={ROUTES.COMPRAS} replace />}
    >
      {children}
    </RequirePermission>
  );
}

function CxPReadGuard({ children }: { children: React.ReactNode }) {
  return (
    <RequirePermission
      anyOf={CXP_READ_PERMS}
      fallback={<Navigate to={ROUTES.HOME} replace />}
    >
      {children}
    </RequirePermission>
  );
}

/**
 * Hook que conecta `setOnAuthExpired` (interceptor del client HTTP) con la
 * navegación de React Router. Cuando un refresh falla, limpiamos el store
 * y mandamos al login. Toast opcional para que el usuario sepa qué pasó.
 */
function useAuthExpiredHandler(): void {
  const navigate = useNavigate();
  const toast = useToast();
  const clear = useAuthStore((s) => s.clear);
  useEffect(() => {
    setOnAuthExpired(() => {
      clear();
      toast.info("Tu sesión expiró", "Inicia sesión nuevamente.");
      navigate(ROUTES.LOGIN, { replace: true });
    });
    return () => setOnAuthExpired(null);
  }, [navigate, toast, clear]);
}

export function AppRoutes() {
  useAuthExpiredHandler();
  return (
    <Routes>
      <Route path={ROUTES.LOGIN} element={<LoginPage />} />
      <Route path={ROUTES.FORGOT_PASSWORD} element={<ForgotPasswordPage />} />
      <Route path={ROUTES.RESET_PASSWORD} element={<ResetPasswordPage />} />
      <Route
        element={
          <RequireAuth>
            <AuthenticatedLayout />
          </RequireAuth>
        }
      >
        <Route path={ROUTES.HOME} element={<HomePage />} />
        <Route
          path={ROUTES.ADMIN_USUARIOS}
          element={<AdminGuard><UsuariosPage /></AdminGuard>}
        />
        <Route
          path={ROUTES.ADMIN_USUARIO_NUEVO}
          element={<AdminGuard><CrearUsuarioPage /></AdminGuard>}
        />
        <Route
          path="/admin/usuarios/:id"
          element={<AdminGuard><EditarUsuarioPage /></AdminGuard>}
        />
        <Route
          path={ROUTES.ADMIN_PERFILES}
          element={<AdminGuard><PerfilesPage /></AdminGuard>}
        />
        <Route
          path={ROUTES.ADMIN_PERFIL_NUEVO}
          element={<AdminGuard><EditarPerfilPage modo="crear" /></AdminGuard>}
        />
        <Route
          path="/admin/perfiles/:id"
          element={<AdminGuard><EditarPerfilPage modo="editar" /></AdminGuard>}
        />
        <Route
          path={ROUTES.ADMIN_PERMISOS}
          element={<AdminGuard><PermisosPage /></AdminGuard>}
        />
        <Route
          path={ROUTES.ADMIN_AUDIT}
          element={<AuditGuard><AuditLogPage /></AuditGuard>}
        />
        <Route
          path={ROUTES.ADMIN_SUCURSALES}
          element={<SucursalGuard><SucursalesPage /></SucursalGuard>}
        />
        <Route
          path={ROUTES.ADMIN_SUCURSAL_NUEVA}
          element={
            <SucursalGuard><EditarSucursalPage modo="crear" /></SucursalGuard>
          }
        />
        <Route
          path="/admin/sucursales/:id/editar"
          element={
            <SucursalGuard><EditarSucursalPage modo="editar" /></SucursalGuard>
          }
        />
        <Route
          path="/admin/sucursales/:id"
          element={<SucursalGuard><SucursalDetallePage /></SucursalGuard>}
        />

        {/* Inventario */}
        <Route
          path={ROUTES.INVENTARIO}
          element={
            <Navigate to={ROUTES.INVENTARIO_PRODUCTOS} replace />
          }
        />
        <Route
          path={ROUTES.INVENTARIO_PRODUCTOS}
          element={
            <InventarioReadGuard><ProductosPage /></InventarioReadGuard>
          }
        />
        <Route
          path={ROUTES.INVENTARIO_PRODUCTO_NUEVO}
          element={
            <ProductoGestionGuard>
              <EditarProductoPage modo="crear" />
            </ProductoGestionGuard>
          }
        />
        <Route
          path="/inventario/productos/:id"
          element={
            <InventarioReadGuard><ProductoDetallePage /></InventarioReadGuard>
          }
        />
        <Route
          path="/inventario/productos/:id/editar"
          element={
            <ProductoGestionGuard>
              <EditarProductoPage modo="editar" />
            </ProductoGestionGuard>
          }
        />
        <Route
          path={ROUTES.INVENTARIO_CATEGORIAS}
          element={
            <InventarioReadGuard><CategoriasPage /></InventarioReadGuard>
          }
        />
        <Route
          path={ROUTES.INVENTARIO_BODEGAS}
          element={
            <InventarioReadGuard><BodegasPage /></InventarioReadGuard>
          }
        />
        <Route
          path={ROUTES.INVENTARIO_RECEPCION}
          element={
            <MercaderiaGuard><RecepcionPage /></MercaderiaGuard>
          }
        />
        <Route
          path={ROUTES.INVENTARIO_TRANSFERENCIAS}
          element={<AjusteGuard><TransferenciasPage /></AjusteGuard>}
        />
        <Route
          path={ROUTES.INVENTARIO_AJUSTES}
          element={<AjusteGuard><AjustesPage /></AjusteGuard>}
        />
        <Route
          path={ROUTES.INVENTARIO_MOVIMIENTOS}
          element={
            <InventarioReadGuard><MovimientosPage /></InventarioReadGuard>
          }
        />
        <Route
          path={ROUTES.INVENTARIO_POR_VENCER}
          element={
            <StockViewGuard><PorVencerPage /></StockViewGuard>
          }
        />

        {/* Caja (operación) */}
        <Route
          path={ROUTES.CAJA}
          element={<CajaOperarGuard><CajaOperacionPage /></CajaOperarGuard>}
        />
        <Route
          path={ROUTES.CAJA_SESIONES}
          element={<CajaOperarGuard><SesionesPage /></CajaOperarGuard>}
        />
        <Route
          path="/caja/sesiones/:id"
          element={<CajaOperarGuard><SesionDetallePage /></CajaOperarGuard>}
        />

        {/* POS y Ventas */}
        <Route
          path={ROUTES.POS}
          element={<VentaCrearGuard><PosPage /></VentaCrearGuard>}
        />
        <Route
          path={ROUTES.VENTAS}
          element={<VentaReadGuard><VentasPage /></VentaReadGuard>}
        />
        <Route
          path="/ventas/:id"
          element={<VentaReadGuard><VentaDetallePage /></VentaReadGuard>}
        />

        {/* Clientes */}
        <Route
          path={ROUTES.CLIENTES}
          element={<ClienteReadGuard><ClientesPage /></ClienteReadGuard>}
        />
        <Route
          path={ROUTES.CLIENTE_NUEVO}
          element={
            <ClienteGestionGuard>
              <EditarClientePage modo="crear" />
            </ClienteGestionGuard>
          }
        />
        <Route
          path="/clientes/:id/editar"
          element={
            <ClienteGestionGuard>
              <EditarClientePage modo="editar" />
            </ClienteGestionGuard>
          }
        />
        <Route
          path="/clientes/:id"
          element={
            <ClienteReadGuard><ClienteDetallePage /></ClienteReadGuard>
          }
        />

        {/* Proveedores */}
        <Route
          path={ROUTES.ADMIN_PROVEEDORES}
          element={<ProveedorReadGuard><ProveedoresPage /></ProveedorReadGuard>}
        />
        <Route
          path={ROUTES.ADMIN_PROVEEDOR_NUEVO}
          element={
            <ProveedorGestGuard>
              <EditarProveedorPage modo="crear" />
            </ProveedorGestGuard>
          }
        />
        <Route
          path="/admin/proveedores/:id/editar"
          element={
            <ProveedorGestGuard>
              <EditarProveedorPage modo="editar" />
            </ProveedorGestGuard>
          }
        />
        <Route
          path="/admin/proveedores/:id"
          element={
            <ProveedorReadGuard><ProveedorDetallePage /></ProveedorReadGuard>
          }
        />

        {/* Compras */}
        <Route
          path={ROUTES.COMPRAS}
          element={<CompraReadGuard><ComprasPage /></CompraReadGuard>}
        />
        <Route
          path={ROUTES.COMPRA_NUEVA}
          element={<CompraCreateGuard><NuevaCompraPage /></CompraCreateGuard>}
        />
        <Route
          path="/compras/:id"
          element={<CompraReadGuard><CompraDetallePage /></CompraReadGuard>}
        />

        {/* CxP */}
        <Route
          path={ROUTES.CXP}
          element={<CxPReadGuard><CxPPage /></CxPReadGuard>}
        />
        <Route
          path="/cxp/:id"
          element={<CxPReadGuard><CxPDetallePage /></CxPReadGuard>}
        />
      </Route>
      <Route path="*" element={<Navigate to={ROUTES.HOME} replace />} />
    </Routes>
  );
}

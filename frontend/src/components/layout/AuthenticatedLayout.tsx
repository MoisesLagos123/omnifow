import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3,
  Boxes,
  ChevronDown,
  FileText,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Receipt,
  ShieldCheck,
  ShoppingCart,
  Users,
  Wallet,
  X,
} from "lucide-react";

import { ThemeToggle } from "../ui/ThemeToggle";
import { SucursalSwitcher } from "./SucursalSwitcher";
import { useAuth } from "../../auth/useAuth";
import { useAnyPermission } from "../../auth/usePermission";
import { CambiarPasswordModal } from "../../auth/CambiarPasswordModal";
import { ROUTES } from "../../routePaths";
import styles from "./AuthenticatedLayout.module.css";

// Permisos de cada sección — fuente única de verdad en `auth/menuPermissions`.
// La sidebar y el dashboard de Inicio importan desde el mismo módulo para
// que los accesos rápidos coincidan con lo que se ve en el menú lateral.
import {
  ADMIN_PERMS,
  AUDIT_PERMS,
  USUARIO_PERMS,
  PERFIL_PERMS,
  PERMISO_PERMS,
  SUCURSAL_PERMS,
  INV_PERMS,
  RECEPCION_PERMS,
  AJUSTE_PERMS,
  STOCK_VIEW_PERMS,
  CAJA_PERMS,
  CLIENTE_PERMS,
  POS_PERMS,
  PROVEEDOR_CONSULTAR_PERMS,
  COMPRA_CREAR_PERMS,
  COMPRA_CONSULTAR_PERMS,
  CXP_CONSULTAR_PERMS,
  CXC_CONSULTAR_PERMS,
  DEVOLUCION_CONSULTAR_PERMS,
  DOCUMENTO_CONSULTAR_PERMS,
  REPORTES_VER_PERMS,
} from "../../auth/menuPermissions";

export function AuthenticatedLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const canAdmin = useAnyPermission(ADMIN_PERMS);
  const canUsuarios = useAnyPermission(USUARIO_PERMS);
  const canPerfiles = useAnyPermission(PERFIL_PERMS);
  const canPermisos = useAnyPermission(PERMISO_PERMS);
  const canAudit = useAnyPermission(AUDIT_PERMS);
  const canSucursales = useAnyPermission(SUCURSAL_PERMS);
  const canInventario = useAnyPermission(INV_PERMS);
  const canRecepcion = useAnyPermission(RECEPCION_PERMS);
  const canAjuste = useAnyPermission(AJUSTE_PERMS);
  const canStockView = useAnyPermission(STOCK_VIEW_PERMS);
  const canCaja = useAnyPermission(CAJA_PERMS);
  const canClientes = useAnyPermission(CLIENTE_PERMS);
  const canPos = useAnyPermission(POS_PERMS);
  const canProveedores = useAnyPermission(PROVEEDOR_CONSULTAR_PERMS);
  const canCompraCrear = useAnyPermission(COMPRA_CREAR_PERMS);
  const canCompraConsultar = useAnyPermission(COMPRA_CONSULTAR_PERMS);
  const canCxP = useAnyPermission(CXP_CONSULTAR_PERMS);
  const canCxC = useAnyPermission(CXC_CONSULTAR_PERMS);
  const canDevoluciones = useAnyPermission(DEVOLUCION_CONSULTAR_PERMS);
  const canDocumentos = useAnyPermission(DOCUMENTO_CONSULTAR_PERMS);
  const canReportes = useAnyPermission(REPORTES_VER_PERMS);
  const canCompras = canProveedores || canCompraCrear || canCompraConsultar || canCxP;
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(
    location.pathname.startsWith(ROUTES.ADMIN)
  );
  const [invOpen, setInvOpen] = useState(
    location.pathname.startsWith(ROUTES.INVENTARIO)
  );
  const [cajaOpen, setCajaOpen] = useState(
    location.pathname.startsWith(ROUTES.CAJA)
  );
  const [posOpen, setPosOpen] = useState(
    location.pathname.startsWith(ROUTES.POS) ||
      location.pathname.startsWith(ROUTES.VENTAS) ||
      location.pathname.startsWith(ROUTES.DEVOLUCIONES)
  );
  const [comprasOpen, setComprasOpen] = useState(
    location.pathname.startsWith(ROUTES.COMPRAS) ||
      location.pathname.startsWith(ROUTES.CXP) ||
      location.pathname.startsWith(ROUTES.ADMIN_PROVEEDORES)
  );
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [cambiarPasswordOpen, setCambiarPasswordOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!userMenuOpen) return;
    function onClick(e: MouseEvent) {
      if (
        userMenuRef.current &&
        e.target instanceof Node &&
        !userMenuRef.current.contains(e.target)
      ) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [userMenuOpen]);

  async function handleLogout() {
    // El logout server-side es best-effort — si el backend está caído
    // igual limpia el store y navega.
    await logout();
    navigate(ROUTES.LOGIN, { replace: true });
  }

  return (
    <div className={styles.layout}>
      {/* Skip-link: primer elemento focuseable de la página. Tab → Enter
          salta toda la nav y enfoca el <main>. Solo visible al recibir foco. */}
      <a href="#main-content" className="skip-link">
        Saltar al contenido principal
      </a>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button
            type="button"
            className={styles.menuBtn}
            onClick={() => setSidebarOpen((s) => !s)}
            aria-label={sidebarOpen ? "Cerrar menú" : "Abrir menú"}
            aria-expanded={sidebarOpen}
          >
            {sidebarOpen ? (
              <X size={20} aria-hidden="true" />
            ) : (
              <Menu size={20} aria-hidden="true" />
            )}
          </button>
          <Link to={ROUTES.HOME} className={styles.brand} aria-label="OMNIFLOW — Inicio">
            <img
              src="/logo.png"
              alt=""
              className={styles.brandMark}
              aria-hidden="true"
            />
            <span className={styles.brandName}>OMNIFLOW</span>
          </Link>
        </div>

        <div className={styles.headerRight}>
          <SucursalSwitcher />
          <ThemeToggle />
          <div className={styles.userMenu} ref={userMenuRef}>
            <button
              type="button"
              className={styles.userBtn}
              onClick={() => setUserMenuOpen((o) => !o)}
              aria-haspopup="menu"
              aria-expanded={userMenuOpen}
            >
              <span className={styles.avatar} aria-hidden="true">
                {(user?.nombre ?? "?").charAt(0).toUpperCase()}
              </span>
              <span className={styles.userName}>{user?.nombre ?? "Usuario"}</span>
              <ChevronDown size={16} aria-hidden="true" />
            </button>
            {userMenuOpen && (
              <div className={styles.dropdown} role="menu">
                <div className={styles.dropdownHeader}>
                  <p className={styles.dropdownName}>{user?.nombre}</p>
                  <p className={styles.dropdownEmail}>{user?.email}</p>
                </div>
                <button
                  type="button"
                  role="menuitem"
                  className={styles.dropdownItem}
                  onClick={() => {
                    setUserMenuOpen(false);
                    setCambiarPasswordOpen(true);
                  }}
                >
                  <KeyRound size={16} aria-hidden="true" />
                  Cambiar contraseña
                </button>
                <button
                  type="button"
                  role="menuitem"
                  className={styles.dropdownItem}
                  onClick={handleLogout}
                >
                  <LogOut size={16} aria-hidden="true" />
                  Cerrar sesión
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className={styles.body}>
        <aside
          className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ""}`}
          aria-label="Navegación principal"
        >
          <nav className={styles.nav}>
            <NavItem
              to={ROUTES.HOME}
              icon={<LayoutDashboard size={18} aria-hidden="true" />}
              end
            >
              Inicio
            </NavItem>

            {(canPos || canCaja || canDocumentos) && (
              <p className={styles.sectionLabel}>Operación</p>
            )}

            {canPos && (
              <div className={styles.group}>
                <button
                  type="button"
                  className={`${styles.groupHeader} ${posOpen ? styles.groupOpen : ""}`}
                  onClick={() => setPosOpen((o) => !o)}
                  aria-expanded={posOpen}
                  aria-controls="nav-pos-children"
                >
                  <ShoppingCart size={18} aria-hidden="true" />
                  <span className={styles.groupLabel}>POS</span>
                  <ChevronDown size={16} aria-hidden="true" className={styles.groupChevron} />
                </button>
                {posOpen && (
                  <div id="nav-pos-children" className={styles.subnav}>
                    <NavItem to={ROUTES.POS} subitem>
                      Vender
                    </NavItem>
                    <NavItem to={ROUTES.VENTAS} subitem>
                      Historial de ventas
                    </NavItem>
                    {canDevoluciones && (
                      <NavItem to={ROUTES.DEVOLUCIONES} subitem>
                        Devoluciones
                      </NavItem>
                    )}
                  </div>
                )}
              </div>
            )}

            {canCaja && (
              <div className={styles.group}>
                <button
                  type="button"
                  className={`${styles.groupHeader} ${cajaOpen ? styles.groupOpen : ""}`}
                  onClick={() => setCajaOpen((o) => !o)}
                  aria-expanded={cajaOpen}
                  aria-controls="nav-caja-children"
                >
                  <Wallet size={18} aria-hidden="true" />
                  <span className={styles.groupLabel}>Caja</span>
                  <ChevronDown size={16} aria-hidden="true" className={styles.groupChevron} />
                </button>
                {cajaOpen && (
                  <div id="nav-caja-children" className={styles.subnav}>
                    <NavItem to={ROUTES.CAJA} subitem end>
                      Operación
                    </NavItem>
                    <NavItem to={ROUTES.CAJA_SESIONES} subitem>
                      Historial de sesiones
                    </NavItem>
                  </div>
                )}
              </div>
            )}

            {canDocumentos && (
              <NavItem
                to={ROUTES.DOCUMENTOS}
                icon={<FileText size={18} aria-hidden="true" />}
              >
                Documentos
              </NavItem>
            )}

            {(canInventario || canClientes) && (
              <p className={styles.sectionLabel}>Catálogo</p>
            )}

            {canInventario && (
              <div className={styles.group}>
                <button
                  type="button"
                  className={`${styles.groupHeader} ${invOpen ? styles.groupOpen : ""}`}
                  onClick={() => setInvOpen((o) => !o)}
                  aria-expanded={invOpen}
                  aria-controls="nav-inv-children"
                >
                  <Boxes size={18} aria-hidden="true" />
                  <span className={styles.groupLabel}>Inventario</span>
                  <ChevronDown size={16} aria-hidden="true" className={styles.groupChevron} />
                </button>
                {invOpen && (
                  <div id="nav-inv-children" className={styles.subnav}>
                    <NavItem to={ROUTES.INVENTARIO_PRODUCTOS} subitem>
                      Productos
                    </NavItem>
                    <NavItem to={ROUTES.INVENTARIO_CATEGORIAS} subitem>
                      Categorías
                    </NavItem>
                    <NavItem to={ROUTES.INVENTARIO_BODEGAS} subitem>
                      Bodegas
                    </NavItem>
                    {canRecepcion && (
                      <NavItem to={ROUTES.INVENTARIO_RECEPCION} subitem>
                        Recepción
                      </NavItem>
                    )}
                    {canAjuste && (
                      <NavItem to={ROUTES.INVENTARIO_TRANSFERENCIAS} subitem>
                        Transferencias
                      </NavItem>
                    )}
                    {canAjuste && (
                      <NavItem to={ROUTES.INVENTARIO_AJUSTES} subitem>
                        Ajustes
                      </NavItem>
                    )}
                    {canStockView && (
                      <NavItem to={ROUTES.INVENTARIO_MOVIMIENTOS} subitem>
                        Movimientos
                      </NavItem>
                    )}
                    {canStockView && (
                      <NavItem to={ROUTES.INVENTARIO_POR_VENCER} subitem>
                        Por vencer
                      </NavItem>
                    )}
                  </div>
                )}
              </div>
            )}

            {canClientes && (
              <NavItem
                to={ROUTES.CLIENTES}
                icon={<Users size={18} aria-hidden="true" />}
              >
                Clientes
              </NavItem>
            )}

            {/* COMPRAS — grupo expandible con Proveedores + ciclo de compra + CxP */}
            {canCompras && (
              <p className={styles.sectionLabel}>Compras</p>
            )}

            {canCompras && (
              <div className={styles.group}>
                <button
                  type="button"
                  className={`${styles.groupHeader} ${comprasOpen ? styles.groupOpen : ""}`}
                  onClick={() => setComprasOpen((o) => !o)}
                  aria-expanded={comprasOpen}
                  aria-controls="nav-compras-children"
                >
                  <Package size={18} aria-hidden="true" />
                  <span className={styles.groupLabel}>Compras</span>
                  <ChevronDown size={16} aria-hidden="true" className={styles.groupChevron} />
                </button>
                {comprasOpen && (
                  <div id="nav-compras-children" className={styles.subnav}>
                    {canProveedores && (
                      <NavItem to={ROUTES.ADMIN_PROVEEDORES} subitem>
                        Proveedores
                      </NavItem>
                    )}
                    {canCompraCrear && (
                      <NavItem to={ROUTES.COMPRA_NUEVA} subitem>
                        Nueva compra
                      </NavItem>
                    )}
                    {canCompraConsultar && (
                      <NavItem to={ROUTES.COMPRAS} subitem>
                        Historial de compras
                      </NavItem>
                    )}
                    {canCxP && (
                      <NavItem to={ROUTES.CXP} subitem>
                        Cuentas por pagar
                      </NavItem>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* FINANZAS — cobros pendientes a clientes (CxC) y reportes.
                CxP queda dentro del módulo Compras porque viene del ciclo
                de compras a proveedor. */}
            {(canCxC || canReportes) && (
              <p className={styles.sectionLabel}>Finanzas</p>
            )}

            {canCxC && (
              <NavItem
                to={ROUTES.CXC}
                icon={<Receipt size={18} aria-hidden="true" />}
              >
                Cuentas por cobrar
              </NavItem>
            )}

            {canReportes && (
              <NavItem
                to={ROUTES.REPORTES}
                icon={<BarChart3 size={18} aria-hidden="true" />}
              >
                Reportes
              </NavItem>
            )}

            {/* ADMINISTRACIÓN — usuarios, perfiles, permisos, sucursales, auditoría */}
            {canAdmin && (
              <p className={styles.sectionLabel}>Administración</p>
            )}

            {canAdmin && (
              <div className={styles.group}>
                <button
                  type="button"
                  className={`${styles.groupHeader} ${adminOpen ? styles.groupOpen : ""}`}
                  onClick={() => setAdminOpen((o) => !o)}
                  aria-expanded={adminOpen}
                  aria-controls="nav-admin-children"
                >
                  <ShieldCheck size={18} aria-hidden="true" />
                  <span className={styles.groupLabel}>Administración</span>
                  <ChevronDown size={16} aria-hidden="true" className={styles.groupChevron} />
                </button>
                {adminOpen && (
                  <div id="nav-admin-children" className={styles.subnav}>
                    {canUsuarios && (
                      <NavItem to={ROUTES.ADMIN_USUARIOS} subitem>
                        Usuarios
                      </NavItem>
                    )}
                    {canPerfiles && (
                      <NavItem to={ROUTES.ADMIN_PERFILES} subitem>
                        Perfiles
                      </NavItem>
                    )}
                    {canPermisos && (
                      <NavItem to={ROUTES.ADMIN_PERMISOS} subitem>
                        Permisos
                      </NavItem>
                    )}
                    {canAudit && (
                      <NavItem to={ROUTES.ADMIN_AUDIT} subitem>
                        Auditoría
                      </NavItem>
                    )}
                    {canSucursales && (
                      <NavItem to={ROUTES.ADMIN_SUCURSALES} subitem>
                        Sucursales
                      </NavItem>
                    )}
                  </div>
                )}
              </div>
            )}

          </nav>
        </aside>

        {sidebarOpen && (
          <div
            className={styles.scrim}
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* tabIndex=-1 permite al skip-link enfocar el main programáticamente
            sin convertirlo en parada normal del orden de tabulación. */}
        <main className={styles.main} id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>

      <CambiarPasswordModal
        open={cambiarPasswordOpen}
        onClose={() => setCambiarPasswordOpen(false)}
      />
    </div>
  );
}

function NavItem({
  to,
  icon,
  children,
  end,
  subitem,
}: {
  to: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  end?: boolean;
  subitem?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          styles.navItem,
          subitem ? styles.subItem : "",
          isActive ? styles.navItemActive : "",
        ]
          .filter(Boolean)
          .join(" ")
      }
    >
      {icon && <span className={styles.navIcon}>{icon}</span>}
      <span className={styles.navLabel}>{children}</span>
    </NavLink>
  );
}


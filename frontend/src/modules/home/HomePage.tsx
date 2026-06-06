import { Link } from "react-router-dom";
import {
  ArrowRight,
  Boxes,
  Receipt,
  ShieldCheck,
  ShoppingCart,
  Users,
  Wallet,
} from "lucide-react";

import { Card } from "../../components/ui/Card";
import { Chip } from "../../components/ui/Chip";
import { PageHeader } from "../../components/ui/PageHeader";
import { useAuth } from "../../auth/useAuth";
import { useAnyPermission } from "../../auth/usePermission";
import {
  ADMIN_PERMS,
  CAJA_PERMS,
  CLIENTE_PERMS,
  INV_PERMS,
  POS_PERMS,
} from "../../auth/menuPermissions";
import { ROUTES } from "../../routePaths";
import styles from "./HomePage.module.css";

const PERFIL_DESCRIPCIONES: Record<string, string> = {
  Sysadmin: "Acceso global al sistema, configuración y auditoría.",
  Administrador: "Gestión de productos, precios, proveedores y reportes.",
  Contador: "Acceso a finanzas, cuentas por cobrar/pagar y conciliación.",
  "Jefe de Sucursal":
    "Operación completa de sucursal, devoluciones y descuentos.",
  Vendedor: "Operación de POS, ventas y cobros.",
  Cajero: "Operación de caja: aperturas, movimientos y cierres.",
  Reponedor: "Recepción de mercadería y ajustes de inventario.",
};

interface QuickLink {
  to: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  /**
   * Permisos requeridos. El usuario solo necesita UNO de ellos para ver el
   * acceso. Se importan desde `auth/menuPermissions` para que coincidan
   * exactamente con los gates de la sidebar.
   */
  permission: readonly string[];
}

/**
 * Catálogo de accesos rápidos. El orden y los permisos coinciden 1:1 con
 * la sidebar — agrega/quita aquí Y allá en sincronía.
 */
const QUICK_LINKS: QuickLink[] = [
  {
    to: ROUTES.POS,
    label: "Vender",
    description: "POS — registrar una venta nueva.",
    icon: <ShoppingCart size={20} aria-hidden="true" />,
    permission: POS_PERMS,
  },
  {
    to: ROUTES.VENTAS,
    label: "Historial",
    description: "Ventas y documentos emitidos.",
    icon: <Receipt size={20} aria-hidden="true" />,
    permission: POS_PERMS,
  },
  {
    to: ROUTES.CAJA,
    label: "Caja",
    description: "Apertura, movimientos y cierre.",
    icon: <Wallet size={20} aria-hidden="true" />,
    permission: CAJA_PERMS,
  },
  {
    to: ROUTES.INVENTARIO_PRODUCTOS,
    label: "Inventario",
    description: "Productos, stock y recepción.",
    icon: <Boxes size={20} aria-hidden="true" />,
    permission: INV_PERMS,
  },
  {
    to: ROUTES.CLIENTES,
    label: "Clientes",
    description: "Buscar, crear y editar clientes.",
    icon: <Users size={20} aria-hidden="true" />,
    permission: CLIENTE_PERMS,
  },
  {
    to: ROUTES.ADMIN_USUARIOS,
    label: "Administración",
    description: "Usuarios, perfiles y sucursales.",
    icon: <ShieldCheck size={20} aria-hidden="true" />,
    permission: ADMIN_PERMS,
  },
];

function QuickLinkCard({ link }: { link: QuickLink }) {
  return (
    <Link to={link.to} className={styles.quickCard}>
      <span className={styles.quickIcon} aria-hidden="true">
        {link.icon}
      </span>
      <span className={styles.quickBody}>
        <span className={styles.quickLabel}>{link.label}</span>
        <span className={styles.quickDescription}>{link.description}</span>
      </span>
      <ArrowRight
        size={16}
        aria-hidden="true"
        className={styles.quickArrow}
      />
    </Link>
  );
}

/** Sólo renderiza el QuickLink si el usuario tiene alguno de los permisos. */
function PermittedQuickLink({ link }: { link: QuickLink }) {
  const allowed = useAnyPermission(link.permission);
  if (!allowed) return null;
  return <QuickLinkCard link={link} />;
}

export function HomePage() {
  const { user, perfiles } = useAuth();
  return (
    <>
      <PageHeader
        eyebrow="Panel"
        title={`Hola, ${user?.nombre ?? "usuario"}`}
        subtitle="Selecciona un módulo del menú o usa los accesos rápidos."
      />

      <div className={styles.page}>
        <section aria-labelledby="quick-title">
          <h2 id="quick-title" className={styles.sectionTitle}>
            Accesos rápidos
          </h2>
          <div className={styles.quickGrid}>
            {QUICK_LINKS.map((link) => (
              <PermittedQuickLink key={link.to} link={link} />
            ))}
          </div>
        </section>

        <section aria-labelledby="perfiles-title">
          <h2 id="perfiles-title" className={styles.sectionTitle}>
            Tus perfiles
          </h2>
          <Card>
            {perfiles.length === 0 ? (
              <p className={styles.empty}>
                Aún no tienes perfiles asignados. Contacta a un administrador.
              </p>
            ) : (
              <ul className={styles.profileList}>
                {perfiles.map((p) => (
                  <li key={p} className={styles.profileItem}>
                    <Chip>{p}</Chip>
                    <p className={styles.profileDesc}>
                      {PERFIL_DESCRIPCIONES[p] ??
                        "Perfil personalizado del sistema."}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </section>
      </div>
    </>
  );
}

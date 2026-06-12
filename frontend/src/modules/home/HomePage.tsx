import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  CreditCard,
  DollarSign,
  FileText,
  Package,
  Receipt,
  RotateCcw,
  ShieldCheck,
  ShoppingCart,
  TrendingUp,
  Users,
  Wallet,
} from "lucide-react";

import { Card } from "../../components/ui/Card";
import { Chip } from "../../components/ui/Chip";
import { EmptyState } from "../../components/ui/EmptyState";
import { Skeleton } from "../../components/ui/Skeleton";
import { useAuth } from "../../auth/useAuth";
import { useAnyPermission } from "../../auth/usePermission";
import {
  ADMIN_PERMS,
  CAJA_PERMS,
  CLIENTE_PERMS,
  COMPRA_CONSULTAR_PERMS,
  CXP_CONSULTAR_PERMS,
  CXC_CONSULTAR_PERMS,
  DEVOLUCION_CONSULTAR_PERMS,
  INV_PERMS,
  POS_PERMS,
} from "../../auth/menuPermissions";
import { ROUTES } from "../../routePaths";
import styles from "./HomePage.module.css";

/* ─── Helpers ───────────────────────────────────────────────────── */

function formatCLP(value: number): string {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(value);
}

function todayLabel(): string {
  return new Intl.DateTimeFormat("es-CL", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());
}

/* ─── KPI Card ──────────────────────────────────────────────────── */

interface KpiCardProps {
  title: string;
  value: string | number | null;
  icon: React.ReactNode;
  /** Color accent del icono */
  accent?: "brand" | "success" | "warning" | "danger";
  /** Subtexto opcional debajo del valor */
  sub?: string;
  /** Si true, muestra skeleton en lugar del valor */
  loading?: boolean;
  /** Formato especial para el valor — "currency" usa font-mono */
  mono?: boolean;
}

function KpiCard({ title, value, icon, accent = "brand", sub, loading, mono }: KpiCardProps) {
  const accentMap: Record<string, string> = {
    brand: "var(--color-brand)",
    success: "var(--color-success)",
    warning: "var(--color-warning)",
    danger: "var(--color-danger)",
  };
  const softMap: Record<string, string> = {
    brand: "var(--color-brand-soft)",
    success: "var(--color-success-soft)",
    warning: "var(--color-warning-soft)",
    danger: "var(--color-danger-soft)",
  };

  return (
    <Card variant="elevated" className={styles.kpiCard}>
      <div className={styles.kpiHeader}>
        <span className={styles.kpiTitle}>{title}</span>
        <span
          className={styles.kpiIcon}
          aria-hidden="true"
          style={{
            color: accentMap[accent],
            background: softMap[accent],
          }}
        >
          {icon}
        </span>
      </div>
      {loading ? (
        <Skeleton height={36} width="60%" style={{ borderRadius: "var(--radius-sm)" }} />
      ) : (
        <p
          className={styles.kpiValue}
          style={mono ? { fontFamily: "var(--font-mono)" } : undefined}
        >
          {value ?? "0"}
        </p>
      )}
      {sub && !loading && (
        <p className={styles.kpiSub}>{sub}</p>
      )}
      {loading && (
        <Skeleton height={14} width="40%" style={{ marginTop: "var(--space-1)", borderRadius: "var(--radius-sm)" }} />
      )}
    </Card>
  );
}

/* ─── Quick links ───────────────────────────────────────────────── */

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
  permission: readonly string[];
}

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
  {
    to: ROUTES.COMPRAS,
    label: "Compras",
    description: "Historial de compras y proveedores.",
    icon: <Package size={20} aria-hidden="true" />,
    permission: COMPRA_CONSULTAR_PERMS,
  },
  {
    to: ROUTES.CXP,
    label: "Cuentas por pagar",
    description: "Saldos pendientes con proveedores.",
    icon: <CreditCard size={20} aria-hidden="true" />,
    permission: CXP_CONSULTAR_PERMS,
  },
  {
    to: ROUTES.CXC,
    label: "Cuentas por cobrar",
    description: "Saldos de clientes por ventas a crédito.",
    icon: <FileText size={20} aria-hidden="true" />,
    permission: CXC_CONSULTAR_PERMS,
  },
  {
    to: ROUTES.DEVOLUCIONES,
    label: "Devoluciones",
    description: "Historial de devoluciones y NC emitidas.",
    icon: <RotateCcw size={20} aria-hidden="true" />,
    permission: DEVOLUCION_CONSULTAR_PERMS,
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

function PermittedQuickLink({ link }: { link: QuickLink }) {
  const allowed = useAnyPermission(link.permission);
  if (!allowed) return null;
  return <QuickLinkCard link={link} />;
}

/* ─── HomePage ──────────────────────────────────────────────────── */

export function HomePage() {
  const { user, perfiles, permisos } = useAuth();

  const hasAnyAccess = useMemo(
    () => QUICK_LINKS.some((l) => l.permission.some((p) => permisos.includes(p))),
    [permisos]
  );

  const hasPosAccess = useAnyPermission(POS_PERMS);

  // KPI data: placeholders con 0 hasta que se conecten endpoints reales.
  // Loading = false porque no hay fetch todavía — se muestra "0".
  const kpiLoading = false;

  return (
    <div className={styles.page}>
      {/* ── Dashboard header ── */}
      <div className={styles.dashHeader}>
        <div className={styles.dashGreeting}>
          <h1 className={styles.greetingTitle}>
            Hola, {user?.nombre ?? "usuario"}
          </h1>
          <p className={styles.greetingDate}>{todayLabel()}</p>
        </div>
        <div className={styles.dashMeta}>
          <TrendingUp size={16} aria-hidden="true" style={{ color: "var(--color-success)" }} />
          <span className={styles.dashMetaText}>Panel de operación</span>
        </div>
      </div>

      {/* ── KPI grid ── */}
      {hasPosAccess && (
        <section aria-labelledby="kpi-title">
          <h2 id="kpi-title" className={styles.sectionTitle}>
            Resumen del día
          </h2>
          <div className={styles.kpiGrid}>
            <KpiCard
              title="Ventas hoy"
              value={formatCLP(0)}
              icon={<DollarSign size={18} />}
              accent="brand"
              sub="Sin datos de ventas aún"
              loading={kpiLoading}
              mono
            />
            <KpiCard
              title="Tickets emitidos"
              value={0}
              icon={<Receipt size={18} />}
              accent="success"
              sub="Boletas y facturas"
              loading={kpiLoading}
            />
            <KpiCard
              title="Stock crítico"
              value={0}
              icon={<AlertTriangle size={18} />}
              accent="warning"
              sub="Productos en bajo stock"
              loading={kpiLoading}
            />
            <KpiCard
              title="CxC pendiente"
              value={formatCLP(0)}
              icon={<CreditCard size={18} />}
              accent="danger"
              sub="Ventas a crédito sin cobrar"
              loading={kpiLoading}
              mono
            />
          </div>
        </section>
      )}

      {/* ── Accesos rápidos ── */}
      <section aria-labelledby="quick-title">
        <h2 id="quick-title" className={styles.sectionTitle}>
          Accesos rápidos
        </h2>
        {hasAnyAccess ? (
          <div className={styles.quickGrid}>
            {QUICK_LINKS.map((link) => (
              <PermittedQuickLink key={link.to} link={link} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<ShieldCheck size={32} />}
            title="Sin accesos disponibles"
            description="No tienes permisos asignados para ningún módulo aún."
            action={
              <Link
                to={ROUTES.ADMIN_USUARIOS}
                style={{
                  color: "var(--color-brand)",
                  fontSize: "var(--font-sm)",
                  textDecoration: "none",
                }}
              >
                Ver mi cuenta
              </Link>
            }
          />
        )}
      </section>

      {/* ── Última actividad (placeholder) ── */}
      {hasPosAccess && (
        <section aria-labelledby="activity-title">
          <h2 id="activity-title" className={styles.sectionTitle}>
            Últimas ventas
          </h2>
          <Card>
            <EmptyState
              variant="inline"
              icon={<Receipt size={24} />}
              title="Sin ventas recientes"
              description="Aquí verás las últimas 5 ventas cuando haya datos disponibles."
            />
          </Card>
        </section>
      )}

      {/* ── Perfiles ── */}
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
  );
}

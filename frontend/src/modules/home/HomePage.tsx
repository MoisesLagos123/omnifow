import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  Clock,
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

/* ─── Bento KPI Card ────────────────────────────────────────────── */

type KpiVariant = "ventas" | "tickets" | "stock" | "cxc";

interface BentoKpiCardProps {
  variant: KpiVariant;
  title: string;
  value: string | number | null;
  icon: React.ReactNode;
  delta: string;
  sub: string;
  loading?: boolean;
  /** spans 2 columns in desktop bento */
  wide?: boolean;
}

const variantStyles: Record<KpiVariant, string> = {
  ventas: styles.kpiVentas,
  tickets: styles.kpiTickets,
  stock: styles.kpiStock,
  cxc: styles.kpiCxc,
};

const bentoSizeStyles: Record<string, string> = {
  hero: styles.kpiHero,
  wide: styles.kpiWide,
  normal: styles.kpiNormal,
};

function BentoKpiCard({
  variant,
  title,
  value,
  icon,
  delta,
  sub,
  loading,
  wide,
}: BentoKpiCardProps) {
  const sizeClass = wide ? bentoSizeStyles.hero : bentoSizeStyles.normal;

  return (
    <article
      className={`${styles.kpiCard} ${variantStyles[variant]} ${sizeClass}`}
      aria-label={title}
    >
      <div className={styles.kpiHeader}>
        <div className={styles.kpiLabel}>{title}</div>
        <div className={styles.kpiIconWrap} aria-hidden="true">
          {icon}
        </div>
      </div>
      {loading ? (
        <Skeleton height={36} width="60%" style={{ borderRadius: "var(--radius-sm)" }} />
      ) : (
        <div className={styles.kpiValue}>{value ?? "0"}</div>
      )}
      {loading ? (
        <Skeleton height={14} width="40%" style={{ marginTop: "var(--space-1)", borderRadius: "var(--radius-sm)" }} />
      ) : (
        <div className={styles.kpiDelta}>
          <TrendingUp size={11} aria-hidden="true" />
          {delta}
          {sub && <span className={styles.kpiSub}>{sub}</span>}
        </div>
      )}
    </article>
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

      {/* ── KPI bento grid ── */}
      {hasPosAccess && (
        <section aria-labelledby="kpi-title">
          <h2 id="kpi-title" className={styles.sectionTitle}>
            Resumen del día
          </h2>
          <div className={styles.kpiBento}>
            {/* Row 1: Ventas (hero/span-2) + Tickets + Stock */}
            <BentoKpiCard
              variant="ventas"
              title="Ventas hoy"
              value={formatCLP(0)}
              icon={<DollarSign size={24} />}
              delta="Sin datos aún"
              sub=""
              loading={kpiLoading}
              wide
            />
            <BentoKpiCard
              variant="tickets"
              title="Tickets emitidos"
              value={0}
              icon={<Receipt size={24} />}
              delta="Boletas y facturas"
              sub=""
              loading={kpiLoading}
            />
            <BentoKpiCard
              variant="stock"
              title="Stock crítico"
              value={0}
              icon={<AlertTriangle size={24} />}
              delta="Bajo mínimo"
              sub=""
              loading={kpiLoading}
            />
            {/* Row 2: CxC span 4 (todo el ancho) */}
            <BentoKpiCard
              variant="cxc"
              title="CxC pendiente"
              value={formatCLP(0)}
              icon={<Clock size={24} />}
              delta="Sin vencimientos"
              sub=""
              loading={kpiLoading}
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
            Ultimas ventas
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

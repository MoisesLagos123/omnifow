import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { ArrowLeft, Pencil, RotateCcw, Trash2 } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Modal } from "../../components/ui/Modal";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import { proveedoresApi, type Proveedor } from "../../api/proveedores";
import {
  comprasApi,
  type CompraListItem,
  ESTADO_COMPRA_LABELS,
  TIPO_DOCUMENTO_COMPRA_LABELS,
} from "../../api/compras";
import {
  describeError,
  extractProveedorEnUso,
} from "../../api/errorMessages";
import { formatearRut } from "../administracion/rut";
import { formatCLP, formatFechaSoloDia } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./ComprasPages.module.css";

export function ProveedorDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const canGestionar = usePermission("proveedor.gestionar");

  const [proveedor, setProveedor] = useState<Proveedor | null>(null);
  const [compras, setCompras] = useState<CompraListItem[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [confirmDeact, setConfirmDeact] = useState(false);
  const [working, setWorking] = useState(false);
  const [enUsoModal, setEnUsoModal] = useState(false);
  const [enUsoInfo, setEnUsoInfo] = useState<{
    cxp_pendientes: number;
    monto_total_clp: number;
  } | null>(null);

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoadError(null);
    proveedoresApi
      .obtener(id, ctl.signal)
      .then(setProveedor)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, reloadTick]);

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    comprasApi
      .listar({ proveedor_id: id, limit: 10 }, ctl.signal)
      .then((res) => setCompras(res.items))
      .catch(() => setCompras([]));
    return () => ctl.abort();
  }, [id, reloadTick]);

  function reload() {
    setReloadTick((t) => t + 1);
  }

  async function handleDeactivate() {
    if (!proveedor) return;
    setWorking(true);
    try {
      await proveedoresApi.desactivar(proveedor.id);
      toast.success("Proveedor desactivado", proveedor.razon_social);
      setConfirmDeact(false);
      reload();
    } catch (err) {
      setConfirmDeact(false);
      const details = extractProveedorEnUso(err);
      if (details) {
        setEnUsoInfo(details);
        setEnUsoModal(true);
        return;
      }
      toast.error("No se pudo desactivar", describeError(err));
    } finally {
      setWorking(false);
    }
  }

  async function handleReactivate() {
    if (!proveedor) return;
    setWorking(true);
    try {
      const actualizado = await proveedoresApi.reactivar(proveedor.id);
      toast.success("Proveedor reactivado", actualizado.razon_social);
      reload();
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setWorking(false);
    }
  }

  const compraColumns: TableColumn<CompraListItem>[] = [
    {
      key: "fecha",
      header: "Fecha",
      width: "110px",
      cell: (c) => (
        <span className={styles.mono}>{formatFechaSoloDia(c.fecha_documento)}</span>
      ),
    },
    {
      key: "tipo",
      header: "Tipo",
      width: "100px",
      cell: (c) => TIPO_DOCUMENTO_COMPRA_LABELS[c.tipo_documento],
    },
    {
      key: "nro",
      header: "N° documento",
      cell: (c) => <span className={styles.mono}>{c.numero_documento}</span>,
    },
    {
      key: "total",
      header: "Total",
      align: "right",
      width: "120px",
      cell: (c) => (
        <span className={styles.numeric}>{formatCLP(c.total_clp)}</span>
      ),
    },
    {
      key: "estado",
      header: "Estado",
      width: "110px",
      cell: (c) => (
        <Badge
          variant={
            c.estado === "CONFIRMADA"
              ? "success"
              : c.estado === "ANULADA"
                ? "danger"
                : "neutral"
          }
        >
          {ESTADO_COMPRA_LABELS[c.estado]}
        </Badge>
      ),
    },
  ];

  if (loadError) {
    return (
      <div className={styles.detail}>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.ADMIN_PROVEEDORES)}
        >
          Volver a proveedores
        </Button>
        <ErrorAlert>{loadError}</ErrorAlert>
        <Button variant="ghost" onClick={reload}>
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.ADMIN_PROVEEDORES)}
        >
          Volver a proveedores
        </Button>
      </div>

      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>
            {proveedor ? (
              <>
                {proveedor.razon_social}
                <span className={styles.codeChip}>
                  {formatearRut(proveedor.rut)}
                </span>
                {proveedor.activo ? (
                  <Badge variant="success">Activo</Badge>
                ) : (
                  <Badge variant="neutral">Inactivo</Badge>
                )}
              </>
            ) : (
              <Skeleton width={280} />
            )}
          </h1>
        </div>

        {proveedor && (
          <div className={styles.headerActions}>
            <RequirePermission code="proveedor.gestionar">
              <Button
                variant="ghost"
                leftIcon={<Pencil size={16} aria-hidden="true" />}
                onClick={() =>
                  navigate(ROUTES.ADMIN_PROVEEDOR_EDITAR(proveedor.id))
                }
              >
                Editar
              </Button>
            </RequirePermission>
            {proveedor.activo
              ? canGestionar && (
                  <Button
                    variant="danger-ghost"
                    leftIcon={<Trash2 size={16} aria-hidden="true" />}
                    onClick={() => setConfirmDeact(true)}
                  >
                    Desactivar
                  </Button>
                )
              : canGestionar && (
                  <Button
                    leftIcon={<RotateCcw size={16} aria-hidden="true" />}
                    onClick={handleReactivate}
                    loading={working}
                  >
                    Reactivar
                  </Button>
                )}
          </div>
        )}
      </header>

      {proveedor ? (
        <Card>
          <dl className={styles.detailGrid}>
            <dt>RUT</dt>
            <dd className={styles.mono}>{formatearRut(proveedor.rut)}</dd>
            <dt>Razón social</dt>
            <dd>{proveedor.razon_social}</dd>
            <dt>Giro</dt>
            <dd>
              {proveedor.giro ?? <em className={styles.muted}>—</em>}
            </dd>
            <dt>Dirección</dt>
            <dd>
              {proveedor.direccion ?? <em className={styles.muted}>—</em>}
            </dd>
            <dt>Email</dt>
            <dd>
              {proveedor.email ?? <em className={styles.muted}>—</em>}
            </dd>
            <dt>Teléfono</dt>
            <dd>
              {proveedor.telefono ?? <em className={styles.muted}>—</em>}
            </dd>
            <dt>Compras totales</dt>
            <dd className={styles.numeric}>{proveedor.cantidad_compras}</dd>
            <dt>CxP pendiente</dt>
            <dd>
              {proveedor.cxp_pendientes_clp > 0 ? (
                <span
                  className={styles.numeric}
                  style={{ color: "var(--color-danger)", fontWeight: 600 }}
                >
                  {formatCLP(proveedor.cxp_pendientes_clp)}
                </span>
              ) : (
                <em className={styles.muted}>Sin deudas pendientes</em>
              )}
            </dd>
          </dl>
        </Card>
      ) : (
        <Skeleton height="280px" />
      )}

      <section aria-labelledby="compras-recientes-title">
        <h2 id="compras-recientes-title" className={styles.sectionTitle}>
          Últimas compras
        </h2>
        {compras.length > 0 ? (
          <Table<CompraListItem>
            density="compact"
            columns={compraColumns}
            rows={compras}
            rowKey={(c) => c.id}
            onRowClick={(c) => navigate(ROUTES.COMPRA_DETALLE(c.id))}
            caption="Últimas compras del proveedor"
          />
        ) : (
          <p className={styles.muted}>
            No hay compras registradas para este proveedor.
          </p>
        )}
        {compras.length > 0 && proveedor && (
          <div style={{ marginTop: "var(--space-2)" }}>
            <Link
              to={`${ROUTES.COMPRAS}?proveedor_id=${proveedor.id}`}
              style={{ fontSize: "0.85rem", color: "var(--color-brand)" }}
            >
              Ver todas las compras
            </Link>
          </div>
        )}
      </section>

      {proveedor && proveedor.cxp_pendientes_clp > 0 && (
        <section aria-labelledby="cxp-title">
          <h2 id="cxp-title" className={styles.sectionTitle}>
            Cuentas por pagar
          </h2>
          <Card>
            <p>
              Saldo pendiente total:{" "}
              <strong style={{ color: "var(--color-danger)" }}>
                {formatCLP(proveedor.cxp_pendientes_clp)}
              </strong>
            </p>
            <div style={{ marginTop: "var(--space-2)" }}>
              <Link
                to={`${ROUTES.CXP}?proveedor_id=${proveedor.id}`}
                style={{ fontSize: "0.88rem", color: "var(--color-brand)" }}
              >
                Ver cuentas por pagar de este proveedor
              </Link>
            </div>
          </Card>
        </section>
      )}

      <ConfirmDialog
        open={confirmDeact}
        onClose={() => setConfirmDeact(false)}
        title="Desactivar proveedor"
        description={
          proveedor
            ? `¿Confirmas que deseas desactivar a "${proveedor.razon_social}"? Podrás reactivarlo más adelante.`
            : ""
        }
        confirmLabel="Desactivar"
        destructive
        onConfirm={handleDeactivate}
      />

      <Modal
        open={enUsoModal}
        onClose={() => setEnUsoModal(false)}
        title="No se puede desactivar"
        description="El proveedor tiene cuentas por pagar pendientes."
        size="sm"
        footer={
          <Button onClick={() => setEnUsoModal(false)}>Entendido</Button>
        }
      >
        {enUsoInfo && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            <p>
              Tiene <strong>{enUsoInfo.cxp_pendientes}</strong> cuenta(s) por
              pagar pendiente(s) con un saldo total de{" "}
              <strong style={{ color: "var(--color-danger)" }}>
                {formatCLP(enUsoInfo.monto_total_clp)}
              </strong>
              .
            </p>
            <p className={styles.muted}>
              Liquida las cuentas pendientes antes de desactivar el proveedor.
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}

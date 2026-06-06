import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { ArrowLeft, XCircle } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Modal } from "../../components/ui/Modal";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table";
import { useToast } from "../../components/ui/Toast";
import { usePermission } from "../../auth/usePermission";
import {
  comprasApi,
  type Compra,
  type CompraDetalleItem,
  ESTADO_COMPRA_LABELS,
  CONDICION_PAGO_LABELS,
  TIPO_DOCUMENTO_COMPRA_LABELS,
} from "../../api/compras";
import {
  describeError,
  extractCompraConAbonos,
} from "../../api/errorMessages";
import { formatCLP, formatFechaSoloDia, formatCantidad, formatFechaISO } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./ComprasPages.module.css";

export function CompraDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const canAnular = usePermission("compra.anular");

  const [compra, setCompra] = useState<Compra | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [confirmAnular, setConfirmAnular] = useState(false);
  const [abonosModal, setAbonosModal] = useState(false);
  const [abonosInfo, setAbonosInfo] = useState<{
    cxp_id: string;
    abonos_count: number;
    abonos_total_clp: number;
  } | null>(null);

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoadError(null);
    comprasApi
      .obtener(id, ctl.signal)
      .then(setCompra)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, reloadTick]);

  async function handleAnular() {
    if (!compra) return;
    try {
      await comprasApi.anular(compra.id);
      toast.success("Compra anulada", `${compra.numero_documento}`);
      setConfirmAnular(false);
      setReloadTick((t) => t + 1);
    } catch (err) {
      setConfirmAnular(false);
      const details = extractCompraConAbonos(err);
      if (details) {
        setAbonosInfo(details);
        setAbonosModal(true);
        return;
      }
      toast.error("No se pudo anular", describeError(err));
    }
  }

  const itemColumns: TableColumn<CompraDetalleItem>[] = [
    {
      key: "nombre",
      header: "Producto",
      cell: (d) => (
        <div>
          <strong>{d.producto_nombre}</strong>
          <span className={styles.cellSub}> · {d.producto_sku}</span>
        </div>
      ),
    },
    {
      key: "cantidad",
      header: "Cantidad",
      width: "100px",
      align: "right",
      cell: (d) => (
        <span className={styles.numeric}>{formatCantidad(d.cantidad)}</span>
      ),
    },
    {
      key: "costo",
      header: "Costo unit.",
      width: "130px",
      align: "right",
      cell: (d) => (
        <span className={styles.numeric}>
          {formatCLP(d.costo_unitario_clp)}
        </span>
      ),
    },
    {
      key: "subtotal",
      header: "Subtotal",
      width: "130px",
      align: "right",
      cell: (d) => (
        <span className={styles.numeric}>{formatCLP(d.subtotal_clp)}</span>
      ),
    },
    {
      key: "lote",
      header: "Lote / Vencimiento",
      width: "160px",
      cell: (d) =>
        d.fecha_vencimiento ? (
          <span className={styles.muted} style={{ fontSize: "0.82rem" }}>
            {d.numero_lote ? `Lote: ${d.numero_lote} · ` : ""}
            Vence: {formatFechaSoloDia(d.fecha_vencimiento)}
          </span>
        ) : (
          <em className={styles.muted}>—</em>
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
          onClick={() => navigate(ROUTES.COMPRAS)}
        >
          Volver a compras
        </Button>
        <ErrorAlert>{loadError}</ErrorAlert>
        <Button variant="ghost" onClick={() => setReloadTick((t) => t + 1)}>
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
          onClick={() => navigate(ROUTES.COMPRAS)}
        >
          Volver a compras
        </Button>
      </div>

      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>
            {compra ? (
              <>
                {TIPO_DOCUMENTO_COMPRA_LABELS[compra.tipo_documento]}{" "}
                <span className={styles.codeChip}>
                  {compra.numero_documento}
                </span>
                <Badge
                  variant={
                    compra.estado === "CONFIRMADA"
                      ? "success"
                      : compra.estado === "ANULADA"
                        ? "danger"
                        : "neutral"
                  }
                >
                  {ESTADO_COMPRA_LABELS[compra.estado]}
                </Badge>
                <Badge
                  variant={
                    compra.condicion_pago === "CREDITO" ? "warning" : "neutral"
                  }
                >
                  {CONDICION_PAGO_LABELS[compra.condicion_pago]}
                </Badge>
              </>
            ) : (
              <Skeleton width={320} />
            )}
          </h1>
          {compra && (
            <p className={styles.subtitle}>
              Fecha: {formatFechaSoloDia(compra.fecha_documento)} · Recibida:{" "}
              {formatFechaISO(compra.fecha_recepcion)}
            </p>
          )}
        </div>

        {compra && canAnular && compra.estado === "CONFIRMADA" && (
          <div className={styles.headerActions}>
            <Button
              variant="danger-ghost"
              leftIcon={<XCircle size={16} aria-hidden="true" />}
              onClick={() => setConfirmAnular(true)}
            >
              Anular compra
            </Button>
          </div>
        )}
      </header>

      {compra ? (
        <>
          <div className={styles.formRow}>
            <Card>
              <h2 className={styles.sectionTitle}>Proveedor</h2>
              <dl className={styles.detailGrid} style={{ gridTemplateColumns: "120px 1fr" }}>
                <dt>Razón social</dt>
                <dd>
                  <Link
                    to={ROUTES.ADMIN_PROVEEDOR_DETALLE(compra.proveedor_id)}
                    style={{ color: "var(--color-brand)" }}
                  >
                    {compra.proveedor_razon_social}
                  </Link>
                </dd>
                <dt>RUT</dt>
                <dd className={styles.mono}>{compra.proveedor_rut}</dd>
              </dl>
            </Card>
            <Card>
              <h2 className={styles.sectionTitle}>Destino</h2>
              <dl className={styles.detailGrid} style={{ gridTemplateColumns: "90px 1fr" }}>
                <dt>Sucursal</dt>
                <dd className={styles.mono}>{compra.sucursal_codigo}</dd>
                <dt>Bodega</dt>
                <dd className={styles.mono}>{compra.bodega_codigo}</dd>
                {compra.condicion_pago === "CREDITO" && (
                  <>
                    <dt>Días crédito</dt>
                    <dd>{compra.dias_credito} días</dd>
                  </>
                )}
              </dl>
            </Card>
          </div>

          {compra.observaciones && (
            <Card>
              <h2 className={styles.sectionTitle}>Observaciones</h2>
              <p className={styles.muted}>{compra.observaciones}</p>
            </Card>
          )}

          <Card>
            <h2 className={styles.sectionTitle}>Ítems</h2>
            <Table<CompraDetalleItem>
              density="compact"
              columns={itemColumns}
              rows={compra.items}
              rowKey={(d) => d.id}
              caption="Ítems de la compra"
            />
            <div className={styles.footerTotal}>
              <span>
                Subtotal neto:{" "}
                <span className={styles.numeric}>
                  {formatCLP(compra.subtotal_neto_clp)}
                </span>
              </span>
              <span>
                IVA 19%:{" "}
                <span className={styles.numeric}>
                  {formatCLP(compra.iva_clp)}
                </span>
              </span>
              <span className={styles.footerTotalBold}>
                Total: {formatCLP(compra.total_clp)}
              </span>
            </div>
          </Card>

          {compra.condicion_pago === "CREDITO" && compra.cxp_id && (
            <Card>
              <h2 className={styles.sectionTitle}>Cuenta por pagar</h2>
              <p style={{ fontSize: "0.9rem", marginBottom: "var(--space-2)" }}>
                Esta compra generó una CxP por{" "}
                <strong>{formatCLP(compra.total_clp)}</strong>.
              </p>
              <Link
                to={ROUTES.CXP_DETALLE(compra.cxp_id)}
                style={{ fontSize: "0.88rem", color: "var(--color-brand)" }}
              >
                Ver cuenta por pagar →
              </Link>
            </Card>
          )}
        </>
      ) : (
        <Skeleton height="400px" />
      )}

      <ConfirmDialog
        open={confirmAnular}
        onClose={() => setConfirmAnular(false)}
        title="Anular compra"
        description={
          compra
            ? `¿Confirmas anular la ${TIPO_DOCUMENTO_COMPRA_LABELS[compra.tipo_documento]} N° ${compra.numero_documento}? El stock ingresado se revertirá.`
            : ""
        }
        confirmLabel="Anular compra"
        destructive
        onConfirm={handleAnular}
      />

      <Modal
        open={abonosModal}
        onClose={() => setAbonosModal(false)}
        title="No se puede anular"
        description="La cuenta por pagar de esta compra tiene abonos registrados."
        size="sm"
        footer={
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <Button variant="ghost" onClick={() => setAbonosModal(false)}>
              Cerrar
            </Button>
            {abonosInfo?.cxp_id && (
              <Button
                onClick={() => {
                  setAbonosModal(false);
                  navigate(ROUTES.CXP_DETALLE(abonosInfo.cxp_id));
                }}
              >
                Ver CxP
              </Button>
            )}
          </div>
        }
      >
        {abonosInfo && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            <p>
              Se han registrado <strong>{abonosInfo.abonos_count}</strong>{" "}
              abono(s) por un total de{" "}
              <strong>{formatCLP(abonosInfo.abonos_total_clp)}</strong>.
            </p>
            <p className={styles.muted}>
              Para anular esta compra, primero debería revertirse los abonos en
              la cuenta por pagar.
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}

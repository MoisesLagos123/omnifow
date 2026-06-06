import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Pencil, Receipt, RotateCcw, Trash2 } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { Table, type TableColumn } from "../../components/ui/Table";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import { clientesApi, type Cliente } from "../../api/clientes";
import { cxcApi, type CxCListItem, ESTADO_CXC_LABELS } from "../../api/cxc";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaSoloDia } from "../../lib/format";
import { formatearRut } from "../administracion/rut";
import { ROUTES } from "../../routePaths";
import styles from "./ClientesPages.module.css";

export function ClienteDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const canGestionar = usePermission("cliente.gestionar");

  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [confirmDeact, setConfirmDeact] = useState(false);
  const [working, setWorking] = useState(false);

  // CxC del cliente
  const [cxcItems, setCxcItems] = useState<CxCListItem[] | null>(null);
  const [cxcLoading, setCxcLoading] = useState(false);
  const canCxCConsultar = usePermission("cxc.consultar");
  const canCxCGestionar = usePermission("cxc.gestionar");
  const canVerCxC = canCxCConsultar || canCxCGestionar;

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoadError(null);
    clientesApi
      .obtenerCliente(id, ctl.signal)
      .then(setCliente)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, reloadTick]);

  // Cargar CxC del cliente
  useEffect(() => {
    if (!id || !canVerCxC) return;
    const ctl = new AbortController();
    setCxcLoading(true);
    cxcApi
      .listarPorCliente(id, ctl.signal)
      .then(setCxcItems)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        // No bloquea la página si falla; solo queda null.
        setCxcItems([]);
      })
      .finally(() => setCxcLoading(false));
    return () => ctl.abort();
  }, [id, canVerCxC, reloadTick]);

  function reload() {
    setReloadTick((t) => t + 1);
  }

  async function handleDeactivate() {
    if (!cliente) return;
    setWorking(true);
    try {
      await clientesApi.desactivarCliente(cliente.id);
      toast.success("Cliente desactivado", cliente.razon_social);
      reload();
    } catch (err) {
      toast.error("No se pudo desactivar", describeError(err));
    } finally {
      setWorking(false);
    }
  }

  async function handleReactivate() {
    if (!cliente) return;
    setWorking(true);
    try {
      const actualizado = await clientesApi.reactivarCliente(cliente.id);
      toast.success("Cliente reactivado", actualizado.razon_social);
      reload();
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setWorking(false);
    }
  }

  if (loadError) {
    return (
      <div className={styles.detail}>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.CLIENTES)}
        >
          Volver a clientes
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
          onClick={() => navigate(ROUTES.CLIENTES)}
        >
          Volver a clientes
        </Button>
      </div>

      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>
            {cliente ? (
              <>
                {cliente.razon_social}
                <span className={styles.codeChip}>
                  {formatearRut(cliente.rut)}
                </span>
                {cliente.activo ? (
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

        {cliente && (
          <div className={styles.headerActions}>
            <RequirePermission code="cliente.gestionar">
              <Button
                variant="ghost"
                leftIcon={<Pencil size={16} aria-hidden="true" />}
                onClick={() => navigate(ROUTES.CLIENTE_EDITAR(cliente.id))}
              >
                Editar
              </Button>
            </RequirePermission>
            {cliente.activo
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

      {cliente ? (
        <Card>
          <dl className={styles.detailGrid}>
            <dt>RUT</dt>
            <dd className={styles.mono}>{formatearRut(cliente.rut)}</dd>
            <dt>Razón social</dt>
            <dd>{cliente.razon_social}</dd>
            <dt>Giro</dt>
            <dd>{cliente.giro ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Dirección</dt>
            <dd>{cliente.direccion ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Comuna</dt>
            <dd>{cliente.comuna ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Región</dt>
            <dd>{cliente.region ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Email</dt>
            <dd>{cliente.email ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Teléfono</dt>
            <dd>{cliente.telefono ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Estado</dt>
            <dd>
              {cliente.activo ? (
                <Badge variant="success">Activo</Badge>
              ) : (
                <Badge variant="neutral">Inactivo</Badge>
              )}
            </dd>
          </dl>
        </Card>
      ) : (
        <Skeleton height="300px" />
      )}

      {/* Estado de cuenta — CxC del cliente */}
      {canVerCxC && (
        <section aria-labelledby="estado-cuenta-title">
          <h2 id="estado-cuenta-title" className={styles.sectionTitle}>
            Estado de cuenta
          </h2>
          {cxcLoading ? (
            <Skeleton height="120px" />
          ) : cxcItems && cxcItems.length > 0 ? (
            <Card>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
                <Receipt size={18} aria-hidden="true" />
                <strong>Cuentas por cobrar</strong>
              </div>
              <Table<CxCListItem>
                density="compact"
                columns={[
                  {
                    key: "documento",
                    header: "Documento",
                    cell: (c) => (
                      <Link
                        to={ROUTES.CXC_DETALLE(c.id)}
                        style={{ color: "var(--color-brand)" }}
                      >
                        {c.venta_tipo_documento} #{c.venta_numero_documento}
                      </Link>
                    ),
                  },
                  {
                    key: "original",
                    header: "Monto original",
                    width: "130px",
                    align: "right",
                    cell: (c) => formatCLP(c.monto_original_clp),
                  },
                  {
                    key: "saldo",
                    header: "Saldo",
                    width: "120px",
                    align: "right",
                    cell: (c) => (
                      <span
                        style={{
                          color: c.monto_saldo_clp > 0 ? "var(--color-danger)" : "var(--color-text-muted)",
                          fontWeight: c.monto_saldo_clp > 0 ? 600 : undefined,
                        }}
                      >
                        {formatCLP(c.monto_saldo_clp)}
                      </span>
                    ),
                  },
                  {
                    key: "vence",
                    header: "Vencimiento",
                    width: "140px",
                    cell: (c) => (
                      <span>
                        {formatFechaSoloDia(c.fecha_vencimiento)}{" "}
                        {c.dias_vencido > 0 && (
                          <span style={{ color: "var(--color-danger)", fontWeight: 600, fontSize: "0.8rem" }}>
                            Vencido {c.dias_vencido}d
                          </span>
                        )}
                      </span>
                    ),
                  },
                  {
                    key: "estado",
                    header: "Estado",
                    width: "90px",
                    cell: (c) => (
                      <Badge
                        variant={
                          c.estado === "PAGADA"
                            ? "success"
                            : c.estado === "ANULADA"
                              ? "neutral"
                              : c.estado === "PARCIAL"
                                ? "warning"
                                : "info"
                        }
                      >
                        {ESTADO_CXC_LABELS[c.estado]}
                      </Badge>
                    ),
                  },
                ] as TableColumn<CxCListItem>[]}
                rows={cxcItems}
                rowKey={(c) => c.id}
                caption="Cuentas por cobrar del cliente"
              />
              <div
                style={{
                  marginTop: "var(--space-3)",
                  textAlign: "right",
                  fontSize: "0.9rem",
                  color: "var(--color-text-muted)",
                }}
              >
                Total adeudado:{" "}
                <strong style={{ color: "var(--color-danger)" }}>
                  {formatCLP(cxcItems.reduce((a, c) => a + c.monto_saldo_clp, 0))}
                </strong>
              </div>
            </Card>
          ) : (
            <Card>
              <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "0.9rem" }}>
                Sin cuentas por cobrar para este cliente.
              </p>
            </Card>
          )}
        </section>
      )}

      <ConfirmDialog
        open={confirmDeact}
        onClose={() => setConfirmDeact(false)}
        title="Desactivar cliente"
        description={
          cliente
            ? `¿Confirmas que deseas desactivar a "${cliente.razon_social}"? Podrás reactivarlo más adelante.`
            : ""
        }
        confirmLabel="Desactivar"
        destructive
        onConfirm={handleDeactivate}
      />
    </div>
  );
}

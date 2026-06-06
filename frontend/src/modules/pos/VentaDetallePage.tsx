import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Ban, Printer } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { Modal } from "../../components/ui/Modal";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import {
  PrintableReceipt,
  PrintArea,
} from "../../components/ui/PrintableReceipt";
import { useToast } from "../../components/ui/Toast";
import { usePermission } from "../../auth/usePermission";
import { Input } from "../../components/ui/Input";
import { TIPO_DOCUMENTO_LABEL, sucursalesApi } from "../../api/sucursales";
import {
  ventasApi,
  ESTADO_VENTA_LABEL,
  TIPO_PAGO_LABEL,
  type VentaConfirmadaResponse,
} from "../../api/ventas";
import { clientesApi, type Cliente } from "../../api/clientes";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatCantidad, formatFechaISO } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./PosPages.module.css";

export function VentaDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const canAnular = usePermission("venta.anular");

  const [data, setData] = useState<VentaConfirmadaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [sucursalNombre, setSucursalNombre] = useState<string | null>(null);

  const [printOpen, setPrintOpen] = useState(false);
  const [anularOpen, setAnularOpen] = useState(false);
  const [motivo, setMotivo] = useState("");

  const reload = useCallback(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    ventasApi
      .obtener(id, ctl.signal)
      .then(setData)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [id]);

  useEffect(() => {
    const cleanup = reload();
    return cleanup;
  }, [reload]);

  // Carga cliente (si aplica).
  useEffect(() => {
    if (!data?.venta.cliente_id) {
      setCliente(null);
      return;
    }
    const ctl = new AbortController();
    clientesApi
      .obtenerCliente(data.venta.cliente_id, ctl.signal)
      .then(setCliente)
      .catch(() => {
        // No es crítico
      });
    return () => ctl.abort();
  }, [data?.venta.cliente_id]);

  // Carga nombre de sucursal para el comprobante.
  useEffect(() => {
    if (!data?.venta.sucursal_id) return;
    const ctl = new AbortController();
    sucursalesApi
      .obtenerSucursal(data.venta.sucursal_id, ctl.signal)
      .then((s) => setSucursalNombre(s.nombre))
      .catch(() => {
        /* no crítico */
      });
    return () => ctl.abort();
  }, [data?.venta.sucursal_id]);

  async function handleAnular() {
    if (!data) return;
    try {
      const res = await ventasApi.anular(data.venta.id, {
        motivo: motivo.trim() || null,
      });
      setData(res);
      setAnularOpen(false);
      setMotivo("");
      toast.success("Venta anulada", "Se emitió la Nota de Crédito.");
    } catch (err) {
      toast.error("No se pudo anular", describeError(err));
    }
  }

  const sucursalParaImpresion = useMemo(() => {
    if (!data) return null;
    return {
      nombre: sucursalNombre ?? "OMNIFOW",
      direccion: null,
      comuna: null,
      region: null,
      rut_emisor: data.documento.rut_emisor,
    };
  }, [data, sucursalNombre]);

  if (loading) {
    return (
      <div className={styles.page}>
        <Skeleton height="2rem" width={240} />
        <Card>
          <Skeleton height="1.5rem" />
        </Card>
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div className={styles.page}>
        <ErrorAlert>{errorMsg}</ErrorAlert>
        <Button variant="ghost" onClick={() => navigate(ROUTES.VENTAS)}>
          Volver al historial
        </Button>
      </div>
    );
  }

  if (!data) return null;
  const { venta, detalles, pagos, documento } = data;
  const anulada = venta.estado === "ANULADA";

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <Button
            size="sm"
            variant="ghost"
            leftIcon={<ArrowLeft size={14} aria-hidden />}
            onClick={() => navigate(ROUTES.VENTAS)}
          >
            Historial
          </Button>
          <h1 className={styles.title}>
            {TIPO_DOCUMENTO_LABEL[documento.tipo]} N° {documento.folio}{" "}
            <Badge variant={anulada ? "danger" : "success"}>
              {ESTADO_VENTA_LABEL[venta.estado]}
            </Badge>
          </h1>
          <p className={styles.subtitle}>{formatFechaISO(venta.fecha)}</p>
        </div>
        <div className={styles.headActions}>
          <Button
            variant="ghost"
            leftIcon={<Printer size={16} aria-hidden />}
            onClick={() => setPrintOpen(true)}
          >
            Imprimir comprobante
          </Button>
          {!anulada && canAnular && (
            <Button
              leftIcon={<Ban size={16} aria-hidden />}
              onClick={() => setAnularOpen(true)}
              data-destructive=""
            >
              Anular venta
            </Button>
          )}
        </div>
      </header>

      <div className={styles.detailGrid}>
        <div className={styles.posColumn}>
          {cliente && (
            <Card>
              <div className={styles.clienteInfo}>
                <span className={styles.clienteRazon}>{cliente.razon_social}</span>
                <span className={styles.clienteGiro}>
                  {cliente.rut}
                  {cliente.giro ? ` · ${cliente.giro}` : ""}
                </span>
              </div>
            </Card>
          )}

          <Card>
            <p className={styles.cartTitle}>Productos</p>
            <table className={styles.cartTable}>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th className={styles.right}>Cantidad</th>
                  <th className={styles.right}>Precio</th>
                  <th className={styles.right}>Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {detalles.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <span className={styles.cartProductoCell}>
                        <span>{d.producto_nombre}</span>
                        <span className={styles.cartProductoSku}>{d.producto_sku}</span>
                      </span>
                    </td>
                    <td className={styles.right}>{formatCantidad(d.cantidad)}</td>
                    <td className={styles.right}>{formatCLP(d.precio_unitario_clp)}</td>
                    <td className={styles.right}>
                      {formatCLP(d.subtotal_clp + d.iva_clp)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <Card>
            <p className={styles.cartTitle}>Pagos</p>
            <table className={styles.cartTable}>
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Referencia</th>
                  <th className={styles.right}>Monto</th>
                </tr>
              </thead>
              <tbody>
                {pagos.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <Badge variant="info">{TIPO_PAGO_LABEL[p.tipo]}</Badge>
                    </td>
                    <td>
                      {p.referencia_externa ?? "—"}
                      {p.ultimos_4_digitos
                        ? ` · **** ${p.ultimos_4_digitos}`
                        : ""}
                    </td>
                    <td className={styles.right}>{formatCLP(p.monto_clp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>

        <div className={styles.posColumn}>
          <Card>
            <div className={styles.totalsCard}>
              <div className={styles.kpi}>
                <span className={styles.kpiLabel}>Total</span>
                <span className={styles.kpiValue}>{formatCLP(venta.total_clp)}</span>
              </div>
              <div className={styles.totalLine}>
                <span className={styles.totalLabel}>Subtotal neto</span>
                <span className={styles.totalValue}>
                  {formatCLP(venta.subtotal_clp)}
                </span>
              </div>
              <div className={styles.totalLine}>
                <span className={styles.totalLabel}>IVA</span>
                <span className={styles.totalValue}>{formatCLP(venta.iva_clp)}</span>
              </div>
            </div>
          </Card>

          <Card>
            <p className={styles.cartTitle}>Documento tributario</p>
            <div className={styles.meta} style={{ display: "grid", gap: "var(--space-2)" }}>
              <div className={styles.totalLine}>
                <span className={styles.totalLabel}>Tipo</span>
                <span>{TIPO_DOCUMENTO_LABEL[documento.tipo]}</span>
              </div>
              <div className={styles.totalLine}>
                <span className={styles.totalLabel}>Folio</span>
                <span className={styles.mono}>{documento.folio}</span>
              </div>
              <div className={styles.totalLine}>
                <span className={styles.totalLabel}>RUT emisor</span>
                <span className={styles.mono}>{documento.rut_emisor}</span>
              </div>
              {documento.rut_receptor && (
                <div className={styles.totalLine}>
                  <span className={styles.totalLabel}>RUT receptor</span>
                  <span className={styles.mono}>{documento.rut_receptor}</span>
                </div>
              )}
              <div className={styles.totalLine}>
                <span className={styles.totalLabel}>Estado SII</span>
                <Badge
                  variant={
                    documento.estado_sii === "ACEPTADO"
                      ? "success"
                      : documento.estado_sii === "RECHAZADO"
                        ? "danger"
                        : "neutral"
                  }
                >
                  {documento.estado_sii}
                </Badge>
              </div>
            </div>
          </Card>

          {anulada && (
            <Card>
              <Badge variant="danger">Anulada</Badge>
              <p className={styles.muted} style={{ marginTop: "var(--space-2)" }}>
                Se emitió una Nota de Crédito que reversa esta venta.
              </p>
            </Card>
          )}
        </div>
      </div>

      {printOpen && (
        <Modal
          open
          onClose={() => setPrintOpen(false)}
          title="Comprobante"
          size="md"
          footer={
            <>
              <Button variant="ghost" onClick={() => setPrintOpen(false)}>
                Cerrar
              </Button>
              <Button
                leftIcon={<Printer size={16} aria-hidden />}
                onClick={() => window.print()}
              >
                Imprimir
              </Button>
            </>
          }
        >
          <div className={styles.receiptPreview}>
            <PrintableReceipt
              venta={venta}
              detalles={detalles}
              pagos={pagos}
              documento={documento}
              sucursal={sucursalParaImpresion}
              clienteNombre={cliente?.razon_social ?? null}
            />
          </div>
          <PrintArea>
            <PrintableReceipt
              venta={venta}
              detalles={detalles}
              pagos={pagos}
              documento={documento}
              sucursal={sucursalParaImpresion}
              clienteNombre={cliente?.razon_social ?? null}
            />
          </PrintArea>
        </Modal>
      )}

      <ConfirmDialog
        open={anularOpen}
        title="Anular venta"
        description={
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            <span>
              Se emitirá una Nota de Crédito que reversa esta venta, el stock y los pagos. Esta acción no se puede deshacer.
            </span>
            <Input
              label="Motivo (opcional)"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Devolución, error en boleta…"
            />
          </div>
        }
        confirmLabel="Anular venta"
        destructive
        onConfirm={handleAnular}
        onClose={() => {
          setAnularOpen(false);
          setMotivo("");
        }}
      />
    </div>
  );
}

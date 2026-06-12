import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Printer } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Modal } from "../../components/ui/Modal";
import { Skeleton } from "../../components/ui/Skeleton";
import {
  PrintableReceipt,
  PrintArea,
} from "../../components/ui/PrintableReceipt";
import {
  documentosApi,
  TIPO_DOCUMENTO_LABEL,
  ESTADO_SII_LABEL,
  type DocumentoDetalle as DocumentoDetalleType,
  type EstadoSii,
  type TipoDocumento,
} from "../../api/documentosApi";
import { describeError } from "../../api/errorMessages";
import { formatCLP, formatFechaISO } from "../../lib/format";
import { ROUTES } from "../../routePaths";
import styles from "./DocumentosPages.module.css";

function estadoBadgeVariant(
  estado: EstadoSii
): "neutral" | "success" | "danger" | "warning" {
  switch (estado) {
    case "PENDIENTE":
      return "neutral";
    case "ACEPTADO":
      return "success";
    case "RECHAZADO":
      return "danger";
    case "ANULADO":
      return "warning";
  }
}

function tipoBadgeVariant(
  tipo: TipoDocumento
): "info" | "brand" | "neutral" | "success" | "warning" | "danger" {
  switch (tipo) {
    case "BOLETA":
      return "info";
    case "FACTURA":
      return "brand";
    case "NC":
      return "warning";
    case "ND":
      return "warning";
    case "GUIA":
      return "neutral";
  }
}

export function DocumentoDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<DocumentoDetalleType | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [printOpen, setPrintOpen] = useState(false);

  const reload = useCallback(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    documentosApi
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

  // Construimos el objeto mínimo compatible con PrintableReceipt para
  // documentos BOLETA/FACTURA que tienen venta adjunta.
  const printData = useMemo(() => {
    if (!data || !data.venta) return null;
    const ventaCompat = {
      id: data.venta.id,
      sucursal_id: data.sucursal_id,
      caja_id: data.venta.caja_id,
      usuario_id: data.venta.usuario_id,
      cliente_id: null,
      tipo_documento: data.tipo as "BOLETA" | "FACTURA",
      subtotal_clp: data.subtotal_clp,
      iva_clp: data.iva_clp,
      total_clp: data.total_clp,
      estado: "CONFIRMADA" as const,
      documento_tributario_id: data.id,
      fecha: data.venta.fecha,
    };
    const detallesCompat = data.venta.detalles.map((det, i) => ({
      id: `det-${String(i)}`,
      venta_id: data.venta!.id,
      producto_id: "",
      producto_sku: det.producto_sku,
      producto_nombre: det.producto_nombre,
      cantidad: String(det.cantidad),
      precio_unitario_clp: det.precio_unitario_clp,
      costo_unitario_clp: 0,
      iva_porcentaje: 19,
      subtotal_clp: det.total_clp,
      iva_clp: 0,
      lote_id: null,
    }));
    const pagosCompat = data.venta.pagos.map((p, i) => ({
      id: `pago-${String(i)}`,
      venta_id: data.venta!.id,
      tipo: p.tipo as "EFECTIVO" | "TRANSFERENCIA" | "DEBITO" | "CREDITO",
      monto_clp: p.monto_clp,
      referencia_externa: p.referencia_externa,
      ultimos_4_digitos: p.ultimos_4_digitos,
    }));
    const docCompat = {
      id: data.id,
      tipo: data.tipo as "BOLETA" | "FACTURA",
      folio: data.folio,
      sucursal_id: data.sucursal_id,
      rut_emisor: data.rut_emisor,
      rut_receptor: data.rut_receptor ?? null,
      razon_social_receptor: data.razon_social_receptor ?? null,
      venta_id: data.venta?.id ?? null,
      subtotal_clp: data.subtotal_clp,
      iva_clp: data.iva_clp,
      total_clp: data.total_clp,
      // DocumentoTributario from ventas.ts uses "ENVIADO" but not "ANULADO";
      // we cast to the accepted union and fall back to "PENDIENTE" for safety.
      estado_sii: (
        data.estado_sii === "ACEPTADO" || data.estado_sii === "RECHAZADO" || data.estado_sii === "PENDIENTE"
          ? data.estado_sii
          : "PENDIENTE"
      ) as "PENDIENTE" | "ENVIADO" | "ACEPTADO" | "RECHAZADO",
      emitido_en: data.emitido_en,
    };
    return { venta: ventaCompat, detalles: detallesCompat, pagos: pagosCompat, documento: docCompat };
  }, [data]);

  if (loading) {
    return (
      <div className={styles.page}>
        <Skeleton height="2rem" width={280} />
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
        <Button variant="ghost" onClick={() => navigate(ROUTES.DOCUMENTOS)}>
          Volver a documentos
        </Button>
      </div>
    );
  }

  if (!data) return null;

  const tipoLabel = TIPO_DOCUMENTO_LABEL[data.tipo];

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.head}>
        <div className={styles.headLeft}>
          <Button
            size="sm"
            variant="ghost"
            leftIcon={<ArrowLeft size={14} aria-hidden />}
            onClick={() => navigate(ROUTES.DOCUMENTOS)}
          >
            Documentos
          </Button>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <Badge variant={tipoBadgeVariant(data.tipo)} size="md">
              {tipoLabel}
            </Badge>
            <Badge variant={estadoBadgeVariant(data.estado_sii)} size="md">
              {ESTADO_SII_LABEL[data.estado_sii]}
            </Badge>
          </div>
          <h1 className={styles.titleFolio}>
            N° {data.folio}
          </h1>
          <p className={styles.subtitle}>{formatFechaISO(data.emitido_en)}</p>
        </div>
        {/* Desktop sticky actions */}
        <div className={styles.headActionsSticky}>
          <Button
            variant="accent"
            leftIcon={<Printer size={16} aria-hidden />}
            onClick={() => setPrintOpen(true)}
          >
            Reimprimir
          </Button>
        </div>
      </header>

      {/* Mobile sticky bottom bar */}
      <div className={styles.mobileActions}>
        <Button
          fullWidth
          variant="accent"
          leftIcon={<Printer size={16} aria-hidden />}
          onClick={() => setPrintOpen(true)}
        >
          Reimprimir
        </Button>
      </div>

      <div className={styles.detailGrid}>
        {/* Columna izquierda */}
        <div className={styles.column}>
          {/* Emisor / Receptor */}
          <Card>
            <p className={styles.cardTitle}>Partes</p>
            <div className={styles.infoGrid}>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Sucursal</span>
                <span className={styles.infoValue}>{data.sucursal_nombre}</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>RUT Emisor</span>
                <span className={`${styles.infoValue} ${styles.mono}`}>
                  {data.rut_emisor}
                </span>
              </div>
              {data.rut_receptor && (
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>RUT Receptor</span>
                  <span className={`${styles.infoValue} ${styles.mono}`}>
                    {data.rut_receptor}
                  </span>
                </div>
              )}
              {data.razon_social_receptor && (
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Razón Social Receptor</span>
                  <span className={styles.infoValue}>
                    {data.razon_social_receptor}
                  </span>
                </div>
              )}
            </div>
          </Card>

          {/* Referencia si es NC/ND */}
          {data.documento_referencia_id && (
            <Card>
              <p className={styles.cardTitle}>Documento Referenciado</p>
              <div className={styles.infoGrid}>
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Tipo</span>
                  <span className={styles.infoValue}>
                    {data.documento_referencia_tipo
                      ? TIPO_DOCUMENTO_LABEL[data.documento_referencia_tipo]
                      : "—"}
                  </span>
                </div>
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Folio</span>
                  <span className={`${styles.infoValue} ${styles.mono}`}>
                    #{data.documento_referencia_folio ?? "—"}
                  </span>
                </div>
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Enlace</span>
                  <Link
                    to={ROUTES.DOCUMENTO_DETALLE(data.documento_referencia_id)}
                    className={styles.refLink}
                  >
                    Ver documento original →
                  </Link>
                </div>
              </div>
            </Card>
          )}

          {/* Detalles según tipo */}
          {(data.tipo === "BOLETA" || data.tipo === "FACTURA") &&
            data.venta && (
              <>
                <Card>
                  <p className={styles.cardTitle}>Productos</p>
                  <table className={styles.itemsTable}>
                    <thead>
                      <tr>
                        <th>Producto</th>
                        <th>SKU</th>
                        <th className={styles.right}>Cant.</th>
                        <th className={styles.right}>P. Unit.</th>
                        <th className={styles.right}>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.venta.detalles.map((det, i) => (
                        // eslint-disable-next-line react/no-array-index-key
                        <tr key={i}>
                          <td>{det.producto_nombre}</td>
                          <td className={styles.mono}>{det.producto_sku}</td>
                          <td className={styles.right}>{det.cantidad}</td>
                          <td className={styles.right}>
                            {formatCLP(det.precio_unitario_clp)}
                          </td>
                          <td className={styles.right}>
                            {formatCLP(det.total_clp)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>

                <Card>
                  <p className={styles.cardTitle}>Pagos</p>
                  <table className={styles.itemsTable}>
                    <thead>
                      <tr>
                        <th>Tipo</th>
                        <th>Referencia</th>
                        <th className={styles.right}>Monto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.venta.pagos.map((pago, i) => (
                        // eslint-disable-next-line react/no-array-index-key
                        <tr key={i}>
                          <td>
                            <Badge variant="info">{pago.tipo}</Badge>
                          </td>
                          <td>
                            {pago.referencia_externa ?? "—"}
                            {pago.ultimos_4_digitos
                              ? ` · **** ${pago.ultimos_4_digitos}`
                              : ""}
                          </td>
                          <td className={styles.right}>
                            {formatCLP(pago.monto_clp)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </>
            )}

          {/* NC: motivo */}
          {data.tipo === "NC" && (
            <Card>
              <p className={styles.cardTitle}>Detalle Nota de Crédito</p>
              <div className={styles.infoGrid}>
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Motivo</span>
                  <span className={styles.infoValue}>
                    {data.venta
                      ? "Devolución de venta"
                      : "—"}
                  </span>
                </div>
              </div>
            </Card>
          )}

          {/* ND: motivo */}
          {data.tipo === "ND" && data.nota_debito && (
            <Card>
              <p className={styles.cardTitle}>Detalle Nota de Débito</p>
              <div className={styles.infoGrid}>
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Motivo</span>
                  <span className={styles.infoValue}>{data.nota_debito.motivo}</span>
                </div>
              </div>
            </Card>
          )}

          {/* GUIA: líneas + datos traslado */}
          {data.tipo === "GUIA" && data.guia_despacho && (
            <>
              <Card>
                <p className={styles.cardTitle}>Datos de Traslado</p>
                <div className={styles.infoGrid}>
                  <div className={styles.infoRow}>
                    <span className={styles.infoLabel}>Tipo de traslado</span>
                    <span className={styles.infoValue}>
                      {data.guia_despacho.tipo_traslado}
                    </span>
                  </div>
                  <div className={styles.infoRow}>
                    <span className={styles.infoLabel}>Dirección destino</span>
                    <span className={styles.infoValue}>
                      {data.guia_despacho.direccion_destino}
                    </span>
                  </div>
                  {data.guia_despacho.patente_vehiculo && (
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>Patente</span>
                      <span className={`${styles.infoValue} ${styles.mono}`}>
                        {data.guia_despacho.patente_vehiculo}
                      </span>
                    </div>
                  )}
                  {data.guia_despacho.observaciones && (
                    <div className={styles.infoRow}>
                      <span className={styles.infoLabel}>Observaciones</span>
                      <span className={styles.infoValue}>
                        {data.guia_despacho.observaciones}
                      </span>
                    </div>
                  )}
                </div>
              </Card>

              <Card>
                <p className={styles.cardTitle}>Líneas Guía</p>
                <table className={styles.itemsTable}>
                  <thead>
                    <tr>
                      <th>Producto</th>
                      <th>SKU</th>
                      <th className={styles.right}>Cant.</th>
                      <th className={styles.right}>P. Unit.</th>
                      <th className={styles.right}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.guia_despacho.detalles.map((det) => (
                      <tr key={det.id}>
                        <td>{det.producto_nombre}</td>
                        <td className={styles.mono}>{det.producto_sku}</td>
                        <td className={styles.right}>{det.cantidad}</td>
                        <td className={styles.right}>
                          {formatCLP(det.precio_unitario_clp)}
                        </td>
                        <td className={styles.right}>
                          {formatCLP(det.total_clp)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </>
          )}
        </div>

        {/* Columna derecha */}
        <div className={styles.column}>
          {/* Totales */}
          <Card>
            <div className={styles.totalsCard}>
              <div className={styles.kpi}>
                <span className={styles.kpiLabel}>Total</span>
                <span className={styles.kpiValue}>{formatCLP(data.total_clp)}</span>
              </div>
              <div className={styles.totalLine}>
                <span className={styles.totalLabel}>Neto</span>
                <span className={styles.totalValue}>
                  {formatCLP(data.subtotal_clp)}
                </span>
              </div>
              <div className={styles.totalLine}>
                <span className={styles.totalLabel}>IVA 19%</span>
                <span className={styles.totalValue}>
                  {formatCLP(data.iva_clp)}
                </span>
              </div>
            </div>
          </Card>

          {/* Estado SII */}
          <Card>
            <p className={styles.cardTitle}>Estado SII</p>
            <div className={styles.infoGrid}>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Estado</span>
                <Badge variant={estadoBadgeVariant(data.estado_sii)}>
                  {ESTADO_SII_LABEL[data.estado_sii]}
                </Badge>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Tipo documento</span>
                <span className={styles.infoValue}>{tipoLabel}</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Folio</span>
                <span className={`${styles.infoValue} ${styles.mono}`}>
                  {data.folio}
                </span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Fecha emisión</span>
                <span className={styles.infoValue}>
                  {formatFechaISO(data.emitido_en)}
                </span>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Modal reimprimir — solo para BOLETA/FACTURA con venta */}
      {printOpen && printData && (
        <Modal
          open
          onClose={() => setPrintOpen(false)}
          title="Reimprimir comprobante"
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
              venta={printData.venta}
              detalles={printData.detalles}
              pagos={printData.pagos}
              documento={printData.documento}
            />
          </div>
          <PrintArea>
            <PrintableReceipt
              venta={printData.venta}
              detalles={printData.detalles}
              pagos={printData.pagos}
              documento={printData.documento}
            />
          </PrintArea>
        </Modal>
      )}

      {/* Reimprimir sin venta (ND/GUIA): abrir directamente window.print() */}
      {printOpen && !printData && (
        <Modal
          open
          onClose={() => setPrintOpen(false)}
          title="Reimprimir"
          size="sm"
          footer={
            <>
              <Button variant="ghost" onClick={() => setPrintOpen(false)}>
                Cerrar
              </Button>
              <Button
                leftIcon={<Printer size={16} aria-hidden />}
                onClick={() => {
                  setPrintOpen(false);
                  window.print();
                }}
              >
                Imprimir página
              </Button>
            </>
          }
        >
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.9rem" }}>
            El comprobante térmico completo está disponible solo para boletas y facturas con datos de venta. Se imprimirá la vista actual de la página.
          </p>
        </Modal>
      )}
    </div>
  );
}

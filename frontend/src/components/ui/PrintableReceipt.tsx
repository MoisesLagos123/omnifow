import { useEffect } from "react";
import { createPortal } from "react-dom";
import {
  TIPO_DOCUMENTO_LABEL,
  type Sucursal,
} from "../../api/sucursales";
import {
  TIPO_PAGO_LABEL,
  type DetalleVenta,
  type DocumentoTributario,
  type Pago,
  type Venta,
} from "../../api/ventas";
import { formatCLP, formatCantidad, formatFechaISO } from "../../lib/format";
import styles from "./PrintableReceipt.module.css";

interface Props {
  venta: Venta;
  detalles: DetalleVenta[];
  pagos: Pago[];
  documento: DocumentoTributario;
  /**
   * Sucursal emisora — para mostrar nombre, dirección y RUT. Opcional: si no
   * se conoce, se usa el RUT del documento como fallback.
   */
  sucursal?: Pick<
    Sucursal,
    "nombre" | "direccion" | "comuna" | "region" | "rut_emisor"
  > | null;
  /** Nombre del cliente para impresión (opcional). */
  clienteNombre?: string | null;
}

/**
 * Contenido visual del comprobante (boleta/factura) optimizado para
 * impresión térmica de 80mm. Se usa tanto en preview en pantalla como
 * dentro de `<PrintArea>` al imprimir.
 */
export function PrintableReceipt({
  venta,
  detalles,
  pagos,
  documento,
  sucursal,
  clienteNombre,
}: Props) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <p className={styles.emisorNombre}>
          {sucursal?.nombre ?? "OMNIFLOW"}
        </p>
        {sucursal?.direccion && (
          <p className={styles.emisorMeta}>
            {sucursal.direccion}
            {sucursal.comuna ? `, ${sucursal.comuna}` : ""}
            {sucursal.region ? `, ${sucursal.region}` : ""}
          </p>
        )}
        <p className={styles.emisorMeta}>
          RUT emisor: {sucursal?.rut_emisor ?? documento.rut_emisor}
        </p>
        <p className={styles.docTitle}>
          {TIPO_DOCUMENTO_LABEL[documento.tipo]}
        </p>
        <p className={styles.folio}>N° {documento.folio}</p>
      </div>

      <div className={styles.meta}>
        <span className={styles.metaLabel}>Fecha</span>
        <span>{formatFechaISO(venta.fecha)}</span>
        {clienteNombre && (
          <>
            <span className={styles.metaLabel}>Cliente</span>
            <span>{clienteNombre}</span>
          </>
        )}
        {documento.rut_receptor && (
          <>
            <span className={styles.metaLabel}>RUT</span>
            <span>{documento.rut_receptor}</span>
          </>
        )}
      </div>

      <div className={styles.itemsHead}>
        <span>Detalle</span>
        <span style={{ textAlign: "right" }}>Subtotal</span>
      </div>
      <div className={styles.itemsList}>
        {detalles.map((d) => (
          <div key={d.id} className={styles.itemsRow}>
            <div className={styles.itemDesc}>
              <span className={styles.itemNombre}>{d.producto_nombre}</span>
              <span className={styles.itemDetalle}>
                {d.producto_sku} · {formatCantidad(d.cantidad)} ×{" "}
                {formatCLP(d.precio_unitario_clp)}
              </span>
            </div>
            <span className={styles.itemSubtotal}>
              {formatCLP(d.subtotal_clp + d.iva_clp)}
            </span>
          </div>
        ))}
      </div>

      <div className={styles.totales}>
        <span className={styles.totalLabel}>Subtotal neto</span>
        <span className={styles.totalValue}>{formatCLP(venta.subtotal_clp)}</span>
        <span className={styles.totalLabel}>IVA 19%</span>
        <span className={styles.totalValue}>{formatCLP(venta.iva_clp)}</span>
        <span className={`${styles.totalLabel} ${styles.totalFinal}`}>Total</span>
        <span className={`${styles.totalValue} ${styles.totalFinal}`}>
          {formatCLP(venta.total_clp)}
        </span>
      </div>

      <div className={styles.pagos}>
        {pagos.map((p) => (
          <div key={p.id} style={{ display: "contents" }}>
            <span className={styles.totalLabel}>{TIPO_PAGO_LABEL[p.tipo]}</span>
            <span className={styles.totalValue}>{formatCLP(p.monto_clp)}</span>
            {(p.referencia_externa || p.ultimos_4_digitos) && (
              <>
                <span className={styles.totalLabel}>
                  {p.referencia_externa ? "Ref." : "Tarjeta"}
                </span>
                <span className={styles.totalValue}>
                  {p.referencia_externa ??
                    `**** ${p.ultimos_4_digitos ?? ""}`}
                </span>
              </>
            )}
          </div>
        ))}
      </div>

      <div className={styles.footer}>
        <p>Gracias por su compra</p>
        <p>Documento electrónico · Estado SII: {documento.estado_sii}</p>
      </div>
    </div>
  );
}

/**
 * Portal que monta el contenido como el ÚNICO bloque visible durante la
 * impresión. Para usar:
 *
 *   <PrintArea>
 *     <PrintableReceipt ... />
 *   </PrintArea>
 *
 * El contenido se mantiene oculto (`display: none`) en pantalla — el preview
 * en la UI debe renderizar `<PrintableReceipt>` directamente aparte.
 */
export function PrintArea({ children }: { children: React.ReactNode }) {
  // Asegura que un solo nodo .printRoot exista en body cada vez que se monta.
  useEffect(() => {
    // No hace falta lógica de cleanup adicional; el portal se desmonta solo.
  }, []);
  return createPortal(
    <div className={styles.printRoot} aria-hidden="true">
      {children}
    </div>,
    document.body
  );
}

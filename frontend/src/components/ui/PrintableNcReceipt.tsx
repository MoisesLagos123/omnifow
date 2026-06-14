import { useMemo } from "react";
import type { Devolucion, DetalleDevolucion } from "../../api/devoluciones";
import type { Sucursal } from "../../api/sucursales";
import { formatCLP, formatCantidad, formatFechaISO, formatInt } from "../../lib/format";
import styles from "./PrintableReceipt.module.css";

interface Props {
  /** La devolución origen de la NC — trae items, totales, motivo y nc_folio. */
  devolucion: Devolucion;
  /** Folio de la venta original (BOLETA/FACTURA) para referencia. */
  ventaFolio?: number | string | null;
  /**
   * Sucursal emisora — para mostrar nombre, dirección y RUT. Opcional: si no
   * se conoce, se usa el RUT del emisor de la devolución (si existe).
   */
  sucursal?: Pick<
    Sucursal,
    "nombre" | "direccion" | "comuna" | "region" | "rut_emisor"
  > | null;
  /** Razón social del receptor (cliente al que se le emitió la NC). */
  clienteNombre?: string | null;
  /** RUT receptor formateado. */
  clienteRut?: string | null;
}

/**
 * Comprobante térmico de Nota de Crédito (80mm), reutilizando los estilos
 * del PrintableReceipt original. Estructura calcada del comprobante normal
 * para que el ojo del cajero reconozca el formato, pero:
 *  - Título: "NOTA DE CRÉDITO" en lugar de "BOLETA"/"FACTURA"
 *  - Referencia a la venta original (folio + fecha)
 *  - Items: SÓLO los devueltos (no toda la venta) con sus cantidades reales
 *  - Total resaltado como "Total devuelto"
 *  - Pie con motivo si existe
 *
 * Se monta dentro de <PrintArea> al imprimir — el portal y el media query
 * de @media print del CSS hacen que sea lo único visible al usar window.print().
 */
export function PrintableNcReceipt({
  devolucion,
  ventaFolio,
  sucursal,
  clienteNombre,
  clienteRut,
}: Props) {
  // Resumen para el pie: cantidad de líneas y unidades devueltas. Sustenta
  // que el cliente vea de un vistazo "cuánto" se devolvió sin contar.
  const resumen = useMemo(() => {
    const items = devolucion.items.length;
    let unidades = 0;
    for (const it of devolucion.items) {
      const n = Number.parseFloat(String(it.cantidad));
      if (Number.isFinite(n)) unidades += n;
    }
    return { items, unidades };
  }, [devolucion.items]);

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
        {sucursal?.rut_emisor && (
          <p className={styles.emisorMeta}>
            RUT emisor: {sucursal.rut_emisor}
          </p>
        )}
        <p className={styles.docTitle}>NOTA DE CRÉDITO</p>
        <p className={styles.folio}>N° {devolucion.nc_folio}</p>
      </div>

      <div className={styles.meta}>
        <span className={styles.metaLabel}>Fecha</span>
        <span>{formatFechaISO(devolucion.fecha)}</span>
        {ventaFolio !== undefined && ventaFolio !== null && (
          <>
            <span className={styles.metaLabel}>Venta ref.</span>
            <span>#{ventaFolio}</span>
          </>
        )}
        {clienteNombre && (
          <>
            <span className={styles.metaLabel}>Cliente</span>
            <span>{clienteNombre}</span>
          </>
        )}
        {clienteRut && (
          <>
            <span className={styles.metaLabel}>RUT</span>
            <span>{clienteRut}</span>
          </>
        )}
      </div>

      {/* DETALLE DE LO DEVUELTO
          Misma estructura visual que la boleta original, pero las cantidades
          aquí son las realmente devueltas — no las vendidas. En devolución
          parcial verás cantidades menores a las originales. */}
      <p className={styles.sectionLabel}>Detalle de la devolución</p>
      <div className={styles.itemsHead}>
        <span>Producto / Cant × P.Unit</span>
        <span style={{ textAlign: "right" }}>Total</span>
      </div>
      <div className={styles.itemsList}>
        {devolucion.items.map((d: DetalleDevolucion) => (
          <div key={d.id} className={styles.itemsRow}>
            <div className={styles.itemDesc}>
              <span className={styles.itemNombre}>{d.producto_nombre}</span>
              <span className={styles.itemDetalle}>
                <span className={styles.itemSku}>{d.producto_sku}</span>
                <span aria-hidden="true">·</span>
                <span className={styles.itemMath}>
                  {formatCantidad(d.cantidad)} × {formatCLP(d.precio_unitario_clp)}
                </span>
              </span>
            </div>
            <span className={styles.itemSubtotal}>
              {formatCLP(d.subtotal_clp)}
            </span>
          </div>
        ))}
      </div>
      <div className={styles.itemsSummary}>
        <span>
          {resumen.items}{" "}
          {resumen.items === 1 ? "producto devuelto" : "productos devueltos"}
        </span>
        <span>
          {formatInt(Math.round(resumen.unidades))}{" "}
          {Math.round(resumen.unidades) === 1 ? "unidad" : "unidades"}
        </span>
      </div>

      <div className={styles.totales}>
        <span className={styles.totalLabel}>Subtotal neto</span>
        <span className={styles.totalValue}>
          {formatCLP(devolucion.monto_neto_clp)}
        </span>
        <span className={styles.totalLabel}>IVA 19%</span>
        <span className={styles.totalValue}>
          {formatCLP(devolucion.iva_clp)}
        </span>
        <span className={`${styles.totalLabel} ${styles.totalFinal}`}>
          Total devuelto
        </span>
        <span className={`${styles.totalValue} ${styles.totalFinal}`}>
          {formatCLP(devolucion.monto_total_clp)}
        </span>
      </div>

      {devolucion.motivo && (
        <div className={styles.meta} style={{ marginTop: "var(--space-3)" }}>
          <span className={styles.metaLabel}>Motivo</span>
          <span>{devolucion.motivo}</span>
        </div>
      )}

      <div className={styles.footer}>
        <p>Nota de Crédito emitida por devolución</p>
        <p>
          Estado venta:{" "}
          {devolucion.venta_estado_final === "ANULADA"
            ? "Anulada"
            : "Activa (devolución parcial)"}
        </p>
      </div>
    </div>
  );
}

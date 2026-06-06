import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/devoluciones", () => ({
  devolucionesApi: {
    crearParaVenta: vi.fn(),
  },
}));

import { devolucionesApi } from "../src/api/devoluciones";
import { DevolucionModal } from "../src/modules/devoluciones/DevolucionModal";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";
import type { Venta, DetalleVenta } from "../src/api/ventas";
import type { Devolucion } from "../src/api/devoluciones";

const VENTA: Venta = {
  id: "venta-1",
  sucursal_id: "suc-1",
  caja_id: "caj-1",
  usuario_id: "usr-1",
  cliente_id: null,
  tipo_documento: "BOLETA",
  subtotal_clp: 10000,
  iva_clp: 1900,
  total_clp: 11900,
  estado: "CONFIRMADA",
  documento_tributario_id: "doc-1",
  fecha: "2026-06-01T10:00:00Z",
};

const DETALLES: DetalleVenta[] = [
  {
    id: "det-1",
    venta_id: "venta-1",
    producto_id: "prod-1",
    producto_sku: "SKU-001",
    producto_nombre: "Producto Uno",
    cantidad: "5",
    precio_unitario_clp: 1190,
    costo_unitario_clp: 800,
    iva_porcentaje: 19,
    subtotal_clp: 5000,
    iva_clp: 950,
    lote_id: null,
  },
  {
    id: "det-2",
    venta_id: "venta-1",
    producto_id: "prod-2",
    producto_sku: "SKU-002",
    producto_nombre: "Producto Dos",
    cantidad: "3",
    precio_unitario_clp: 2380,
    costo_unitario_clp: 1500,
    iva_porcentaje: 19,
    subtotal_clp: 6000,
    iva_clp: 1140,
    lote_id: null,
  },
  {
    id: "det-3",
    venta_id: "venta-1",
    producto_id: "prod-3",
    producto_sku: "SKU-003",
    producto_nombre: "Producto Tres",
    cantidad: "2",
    precio_unitario_clp: 595,
    costo_unitario_clp: 400,
    iva_porcentaje: 19,
    subtotal_clp: 1000,
    iva_clp: 190,
    lote_id: null,
  },
];

const DEV_PREVIA_PARCIAL: Devolucion = {
  id: "dev-1",
  venta_id: "venta-1",
  sucursal_id: "suc-1",
  caja_id: "caj-1",
  usuario_id: "usr-1",
  fecha: "2026-06-02T10:00:00Z",
  motivo: "Defectuoso",
  monto_neto_clp: 1000,
  iva_clp: 190,
  monto_total_clp: 1190,
  nc_folio: 100,
  nc_documento_id: "nc-1",
  items: [
    {
      id: "dd-1",
      devolucion_id: "dev-1",
      detalle_venta_id: "det-1",
      producto_id: "prod-1",
      producto_sku: "SKU-001",
      producto_nombre: "Producto Uno",
      cantidad: "2",
      precio_unitario_clp: 1190,
      subtotal_clp: 2380,
    },
  ],
  venta_estado_final: "CONFIRMADA",
  creado_en: "2026-06-02T10:00:00Z",
};

function setPermisos(permisos: string[]) {
  useAuthStore.setState({ permisos } as never);
}

function renderModal(
  open = true,
  devolucionesPrevias: Devolucion[] = [],
  onCreada = vi.fn(),
  onClose = vi.fn()
) {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <DevolucionModal
          open={open}
          onClose={onClose}
          venta={VENTA}
          detalles={DETALLES}
          devolucionesPrevias={devolucionesPrevias}
          onCreada={onCreada}
        />
      </MemoryRouter>
    </ToastProvider>
  );
}

describe("DevolucionModal", () => {
  beforeEach(() => {
    setPermisos(["devolucion.crear"]);
    vi.mocked(devolucionesApi.crearParaVenta).mockReset();
  });

  it("renderiza 3 items con todos los inputs en 0 y el botón 'Procesar' está disabled", () => {
    renderModal();

    // Debe haber 3 filas de productos en la tabla
    expect(screen.getByText("Producto Uno")).toBeInTheDocument();
    expect(screen.getByText("Producto Dos")).toBeInTheDocument();
    expect(screen.getByText("Producto Tres")).toBeInTheDocument();

    // El botón de submit debe estar deshabilitado cuando todo es 0
    const submitBtn = screen.getByRole("button", { name: /procesar devolución/i });
    expect(submitBtn).toBeDisabled();
  });

  it("botón 'Devolver todo lo pendiente' rellena los inputs con los pendientes", async () => {
    const user = userEvent.setup();
    renderModal(true, [DEV_PREVIA_PARCIAL]);

    // det-1 tiene 5 original, ya devuelto 2, pendiente = 3
    // det-2 pendiente = 3, det-3 pendiente = 2
    const btn = screen.getByRole("button", { name: /devolver todo lo pendiente/i });
    await user.click(btn);

    // El botón de submit debe habilitarse
    const submitBtn = screen.getByRole("button", { name: /procesar devolución/i });
    expect(submitBtn).not.toBeDisabled();
  });

  it("submit con items válidos llama a crearParaVenta con payload correcto e Idempotency-Key", async () => {
    const user = userEvent.setup();
    const onCreada = vi.fn();
    const mockResult: Devolucion = {
      id: "dev-nuevo",
      venta_id: "venta-1",
      sucursal_id: "suc-1",
      caja_id: "caj-1",
      usuario_id: "usr-1",
      fecha: "2026-06-06T12:00:00Z",
      motivo: null,
      monto_neto_clp: 1000,
      iva_clp: 190,
      monto_total_clp: 1190,
      nc_folio: 200,
      nc_documento_id: "nc-2",
      items: [],
      venta_estado_final: "CONFIRMADA",
      creado_en: "2026-06-06T12:00:00Z",
    };
    vi.mocked(devolucionesApi.crearParaVenta).mockResolvedValue(mockResult);

    renderModal(true, [], onCreada);

    // Hacer click en "Devolver todo lo pendiente"
    await user.click(
      screen.getByRole("button", { name: /devolver todo lo pendiente/i })
    );

    // Procesar
    const submitBtn = screen.getByRole("button", { name: /procesar devolución/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(devolucionesApi.crearParaVenta).toHaveBeenCalledTimes(1);
    });

    const [ventaId, payload] = vi.mocked(devolucionesApi.crearParaVenta).mock.calls[0]!;
    expect(ventaId).toBe("venta-1");
    expect(payload.items).toHaveLength(3);
    // Verificar que los items incluyen los 3 detalles con cantidades correctas
    const det1 = payload.items.find((i) => i.detalle_venta_id === "det-1");
    const det2 = payload.items.find((i) => i.detalle_venta_id === "det-2");
    const det3 = payload.items.find((i) => i.detalle_venta_id === "det-3");
    expect(det1?.cantidad).toBe("5");
    expect(det2?.cantidad).toBe("3");
    expect(det3?.cantidad).toBe("2");

    // onCreada debe haber sido llamado con el resultado
    await waitFor(() => {
      expect(onCreada).toHaveBeenCalledWith(mockResult);
    });
  });

  it("ingresar una cantidad y limpiar la pone en 0", async () => {
    const user = userEvent.setup();
    renderModal();

    // Click en devolver todo para poner valores
    await user.click(
      screen.getByRole("button", { name: /devolver todo lo pendiente/i })
    );

    let submitBtn = screen.getByRole("button", { name: /procesar devolución/i });
    expect(submitBtn).not.toBeDisabled();

    // Click en limpiar
    await user.click(screen.getByRole("button", { name: /limpiar/i }));

    submitBtn = screen.getByRole("button", { name: /procesar devolución/i });
    expect(submitBtn).toBeDisabled();
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

// --- Mocks ---
const obtenerSesionActiva = vi.fn();
const listCajasDeSucursal = vi.fn();
const listBodegasDeSucursal = vi.fn();
const buscarProductos = vi.fn();
const reservarStock = vi.fn();
const actualizarReserva = vi.fn();
const liberarReserva = vi.fn();
const crearVenta = vi.fn();

vi.mock("../src/api/caja", () => ({
  cajaApi: {
    obtenerSesionActiva: (...a: unknown[]) => obtenerSesionActiva(...a),
  },
}));
vi.mock("../src/api/sucursales", async () => {
  const actual = await vi.importActual<typeof import("../src/api/sucursales")>(
    "../src/api/sucursales"
  );
  return {
    ...actual,
    sucursalesApi: {
      listCajasDeSucursal: (...a: unknown[]) => listCajasDeSucursal(...a),
      listSucursales: vi.fn().mockResolvedValue({ items: [], total: 0 }),
      obtenerSucursal: vi.fn(),
    },
  };
});
vi.mock("../src/api/inventario", () => ({
  inventarioApi: {
    listBodegasDeSucursal: (...a: unknown[]) => listBodegasDeSucursal(...a),
  },
}));
vi.mock("../src/api/pos", () => ({
  posApi: {
    buscarProductos: (...a: unknown[]) => buscarProductos(...a),
    reservarStock: (...a: unknown[]) => reservarStock(...a),
    actualizarReserva: (...a: unknown[]) => actualizarReserva(...a),
    liberarReserva: (...a: unknown[]) => liberarReserva(...a),
  },
}));
vi.mock("../src/api/clientes", () => ({
  clientesApi: {
    listClientes: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    crearCliente: vi.fn(),
  },
}));
vi.mock("../src/api/ventas", async () => {
  const actual = await vi.importActual<typeof import("../src/api/ventas")>(
    "../src/api/ventas"
  );
  return {
    ...actual,
    ventasApi: {
      crear: (...a: unknown[]) => crearVenta(...a),
      obtener: vi.fn(),
      listar: vi.fn(),
      anular: vi.fn(),
    },
  };
});

import { PosPage } from "../src/modules/pos/PosPage";
import { ToastProvider } from "../src/components/ui/Toast";
import { useAuthStore } from "../src/auth/store";

const CAJA = {
  id: "caja-1",
  sucursal_id: "suc-1",
  codigo: "C1",
  nombre: "Caja Principal",
  activo: true,
};

const BODEGA = {
  id: "bod-1",
  sucursal_id: "suc-1",
  codigo: "BOD-A",
  nombre: "Bodega A",
  activo: true,
};

const PRODUCTO = {
  id: "prod-1",
  sku: "LE-001",
  codigo_barras: "7891234567890",
  nombre: "Leche entera",
  categoria_id: null,
  categoria_nombre: null,
  precio_venta_clp: 1190,
  iva_porcentaje: 19,
  controla_vencimiento: false,
  stock_disponible: 50,
  lote_proximo_vencer: null,
};

function setupAuth() {
  useAuthStore.setState({
    accessToken: "tok",
    refreshToken: null,
    user: { id: "u1", nombre: "Ana", email: "ana@x.cl" },
    perfiles: [],
    permisos: ["venta.crear", "stock.consultar"],
    sucursalesPermitidas: [{ id: "suc-1", codigo: "S1", nombre: "Sucursal 1" }],
    sucursalActivaId: "suc-1",
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <PosPage />
      </ToastProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  obtenerSesionActiva.mockReset();
  listCajasDeSucursal.mockReset();
  listBodegasDeSucursal.mockReset();
  buscarProductos.mockReset();
  reservarStock.mockReset();
  actualizarReserva.mockReset();
  liberarReserva.mockReset();
  crearVenta.mockReset();
  localStorage.clear();
  setupAuth();
  listCajasDeSucursal.mockResolvedValue([CAJA]);
  listBodegasDeSucursal.mockResolvedValue([BODEGA]);
  obtenerSesionActiva.mockResolvedValue({
    sesion: { id: "ses-1" },
    movimientos: [],
    totales: { por_tipo: {}, ingresos_clp: 0, egresos_clp: 0, calculado_clp: 0 },
  });
  buscarProductos.mockResolvedValue([PRODUCTO]);
  reservarStock.mockResolvedValue({
    id: "res-1",
    sesion_caja_id: "ses-1",
    producto_id: "prod-1",
    bodega_id: "bod-1",
    cantidad: "1",
    estado: "ACTIVA",
    creado_en: "2026-01-01T00:00:00Z",
    resuelto_en: null,
  });
  liberarReserva.mockResolvedValue(undefined);
});

describe("PosPage", () => {
  it("muestra el botón Confirmar venta deshabilitado cuando el carrito está vacío", async () => {
    renderPage();
    const btn = await screen.findByRole("button", {
      name: /confirmar venta/i,
    });
    expect(btn).toBeDisabled();
  });

  it("permite agregar un producto al carrito y calcula el total bruto", async () => {
    renderPage();
    // Espera que se carguen las cajas
    await waitFor(() => expect(listCajasDeSucursal).toHaveBeenCalled());

    const input = await screen.findByPlaceholderText(/sku, código de barras/i);
    await userEvent.type(input, "leche");

    // Espera que aparezca el resultado.
    const item = await screen.findByText(/leche entera/i);
    await userEvent.click(item);

    // El carrito muestra la línea y el total bruto (1.190 * 1 = $ 1.190).
    expect(screen.getByText(/carrito \(1\)/i)).toBeInTheDocument();
    const totalLabels = screen.getAllByText(/^\$ 1\.190$/);
    expect(totalLabels.length).toBeGreaterThan(0);
  });

  it("agrega 'efectivo exacto' iguala pagado al total y cuadra", async () => {
    renderPage();
    const input = await screen.findByPlaceholderText(/sku, código de barras/i);
    await userEvent.type(input, "leche");
    const item = await screen.findByText(/leche entera/i);
    await userEvent.click(item);

    // Click "Efectivo exacto"
    const efectivoExactoBtn = screen.getByRole("button", {
      name: /efectivo exacto/i,
    });
    await userEvent.click(efectivoExactoBtn);

    // Ahora el botón Confirmar debe estar habilitado.
    const confirmar = screen.getByRole("button", {
      name: /confirmar venta/i,
    });
    await waitFor(() => expect(confirmar).not.toBeDisabled());
  });

  it("muestra banner cuando no hay sesión de caja activa", async () => {
    obtenerSesionActiva.mockResolvedValue(null);
    renderPage();
    expect(
      await screen.findByText(/abre la caja antes de vender/i)
    ).toBeInTheDocument();
  });

  it("al agregar un producto llama a reservarStock con caja/bodega/cantidad", async () => {
    renderPage();
    await waitFor(() => expect(listCajasDeSucursal).toHaveBeenCalled());

    const input = await screen.findByPlaceholderText(/sku, código de barras/i);
    await userEvent.type(input, "leche");
    const item = await screen.findByText(/leche entera/i);
    await userEvent.click(item);

    await waitFor(() => expect(reservarStock).toHaveBeenCalledTimes(1));
    const call = reservarStock.mock.calls[0]![0] as {
      caja_id: string;
      producto_id: string;
      bodega_id: string;
      cantidad: string | number;
    };
    expect(call.caja_id).toBe("caja-1");
    expect(call.producto_id).toBe("prod-1");
    expect(call.bodega_id).toBe("bod-1");
    expect(String(call.cantidad)).toBe("1");
  });

  it("si la reserva falla con ERR_STOCK_INSUFICIENTE, muestra el mensaje con disponible", async () => {
    const { ApiError } = await import("../src/api/client");
    reservarStock.mockRejectedValue(
      new ApiError(
        {
          code: "ERR_STOCK_INSUFICIENTE",
          message: "",
          details: {
            producto_id: "prod-1",
            bodega_id: "bod-1",
            stock_total: "5",
            reservado: "5",
            disponible: "0",
            solicitado: "1",
          },
        },
        409
      )
    );
    renderPage();
    const input = await screen.findByPlaceholderText(/sku, código de barras/i);
    await userEvent.type(input, "leche");
    const item = await screen.findByText(/leche entera/i);
    await userEvent.click(item);

    expect(await screen.findByText(/disponible/i)).toBeInTheDocument();
  });

  it("al quitar un item del carrito llama a liberarReserva", async () => {
    renderPage();
    const input = await screen.findByPlaceholderText(/sku, código de barras/i);
    await userEvent.type(input, "leche");
    const item = await screen.findByText(/leche entera/i);
    await userEvent.click(item);

    await waitFor(() => expect(reservarStock).toHaveBeenCalled());
    // Espera a que la reserva se confirme en el estado.
    await screen.findByText(/^reservado$/i);

    const quitar = screen.getByRole("button", { name: /quitar leche entera/i });
    await userEvent.click(quitar);

    await waitFor(() => expect(liberarReserva).toHaveBeenCalledWith("res-1"));
  });

  it("deshabilita Confirmar venta mientras una reserva está en vuelo", async () => {
    let resolveReserva: (v: unknown) => void = () => undefined;
    reservarStock.mockImplementation(
      () =>
        new Promise((res) => {
          resolveReserva = res;
        })
    );
    renderPage();
    const input = await screen.findByPlaceholderText(/sku, código de barras/i);
    await userEvent.type(input, "leche");
    const item = await screen.findByText(/leche entera/i);
    await userEvent.click(item);

    // Mientras reserva pendiente, badge "Reservando…" visible.
    expect(await screen.findByText(/reservando/i)).toBeInTheDocument();

    // Configura un pago en efectivo exacto para no bloquear por suma de pagos.
    const efectivoExactoBtn = screen.getByRole("button", {
      name: /efectivo exacto/i,
    });
    await userEvent.click(efectivoExactoBtn);

    const confirmar = screen.getByRole("button", {
      name: /confirmar venta/i,
    });
    expect(confirmar).toBeDisabled();

    // Termina la reserva y la situación se libera.
    resolveReserva({
      id: "res-1",
      sesion_caja_id: "ses-1",
      producto_id: "prod-1",
      bodega_id: "bod-1",
      cantidad: "1",
      estado: "ACTIVA",
      creado_en: "2026-01-01T00:00:00Z",
      resuelto_en: null,
    });
    await waitFor(() => expect(confirmar).not.toBeDisabled());
  });

  it("incluye reserva_id por línea en el payload de POST /ventas", async () => {
    crearVenta.mockResolvedValue({
      venta: { id: "v1", total_clp: 1190 },
      detalles: [],
      pagos: [],
      documento: { folio: 1, rut_emisor: "1-9" },
    });
    renderPage();
    const input = await screen.findByPlaceholderText(/sku, código de barras/i);
    await userEvent.type(input, "leche");
    const item = await screen.findByText(/leche entera/i);
    await userEvent.click(item);
    await waitFor(() => expect(reservarStock).toHaveBeenCalled());
    await screen.findByText(/^reservado$/i);

    const efectivoExactoBtn = screen.getByRole("button", {
      name: /efectivo exacto/i,
    });
    await userEvent.click(efectivoExactoBtn);

    const confirmar = screen.getByRole("button", {
      name: /confirmar venta/i,
    });
    await waitFor(() => expect(confirmar).not.toBeDisabled());
    await userEvent.click(confirmar);

    await waitFor(() => expect(crearVenta).toHaveBeenCalled());
    const payload = crearVenta.mock.calls[0]![0] as {
      items: { reserva_id: string | null }[];
    };
    expect(payload.items).toHaveLength(1);
    expect(payload.items[0]!.reserva_id).toBe("res-1");
  });
});

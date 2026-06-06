import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  ArqueoModal,
  RegistrarMovimientoModal,
} from "../src/modules/caja/components";

describe("ArqueoModal", () => {
  it("muestra el monto calculado y calcula la diferencia (declarado − calculado)", async () => {
    const onConfirm = vi.fn().mockResolvedValue({});
    render(
      <ArqueoModal
        open
        onClose={() => {}}
        montoCalculado={50000}
        porTipo={{}}
        onConfirm={onConfirm}
      />
    );

    // Calculado visible.
    expect(screen.getByTestId("arqueo-calculado")).toHaveTextContent("$ 50.000");

    // Diferencia inicial: declarado=0 → faltante de 50.000.
    expect(screen.getByTestId("arqueo-diferencia")).toHaveTextContent(
      "-$ 50.000"
    );

    // Ingresa un declarado mayor → sobrante.
    const input = screen.getByLabelText(/Monto declarado/i);
    fireEvent.change(input, { target: { value: "60000" } });
    await waitFor(() =>
      expect(screen.getByTestId("arqueo-diferencia")).toHaveTextContent(
        "+$ 10.000"
      )
    );

    // Confirmar envía el monto declarado.
    await userEvent.click(screen.getByRole("button", { name: /Cerrar caja/i }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith(60000));
  });

  it("muestra diferencia 0 (cuadrada) cuando declarado = calculado", async () => {
    render(
      <ArqueoModal
        open
        onClose={() => {}}
        montoCalculado={30000}
        porTipo={{}}
        onConfirm={vi.fn().mockResolvedValue({})}
      />
    );
    const input = screen.getByLabelText(/Monto declarado/i);
    fireEvent.change(input, { target: { value: "30000" } });
    await waitFor(() =>
      expect(screen.getByText("Caja cuadrada")).toBeInTheDocument()
    );
    expect(screen.getByTestId("arqueo-diferencia")).toHaveTextContent("$ 0");
  });
});

describe("RegistrarMovimientoModal", () => {
  it("envía tipo, monto y descripción al confirmar", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      <RegistrarMovimientoModal
        open
        onClose={() => {}}
        onConfirm={onConfirm}
      />
    );

    fireEvent.change(screen.getByLabelText("Monto"), {
      target: { value: "1500" },
    });
    fireEvent.change(screen.getByLabelText("Descripción"), {
      target: { value: "Compra de insumos" },
    });
    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));

    await waitFor(() =>
      expect(onConfirm).toHaveBeenCalledWith({
        tipo: "INGRESO_OTRO",
        monto_clp: 1500,
        descripcion: "Compra de insumos",
      })
    );
  });

  it("bloquea el submit y muestra errores si faltan monto o descripción", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      <RegistrarMovimientoModal
        open
        onClose={() => {}}
        onConfirm={onConfirm}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(
      screen.getByText("El monto debe ser mayor a 0.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("La descripción es obligatoria.")
    ).toBeInTheDocument();
  });

  it("no ofrece INGRESO_VENTA como opción manual", () => {
    render(
      <RegistrarMovimientoModal
        open
        onClose={() => {}}
        onConfirm={vi.fn()}
      />
    );
    const select = screen.getByLabelText("Tipo de movimiento");
    expect(select).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: "Ingreso por venta" })
    ).not.toBeInTheDocument();
  });
});

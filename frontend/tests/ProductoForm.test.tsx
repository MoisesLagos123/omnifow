import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProductoForm } from "../src/modules/inventario/ProductoForm";

function renderForm() {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  render(
    <ProductoForm
      modo="crear"
      categorias={[]}
      submitLabel="Crear producto"
      onSubmit={onSubmit}
    />
  );
  return { onSubmit };
}

describe("ProductoForm — control de vencimiento", () => {
  it("oculta el campo de días por defecto y lo muestra al activar el toggle", async () => {
    renderForm();

    // Inicialmente no hay campo de días de alerta.
    expect(
      screen.queryByLabelText(/días de alerta/i)
    ).not.toBeInTheDocument();

    // El checkbox de control de vencimiento existe y está apagado.
    const checkbox = screen.getByRole("checkbox", {
      name: /controla vencimiento/i,
    });
    expect(checkbox).not.toBeChecked();

    await userEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    // Ahora aparece el campo opcional de días de alerta.
    expect(
      await screen.findByLabelText(/días de alerta/i)
    ).toBeInTheDocument();

    // Y se oculta de nuevo al desactivar.
    await userEvent.click(checkbox);
    expect(screen.queryByLabelText(/días de alerta/i)).not.toBeInTheDocument();
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Modal } from "../src/components/ui/Modal";
import { ConfirmDialog } from "../src/components/ui/ConfirmDialog";

describe("Modal", () => {
  it("se cierra con la tecla Escape", async () => {
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="Hola">
        <p>contenido</p>
      </Modal>
    );
    expect(screen.getByRole("dialog", { name: /hola/i })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("no renderiza nada cuando open es false", () => {
    const onClose = vi.fn();
    render(
      <Modal open={false} onClose={onClose} title="Hola">
        <p>contenido</p>
      </Modal>
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("ConfirmDialog", () => {
  it("se cierra con Escape", async () => {
    const onClose = vi.fn();
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        open
        title="Eliminar"
        description="¿seguro?"
        onClose={onClose}
        onConfirm={onConfirm}
      />
    );
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});

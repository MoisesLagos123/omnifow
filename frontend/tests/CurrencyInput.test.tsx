import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { CurrencyInput } from "../src/components/ui/CurrencyInput";

function Wrapper({ onValueChange }: { onValueChange?: (n: number) => void }) {
  const [v, setV] = useState(0);
  return (
    <CurrencyInput
      label="Monto inicial en efectivo"
      value={v}
      onChange={(n) => {
        setV(n);
        onValueChange?.(n);
      }}
      autoFocus
    />
  );
}

describe("CurrencyInput — bug del cursor", () => {
  it("permite escribir 50000 dígito a dígito sin perder caracteres", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Wrapper onValueChange={onChange} />);

    const input = screen.getByLabelText(/monto inicial/i) as HTMLInputElement;
    input.focus();

    await user.keyboard("5");
    expect(input.value).toBe("5");
    await user.keyboard("0");
    expect(input.value).toBe("50");
    await user.keyboard("0");
    expect(input.value).toBe("500");
    await user.keyboard("0");
    expect(input.value).toBe("5000");
    await user.keyboard("0");
    expect(input.value).toBe("50000");

    // Al hacer blur se formatea (Tab dispara onBlur en React)
    await user.tab();
    expect(input.value).toBe("$ 50.000");

    // onChange final con el número correcto
    expect(onChange).toHaveBeenLastCalledWith(50000);
  });

  it("ignora caracteres no numéricos", async () => {
    const user = userEvent.setup();
    render(<Wrapper />);
    const input = screen.getByLabelText(/monto inicial/i) as HTMLInputElement;
    input.focus();
    await user.keyboard("1a2b3c");
    expect(input.value).toBe("123");
  });

  it("dentro de un Modal mantiene el foco al escribir (regresión: focus trap no debe robar el foco al cerrar handler nuevo)", async () => {
    const { Modal } = await import("../src/components/ui/Modal");
    const user = userEvent.setup();

    function Host() {
      const [v, setV] = useState(0);
      // onClose se recrea en cada render — es el caso real del bug.
      return (
        <Modal open onClose={() => undefined} title="Abrir caja" size="sm">
          <CurrencyInput
            label="Monto inicial en efectivo"
            value={v}
            onChange={setV}
            autoFocus
          />
        </Modal>
      );
    }

    render(<Host />);
    const input = screen.getByLabelText(/monto inicial/i) as HTMLInputElement;
    input.focus();
    await user.keyboard("50000");
    expect(input.value).toBe("50000");
    // Si el modal robara el foco, el dígito siguiente no terminaría en el input.
    expect(document.activeElement).toBe(input);
  });

  it("borra correctamente con backspace", async () => {
    const user = userEvent.setup();
    render(<Wrapper />);
    const input = screen.getByLabelText(/monto inicial/i) as HTMLInputElement;
    input.focus();
    await user.keyboard("1234");
    expect(input.value).toBe("1234");
    await user.keyboard("{Backspace}");
    expect(input.value).toBe("123");
    await user.keyboard("{Backspace}{Backspace}{Backspace}");
    expect(input.value).toBe("");
  });
});

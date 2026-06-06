import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProgressBar } from "../src/components/ui/ProgressBar";

describe("ProgressBar", () => {
  it("calcula aria-valuenow respetando el rango [0, max]", () => {
    render(<ProgressBar value={25} max={100} ariaLabel="Test" />);
    const bar = screen.getByRole("progressbar", { name: "Test" });
    expect(bar).toHaveAttribute("aria-valuenow", "25");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
  });

  it("clampa el valor cuando excede el max", () => {
    render(<ProgressBar value={500} max={100} ariaLabel="Overflow" />);
    const bar = screen.getByRole("progressbar", { name: "Overflow" });
    expect(bar).toHaveAttribute("aria-valuenow", "100");
  });

  it("se mantiene válido si max es 0 (evita división por cero)", () => {
    render(<ProgressBar value={5} max={0} ariaLabel="Zero" />);
    const bar = screen.getByRole("progressbar", { name: "Zero" });
    expect(bar).toHaveAttribute("aria-valuemax", "1");
  });
});

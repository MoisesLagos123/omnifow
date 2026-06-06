import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "../src/components/ui/ThemeToggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    document.documentElement.setAttribute("data-theme", "light");
    localStorage.clear();
  });

  it("alterna data-theme entre light y dark al hacer click", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);

    expect(document.documentElement.getAttribute("data-theme")).toBe("light");

    await user.click(screen.getByRole("button"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(localStorage.getItem("mini-erp-theme")).toBe("dark");

    await user.click(screen.getByRole("button"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(localStorage.getItem("mini-erp-theme")).toBe("light");
  });
});

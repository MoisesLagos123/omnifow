import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { RequirePermission } from "../src/auth/RequirePermission";
import { useAuthStore } from "../src/auth/store";

function setPermisos(permisos: string[]) {
  useAuthStore.setState({
    accessToken: "tok",
    refreshToken: "ref",
    user: { id: "u1", nombre: "T", email: "t@e.cl" },
    perfiles: [],
    permisos,
  });
}

describe("RequirePermission", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
  });

  it("oculta children si no tiene el permiso", () => {
    setPermisos([]);
    render(
      <RequirePermission code="usuario.gestionar">
        <span>SECRETO</span>
      </RequirePermission>
    );
    expect(screen.queryByText("SECRETO")).not.toBeInTheDocument();
  });

  it("muestra children si tiene el permiso", () => {
    setPermisos(["usuario.gestionar"]);
    render(
      <RequirePermission code="usuario.gestionar">
        <span>SECRETO</span>
      </RequirePermission>
    );
    expect(screen.getByText("SECRETO")).toBeInTheDocument();
  });

  it("anyOf: muestra si tiene al menos uno", () => {
    setPermisos(["perfil.gestionar"]);
    render(
      <RequirePermission anyOf={["usuario.gestionar", "perfil.gestionar"]}>
        <span>OK</span>
      </RequirePermission>
    );
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  it("renderiza fallback si se especifica", () => {
    setPermisos([]);
    render(
      <RequirePermission code="usuario.gestionar" fallback={<span>NO-AUTH</span>}>
        <span>SECRETO</span>
      </RequirePermission>
    );
    expect(screen.getByText("NO-AUTH")).toBeInTheDocument();
  });
});

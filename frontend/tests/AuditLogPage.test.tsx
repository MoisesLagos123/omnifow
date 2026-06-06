import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../src/api/audit", () => ({
  auditApi: {
    listar: vi.fn(),
    obtener: vi.fn(),
  },
}));

import { auditApi } from "../src/api/audit";
import { AuditLogPage } from "../src/modules/administracion/AuditLogPage";
import { useAuthStore } from "../src/auth/store";
import type { AuditLogEntry } from "../src/api/audit";

const AUDIT_ENTRY: AuditLogEntry = {
  id: "aud-1",
  ts: "2026-06-01T10:00:00Z",
  usuario_id: "u1",
  usuario_nombre: "Ada Lagos",
  usuario_email: "ada@erp.cl",
  ip: "192.168.1.1",
  user_agent: "Chrome",
  accion: "auth.login",
  recurso_tipo: null,
  recurso_id: null,
  resultado: "OK",
  metadata: null,
  before: null,
  after: null,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AuditLogPage />
    </MemoryRouter>
  );
}

describe("AuditLogPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "tok",
      user: { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
      perfiles: ["Sysadmin"],
      permisos: ["audit.ver"],
    });
    vi.mocked(auditApi.listar).mockReset();
  });

  it("renderiza la lista de audit log correctamente", async () => {
    vi.mocked(auditApi.listar).mockResolvedValue({
      items: [AUDIT_ENTRY],
      total: 1,
      limit: 50,
      offset: 0,
    });

    renderPage();

    expect(screen.getByText(/Auditoría/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("auth.login")).toBeInTheDocument();
      expect(screen.getByText("Ada Lagos")).toBeInTheDocument();
    });

    expect(screen.getByText("192.168.1.1")).toBeInTheDocument();
  });

  it("filtro de acción pasa el parámetro a la API", async () => {
    vi.mocked(auditApi.listar).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(vi.mocked(auditApi.listar).mock.calls.length).toBeGreaterThanOrEqual(1);
    });

    const callsBefore = vi.mocked(auditApi.listar).mock.calls.length;

    const accionInput = screen.getByLabelText(/Acción/i);
    await user.type(accionInput, "venta.crear");

    await waitFor(() => {
      expect(vi.mocked(auditApi.listar).mock.calls.length).toBeGreaterThan(callsBefore);
      const calls = vi.mocked(auditApi.listar).mock.calls;
      const lastArgs = calls[calls.length - 1]![0];
      expect(lastArgs?.accion).toBe("venta.crear");
    });
  });
});

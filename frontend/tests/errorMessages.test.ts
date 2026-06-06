import { describe, it, expect } from "vitest";
import { ApiError } from "../src/api/client";
import {
  describeError,
  extractPerfilEnUso,
} from "../src/api/errorMessages";

describe("describeError + extractPerfilEnUso", () => {
  it("ERR_PERFIL_EN_USO devuelve mensaje amigable", () => {
    const err = new ApiError(
      {
        code: "ERR_PERFIL_EN_USO",
        message: "perfil en uso",
        details: { usuarios: [], total: 0 },
      },
      409
    );
    expect(describeError(err)).toMatch(/asignado a uno o más usuarios/i);
  });

  it("extractPerfilEnUso obtiene la lista de usuarios", () => {
    const err = new ApiError(
      {
        code: "ERR_PERFIL_EN_USO",
        message: "x",
        details: {
          total: 2,
          usuarios: [
            { id: "u1", nombre: "Ada", email: "ada@erp.cl" },
            { id: "u2", nombre: "Bea", email: "bea@erp.cl" },
            { id: "bad" }, // descartado por falta de campos
          ],
        },
      },
      409
    );
    const details = extractPerfilEnUso(err);
    expect(details).not.toBeNull();
    expect(details?.total).toBe(2);
    expect(details?.usuarios).toHaveLength(2);
    expect(details?.usuarios[0]?.nombre).toBe("Ada");
    expect(details?.usuarios[1]?.email).toBe("bea@erp.cl");
  });

  it("extractPerfilEnUso devuelve null si el código no coincide", () => {
    const err = new ApiError(
      { code: "ERR_OTRO", message: "x", details: { usuarios: [] } },
      400
    );
    expect(extractPerfilEnUso(err)).toBeNull();
  });

  it("ERR_PERMISO_NO_EXISTE y ERR_PERFIL_YA_ACTIVO tienen mensajes amigables", () => {
    const a = new ApiError(
      { code: "ERR_PERMISO_NO_EXISTE", message: "" },
      400
    );
    const b = new ApiError(
      { code: "ERR_PERFIL_YA_ACTIVO", message: "" },
      409
    );
    expect(describeError(a)).toMatch(/permisos seleccionados no existen/i);
    expect(describeError(b)).toMatch(/ya está activo/i);
  });
});

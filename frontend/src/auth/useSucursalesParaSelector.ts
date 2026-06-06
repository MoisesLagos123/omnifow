import { useEffect, useState } from "react";
import { useSucursalesPermitidas } from "./store";
import { sucursalesApi } from "../api/sucursales";

export interface SucursalOpcion {
  id: string;
  codigo: string;
  nombre: string;
}

interface State {
  sucursales: SucursalOpcion[];
  loading: boolean;
  /**
   * `true` cuando el usuario no tiene restricción (lista vacía = Sysadmin) y
   * por lo tanto las sucursales se cargaron desde el API.
   */
  esSysadmin: boolean;
  error: string | null;
}

/**
 * Devuelve las sucursales disponibles para que el usuario opere/seleccione.
 *
 * - Si el usuario tiene una lista explícita (`sucursalesPermitidas.length > 0`),
 *   esa lista es la usada (sin llamadas extra al API).
 * - Si la lista está vacía (semántica "Sysadmin = todas las sucursales"),
 *   carga las sucursales activas del backend para que el usuario pueda
 *   elegir cualquiera.
 */
export function useSucursalesParaSelector(): State {
  const permitidas = useSucursalesPermitidas();
  const [todas, setTodas] = useState<SucursalOpcion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esSysadmin = permitidas.length === 0;

  useEffect(() => {
    if (!esSysadmin) return;
    const ctl = new AbortController();
    setLoading(true);
    setError(null);
    sucursalesApi
      .listSucursales({ activo: true, limit: 200 }, ctl.signal)
      .then((res) => {
        setTodas(
          res.items.map((s) => ({ id: s.id, codigo: s.codigo, nombre: s.nombre })),
        );
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Error al cargar sucursales");
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [esSysadmin]);

  return {
    sucursales: esSysadmin ? todas : permitidas,
    loading,
    esSysadmin,
    error,
  };
}

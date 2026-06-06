import { useEffect, useMemo, useState } from "react";
import { Card } from "../../components/ui/Card";
import { SearchInput } from "../../components/ui/SearchInput";
import { Skeleton } from "../../components/ui/Skeleton";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { adminApi, recursoOf, type Permiso } from "../../api/admin";
import { describeError } from "../../api/errorMessages";
import styles from "./AdminPages.module.css";

export function PermisosPage() {
  const [permisos, setPermisos] = useState<Permiso[] | null>(null);
  const [search, setSearch] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    adminApi
      .listPermisos(ctl.signal)
      .then(setPermisos)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      });
    return () => ctl.abort();
  }, []);

  const grupos = useMemo(() => {
    if (!permisos) return null;
    const q = search.trim().toLowerCase();
    const filtered = q
      ? permisos.filter(
          (p) =>
            p.codigo.toLowerCase().includes(q) ||
            (p.descripcion ?? "").toLowerCase().includes(q)
        )
      : permisos;
    const map = new Map<string, Permiso[]>();
    for (const p of filtered) {
      const recurso = p.recurso ?? recursoOf(p.codigo);
      const arr = map.get(recurso) ?? [];
      arr.push(p);
      map.set(recurso, arr);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [permisos, search]);

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Administración"
        title="Permisos"
        subtitle="Catálogo de permisos disponibles. Estos códigos se asignan a los perfiles."
      />

      <div className={styles.filters}>
        <div className={styles.searchSlot}>
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Buscar por código o descripción..."
            debounceMs={150}
          />
        </div>
      </div>

      {errorMsg && <ErrorAlert>{errorMsg}</ErrorAlert>}

      <Card style={{ padding: "var(--space-4)" }}>
        {!grupos ? (
          <>
            <Skeleton height={20} style={{ marginBottom: 12 }} />
            <Skeleton height={20} style={{ marginBottom: 12 }} />
            <Skeleton height={20} />
          </>
        ) : grupos.length === 0 ? (
          <p className={styles.muted}>Sin resultados.</p>
        ) : (
          grupos.map(([recurso, perms]) => (
            <div key={recurso} className={styles.permGroup}>
              <div className={styles.permGroupHeader}>
                <span>{recurso}</span>
                <span className={styles.permGroupCount}>
                  {perms.length} permisos
                </span>
              </div>
              <div className={styles.permList}>
                {perms.map((p) => (
                  <div key={p.codigo} className={styles.permRow}>
                    <span className={styles.permCode}>{p.codigo}</span>
                    <span className={styles.permDesc}>{p.descripcion}</span>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </Card>
    </div>
  );
}

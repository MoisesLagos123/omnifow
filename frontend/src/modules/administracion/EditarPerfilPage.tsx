import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft } from "lucide-react";

import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Input } from "../../components/ui/Input";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { SearchInput } from "../../components/ui/SearchInput";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import {
  adminApi,
  recursoOf,
  type PerfilDetalle,
  type Permiso,
} from "../../api/admin";
import {
  describeError,
  extractPerfilEnUso,
  type PerfilEnUsoDetails,
} from "../../api/errorMessages";
import { perfilSchema, type PerfilFormValues } from "./schemas";
import { ROUTES } from "../../routePaths";
import styles from "./AdminPages.module.css";

interface Props {
  modo: "crear" | "editar";
}

export function EditarPerfilPage({ modo }: Props) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const [perfil, setPerfil] = useState<PerfilDetalle | null>(null);
  const [permisosCatalog, setPermisosCatalog] = useState<Permiso[]>([]);
  const [seleccion, setSeleccion] = useState<Set<string>>(new Set());
  const [loadError, setLoadError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [enUso, setEnUso] = useState<PerfilEnUsoDetails | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PerfilFormValues>({
    resolver: zodResolver(perfilSchema),
    mode: "onTouched",
    defaultValues: { nombre: "", descripcion: "" },
  });

  useEffect(() => {
    const ctl = new AbortController();
    adminApi
      .listPermisos(ctl.signal)
      .then(setPermisosCatalog)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, []);

  useEffect(() => {
    if (modo !== "editar" || !id) return;
    const ctl = new AbortController();
    adminApi
      .obtenerPerfil(id, ctl.signal)
      .then((p) => {
        setPerfil(p);
        reset({ nombre: p.nombre, descripcion: p.descripcion ?? "" });
        setSeleccion(new Set(p.permisos.map((perm) => perm.id)));
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [modo, id, reset]);

  const grupos = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = q
      ? permisosCatalog.filter(
          (p) =>
            p.codigo.toLowerCase().includes(q) ||
            (p.descripcion ?? "").toLowerCase().includes(q)
        )
      : permisosCatalog;
    const map = new Map<string, Permiso[]>();
    for (const p of filtered) {
      const recurso = p.recurso ?? recursoOf(p.codigo);
      const arr = map.get(recurso) ?? [];
      arr.push(p);
      map.set(recurso, arr);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [permisosCatalog, search]);

  function togglePerm(permId: string) {
    setSeleccion((prev) => {
      const next = new Set(prev);
      if (next.has(permId)) next.delete(permId);
      else next.add(permId);
      return next;
    });
  }

  function toggleGrupo(ids: string[], allSelected: boolean) {
    setSeleccion((prev) => {
      const next = new Set(prev);
      if (allSelected) ids.forEach((i) => next.delete(i));
      else ids.forEach((i) => next.add(i));
      return next;
    });
  }

  function seleccionarTodos() {
    setSeleccion(new Set(permisosCatalog.map((p) => p.id)));
  }

  function limpiarSeleccion() {
    setSeleccion(new Set());
  }

  async function onSubmit(values: PerfilFormValues) {
    setServerError(null);
    setSubmitting(true);
    try {
      if (modo === "crear") {
        const created = await adminApi.crearPerfil({
          nombre: values.nombre,
          descripcion: values.descripcion,
          permiso_ids: Array.from(seleccion),
        });
        toast.success("Perfil creado");
        navigate(ROUTES.ADMIN_PERFIL_DETALLE(created.id), { replace: true });
      } else if (id) {
        const updated = await adminApi.actualizarPerfil(id, {
          nombre: values.nombre,
          descripcion: values.descripcion ?? null,
        });
        const sync = await adminApi.sincronizarPermisosPerfil(
          id,
          Array.from(seleccion)
        );
        setPerfil(sync);
        setSeleccion(new Set(sync.permisos.map((p) => p.id)));
        toast.success("Cambios guardados");
        reset({
          nombre: updated.nombre,
          descripcion: updated.descripcion ?? "",
        });
      }
    } catch (err) {
      setServerError(describeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!id || !perfil) return;
    try {
      await adminApi.eliminarPerfil(id);
      toast.success("Perfil eliminado");
      navigate(ROUTES.ADMIN_PERFILES);
    } catch (err) {
      const details = extractPerfilEnUso(err);
      if (details) {
        setEnUso(details);
      } else {
        toast.error("No se pudo eliminar", describeError(err));
      }
    }
  }

  if (loadError) {
    return (
      <div className={styles.detail}>
        <ErrorAlert>{loadError}</ErrorAlert>
      </div>
    );
  }

  const esSistema = perfil?.es_sistema === true;
  const SISTEMA_TOOLTIP = "El perfil Sysadmin es de sistema y no puede modificarse";

  const totalPermisos = permisosCatalog.length;
  const seleccionados = seleccion.size;

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(ROUTES.ADMIN_PERFILES)}
          leftIcon={<ArrowLeft size={16} />}
        >
          Volver a perfiles
        </Button>
      </div>

      <header>
        <h1 className={styles.title} style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
          {modo === "crear" ? "Crear perfil" : perfil?.nombre ?? "Cargando..."}
          {perfil?.es_sistema && (
            <Badge variant="warning">Sistema (protegido)</Badge>
          )}
        </h1>
        <p className={styles.subtitle}>
          {perfil?.es_sistema
            ? "Este perfil es de sistema y no puede modificarse."
            : "Define los permisos que tendrán los usuarios con este perfil."}
        </p>
      </header>

      <Card className={styles.formCard}>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

          <Input
            label="Nombre"
            error={errors.nombre?.message}
            disabled={esSistema}
            {...register("nombre")}
          />
          <Input
            label="Descripción"
            error={errors.descripcion?.message}
            disabled={esSistema}
            {...register("descripcion")}
          />

          <div>
            <h2 className={styles.sectionTitle}>Permisos</h2>
            <div className={styles.selectionHeader}>
              <span className={styles.selectionCount}>
                <strong>{seleccionados}</strong> de {totalPermisos} permisos
                seleccionados
              </span>
              <div className={styles.selectionActions}>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={seleccionarTodos}
                  disabled={
                    esSistema ||
                    totalPermisos === 0 ||
                    seleccionados === totalPermisos
                  }
                  title={esSistema ? SISTEMA_TOOLTIP : undefined}
                >
                  Seleccionar todos
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={limpiarSeleccion}
                  disabled={esSistema || seleccionados === 0}
                  title={esSistema ? SISTEMA_TOOLTIP : undefined}
                >
                  Limpiar selección
                </Button>
              </div>
            </div>
            <div className={styles.permSearchSlot}>
              <SearchInput
                value={search}
                onChange={setSearch}
                placeholder="Buscar permisos..."
                debounceMs={150}
              />
            </div>

            {grupos.length === 0 ? (
              <p className={styles.muted}>
                {permisosCatalog.length === 0
                  ? "Cargando catálogo de permisos..."
                  : "Sin resultados para tu búsqueda."}
              </p>
            ) : (
              grupos.map(([recurso, perms]) => {
                const ids = perms.map((p) => p.id);
                const allSelected = ids.every((i) => seleccion.has(i));
                return (
                  <div key={recurso} className={styles.permGroup}>
                    <div className={styles.permGroupHeader}>
                      <label
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "var(--space-2)",
                          cursor: "pointer",
                        }}
                      >
                        <input
                          type="checkbox"
                          className={styles.permCheckbox}
                          checked={allSelected}
                          onChange={() => toggleGrupo(ids, allSelected)}
                          disabled={esSistema}
                        />
                        {recurso}
                      </label>
                      <span className={styles.permGroupCount}>
                        {ids.filter((i) => seleccion.has(i)).length}/
                        {ids.length}
                      </span>
                    </div>
                    <div className={styles.permList}>
                      {perms.map((p) => {
                        const checked = seleccion.has(p.id);
                        return (
                          <label key={p.id} className={styles.permRow}>
                            <input
                              type="checkbox"
                              className={styles.permCheckbox}
                              checked={checked}
                              onChange={() => togglePerm(p.id)}
                              disabled={esSistema}
                            />
                            <span className={styles.permCode}>{p.codigo}</span>
                            <span className={styles.permDesc}>
                              {p.descripcion}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className={styles.formActions}>
            <Button
              variant="ghost"
              type="button"
              onClick={() => navigate(ROUTES.ADMIN_PERFILES)}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              loading={submitting}
              disabled={esSistema}
              title={esSistema ? SISTEMA_TOOLTIP : undefined}
            >
              {modo === "crear" ? "Crear perfil" : "Guardar cambios"}
            </Button>
          </div>
        </form>
      </Card>

      {modo === "editar" && perfil && !esSistema && (
        <div className={styles.dangerZone}>
          <div>
            <p className={styles.dangerLabel}>Eliminar perfil</p>
            <p className={styles.dangerHelp}>
              Solo es posible si no hay usuarios con este perfil asignado.
            </p>
          </div>
          <Button
            variant="danger-ghost"
            onClick={() => setConfirmOpen(true)}
          >
            Eliminar
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Eliminar perfil"
        description={
          perfil
            ? `¿Eliminar el perfil "${perfil.nombre}"? Esta acción no se puede deshacer.`
            : ""
        }
        confirmLabel="Eliminar"
        destructive
        onConfirm={handleDelete}
      />

      {enUso && perfil && id && (
        <Modal
          open
          onClose={() => setEnUso(null)}
          title="Perfil en uso"
          description={`No puedes eliminar este perfil porque está asignado a ${enUso.total} usuario(s) activo(s).`}
          footer={
            <>
              <Button variant="ghost" onClick={() => setEnUso(null)}>
                Cerrar
              </Button>
              <Button
                onClick={() => {
                  // TODO: filtro `?perfil_id=` pendiente en UsuariosPage —
                  // mantenemos el link funcional para retomarlo después.
                  navigate(`${ROUTES.ADMIN_USUARIOS}?perfil_id=${id}`);
                  setEnUso(null);
                }}
              >
                Ver usuarios
              </Button>
            </>
          }
        >
          <p
            className={styles.muted}
            style={{ marginBottom: "var(--space-3)" }}
          >
            Usuarios con el perfil <strong>{perfil.nombre}</strong>:
          </p>
          <ul className={styles.enUsoList}>
            {enUso.usuarios.map((u) => (
              <li key={u.id}>
                <strong>{u.nombre}</strong>
                <span className={styles.cellSub}> · {u.email}</span>
              </li>
            ))}
          </ul>
        </Modal>
      )}
    </div>
  );
}
